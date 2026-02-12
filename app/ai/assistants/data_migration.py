"""
SAP Transformation Management Platform
Data Migration Advisor — Sprint 21 (AI Phase 5).

Analyses DataObject / MigrationWave / LoadCycle entities and recommends:
    - Wave sequencing (dependency-aware ordering)
    - Load time estimates
    - Pre/post load reconciliation checks
    - Migration strategy document generation
"""

import json
import logging

from app.models import db

logger = logging.getLogger(__name__)


class DataMigrationAdvisor:
    """AI-powered data migration planning and advisory assistant."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def analyze(
        self,
        program_id: int,
        *,
        scope: str = "full",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Full migration analysis: wave ordering, risk identification, strategy.

        Args:
            program_id: Program to analyse.
            scope: "full" | "delta" | "initial_load"
            create_suggestion: Push result to suggestion queue.

        Returns:
            dict with strategy, waves, risks, recommendations, confidence.
        """
        result = {
            "program_id": program_id,
            "scope": scope,
            "strategy": "",
            "wave_sequence": [],
            "data_objects": [],
            "risk_areas": [],
            "recommendations": [],
            "estimated_duration_hours": 0,
            "confidence": 0.0,
            "suggestion_id": None,
        }

        # Gather context
        context = self._gather_context(program_id)

        # Build prompt
        prompt_text = self._build_prompt(context, scope)

        messages = [
            {"role": "system", "content": "You are a senior SAP data migration specialist. "
             "Respond in valid JSON only."},
            {"role": "user", "content": prompt_text},
        ]

        try:
            if not self.gateway:
                from app.ai.gateway import LLMGateway
                self.gateway = LLMGateway()

            llm_result = self.gateway.chat(
                messages,
                purpose="data_migration",
                program_id=program_id,
            )
            parsed = json.loads(llm_result["content"])
            result.update({
                "strategy": parsed.get("strategy", ""),
                "wave_sequence": parsed.get("wave_sequence", []),
                "data_objects": parsed.get("data_objects", []),
                "risk_areas": parsed.get("risk_areas", []),
                "recommendations": parsed.get("recommendations", []),
                "estimated_duration_hours": parsed.get("estimated_duration_hours", 0),
                "confidence": parsed.get("confidence", 0.0),
            })
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("DataMigrationAdvisor: Failed to parse LLM response: %s", e)
            result["error"] = f"Parse error: {e}"
        except Exception as e:
            logger.error("DataMigrationAdvisor: LLM call failed: %s", e)
            result["error"] = str(e)

        # Push to suggestion queue
        if create_suggestion and self.suggestion_queue and not result.get("error"):
            try:
                suggestion = self.suggestion_queue.push(
                    suggestion_type="data_migration_analysis",
                    title=f"Data Migration Strategy — {scope}",
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

    def optimize_waves(
        self,
        program_id: int,
        *,
        max_parallel: int = 3,
    ) -> dict:
        """
        Optimise migration wave sequencing for minimal downtime.

        Returns:
            dict with optimized_sequence, parallel_groups, critical_path, est_hours.
        """
        result = {
            "program_id": program_id,
            "optimized_sequence": [],
            "parallel_groups": [],
            "critical_path": [],
            "estimated_hours": 0,
            "confidence": 0.0,
        }

        context = self._gather_context(program_id)
        prompt = (
            f"Optimise the following SAP data migration wave sequence for minimal downtime.\n"
            f"Max parallel streams: {max_parallel}\n\n"
            f"Context:\n{json.dumps(context, default=str)}\n\n"
            f"Return JSON with: optimized_sequence (list), parallel_groups (list of lists), "
            f"critical_path (list), estimated_hours (int), confidence (float)."
        )

        messages = [
            {"role": "system", "content": "You are a data migration optimization expert. JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            if not self.gateway:
                from app.ai.gateway import LLMGateway
                self.gateway = LLMGateway()
            llm_result = self.gateway.chat(messages, purpose="data_migration", program_id=program_id)
            parsed = json.loads(llm_result["content"])
            result.update({k: parsed[k] for k in result if k in parsed})
        except Exception as e:
            logger.error("DataMigrationAdvisor.optimize_waves failed: %s", e)
            result["error"] = str(e)

        return result

    def reconciliation_check(
        self,
        program_id: int,
        *,
        data_object: str = "",
    ) -> dict:
        """
        Generate reconciliation checklist for a data object or full program.

        Returns:
            dict with checks (list), summary, pass_rate, recommendations.
        """
        result = {
            "program_id": program_id,
            "data_object": data_object,
            "checks": [],
            "summary": "",
            "pass_rate_pct": 0.0,
            "recommendations": [],
            "confidence": 0.0,
        }

        context = self._gather_context(program_id)
        prompt = (
            f"Generate a reconciliation checklist for SAP data migration.\n"
            f"Data object focus: {data_object or 'all'}\n\n"
            f"Context:\n{json.dumps(context, default=str)}\n\n"
            f"Return JSON with: checks (list of {{name, category, description, validation_query}}), "
            f"summary, pass_rate_pct, recommendations (list), confidence."
        )

        messages = [
            {"role": "system", "content": "You are a data migration reconciliation specialist. JSON only."},
            {"role": "user", "content": prompt},
        ]

        try:
            if not self.gateway:
                from app.ai.gateway import LLMGateway
                self.gateway = LLMGateway()
            llm_result = self.gateway.chat(messages, purpose="data_migration", program_id=program_id)
            parsed = json.loads(llm_result["content"])
            result.update({k: parsed[k] for k in result if k in parsed})
        except Exception as e:
            logger.error("DataMigrationAdvisor.reconciliation_check failed: %s", e)
            result["error"] = str(e)

        return result

    # ── Internal ──────────────────────────────────────────────────────────

    def _gather_context(self, program_id: int) -> dict:
        """Gather migration-relevant entities from the DB."""
        context = {"program_id": program_id, "data_objects": [], "waves": [], "load_cycles": []}
        try:
            from app.models.data_factory import DataObject, MigrationWave, LoadCycle
            objs = DataObject.query.filter_by(program_id=program_id).limit(50).all()
            context["data_objects"] = [
                {"id": o.id, "name": getattr(o, "name", ""), "object_type": getattr(o, "object_type", ""),
                 "status": getattr(o, "status", "")}
                for o in objs
            ]
            waves = MigrationWave.query.filter_by(program_id=program_id).limit(20).all()
            context["waves"] = [
                {"id": w.id, "name": getattr(w, "name", ""), "sequence": getattr(w, "sequence", 0),
                 "status": getattr(w, "status", "")}
                for w in waves
            ]
            cycles = LoadCycle.query.limit(30).all()
            context["load_cycles"] = [
                {"id": c.id, "name": getattr(c, "name", ""), "status": getattr(c, "status", "")}
                for c in cycles
            ]
        except Exception as e:
            logger.debug("DataMigrationAdvisor context: %s", e)

        # RAG search
        if self.rag:
            try:
                hits = self.rag.search("data migration wave sequencing", top_k=5)
                context["rag_context"] = [h.get("content", "")[:300] for h in hits]
            except Exception:
                pass

        return context

    def _build_prompt(self, context: dict, scope: str) -> str:
        """Build the full analysis prompt."""
        if self.prompt_registry:
            try:
                return self.prompt_registry.render(
                    "data_migration",
                    context=json.dumps(context, default=str),
                    scope=scope,
                )
            except Exception:
                pass

        return (
            f"Analyze the following SAP data migration context and provide a comprehensive "
            f"migration strategy.\n\nScope: {scope}\n\n"
            f"Context:\n{json.dumps(context, default=str)}\n\n"
            f"Return JSON with: strategy (string), wave_sequence (list of wave objects), "
            f"data_objects (list), risk_areas (list), recommendations (list), "
            f"estimated_duration_hours (int), confidence (float 0-1)."
        )
