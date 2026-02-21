"""
WorkshopDocumentService — Generate structured documents from workshop data.

Supports three document types:
  - meeting_minutes: Structured record of workshop session
  - workshop_summary: Fit/gap analysis with requirement coverage
  - traceability_report: Requirement → BacklogItem → TestCase chain
"""

from datetime import datetime, timezone

from app.core.exceptions import NotFoundError
from app.models import db
from app.models.explore import (
    ExploreWorkshop,
    ExploreWorkshopDocument,
    ExploreRequirement,
    ExploreDecision,
    ExploreOpenItem,
    ProcessStep,
    ProcessLevel,
    WorkshopAttendee,
    WorkshopAgendaItem,
)
from app.models.backlog import BacklogItem, ConfigItem
from app.models.testing import TestCase
from app.services.helpers.scoped_queries import get_scoped


def _uuid():
    import uuid
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


def _step_label(step):
    """Get a human-readable label for a process step via its linked ProcessLevel."""
    pl = db.session.get(ProcessLevel, step.process_level_id) if step.process_level_id else None
    if pl:
        return f"{pl.code} — {pl.name}"
    return f"Step {step.id[:8]}"


class WorkshopDocumentService:
    """Generate and store workshop documents."""

    GENERATORS = {
        "meeting_minutes": "_gen_meeting_minutes",
        "workshop_summary": "_gen_workshop_summary",
        "traceability_report": "_gen_traceability_report",
    }

    @classmethod
    def generate(cls, workshop_id: str, doc_type: str, *, project_id: int, created_by: str = None) -> dict:
        """
        Generate a document for the given workshop.

        Args:
            workshop_id: Workshop UUID
            doc_type: One of meeting_minutes, workshop_summary, traceability_report
            project_id: Required — owner project scope. Raises ValueError if
                workshop_id does not belong to this project (isolation enforcement).
            created_by: User ID (optional)

        Returns:
            ExploreWorkshopDocument.to_dict()

        Raises:
            ValueError: If invalid doc_type or workshop not found in project_id scope.
        """
        if doc_type not in cls.GENERATORS:
            raise ValueError(
                f"Unknown document type: {doc_type}. "
                f"Valid: {list(cls.GENERATORS.keys())}"
            )

        try:
            ws = get_scoped(ExploreWorkshop, workshop_id, project_id=project_id)
        except NotFoundError:
            raise ValueError(f"Workshop not found: {workshop_id}")

        gen_method = getattr(cls, cls.GENERATORS[doc_type])
        title, content = gen_method(ws)

        doc = ExploreWorkshopDocument(
            id=_uuid(),
            workshop_id=workshop_id,
            project_id=ws.project_id,
            type=doc_type,
            format="markdown",
            title=title,
            content=content,
            generated_by="template",
            generated_at=_utcnow(),
            created_by=created_by,
        )
        db.session.add(doc)
        db.session.commit()
        return doc.to_dict()

    # ── Meeting Minutes ──────────────────────────────────────────────

    @staticmethod
    def _gen_meeting_minutes(ws):
        """Generate meeting minutes from workshop data."""
        pid = ws.project_id

        # Attendees
        attendees = WorkshopAttendee.query.filter_by(workshop_id=ws.id).all()
        attendee_lines = "\n".join(
            f"- {a.name} ({a.role or 'Participant'})"
            for a in attendees
        ) or "- No attendees recorded"

        # Agenda
        agenda_items = WorkshopAgendaItem.query.filter_by(
            workshop_id=ws.id
        ).order_by(WorkshopAgendaItem.sort_order).all()
        agenda_lines = "\n".join(
            f"{i+1}. {a.title}"
            + (f" ({a.duration_minutes} min)" if a.duration_minutes else "")
            for i, a in enumerate(agenda_items)
        ) or "- No agenda items recorded"

        # Steps & decisions
        steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
        decisions = ExploreDecision.query.filter_by(
            project_id=pid
        ).all()
        # Filter decisions to those belonging to this workshop's steps
        step_ids = {s.id for s in steps}
        decisions = [d for d in decisions if d.process_step_id in step_ids]

        open_items = ExploreOpenItem.query.filter_by(workshop_id=ws.id).all()
        requirements = ExploreRequirement.query.filter_by(
            workshop_id=ws.id, project_id=pid
        ).all()

        # Fit/Gap summary
        fit_count = sum(1 for s in steps if s.fit_decision == "fit")
        gap_count = sum(1 for s in steps if s.fit_decision == "gap")
        partial_count = sum(1 for s in steps if s.fit_decision == "partial_fit")
        pending_count = sum(
            1 for s in steps
            if not s.fit_decision
        )

        # Step detail section
        step_sections = []
        for s in steps:
            label = _step_label(s)
            status_emoji = {
                "fit": "✅", "gap": "❌", "partial_fit": "⚠️"
            }.get(s.fit_decision, "⬜")
            step_decisions = [d for d in decisions if d.process_step_id == s.id]
            step_ois = [o for o in open_items if o.process_step_id == s.id]

            section = f"### {status_emoji} {label}\n"
            section += (
                f"**Decision:** "
                f"{(s.fit_decision or 'pending').replace('_', ' ').title()}\n"
            )
            if s.notes:
                section += f"**Notes:** {s.notes}\n"

            if step_decisions:
                section += "\n**Decisions recorded:**\n"
                for d in step_decisions:
                    section += f"- {d.text} (by {d.decided_by or 'Unknown'})\n"

            if step_ois:
                section += "\n**Open Items raised:**\n"
                for o in step_ois:
                    section += (
                        f"- [{o.priority or 'P3'}] {o.title} "
                        f"(→ {o.owner or 'Unassigned'})\n"
                    )

            step_sections.append(section)

        steps_content = (
            "\n".join(step_sections)
            if step_sections
            else "No process steps recorded."
        )

        # Requirements section
        req_lines = "\n".join(
            f"- [{r.code}] {r.title} ({r.type or 'N/A'}, {r.priority or 'P3'})"
            for r in requirements
        ) or "No requirements captured."

        ws_date = ""
        if ws.date:
            ws_date = (
                ws.date.strftime("%Y-%m-%d")
                if hasattr(ws.date, "strftime")
                else str(ws.date)
            )

        # Open items table rows
        oi_rows = "".join(
            f"| {i+1} | {o.priority or 'P3'} | {o.title} "
            f"| {o.owner or '—'} | {o.status} |\n"
            for i, o in enumerate(open_items)
        ) or "| — | — | No open items | — | — |\n"

        title = f"Meeting Minutes — {ws.name}"
        content = f"""# Meeting Minutes: {ws.name}

**Date:** {ws_date or 'N/A'}
**Status:** {ws.status}
**Facilitator:** {ws.facilitator_id or 'N/A'}
**Process Area:** {ws.process_area or 'N/A'}
**Wave:** {ws.wave or 'N/A'}

---

## Attendees

{attendee_lines}

---

## Agenda

{agenda_lines}

---

## Fit/Gap Assessment Summary

| Status | Count |
|--------|-------|
| Fit | {fit_count} |
| Gap | {gap_count} |
| Partial Fit | {partial_count} |
| Pending | {pending_count} |
| **Total** | **{len(steps)}** |

---

## Process Steps Detail

{steps_content}

---

## Requirements Captured

{req_lines}

---

## Open Items Summary

| # | Priority | Title | Owner | Status |
|---|----------|-------|-------|--------|
{oi_rows}
---

*Generated on {_utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""
        return title, content

    # ── Workshop Summary ─────────────────────────────────────────────

    @staticmethod
    def _gen_workshop_summary(ws):
        """Generate a workshop summary report with coverage analysis."""
        pid = ws.project_id

        steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
        requirements = ExploreRequirement.query.filter_by(
            workshop_id=ws.id, project_id=pid
        ).all()
        open_items = ExploreOpenItem.query.filter_by(workshop_id=ws.id).all()

        # Fit/Gap
        fit = sum(1 for s in steps if s.fit_decision == "fit")
        gap = sum(1 for s in steps if s.fit_decision == "gap")
        partial = sum(1 for s in steps if s.fit_decision == "partial_fit")
        total_steps = len(steps)
        assessed = fit + gap + partial
        assess_pct = round(assessed / total_steps * 100) if total_steps else 0

        # Requirements by status
        req_by_status = {}
        for r in requirements:
            req_by_status[r.status] = req_by_status.get(r.status, 0) + 1

        # Requirements by type
        req_by_type = {}
        for r in requirements:
            key = r.type or "untyped"
            req_by_type[key] = req_by_type.get(key, 0) + 1

        # Conversion coverage (W-3 linkage)
        converted = sum(
            1 for r in requirements
            if r.is_converted
        )
        conv_pct = round(converted / len(requirements) * 100) if requirements else 0

        # Effort
        total_effort = sum(r.effort_hours or 0 for r in requirements)

        # OI stats
        oi_open = sum(
            1 for o in open_items
            if o.status in ("open", "in_progress")
        )
        oi_resolved = sum(
            1 for o in open_items
            if o.status in ("resolved", "closed")
        )

        req_status_rows = "\n".join(
            f"| {s.replace('_', ' ').title()} | {c} |"
            for s, c in sorted(req_by_status.items())
        ) or "| — | 0 |"

        req_type_rows = "\n".join(
            f"| {t.replace('_', ' ').title()} | {c} |"
            for t, c in sorted(req_by_type.items())
        ) or "| — | 0 |"

        # Risk indicators
        risk_lines = []
        if total_steps and gap / total_steps > 0.3:
            risk_lines.append(
                f"⚠️ **HIGH GAP RATIO** — "
                f"{round(gap / total_steps * 100)}% of steps identified as gaps"
            )
        else:
            risk_lines.append("✅ Gap ratio within acceptable range")

        if oi_open > 5:
            risk_lines.append(
                f"⚠️ **UNRESOLVED OPEN ITEMS** — {oi_open} items still open"
            )
        else:
            risk_lines.append(
                f"✅ Open items manageable ({oi_open} remaining)"
            )

        if conv_pct < 50 and len(requirements) > 0:
            risk_lines.append(
                f"⚠️ **LOW CONVERSION** — "
                f"{100 - conv_pct}% of requirements not yet converted"
            )
        else:
            risk_lines.append(f"✅ Conversion coverage: {conv_pct}%")

        risk_section = "\n\n".join(risk_lines)

        title = f"Workshop Summary — {ws.name}"
        content = f"""# Workshop Summary: {ws.name}

