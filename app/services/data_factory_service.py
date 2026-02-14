"""Data Factory service layer — business logic extracted from data_factory_bp.py.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().

Extracted operations:
- Cleansing task run simulation
- Load cycle state transitions (start / complete)
- Reconciliation variance calculation
- Quality score dashboard aggregation
- Cycle comparison dashboard aggregation
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func

from app.models import db
from app.models.data_factory import (
    DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation,
)

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


# ── Cleansing Task ───────────────────────────────────────────────────────


def run_cleansing_task(task, data):
    """Simulate running a cleansing task (sets pass/fail counts + status).

    Returns the updated CleansingTask.
    """
    task.status = "running"
    db.session.flush()

    # Simulation: accept pass/fail from request or use defaults
    task.pass_count = data.get("pass_count", task.pass_count or 0)
    task.fail_count = data.get("fail_count", task.fail_count or 0)
    task.status = "passed" if (task.fail_count or 0) == 0 else "failed"
    task.last_run_at = _utcnow()
    db.session.flush()
    return task


# ── Load Cycle ───────────────────────────────────────────────────────────


def start_load_cycle(lc):
    """Mark a load cycle as running.

    Returns:
        (LoadCycle, None) on success
        (None, error_dict) if status transition invalid.
    """
    if lc.status not in ("pending", "failed"):
        return None, {
            "error": f"Cannot start from status '{lc.status}'",
            "status": 400,
        }
    lc.status = "running"
    lc.started_at = _utcnow()
    db.session.flush()
    return lc, None


def complete_load_cycle(lc, data):
    """Mark a load cycle as completed or failed based on records_failed.

    Returns the updated LoadCycle.
    """
    lc.records_loaded = data.get("records_loaded", lc.records_loaded or 0)
    lc.records_failed = data.get("records_failed", lc.records_failed or 0)
    lc.error_log = data.get("error_log", lc.error_log)
    lc.status = "failed" if (lc.records_failed or 0) > 0 else "completed"
    lc.completed_at = _utcnow()
    db.session.flush()
    return lc


# ── Reconciliation ───────────────────────────────────────────────────────


def calculate_reconciliation(recon):
    """Calculate variance and update reconciliation status.

    Returns the updated Reconciliation.
    """
    recon.variance = recon.source_count - recon.target_count
    if recon.source_count > 0:
        recon.variance_pct = round(
            abs(recon.variance) / recon.source_count * 100, 2,
        )
    else:
        recon.variance_pct = 0.0

    if recon.variance == 0 and recon.match_count == recon.source_count:
        recon.status = "matched"
    elif abs(recon.variance) > 0:
        recon.status = "variance"
    else:
        recon.status = "matched"

    recon.checked_at = _utcnow()
    db.session.flush()
    return recon


# ── Dashboard ────────────────────────────────────────────────────────────


def compute_quality_score(program_id):
    """Aggregate quality score across data objects for a program.

    Returns:
        dict with total_objects, avg_quality_score, by_status, objects.
    """
    objects = DataObject.query.filter_by(program_id=program_id).all()
    if not objects:
        return {
            "total_objects": 0, "avg_quality_score": 0,
            "by_status": {}, "objects": [],
        }

    scores = [o.quality_score for o in objects if o.quality_score is not None]
    avg = round(sum(scores) / len(scores), 2) if scores else 0

    by_status = {}
    for o in objects:
        by_status.setdefault(o.status, 0)
        by_status[o.status] += 1

    return {
        "total_objects": len(objects),
        "avg_quality_score": avg,
        "by_status": by_status,
        "objects": [
            {"id": o.id, "name": o.name, "quality_score": o.quality_score, "status": o.status}
            for o in objects
        ],
    }


def compute_cycle_comparison(program_id):
    """Compare load cycles across environments for a program.

    Returns:
        dict with environments breakdown and total_cycles.
    """
    obj_ids = [o.id for o in DataObject.query.filter_by(program_id=program_id).all()]
    if not obj_ids:
        return {"environments": {}, "total_cycles": 0}

    cycles = LoadCycle.query.filter(LoadCycle.data_object_id.in_(obj_ids)).all()

    by_env = {}
    for c in cycles:
        env = c.environment or "UNKNOWN"
        if env not in by_env:
            by_env[env] = {
                "total": 0, "completed": 0, "failed": 0,
                "records_loaded": 0, "records_failed": 0,
            }
        by_env[env]["total"] += 1
        if c.status == "completed":
            by_env[env]["completed"] += 1
        elif c.status == "failed":
            by_env[env]["failed"] += 1
        by_env[env]["records_loaded"] += c.records_loaded or 0
        by_env[env]["records_failed"] += c.records_failed or 0

    return {
        "environments": by_env,
        "total_cycles": len(cycles),
    }
