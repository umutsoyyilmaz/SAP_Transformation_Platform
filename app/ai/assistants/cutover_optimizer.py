"""
SAP Transformation Management Platform
Cutover Optimizer Assistant — Sprint 15 (AI Phase 3).

Two capabilities:
    1. optimize_runbook — Analyze runbook timing, identify bottlenecks, suggest parallelisation
    2. assess_go_nogo   — AI-driven go/no-go readiness assessment with cross-domain signals

Pipeline:
    1. Load cutover plan, tasks, dependencies, rehearsals from DB
    2. RAG search for relevant project context
    3. Build prompt from YAML template (cutover_optimizer.yaml)
    4. Call LLM → structured JSON response
    5. Push result to SuggestionQueue (human-in-the-loop)
"""

import json
import logging
import re

from app.models import db
from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    RunbookTask,
    TaskDependency,
    Rehearsal,
    GoNoGoItem,
    HypercareIncident,
)
from app.models.program import Program

logger = logging.getLogger(__name__)


class CutoverOptimizer:
    """AI-powered cutover runbook optimiser and go/no-go assessor."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    # ── Runbook Optimisation ───────────────────────────────────────────────

    def optimize_runbook(self, plan_id: int, *, create_suggestion: bool = True) -> dict:
        """
        Analyse a cutover plan's runbook and provide optimisation recommendations.

        Returns:
            dict with keys: critical_path, bottlenecks, parallel_opportunities,
                  estimated_duration_hours, risk_areas, recommendations,
                  confidence, suggestion_id, error
        """
        result = {
            "critical_path": [],
            "bottlenecks": [],
            "parallel_opportunities": [],
            "estimated_duration_hours": None,
            "risk_areas": [],
            "recommendations": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        plan = db.session.get(CutoverPlan, plan_id)
        if not plan:
            result["error"] = f"CutoverPlan {plan_id} not found"
            return result

        context = self._build_runbook_context(plan)
        if not context.get("tasks"):
            result["error"] = "No runbook tasks found for this plan"
            return result

        # RAG enrichment
        rag_context = ""
        if self.rag:
            try:
                hits = self.rag.search(
                    query=f"cutover runbook optimization {plan.name}",
                    program_id=plan.program_id,
                    top_k=5,
                )
                if hits:
                    rag_context = f"\nRelated artifacts:\n{json.dumps(hits[:5], indent=2)}"
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        # Build prompt
        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        prompt_context = json.dumps(context, indent=2, default=str)
        try:
            messages = self.prompt_registry.render(
                "cutover_optimizer",
                plan_title=plan.name or f"Plan #{plan.id}",
                plan_status=plan.status,
                runbook_context=prompt_context + rag_context,
                task_count=str(len(context["tasks"])),
                dependency_count=str(len(context["dependencies"])),
                rehearsal_count=str(len(context["rehearsals"])),
            )
        except KeyError:
            # Fallback inline prompt
            messages = self._fallback_optimize_prompt(plan, context, rag_context)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="cutover_optimizer",
                program_id=plan.program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "critical_path": parsed.get("critical_path", []),
                "bottlenecks": parsed.get("bottlenecks", []),
                "parallel_opportunities": parsed.get("parallel_opportunities", []),
                "estimated_duration_hours": parsed.get("estimated_duration_hours"),
                "risk_areas": parsed.get("risk_areas", []),
                "recommendations": parsed.get("recommendations", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("CutoverOptimizer LLM call failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        if create_suggestion and self.suggestion_queue:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="cutover_optimization",
                    entity_type="cutover_plan",
                    entity_id=plan_id,
                    program_id=plan.program_id,
                    title=f"Runbook optimization for {plan.code or plan.name}",
                    description="; ".join(result.get("recommendations", [])[:3]),
                    suggestion_data={
                        "critical_path": result["critical_path"],
                        "bottlenecks": result["bottlenecks"],
                        "parallel_opportunities": result["parallel_opportunities"],
                        "estimated_duration_hours": result["estimated_duration_hours"],
                        "risk_areas": result["risk_areas"],
                        "recommendations": result["recommendations"],
                    },
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="Cutover runbook analysis and optimisation",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    # ── Go / No-Go AI Assessment ──────────────────────────────────────────

    def assess_go_nogo(self, plan_id: int, *, create_suggestion: bool = True) -> dict:
        """
        AI-driven go/no-go readiness assessment based on checklist items,
        rehearsal outcomes, and cross-domain project signals.

        Returns:
            dict with keys: verdict, readiness_score, risk_factors,
                  blocking_items, recommendations, confidence,
                  suggestion_id, error
        """
        result = {
            "verdict": None,          # "go" | "no_go" | "conditional_go"
            "readiness_score": 0.0,    # 0-100
            "risk_factors": [],
            "blocking_items": [],
            "recommendations": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        plan = db.session.get(CutoverPlan, plan_id)
        if not plan:
            result["error"] = f"CutoverPlan {plan_id} not found"
            return result

        context = self._build_gonogo_context(plan)

        rag_context = ""
        if self.rag:
            try:
                hits = self.rag.search(
                    query=f"go-live readiness assessment {plan.name}",
                    program_id=plan.program_id,
                    top_k=5,
                )
                if hits:
                    rag_context = f"\nRelated artifacts:\n{json.dumps(hits[:5], indent=2)}"
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        prompt_context = json.dumps(context, indent=2, default=str)
        try:
            messages = self.prompt_registry.render(
                "cutover_gonogo",
                plan_title=plan.name or f"Plan #{plan.id}",
                plan_status=plan.status,
                gonogo_context=prompt_context + rag_context,
                checklist_count=str(len(context["checklist_items"])),
                rehearsal_count=str(len(context["rehearsals"])),
            )
        except KeyError:
            messages = self._fallback_gonogo_prompt(plan, context, rag_context)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="cutover_gonogo",
                program_id=plan.program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "verdict": parsed.get("verdict"),
                "readiness_score": parsed.get("readiness_score", 0.0),
                "risk_factors": parsed.get("risk_factors", []),
                "blocking_items": parsed.get("blocking_items", []),
                "recommendations": parsed.get("recommendations", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("CutoverOptimizer go/no-go LLM call failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        if create_suggestion and self.suggestion_queue:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="cutover_gonogo",
                    entity_type="cutover_plan",
                    entity_id=plan_id,
                    program_id=plan.program_id,
                    title=f"Go/No-Go: {result.get('verdict', 'unknown')} — {plan.code or plan.name}",
                    description=f"Score: {result.get('readiness_score', 0)}/100",
                    suggestion_data={
                        "verdict": result["verdict"],
                        "readiness_score": result["readiness_score"],
                        "risk_factors": result["risk_factors"],
                        "blocking_items": result["blocking_items"],
                        "recommendations": result["recommendations"],
                    },
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-driven go/no-go readiness assessment",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    # ── Context builders ──────────────────────────────────────────────────

    def _build_runbook_context(self, plan: CutoverPlan) -> dict:
        """Build structured context from cutover plan's runbook data."""
        scope_items = CutoverScopeItem.query.filter_by(cutover_plan_id=plan.id).all()
        scope_ids = [s.id for s in scope_items]

        tasks = RunbookTask.query.filter(
            RunbookTask.scope_item_id.in_(scope_ids)
        ).order_by(RunbookTask.sequence).all() if scope_ids else []

        task_ids = [t.id for t in tasks]
        deps = TaskDependency.query.filter(
            TaskDependency.predecessor_id.in_(task_ids) | TaskDependency.successor_id.in_(task_ids)
        ).all() if task_ids else []

        rehearsals = Rehearsal.query.filter_by(cutover_plan_id=plan.id).all()

        return {
            "plan": {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "status": plan.status,
                "planned_start": str(plan.planned_start) if plan.planned_start else None,
                "planned_end": str(plan.planned_end) if plan.planned_end else None,
                "actual_start": str(plan.actual_start) if plan.actual_start else None,
                "actual_end": str(plan.actual_end) if plan.actual_end else None,
            },
            "scope_items": [
                {"id": s.id, "category": s.category, "name": s.name, "status": s._compute_status()}
                for s in scope_items
            ],
            "tasks": [
                {
                    "id": t.id,
                    "code": t.code,
                    "title": t.title,
                    "sequence": t.sequence,
                    "status": t.status,
                    "planned_start": str(t.planned_start) if t.planned_start else None,
                    "planned_end": str(t.planned_end) if t.planned_end else None,
                    "actual_start": str(t.actual_start) if t.actual_start else None,
                    "actual_end": str(t.actual_end) if t.actual_end else None,
                    "planned_duration_min": t.planned_duration_min,
                    "responsible": t.responsible,
                    "accountable": t.accountable,
                    "rollback_action": t.rollback_action,
                    "scope_item_id": t.scope_item_id,
                }
                for t in tasks
            ],
            "dependencies": [
                {
                    "predecessor_id": d.predecessor_id,
                    "successor_id": d.successor_id,
                    "dependency_type": d.dependency_type,
                    "lag_minutes": d.lag_minutes,
                }
                for d in deps
            ],
            "rehearsals": [
                {
                    "id": r.id,
                    "rehearsal_number": r.rehearsal_number,
                    "name": r.name,
                    "status": r.status,
                    "planned_duration_min": r.planned_duration_min,
                    "actual_duration_min": r.actual_duration_min,
                    "duration_variance_pct": r.duration_variance_pct,
                    "runbook_revision_needed": r.runbook_revision_needed,
                    "findings_summary": r.findings_summary,
                }
                for r in rehearsals
            ],
        }

    def _build_gonogo_context(self, plan: CutoverPlan) -> dict:
        """Build context for go/no-go assessment."""
        checklist = GoNoGoItem.query.filter_by(cutover_plan_id=plan.id).all()
        rehearsals = Rehearsal.query.filter_by(cutover_plan_id=plan.id).all()
        incidents = HypercareIncident.query.filter_by(cutover_plan_id=plan.id).all()

        scope_items = CutoverScopeItem.query.filter_by(cutover_plan_id=plan.id).all()
        scope_ids = [s.id for s in scope_items]
        tasks = RunbookTask.query.filter(
            RunbookTask.scope_item_id.in_(scope_ids)
        ).all() if scope_ids else []
        task_stats = {}
        for t in tasks:
            task_stats[t.status] = task_stats.get(t.status, 0) + 1

        return {
            "plan": {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "status": plan.status,
                "planned_start": str(plan.planned_start) if plan.planned_start else None,
                "planned_end": str(plan.planned_end) if plan.planned_end else None,
            },
            "checklist_items": [
                {
                    "id": g.id,
                    "source_domain": g.source_domain,
                    "criterion": g.criterion,
                    "verdict": g.verdict,
                    "evidence": g.evidence,
                }
                for g in checklist
            ],
            "rehearsals": [
                {
                    "id": r.id,
                    "rehearsal_number": r.rehearsal_number,
                    "status": r.status,
                    "duration_variance_pct": r.duration_variance_pct,
                    "runbook_revision_needed": r.runbook_revision_needed,
                    "findings_summary": r.findings_summary,
                }
                for r in rehearsals
            ],
            "task_status_summary": task_stats,
            "total_tasks": len(tasks),
            "open_incidents": len([i for i in incidents if i.status in ("open", "investigating")]),
            "total_incidents": len(incidents),
        }

    # ── Fallback prompts (when YAML not found) ───────────────────────────

    def _fallback_optimize_prompt(self, plan, context, rag_context):
        system = (
            "You are an SAP cutover specialist with deep expertise in runbook "
            "optimization, critical path analysis, and go-live planning.\n\n"
            "Analyze the cutover runbook and provide optimization recommendations.\n"
            "Return valid JSON with these keys:\n"
            "{\n"
            '  "critical_path": [{"task_id": int, "task_title": str, "reason": str}],\n'
            '  "bottlenecks": [{"task_id": int, "description": str, "severity": "high"|"medium"|"low"}],\n'
            '  "parallel_opportunities": [{"tasks": [int], "description": str, "time_saved_min": int}],\n'
            '  "estimated_duration_hours": float,\n'
            '  "risk_areas": [{"area": str, "description": str, "mitigation": str}],\n'
            '  "recommendations": [str],\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )
        user = (
            f"Analyze this cutover runbook for: {plan.name or plan.code}\n"
            f"Status: {plan.status}\n\n"
            f"Runbook data:\n{json.dumps(context, indent=2, default=str)}"
            f"{rag_context}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _fallback_gonogo_prompt(self, plan, context, rag_context):
        system = (
            "You are an SAP go-live readiness assessor. Evaluate all checklist items, "
            "rehearsal outcomes, and project signals to make a go/no-go recommendation.\n\n"
            "Return valid JSON with these keys:\n"
            "{\n"
            '  "verdict": "go"|"no_go"|"conditional_go",\n'
            '  "readiness_score": 0-100,\n'
            '  "risk_factors": [{"factor": str, "severity": "high"|"medium"|"low", "description": str}],\n'
            '  "blocking_items": [{"item": str, "reason": str}],\n'
            '  "recommendations": [str],\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )
        user = (
            f"Assess go/no-go readiness for: {plan.name or plan.code}\n"
            f"Status: {plan.status}\n\n"
            f"Assessment data:\n{json.dumps(context, indent=2, default=str)}"
            f"{rag_context}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── Response parser ───────────────────────────────────────────────────

    @staticmethod
    def _parse_response(content: str) -> dict:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
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