**Process Area:** {ws.process_area or 'N/A'}  |  **Wave:** {ws.wave or 'N/A'}  |  **Status:** {ws.status}

---

## Assessment Coverage

**{assessed}/{total_steps}** process steps assessed ({assess_pct}%)

| Decision | Count | % |
|----------|-------|---|
| Fit | {fit} | {round(fit / total_steps * 100) if total_steps else 0}% |
| Gap | {gap} | {round(gap / total_steps * 100) if total_steps else 0}% |
| Partial Fit | {partial} | {round(partial / total_steps * 100) if total_steps else 0}% |
| Pending | {total_steps - assessed} | {100 - assess_pct}% |

---

## Requirements ({len(requirements)} total)

### By Status
| Status | Count |
|--------|-------|
{req_status_rows}

### By Type
| Type | Count |
|------|-------|
{req_type_rows}

### Conversion Coverage
- **{converted}/{len(requirements)}** requirements converted to backlog/config items ({conv_pct}%)
- **Total estimated effort:** {total_effort} hours

---

## Open Items ({len(open_items)} total)

- Open/In Progress: **{oi_open}**
- Resolved/Closed: **{oi_resolved}**

---

## Risk Indicators

{risk_section}

---

*Generated on {_utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""
        return title, content

    # ── Traceability Report ──────────────────────────────────────────

    @staticmethod
    def _gen_traceability_report(ws):
        """Generate requirement → backlog → test traceability report."""
        pid = ws.project_id

        requirements = ExploreRequirement.query.filter_by(
            workshop_id=ws.id, project_id=pid
        ).all()

        rows = []
        total_tc = 0
        covered = 0
        uncovered_reqs = []

        for req in requirements:
            # BacklogItem link via relationship
            bl_items = req.linked_backlog_items
            bl = bl_items[0] if bl_items else None

            # ConfigItem link via relationship
            ci_items = req.linked_config_items
            ci = ci_items[0] if ci_items else None

            # TestCases linked via explore_requirement_id (W-6)
            test_cases = TestCase.query.filter_by(
                explore_requirement_id=req.id
            ).all()

            # Also check via backlog_item_id
            if bl and not test_cases:
                test_cases = TestCase.query.filter_by(
                    backlog_item_id=bl.id
                ).all()

            tc_count = len(test_cases)
            total_tc += tc_count
            if tc_count > 0:
                covered += 1
            else:
                uncovered_reqs.append(req)

            backlog_code = bl.code if bl else (ci.code if ci else "—")
            backlog_type = "WRICEF" if bl else ("Config" if ci else "—")
            tc_codes = ", ".join(tc.code for tc in test_cases[:5])
            if len(test_cases) > 5:
                tc_codes += f" (+{len(test_cases) - 5} more)"

            title_trunc = req.title[:40] + ("…" if len(req.title) > 40 else "")
            rows.append(
                f"| {req.code} | {title_trunc} "
                f"| {req.status} | {backlog_type} | {backlog_code} "
                f"| {tc_count} | {tc_codes or '—'} |"
            )

        coverage_pct = (
            round(covered / len(requirements) * 100) if requirements else 0
        )

        # Uncovered requirements list
        uncovered_lines = "\n".join(
            f"- [{r.code}] {r.title} ({r.priority or 'P3'})"
            for r in uncovered_reqs
        ) or "All requirements have linked test cases ✅"

        # Coverage indicator
        if coverage_pct < 70:
            coverage_indicator = (
                f"⚠️ **LOW TEST COVERAGE** — Only {coverage_pct}% "
                f"of requirements have linked test cases"
            )
        else:
            coverage_indicator = f"✅ Test coverage at {coverage_pct}%"

        title = f"Traceability Report — {ws.name}"
        content = f"""# Traceability Report: {ws.name}

**Process Area:** {ws.process_area or 'N/A'}  |  **Wave:** {ws.wave or 'N/A'}

---

## Coverage Summary

- **Requirements:** {len(requirements)}
- **With Test Cases:** {covered} ({coverage_pct}%)
- **Without Test Cases:** {len(requirements) - covered}
- **Total Test Cases Linked:** {total_tc}

---

## Traceability Matrix

| Req Code | Title | Status | Backlog Type | Backlog Code | Tests | Test Codes |
|----------|-------|--------|-------------|-------------|-------|------------|
{chr(10).join(rows) if rows else "| — | No requirements | — | — | — | 0 | — |"}

---

## Gap Analysis

{coverage_indicator}

### Requirements Without Tests:

{uncovered_lines}

---

*Generated on {_utcnow().strftime('%Y-%m-%d %H:%M UTC')}*
"""
        return title, content
