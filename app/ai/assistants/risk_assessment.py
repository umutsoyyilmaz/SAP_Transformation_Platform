"""
SAP Transformation Management Platform
Risk Assessment Assistant - Sprint 12 (Task 12a.1).

Risk assessment pipeline:
    1. Gather project signals (stats from all modules)
    2. Search similar past risks via RAG
    3. Build prompt from YAML template (risk_assessment.yaml)
    4. Call LLM -> identify new risks with probability x impact scoring
    5. Push results to Suggestion Queue (human-in-the-loop)

Architecture ref: 10.6 - AI Assistants
"""

import json
import logging
from typing import Any

from app.models import db
from app.models.program import Program
from app.models.raid import Risk, Action, Issue
from app.models.testing import TestCase, Defect
from app.models.backlog import BacklogItem

logger = logging.getLogger(__name__)


class RiskAssessment:
    """
    AI-powered project risk assessment.

    Analyzes project data signals to proactively identify risks:
    - Backlog growth rate -> scope creep
    - Defect aging and S1 count -> testing bottleneck
    - Overdue actions -> resource constraints
    - Interface failure rate -> integration risk
    - Timeline proximity -> go-live readiness
    """

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def assess(self, program_id: int, *, create_suggestion: bool = True) -> dict:
        """
        Run risk assessment for a program.

        Gathers signals from all modules, calls LLM for pattern matching,
        returns identified risks with scoring.

        Returns:
            dict: risks (list), signal_summary, confidence, suggestion_ids, error
        """
        result = {
            "program_id": program_id,
            "risks": [],
            "signal_summary": {},
            "error": None,
        }

        try:
            signals = self._gather_signals(program_id)
            result["signal_summary"] = signals

            if not signals:
                result["error"] = "No data found for this program"
                return result

            similar_risks = []
            if self.rag:
                try:
                    signal_text = json.dumps(signals, indent=2)
                    hits = self.rag.search(signal_text, top_k=5, entity_types=["risk"])
                    similar_risks = [
                        {"content": h.get("content", ""), "score": round(h.get("score", 0), 3)}
                        for h in hits
                    ]
                except Exception as exc:
                    logger.warning("RAG search failed: %s", exc)

            if not self.prompt_registry:
                result["error"] = "Prompt registry not available"
                return result

            template = self.prompt_registry.get("risk_assessment")
            if not template:
                result["error"] = "risk_assessment prompt template not found"
                return result

            program = db.session.get(Program, program_id)
            program_context = ""
            if program:
                program_context = (
                    f"Program: {program.name}\n"
                    f"Type: {program.project_type}\n"
                    f"Methodology: {program.methodology}\n"
                    f"SAP Product: {program.sap_product}\n"
                    f"Go-Live: {program.go_live_date or 'Not set'}\n"
                )
            if similar_risks:
                program_context += f"\nSimilar past risks:\n{json.dumps(similar_risks[:3], indent=2)}"

            rendered = template.render(
                project_signals=json.dumps(signals, indent=2),
                program_context=program_context,
            )

            if not self.gateway:
                result["error"] = "LLM Gateway not available"
                return result

            messages = [
                {"role": "system", "content": rendered["system"]},
                {"role": "user", "content": rendered["user"]},
            ]

            llm_result = self.gateway.chat(
                messages,
                temperature=0.3,
                max_tokens=2000,
                metadata={"assistant": "risk_assessment", "program_id": program_id},
            )

            content = llm_result.get("content", "")
            try:
                import re

                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    risks = json.loads(json_match.group())
                else:
                    risks = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse risk assessment response")
                risks = []

            result["risks"] = risks

            if create_suggestion and self.suggestion_queue and risks:
                for risk in risks[:5]:
                    try:
                        suggestion = self.suggestion_queue.push(
                            suggestion_type="risk_assessment",
                            entity_type="risk",
                            entity_id=program_id,
                            title=f"AI Risk: {risk.get('title', 'Unknown')}",
                            body=json.dumps(risk),
                            confidence=risk.get("confidence", 0.5),
                            source_assistant="risk_assessment",
                        )
                        if suggestion:
                            result.setdefault("suggestion_ids", []).append(suggestion.id)
                    except Exception as exc:
                        logger.warning("Failed to create suggestion: %s", exc)

        except Exception as exc:
            logger.exception("Risk assessment failed for program %s", program_id)
            result["error"] = str(exc)

        return result

    def _gather_signals(self, program_id: int) -> dict:
        """Collect project signals from all modules."""
        from datetime import date

        pid = program_id
        signals = {}

        total_items = BacklogItem.query.filter_by(program_id=pid).count()
        done_items = BacklogItem.query.filter_by(program_id=pid).filter(
            BacklogItem.status.in_(["done", "deployed"])
        ).count()
        signals["backlog"] = {
            "total": total_items,
            "done": done_items,
            "completion_pct": round(done_items / total_items * 100) if total_items else 0,
        }

        total_defects = Defect.query.filter_by(program_id=pid).count()
        open_defects = Defect.query.filter_by(program_id=pid).filter(
            Defect.status.notin_(["closed", "rejected", "resolved"])
        ).count()
        s1_open = Defect.query.filter_by(program_id=pid, severity="S1").filter(
            Defect.status.notin_(["closed", "rejected", "resolved"])
        ).count()
        signals["testing"] = {
            "total_defects": total_defects,
            "open_defects": open_defects,
            "s1_open": s1_open,
            "test_cases": TestCase.query.filter_by(program_id=pid).count(),
        }

        open_risks = Risk.query.filter_by(program_id=pid).filter(
            Risk.status.notin_(["closed", "expired"])
        ).count()
        red_risks = Risk.query.filter_by(program_id=pid, rag_status="red").filter(
            Risk.status.notin_(["closed", "expired"])
        ).count()
        overdue_actions = Action.query.filter_by(program_id=pid).filter(
            Action.status.in_(["open", "in_progress"]),
            Action.due_date < date.today(),
        ).count()
        critical_issues = Issue.query.filter_by(program_id=pid, severity="critical").filter(
            Issue.status.notin_(["resolved", "closed"])
        ).count()
        signals["raid"] = {
            "open_risks": open_risks,
            "red_risks": red_risks,
            "overdue_actions": overdue_actions,
            "critical_issues": critical_issues,
        }

        program = db.session.get(Program, pid)
        if program and program.go_live_date:
            days_to_golive = (program.go_live_date - date.today()).days
            signals["timeline"] = {"days_to_go_live": days_to_golive}

        return signals
