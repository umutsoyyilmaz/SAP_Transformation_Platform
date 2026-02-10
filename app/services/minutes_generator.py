"""
MinutesGeneratorService — Workshop meeting-minutes generation [GAP-06] (S-009)

Generates structured meeting minutes from workshop data:
  - Markdown output (default)
  - Template-based formatting
  - Includes: agenda, attendees, decisions, open items, requirements
"""

import json
from datetime import datetime, timezone

from app.models import db
from app.models.explore import (
    ExploreWorkshop, WorkshopAttendee, WorkshopAgendaItem,
    ProcessStep, ExploreDecision, ExploreOpenItem, ExploreRequirement,
    ExploreWorkshopDocument,
)


class MinutesGeneratorService:
    """Generates meeting minutes for Explore workshops."""

    # ── Public API ────────────────────────────────────────────────────

    @staticmethod
    def generate(workshop_id: str, *, format: str = "markdown",
                 created_by: str | None = None, session_number: int | None = None) -> dict:
        """
        Generate meeting minutes for the given workshop.

        Args:
            workshop_id: Workshop UUID
            format: 'markdown' (default) — future: 'docx', 'pdf'
            created_by: User ID who triggered the generation
            session_number: If multi-session, which session to limit to

        Returns:
            dict with keys: id, content, title, format
        """
        ws = db.session.get(ExploreWorkshop, workshop_id)
        if not ws:
            raise ValueError(f"Workshop {workshop_id} not found")

        # Gather data
        attendees = WorkshopAttendee.query.filter_by(workshop_id=workshop_id).all()
        agenda = (WorkshopAgendaItem.query
                  .filter_by(workshop_id=workshop_id)
                  .order_by(WorkshopAgendaItem.order_index)
                  .all())
        steps_q = ProcessStep.query.filter_by(workshop_id=workshop_id)
        if session_number is not None:
            steps_q = steps_q.filter_by(session_number=session_number)
        steps = steps_q.order_by(ProcessStep.order_index).all()
        step_ids = [s.id for s in steps]

        decisions = ExploreDecision.query.filter(
            ExploreDecision.process_step_id.in_(step_ids)
        ).all() if step_ids else []

        open_items = ExploreOpenItem.query.filter_by(
            workshop_id=workshop_id
        ).all()

        requirements = ExploreRequirement.query.filter_by(
            workshop_id=workshop_id
        ).all()

        # Build minutes
        content = MinutesGeneratorService._build_markdown(
            ws, attendees, agenda, steps, decisions, open_items, requirements,
            session_number=session_number,
        )

        title = f"Meeting Minutes — {ws.code or 'Workshop'}"
        if session_number:
            title += f" (Session {session_number})"

        # Persist as WorkshopDocument
        doc = ExploreWorkshopDocument(
            workshop_id=workshop_id,
            project_id=ws.project_id,
            type="meeting_minutes",
            format=format,
            title=title,
            content=content,
            generated_by="template",
            generated_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        db.session.add(doc)
        db.session.commit()

        return doc.to_dict()

    # ── Private: Markdown Builder ─────────────────────────────────────

    @staticmethod
    def _build_markdown(ws, attendees, agenda, steps, decisions,
                        open_items, requirements, *, session_number=None) -> str:
        lines = []
        _a = lines.append

        _a(f"# Meeting Minutes: {ws.code or 'Workshop'}")
        if session_number:
            _a(f"**Session:** {session_number}")
        _a("")
        _a(f"**Status:** {ws.status}")
        _a(f"**Process Area:** {ws.process_area or '—'}")
        _a(f"**Wave:** {ws.wave or '—'}")
        if ws.scheduled_date:
            _a(f"**Date:** {ws.scheduled_date}")
        _a("")

        # Attendees
        if attendees:
            _a("## Attendees")
            _a("")
            _a("| Name | Role | Present |")
            _a("|------|------|---------|")
            for a in attendees:
                present = "✅" if a.attended else "❌"
                _a(f"| {a.name or '—'} | {a.role or '—'} | {present} |")
            _a("")

        # Agenda
        if agenda:
            _a("## Agenda")
            _a("")
            for item in agenda:
                status = "✅" if item.status == "completed" else "⬜"
                duration = f" ({item.duration_minutes}min)" if item.duration_minutes else ""
                _a(f"- {status} {item.title or '—'}{duration}")
            _a("")

        # Process Steps & Decisions
        if steps:
            _a("## Process Steps & Fit Decisions")
            _a("")
            _a("| # | Process Step | Fit Decision | Notes |")
            _a("|---|-------------|-------------|-------|")
            for i, s in enumerate(steps, 1):
                fit = s.fit_decision or "—"
                notes = (s.notes or "")[:80]
                _a(f"| {i} | {s.l4_code or '—'} | **{fit}** | {notes} |")
            _a("")

        # Decisions
        if decisions:
            _a("## Decisions")
            _a("")
            for d in decisions:
                _a(f"### {d.code or 'DEC'}")
                _a(f"- **Decision:** {d.decision_text or '—'}")
                _a(f"- **Rationale:** {d.rationale or '—'}")
                _a(f"- **Owner:** {d.decided_by or '—'}")
                _a("")

        # Open Items
        if open_items:
            _a("## Open Items")
            _a("")
            _a("| Code | Title | Assignee | Priority | Due | Status |")
            _a("|------|-------|---------|----------|-----|--------|")
            for o in open_items:
                _a(f"| {o.code or '—'} | {o.title or '—'} | {o.assignee_name or '—'} "
                   f"| {o.priority or '—'} | {o.due_date or '—'} | {o.status or '—'} |")
            _a("")

        # Requirements
        if requirements:
            _a("## Requirements")
            _a("")
            _a("| Code | Title | Type | Priority | Status |")
            _a("|------|-------|------|----------|--------|")
            for r in requirements:
                _a(f"| {r.code or '—'} | {r.title or '—'} | {r.requirement_type or '—'} "
                   f"| {r.priority or '—'} | {r.status or '—'} |")
            _a("")

        # Footer
        _a("---")
        _a(f"*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

        return "\n".join(lines)

    # ── AI Summary (placeholder for Gemini integration) ──────────────

    @staticmethod
    def generate_ai_summary(workshop_id: str, *, created_by: str | None = None) -> dict:
        """
        Generate an AI-powered summary of a workshop (A-030).
        Currently outputs a structured summary from raw data;
        future: calls Gemini/GPT for natural language synthesis.
        """
        ws = db.session.get(ExploreWorkshop, workshop_id)
        if not ws:
            raise ValueError(f"Workshop {workshop_id} not found")

        steps = ProcessStep.query.filter_by(workshop_id=workshop_id).all()
        open_items = ExploreOpenItem.query.filter_by(workshop_id=workshop_id).all()
        requirements = ExploreRequirement.query.filter_by(workshop_id=workshop_id).all()

        fit_count = sum(1 for s in steps if s.fit_decision == "fit")
        gap_count = sum(1 for s in steps if s.fit_decision == "gap")
        partial = sum(1 for s in steps if s.fit_decision == "partial_fit")

        summary = {
            "workshop_code": ws.code,
            "process_area": ws.process_area,
            "total_steps": len(steps),
            "fit": fit_count,
            "gap": gap_count,
            "partial_fit": partial,
            "pending": len(steps) - fit_count - gap_count - partial,
            "open_items_count": len(open_items),
            "open_items_open": sum(1 for o in open_items if o.status in ("open", "in_progress")),
            "requirements_count": len(requirements),
            "key_gaps": [s.l4_code for s in steps if s.fit_decision == "gap"][:10],
        }

        content = json.dumps(summary, indent=2)
        title = f"AI Summary — {ws.code or 'Workshop'}"

        doc = ExploreWorkshopDocument(
            workshop_id=workshop_id,
            project_id=ws.project_id,
            type="ai_summary",
            format="markdown",
            title=title,
            content=content,
            generated_by="ai",
            generated_at=datetime.now(timezone.utc),
            created_by=created_by,
        )
        db.session.add(doc)
        db.session.commit()

        return doc.to_dict()
