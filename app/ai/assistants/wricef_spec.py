"""
SAP Transformation Management Platform
WRICEF Spec Drafter — Sprint 19 (AI Phase 4).

Generates functional specification documents from BacklogItem/WRICEF data:
    - Technical overview
    - Functional requirements
    - Integration points
    - Data mapping
    - Test approach
"""

import json
import logging

from app.models import db

logger = logging.getLogger(__name__)


class WRICEFSpecDrafter:
    """AI-powered WRICEF functional spec document generator."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def generate(
        self,
        backlog_item_id: int,
        *,
        spec_type: str = "functional",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Generate a functional spec from a backlog item.

        Args:
            backlog_item_id: BacklogItem ID to draft spec for
            spec_type: "functional" | "technical" | "integration"
            create_suggestion: Whether to push to suggestion queue

        Returns:
            dict with title, overview, requirements, integrations, data_mapping, test_approach, etc.
        """
        result = {
            "title": "",
            "spec_type": spec_type,
            "backlog_item_id": backlog_item_id,
            "overview": "",
            "functional_requirements": [],
            "technical_details": "",
            "integration_points": [],
            "data_mapping": [],
            "test_approach": "",
            "assumptions": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        from app.models.backlog import BacklogItem
        item = db.session.get(BacklogItem, backlog_item_id)
        if not item:
            result["error"] = "Backlog item not found"
            return result

        # Build context
        context = self._build_item_context(item)

        # RAG context
        rag_context = ""
        if self.rag:
            try:
                hits = self.rag.search(
                    query=f"WRICEF specification for {item.title}",
                    program_id=item.program_id,
                    top_k=5,
                )
                if hits:
                    rag_context = json.dumps(hits[:5], indent=2)
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        # Build prompt
        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            messages = self.prompt_registry.render(
                "wricef_spec",
                item_title=item.title,
                item_context=context,
                spec_type=spec_type,
                rag_context=rag_context or "No additional context",
            )
        except KeyError:
            messages = self._fallback_prompt(item, context, spec_type)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="wricef_spec",
                program_id=item.program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "title": parsed.get("title", f"Spec — {item.title}"),
                "overview": parsed.get("overview", ""),
                "functional_requirements": parsed.get("functional_requirements", []),
                "technical_details": parsed.get("technical_details", ""),
                "integration_points": parsed.get("integration_points", []),
                "data_mapping": parsed.get("data_mapping", []),
                "test_approach": parsed.get("test_approach", ""),
                "assumptions": parsed.get("assumptions", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("WRICEFSpecDrafter LLM call failed: %s", exc)
            result["error"] = f"AI generation failed: {str(exc)}"
            return result

        # Suggestion queue
        if create_suggestion and self.suggestion_queue and item.program_id:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="wricef_spec",
                    entity_type="backlog_item",
                    entity_id=backlog_item_id,
                    program_id=item.program_id,
                    title=result["title"],
                    description=result["overview"][:200],
                    suggestion_data=result,
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-generated WRICEF specification",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    @staticmethod
    def _build_item_context(item) -> str:
        """Build text summary of backlog item for the prompt."""
        parts = [
            f"Title: {item.title}",
            f"Type: {getattr(item, 'object_type', 'N/A')}",
            f"Module: {getattr(item, 'module', 'N/A')}",
            f"Status: {item.status}",
            f"Priority: {getattr(item, 'priority', 'N/A')}",
        ]
        if getattr(item, "description", None):
            parts.append(f"Description: {item.description[:500]}")
        if getattr(item, "classification", None):
            parts.append(f"Classification: {item.classification}")
        return "\n".join(parts)

    @staticmethod
    def _fallback_prompt(item, context: str, spec_type: str):
        return [
            {"role": "system", "content": (
                "You are an SAP WRICEF (Workflow, Report, Interface, Conversion, Enhancement, Form) "
                "specification document writer. Generate a structured spec in JSON format with keys: "
                "title, overview, functional_requirements (list), technical_details, "
                "integration_points (list), data_mapping (list), test_approach, assumptions (list), confidence."
            )},
            {"role": "user", "content": (
                f"Generate a {spec_type} specification for this backlog item:\n{context}"
            )},
        ]

    @staticmethod
    def _parse_response(content: str) -> dict:
        """Parse JSON response from LLM."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
        return {"overview": content, "confidence": 0.5}
