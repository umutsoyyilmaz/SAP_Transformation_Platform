"""
SAP Transformation Management Platform
Steering Pack Generator — Sprint 19 (AI Phase 4).

Generates executive steering committee briefing packs from program data:
    - Status summary across all workstreams
    - KPI dashboard highlights
    - Risk/issue escalations
    - Key decisions needed
    - Next steps & milestones
"""

import json
import logging

from app.models import db
from app.models.program import Program

logger = logging.getLogger(__name__)


class SteeringPackGenerator:
    """AI-powered steering committee pack generator."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def generate(
        self,
        program_id: int,
        *,
        period: str = "weekly",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Generate a steering committee briefing pack.

        Args:
            program_id: Program ID to generate pack for
            period: "weekly" | "monthly" | "milestone"
            create_suggestion: Whether to push to suggestion queue

        Returns:
            dict with executive summary, kpis, risks, decisions, next_steps, etc.
        """
        result = {
            "title": "",
            "period": period,
            "program_id": program_id,
            "executive_summary": "",
            "workstream_status": [],
            "kpi_highlights": [],
            "risk_escalations": [],
            "decisions_needed": [],
            "next_steps": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        program = db.session.get(Program, program_id)
        if not program:
            result["error"] = "Program not found"
            return result

        # Build context from program data
        context = self._build_program_context(program)

        # RAG context
        rag_context = ""
        if self.rag:
            try:
                hits = self.rag.search(
                    query=f"steering committee status report for {program.name}",
                    program_id=program_id,
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
                "steering_pack",
                program_name=program.name,
                program_context=context,
                rag_context=rag_context or "No additional context",
                period=period,
            )
        except KeyError:
            messages = self._fallback_prompt(program, context, period)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="steering_pack",
                program_id=program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "title": parsed.get("title", f"Steering Pack — {program.name}"),
                "executive_summary": parsed.get("executive_summary", ""),
                "workstream_status": parsed.get("workstream_status", []),
                "kpi_highlights": parsed.get("kpi_highlights", []),
                "risk_escalations": parsed.get("risk_escalations", []),
                "decisions_needed": parsed.get("decisions_needed", []),
                "next_steps": parsed.get("next_steps", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("SteeringPackGenerator LLM call failed: %s", exc)
            result["error"] = f"AI generation failed: {str(exc)}"
            return result

        # Suggestion queue
        if create_suggestion and self.suggestion_queue and program_id:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="steering_pack",
                    entity_type="program",
                    entity_id=program_id,
                    program_id=program_id,
                    title=result["title"],
                    description=result["executive_summary"][:200],
                    suggestion_data=result,
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-generated steering committee pack",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    def _build_program_context(self, program: Program) -> str:
        """Build text summary of program data for the prompt."""
        parts = [f"Program: {program.name}", f"Status: {program.status or 'N/A'}"]

        # Gather workstreams / backlog stats
        try:
            from app.models.backlog import BacklogItem
            total = BacklogItem.query.filter_by(program_id=program.id).count()
            completed = BacklogItem.query.filter_by(program_id=program.id, status="completed").count()
            parts.append(f"Backlog: {completed}/{total} items completed")
        except Exception:
            pass

        # Risks
        try:
            from app.models.raid import Risk
            open_risks = Risk.query.filter_by(program_id=program.id, status="open").count()
            parts.append(f"Open risks: {open_risks}")
        except Exception:
            pass

        # Issues
        try:
            from app.models.raid import Issue
            open_issues = Issue.query.filter_by(program_id=program.id, status="open").count()
            parts.append(f"Open issues: {open_issues}")
        except Exception:
            pass

        return "\n".join(parts)

    @staticmethod
    def _fallback_prompt(program, context: str, period: str):
        return [
            {"role": "system", "content": (
                "You are an SAP project steering committee document generator. "
                "Generate a structured briefing pack in JSON format with keys: "
                "title, executive_summary, workstream_status (list), kpi_highlights (list), "
                "risk_escalations (list), decisions_needed (list), next_steps (list), confidence."
            )},
            {"role": "user", "content": (
                f"Generate a {period} steering committee pack for:\n{context}"
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
        return {"executive_summary": content, "confidence": 0.5}
