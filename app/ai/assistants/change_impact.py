"""
SAP Transformation Management Platform
Change Impact Analyzer Assistant - Sprint 12.

Change impact pipeline:
    1. Build project context from program data
    2. Search related artifacts via RAG
    3. Build prompt from YAML template (change_impact.yaml)
    4. Call LLM -> impact analysis
    5. Push result to Suggestion Queue (human-in-the-loop)
"""

import json
import logging
import re

from app.models import db
from app.models.program import Program
from app.models.testing import TestCase
from app.models.integration import Interface
from app.models.backlog import BacklogItem, ConfigItem
from app.models.requirement import Requirement
from app.models.explore import ProcessLevel, ProcessStep

logger = logging.getLogger(__name__)


class ChangeImpactAnalyzer:
    """AI-powered change impact analyzer for SAP transformation programs."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def analyze(
        self,
        change_description: str,
        program_id: int,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        create_suggestion: bool = True,
    ) -> dict:
        """
        Analyze change impact for a program.

        Returns:
            dict: impact_summary, severity, affected_modules, affected_test_cases,
                  affected_interfaces, risks, recommendations, suggestion_id, error
        """
        result = {
            "impact_summary": "",
            "severity": None,
            "affected_modules": [],
            "affected_test_cases": [],
            "affected_interfaces": [],
            "affected_processes": [],
            "risks": [],
            "recommendations": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        if not change_description:
            result["error"] = "change_description is required"
            return result

        program = db.session.get(Program, program_id)
        if not program:
            result["error"] = f"Program {program_id} not found"
            return result

        project_context = self._build_project_context(program_id)
        entity_context = self._build_entity_context(entity_type, entity_id)
        if entity_context:
            project_context = f"{project_context}\n\nSpecific change context:\n{entity_context}"

        related_artifacts = []
        if self.rag:
            try:
                related_artifacts = self.rag.search(
                    query=change_description,
                    program_id=program_id,
                    top_k=5,
                )
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        if related_artifacts:
            project_context += f"\n\nRelated artifacts:\n{json.dumps(related_artifacts[:5], indent=2)}"

        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            messages = self.prompt_registry.render(
                "change_impact",
                change_description=change_description,
                project_context=project_context,
            )
        except KeyError:
            result["error"] = "change_impact prompt template not found"
            return result

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="change_impact",
                program_id=program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "impact_summary": parsed.get("impact_summary", ""),
                "severity": parsed.get("severity"),
                "affected_modules": parsed.get("affected_modules", []),
                "affected_test_cases": parsed.get("affected_test_cases", []),
                "affected_interfaces": parsed.get("affected_interfaces", []),
                "affected_processes": parsed.get("affected_processes", []),
                "risks": parsed.get("risks", []),
                "recommendations": parsed.get("recommendations", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("ChangeImpactAnalyzer LLM call failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        if create_suggestion and self.suggestion_queue:
            try:
                suggestion_entity_type = entity_type or "program"
                suggestion_entity_id = entity_id or program_id
                suggestion = self.suggestion_queue.create(
                    suggestion_type="change_impact",
                    entity_type=suggestion_entity_type,
                    entity_id=suggestion_entity_id,
                    program_id=program_id,
                    title=f"Change impact: {result.get('severity', 'unknown')}",
                    description=result.get("impact_summary", ""),
                    suggestion_data={
                        "affected_modules": result.get("affected_modules", []),
                        "affected_test_cases": result.get("affected_test_cases", []),
                        "affected_interfaces": result.get("affected_interfaces", []),
                        "affected_processes": result.get("affected_processes", []),
                        "risks": result.get("risks", []),
                        "recommendations": result.get("recommendations", []),
                        "confidence": result.get("confidence", 0.0),
                    },
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning=result.get("impact_summary", ""),
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    def _build_project_context(self, program_id: int) -> str:
        modules = set()

        backlog_modules = [
            m[0] for m in db.session.query(BacklogItem.module)
            .filter(BacklogItem.program_id == program_id)
            .distinct().all()
            if m[0]
        ]
        config_modules = [
            m[0] for m in db.session.query(ConfigItem.module)
            .filter(ConfigItem.program_id == program_id)
            .distinct().all()
            if m[0]
        ]
        test_modules = [
            m[0] for m in db.session.query(TestCase.module)
            .filter(TestCase.program_id == program_id)
            .distinct().all()
            if m[0]
        ]
        interface_modules = [
            m[0] for m in db.session.query(Interface.module)
            .filter(Interface.program_id == program_id)
            .distinct().all()
            if m[0]
        ]

        for group in (backlog_modules, config_modules, test_modules, interface_modules):
            modules.update(group)

        test_cases = TestCase.query.filter_by(program_id=program_id).limit(10).all()
        interfaces = Interface.query.filter_by(program_id=program_id).limit(10).all()
        process_levels = ProcessLevel.query.filter_by(project_id=program_id).filter(
            ProcessLevel.level.in_([3, 4])
        ).order_by(ProcessLevel.sort_order).limit(10).all()

        context_lines = [
            f"Modules in use: {', '.join(sorted(modules)) or 'N/A'}",
            f"Test cases (sample): {', '.join([tc.code or tc.title for tc in test_cases]) or 'None'}",
            f"Interfaces (sample): {', '.join([iface.code or iface.name for iface in interfaces]) or 'None'}",
            f"Process steps (sample): {', '.join([pl.name for pl in process_levels]) or 'None'}",
        ]
        return "\n".join(context_lines)

    def _build_entity_context(self, entity_type: str | None, entity_id: int | None) -> str:
        if not entity_type or entity_id is None:
            return ""

        if entity_type == "requirement":
            req = db.session.get(Requirement, entity_id)
            if req:
                return f"Requirement {req.code or req.id}: {req.title}\n{req.description or ''}"

        if entity_type == "config_item":
            cfg = db.session.get(ConfigItem, entity_id)
            if cfg:
                return (
                    f"Config item {cfg.code or cfg.id}: {cfg.title}\n"
                    f"Module: {cfg.module or 'N/A'}\n"
                    f"Config key: {cfg.config_key or 'N/A'}\n"
                    f"Description: {cfg.description or ''}"
                )

        if entity_type == "backlog_item":
            item = db.session.get(BacklogItem, entity_id)
            if item:
                return (
                    f"Backlog item {item.code or item.id}: {item.title}\n"
                    f"Module: {item.module or 'N/A'}\n"
                    f"Type: {item.wricef_type or 'N/A'}\n"
                    f"Description: {item.description or ''}"
                )

        if entity_type == "process_step":
            step = db.session.get(ProcessStep, str(entity_id))
            if step:
                return f"Process step {step.id}: fit_decision={step.fit_decision or 'N/A'}\n{step.notes or ''}"

        if entity_type == "interface":
            iface = db.session.get(Interface, entity_id)
            if iface:
                return (
                    f"Interface {iface.code or iface.id}: {iface.name}\n"
                    f"Protocol: {iface.protocol or 'N/A'}\n"
                    f"Direction: {iface.direction or 'N/A'}\n"
                    f"Description: {iface.description or ''}"
                )

        return ""

    @staticmethod
    def _parse_response(content: str) -> dict:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return {}
        return {}
