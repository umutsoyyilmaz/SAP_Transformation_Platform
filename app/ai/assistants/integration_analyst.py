"""
SAP Transformation Management Platform
Integration Dependency Analyzer — Sprint 21 (AI Phase 5).

Maps interface dependencies, validates connectivity test coverage,
analyses switch-plan conflicts, and recommends integration testing sequences.
"""

import json
import logging

from app.models import db

logger = logging.getLogger(__name__)


class IntegrationAnalyst:
    """AI-powered integration dependency and switch-plan analysis."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def analyze_dependencies(
        self,
        program_id: int,
        *,
        create_suggestion: bool = True,
    ) -> dict:
        """
        Map all interface dependencies and identify gaps/risks.

        Returns:
            dict with dependency_map, critical_interfaces, gaps, risks, confidence.
        """
        result = {
            "program_id": program_id,
            "dependency_map": [],
            "critical_interfaces": [],
            "coverage_gaps": [],
            "risks": [],
            "recommendations": [],
            "confidence": 0.0,
            "suggestion_id": None,
        }

        context = self._gather_context(program_id)
        prompt = (
            f"Analyze the following SAP integration landscape and map all interface dependencies.\n\n"
            f"Context:\n{json.dumps(context, default=str)}\n\n"
            f"Return JSON with: dependency_map (list of {{source, target, interface, protocol, direction, "
            f"criticality}}), critical_interfaces (list), coverage_gaps (list), "
            f"risks (list), recommendations (list), confidence (float 0-1)."
        )

        messages = [
            {"role": "system", "content": "You are a senior SAP integration architect. JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            if not self.gateway:
                from app.ai.gateway import LLMGateway
                self.gateway = LLMGateway()
            llm_result = self.gateway.chat(messages, purpose="integration_analyst", program_id=program_id)
            parsed = json.loads(llm_result["content"])
            result.update({k: parsed[k] for k in result if k in parsed and k != "suggestion_id"})
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("IntegrationAnalyst: parse error: %s", e)
            result["error"] = f"Parse error: {e}"
        except Exception as e:
            logger.error("IntegrationAnalyst: LLM call failed: %s", e)
            result["error"] = str(e)

        # Push to suggestion queue
        if create_suggestion and self.suggestion_queue and not result.get("error"):
            try:
                suggestion = self.suggestion_queue.push(
                    suggestion_type="integration_dependency_analysis",
                    title="Integration Dependency Map",
                    content=json.dumps(result, default=str),
                    source_entity_type="program",
                    source_entity_id=program_id,
                    confidence=result.get("confidence", 0.0),
                    program_id=program_id,
                )
                result["suggestion_id"] = suggestion.id if suggestion else None
            except Exception:
                pass

        return result

    def validate_switch_plan(
        self,
        program_id: int,
        *,
        switch_plan_id: int | None = None,
    ) -> dict:
        """
        Validate a switch plan for integration conflicts and completeness.

        Returns:
            dict with validation_status, conflicts, missing_steps, recommendations.
        """
        result = {
            "program_id": program_id,
            "switch_plan_id": switch_plan_id,
            "validation_status": "unknown",
            "conflicts": [],
            "missing_steps": [],
            "sequence_issues": [],
            "recommendations": [],
            "confidence": 0.0,
        }

        context = self._gather_context(program_id)
        prompt = (
            f"Validate the following SAP integration switch plan for conflicts and completeness.\n"
            f"Switch plan ID: {switch_plan_id or 'all'}\n\n"
            f"Context:\n{json.dumps(context, default=str)}\n\n"
            f"Return JSON with: validation_status (pass/fail/warning), conflicts (list), "
            f"missing_steps (list), sequence_issues (list), recommendations (list), confidence."
        )

        messages = [
            {"role": "system", "content": "You are an integration testing specialist. JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            if not self.gateway:
                from app.ai.gateway import LLMGateway
                self.gateway = LLMGateway()
            llm_result = self.gateway.chat(messages, purpose="integration_analyst", program_id=program_id)
            parsed = json.loads(llm_result["content"])
            result.update({k: parsed[k] for k in result if k in parsed})
        except Exception as e:
            logger.error("IntegrationAnalyst.validate_switch_plan failed: %s", e)
            result["error"] = str(e)

        return result

    # ── Internal ──────────────────────────────────────────────────────────

    def _gather_context(self, program_id: int) -> dict:
        """Gather integration-relevant entities."""
        context = {"program_id": program_id, "interfaces": [], "waves": [],
                    "connectivity_tests": [], "switch_plans": []}
        try:
            from app.models.integration import Interface
            interfaces = Interface.query.filter_by(program_id=program_id).limit(50).all()
            context["interfaces"] = [
                {"id": i.id, "name": getattr(i, "name", ""),
                 "source_system": getattr(i, "source_system", ""),
                 "target_system": getattr(i, "target_system", ""),
                 "protocol": getattr(i, "protocol", ""),
                 "status": getattr(i, "status", "")}
                for i in interfaces
            ]
        except Exception as e:
            logger.debug("IntegrationAnalyst context (interfaces): %s", e)

        try:
            from app.models.integration import Wave
            waves = Wave.query.filter_by(program_id=program_id).limit(20).all()
            context["waves"] = [
                {"id": w.id, "name": getattr(w, "name", ""),
                 "status": getattr(w, "status", "")}
                for w in waves
            ]
        except Exception as e:
            logger.debug("IntegrationAnalyst context (waves): %s", e)

        try:
            from app.models.integration import ConnectivityTest
            tests = ConnectivityTest.query.limit(30).all()
            context["connectivity_tests"] = [
                {"id": t.id, "interface_id": getattr(t, "interface_id", None),
                 "status": getattr(t, "status", ""),
                 "result": getattr(t, "result", "")}
                for t in tests
            ]
        except Exception as e:
            logger.debug("IntegrationAnalyst context (connectivity): %s", e)

        # RAG context
        if self.rag:
            try:
                hits = self.rag.search("integration dependency interface switch plan", top_k=5)
                context["rag_context"] = [h.get("content", "")[:300] for h in hits]
            except Exception:
                pass

        return context
