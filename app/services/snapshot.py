"""
SnapshotService — Daily project metrics snapshot [GAP-08] (S-010)

Captures daily aggregated metrics for trend dashboards and
steering-committee reporting.  Stores as JSON blob for flexibility.
"""

import json
from datetime import date, datetime, timezone

from sqlalchemy import func

from app.models import db
from app.models.explore import (
    ProcessLevel, ExploreWorkshop, ProcessStep,
    ExploreOpenItem, ExploreRequirement, ExploreDecision,
    DailySnapshot,
)


class SnapshotService:
    """Captures and retrieves daily project metric snapshots."""

    # ── Capture ───────────────────────────────────────────────────────

    @staticmethod
    def capture(project_id: str, *, snapshot_date: date | None = None) -> dict:
        """
        Capture a metrics snapshot for today (or a specific date).

        Uses UPSERT semantics: if a snapshot already exists for the
        (project_id, snapshot_date) pair, it is overwritten.

        Returns the snapshot dict.
        """
        snap_date = snapshot_date or date.today()

        # Check for existing snapshot
        existing = DailySnapshot.query.filter_by(
            project_id=project_id, snapshot_date=snap_date
        ).first()

        metrics = SnapshotService._compute_metrics(project_id)

        if existing:
            existing.metrics = json.dumps(metrics)
            existing.created_at = datetime.now(timezone.utc)
            snapshot = existing
        else:
            snapshot = DailySnapshot(
                project_id=project_id,
                snapshot_date=snap_date,
                metrics=json.dumps(metrics),
            )
            db.session.add(snapshot)

        db.session.commit()
        return snapshot.to_dict()

    # ── Query ─────────────────────────────────────────────────────────

    @staticmethod
    def list_snapshots(project_id: str, *, from_date: date | None = None,
                       to_date: date | None = None, limit: int = 90) -> list[dict]:
        """Return recent snapshots for a project."""
        q = DailySnapshot.query.filter_by(project_id=project_id)
        if from_date:
            q = q.filter(DailySnapshot.snapshot_date >= from_date)
        if to_date:
            q = q.filter(DailySnapshot.snapshot_date <= to_date)
        q = q.order_by(DailySnapshot.snapshot_date.desc()).limit(limit)
        return [s.to_dict() for s in q.all()]

    @staticmethod
    def latest(project_id: str) -> dict | None:
        """Return the most recent snapshot."""
        snap = (DailySnapshot.query
                .filter_by(project_id=project_id)
                .order_by(DailySnapshot.snapshot_date.desc())
                .first())
        return snap.to_dict() if snap else None

    # ── Steering-Committee Report (A-057) ─────────────────────────────

    @staticmethod
    def steering_committee_report(project_id: str) -> dict:
        """
        Build a steering-committee ready report:
          - Current metrics (live)
          - 7-day trend from snapshots
          - Key risks & blockers
        """
        current = SnapshotService._compute_metrics(project_id)

        # Last 7 snapshots
        snaps = SnapshotService.list_snapshots(project_id, limit=7)
        trend = [{"date": s["snapshot_date"], "metrics": s["metrics"]} for s in snaps]

        # Blockers
        blockers = ExploreOpenItem.query.filter_by(
            project_id=project_id, status="blocked"
        ).all()
        blocker_list = [{"code": b.code, "title": b.title, "assignee": b.assignee_name}
                        for b in blockers[:10]]

        return {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "current_metrics": current,
            "trend_7d": trend,
            "blockers": blocker_list,
        }

    # ── Private: Metric Computation ───────────────────────────────────

    @staticmethod
    def _compute_metrics(project_id: str) -> dict:
        """Compute all key metrics for the project."""

        # Process levels
        levels = ProcessLevel.query.filter_by(project_id=project_id)
        l1_count = levels.filter_by(level="L1").count()
        l2_count = levels.filter_by(level="L2").count()
        l3_count = levels.filter_by(level="L3").count()
        l4_count = levels.filter_by(level="L4").count()

        # Fit status at L3
        l3_fit = db.session.query(
            ProcessLevel.fit_status, func.count(ProcessLevel.id)
        ).filter(
            ProcessLevel.project_id == project_id,
            ProcessLevel.level == "L3",
        ).group_by(ProcessLevel.fit_status).all()
        l3_fit_map = {r[0] or "pending": r[1] for r in l3_fit}

        # Workshops
        ws_total = ExploreWorkshop.query.filter_by(project_id=project_id).count()
        ws_completed = ExploreWorkshop.query.filter_by(
            project_id=project_id, status="completed"
        ).count()
        ws_in_progress = ExploreWorkshop.query.filter_by(
            project_id=project_id, status="in_progress"
        ).count()

        # Process steps
        steps_total = ProcessStep.query.filter_by(project_id=project_id).count()
        steps_decided = ProcessStep.query.filter(
            ProcessStep.project_id == project_id,
            ProcessStep.fit_decision.isnot(None),
        ).count()
        step_fit = db.session.query(
            ProcessStep.fit_decision, func.count(ProcessStep.id)
        ).filter(
            ProcessStep.project_id == project_id,
            ProcessStep.fit_decision.isnot(None),
        ).group_by(ProcessStep.fit_decision).all()
        step_fit_map = {r[0]: r[1] for r in step_fit}

        # Requirements
        req_total = ExploreRequirement.query.filter_by(project_id=project_id).count()
        req_by_status = dict(db.session.query(
            ExploreRequirement.status, func.count(ExploreRequirement.id)
        ).filter_by(project_id=project_id).group_by(ExploreRequirement.status).all())
        req_effort = db.session.query(
            func.sum(ExploreRequirement.estimated_effort)
        ).filter_by(project_id=project_id).scalar() or 0

        # Open items
        oi_total = ExploreOpenItem.query.filter_by(project_id=project_id).count()
        oi_open = ExploreOpenItem.query.filter(
            ExploreOpenItem.project_id == project_id,
            ExploreOpenItem.status.in_(["open", "in_progress"]),
        ).count()
        oi_overdue = ExploreOpenItem.query.filter(
            ExploreOpenItem.project_id == project_id,
            ExploreOpenItem.status.in_(["open", "in_progress"]),
            ExploreOpenItem.due_date < date.today(),
        ).count()

        # Decisions
        dec_total = ExploreDecision.query.filter_by(project_id=project_id).count()

        return {
            "hierarchy": {
                "l1": l1_count, "l2": l2_count, "l3": l3_count, "l4": l4_count,
            },
            "l3_fit_status": l3_fit_map,
            "workshops": {
                "total": ws_total, "completed": ws_completed,
                "in_progress": ws_in_progress,
                "completion_rate": round(ws_completed / ws_total * 100, 1) if ws_total else 0,
            },
            "process_steps": {
                "total": steps_total, "decided": steps_decided,
                "by_decision": step_fit_map,
                "decision_rate": round(steps_decided / steps_total * 100, 1) if steps_total else 0,
            },
            "requirements": {
                "total": req_total, "by_status": req_by_status,
                "total_effort": float(req_effort),
            },
            "open_items": {
                "total": oi_total, "open": oi_open, "overdue": oi_overdue,
            },
            "decisions": {"total": dec_total},
        }
