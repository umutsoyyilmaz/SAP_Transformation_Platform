"""
SAP Transformation Management Platform
Test Case Generator Assistant - Sprint 12.

Test case generation pipeline:
    1. Load requirement or process step details
    2. Search similar test cases via RAG embeddings
    3. Build prompt from YAML template (test_case_generator.yaml)
    4. Call LLM -> test case suggestions
    5. Parse JSON response -> list of test case dicts
    6. Push results to Suggestion Queue (human-in-the-loop)
"""

import json
import logging
import re

from app.models import db
from app.models.requirement import Requirement
from app.models.explore import ProcessStep, ExploreWorkshop, ProcessLevel

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """AI-powered test case generator for requirements or process steps."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def generate(
        self,
        requirement_id: int | None = None,
        process_step: str | None = None,
        *,
        module: str = "FI",
        test_layer: str = "sit",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Generate test case suggestions from a requirement or process step.

        Returns:
            dict: test_cases, source_type, source_id, suggestion_ids, error
        """
        result = {
            "test_cases": [],
            "source_type": None,
            "source_id": None,
            "suggestion_ids": [],
            "error": None,
        }

        source_context = ""
        additional_context = ""
        program_id = None

        if requirement_id:
            req = db.session.get(Requirement, requirement_id)
            if not req:
                result["error"] = f"Requirement {requirement_id} not found"
                return result
            result["source_type"] = "requirement"
            result["source_id"] = requirement_id
            program_id = req.program_id
            if not module:
                module = req.module or "FI"
            source_context = f"[{req.code or 'REQ'}] {req.title}\n{req.description or ''}"
            if req.acceptance_criteria:
                additional_context = f"Acceptance criteria: {req.acceptance_criteria}"
        elif process_step:
            step = db.session.get(ProcessStep, process_step)
            if not step:
                result["error"] = f"Process step {process_step} not found"
                return result
            result["source_type"] = "process_step"
            result["source_id"] = process_step

            workshop = db.session.get(ExploreWorkshop, step.workshop_id)
            process_level = db.session.get(ProcessLevel, step.process_level_id)
            program_id = workshop.project_id if workshop else None
            if not module:
                module = process_level.process_area_code if process_level else "FI"

            step_name = process_level.name if process_level else "Process Step"
            source_context = f"{step_name}\nNotes: {step.notes or 'No notes'}"
            additional_context = (
                f"Fit decision: {step.fit_decision or 'not assessed'}; "
                f"Demo shown: {step.demo_shown}; BPMN reviewed: {step.bpmn_reviewed}"
            )
        else:
            result["error"] = "requirement_id or process_step is required"
            return result

        similar = []
        if self.rag:
            try:
                search_text = f"{source_context} {additional_context}".strip()
                similar = self.rag.search(
                    query=search_text,
                    program_id=program_id,
                    entity_type="test_case",
                    module=module,
                    top_k=5,
                )
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            extra_context = additional_context
            if similar:
                similar_block = f"Similar test cases:\n{json.dumps(similar[:3], indent=2)}"
                extra_context = f"{extra_context}\n{similar_block}" if extra_context else similar_block

            messages = self.prompt_registry.render(
                "test_case_generator",
                source_context=source_context,
                module=module,
                test_layer=test_layer,
                additional_context=extra_context,
            )
        except KeyError:
            result["error"] = "test_case_generator prompt template not found"
            return result

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="test_case_generator",
                program_id=program_id,
            )
            test_cases = self._parse_response(llm_response.get("content", ""))
            result["test_cases"] = test_cases
        except Exception as exc:
            logger.error("TestCaseGenerator LLM call failed: %s", exc)
            result["error"] = f"AI generation failed: {str(exc)}"
            return result

        if create_suggestion and self.suggestion_queue and result["test_cases"]:
            for tc in result["test_cases"]:
                try:
                    suggestion = self.suggestion_queue.create(
                        suggestion_type="test_case_generation",
                        entity_type=result["source_type"],
                        entity_id=result["source_id"],
                        program_id=program_id,
                        title=f"Test Case: {tc.get('title', 'Untitled')}",
                        description=tc.get("expected_outcome", ""),
                        suggestion_data=tc,
                        confidence=tc.get("confidence", 0.5),
                        model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                        prompt_version="v1",
                        reasoning=tc.get("reasoning", ""),
                    )
                    result["suggestion_ids"].append(suggestion.id)
                except Exception as exc:
                    logger.warning("Failed to create suggestion: %s", exc)

        return result

    @staticmethod
    def _parse_response(content: str) -> list[dict]:
        """Parse LLM response into a list of test cases."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return []
        return []
