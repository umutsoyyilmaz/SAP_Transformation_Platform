"""Data Factory service layer — business logic for data migration lifecycle.

Provides CRUD helpers and business operations for DataObject, MigrationWave,
CleansingTask, LoadCycle, Reconciliation, TestDataSet, and TestDataSetItem.

All db.session.commit() calls for mutations live here; blueprints never commit.
"""

import logging
from datetime import datetime, timezone

from app.models import db
from app.models.data_factory import (
    CleansingTask,
    DataObject,
    LoadCycle,
    MigrationWave,
    Reconciliation,
    TestDataSet,
    TestDataSetItem,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════
# DataObject CRUD
# ═════════════════════════════════════════════════════════════════════════


def list_data_objects(program_id: int | None = None, status: str | None = None) -> dict:
    """List data objects with optional filters.

    Args:
        program_id: Filter by program.
        status: Filter by status string.

    Returns:
        Dict with items list and total count.
    """
    q = DataObject.query
    if program_id:
        q = q.filter_by(program_id=program_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(DataObject.name)
    items = q.all()
    return {"items": [o.to_dict() for o in items], "total": len(items)}


def create_data_object(data: dict) -> dict:
    """Create a new DataObject.

    Args:
        data: Validated input dict from blueprint.

    Returns:
        Serialized DataObject dict.
    """
    obj = DataObject(
        program_id=data["program_id"],
        name=data["name"],
        description=data.get("description"),
        source_system=data["source_system"],
        target_table=data.get("target_table"),
        record_count=data.get("record_count", 0),
        quality_score=data.get("quality_score"),
        status=data.get("status", "draft"),
        owner=data.get("owner"),
        owner_id=data.get("owner_id"),
    )
    db.session.add(obj)
    db.session.commit()
    return obj.to_dict()


def get_data_object_with_stats(obj_id: int) -> tuple[dict | None, dict | None]:
    """Get a DataObject with aggregated task/load counts.

    Args:
        obj_id: DataObject primary key.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    obj = db.session.get(DataObject, obj_id)
    if not obj:
        return None, {"error": "DataObject not found", "status": 404}
    d = obj.to_dict()
    d["task_count"] = obj.cleansing_tasks.count()
    d["load_count"] = obj.load_cycles.count()
    return d, None


def update_data_object(obj_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a DataObject.

    Args:
        obj_id: DataObject primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    obj = db.session.get(DataObject, obj_id)
    if not obj:
        return None, {"error": "DataObject not found", "status": 404}
    for f in ("name", "description", "source_system", "target_table",
              "record_count", "quality_score", "status", "owner", "owner_id"):
        if f in data:
            setattr(obj, f, data[f])
    db.session.commit()
    return obj.to_dict(), None


def delete_data_object(obj_id: int) -> dict | None:
    """Delete a DataObject and its children.

    Args:
        obj_id: DataObject primary key.

    Returns:
        Error dict if not found, None on success.
    """
    obj = db.session.get(DataObject, obj_id)
    if not obj:
        return {"error": "DataObject not found", "status": 404}
    db.session.delete(obj)
    db.session.commit()
    return None


# ═════════════════════════════════════════════════════════════════════════
# MigrationWave CRUD
# ═════════════════════════════════════════════════════════════════════════


def list_waves(program_id: int | None = None) -> dict:
    """List migration waves with optional program filter.

    Args:
        program_id: Filter by program.

    Returns:
        Dict with items list and total count.
    """
    q = MigrationWave.query
    if program_id:
        q = q.filter_by(program_id=program_id)
    q = q.order_by(MigrationWave.wave_number)
    items = q.all()
    return {"items": [w.to_dict() for w in items], "total": len(items)}


def create_wave(data: dict) -> dict:
    """Create a new MigrationWave.

    Args:
        data: Validated input dict from blueprint.

    Returns:
        Serialized MigrationWave dict.
    """
    wave = MigrationWave(
        program_id=data["program_id"],
        wave_number=data["wave_number"],
        name=data["name"],
        description=data.get("description"),
        planned_start=data.get("planned_start"),
        planned_end=data.get("planned_end"),
        status=data.get("status", "planned"),
    )
    db.session.add(wave)
    db.session.commit()
    return wave.to_dict()


def get_wave_with_stats(wave_id: int) -> tuple[dict | None, dict | None]:
    """Get a MigrationWave with load cycle summary.

    Args:
        wave_id: MigrationWave primary key.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    wave = db.session.get(MigrationWave, wave_id)
    if not wave:
        return None, {"error": "MigrationWave not found", "status": 404}
    d = wave.to_dict()
    cycles = wave.load_cycles.all()
    d["load_cycle_count"] = len(cycles)
    d["total_loaded"] = sum(c.records_loaded or 0 for c in cycles)
    d["total_failed"] = sum(c.records_failed or 0 for c in cycles)
    return d, None


def update_wave(wave_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a MigrationWave.

    Args:
        wave_id: MigrationWave primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    wave = db.session.get(MigrationWave, wave_id)
    if not wave:
        return None, {"error": "MigrationWave not found", "status": 404}
    for f in ("wave_number", "name", "description", "planned_start", "planned_end",
              "actual_start", "actual_end", "status"):
        if f in data:
            setattr(wave, f, data[f])
    db.session.commit()
    return wave.to_dict(), None


def delete_wave(wave_id: int) -> dict | None:
    """Delete a MigrationWave.

    Args:
        wave_id: MigrationWave primary key.

    Returns:
        Error dict if not found, None on success.
    """
    wave = db.session.get(MigrationWave, wave_id)
    if not wave:
        return {"error": "MigrationWave not found", "status": 404}
    db.session.delete(wave)
    db.session.commit()
    return None


# ═════════════════════════════════════════════════════════════════════════
# CleansingTask CRUD + run
# ═════════════════════════════════════════════════════════════════════════


def list_cleansing_tasks(data_object_id: int) -> list[dict]:
    """List cleansing tasks for a data object.

    Args:
        data_object_id: Parent DataObject primary key.

    Returns:
        List of serialized CleansingTask dicts.
    """
    tasks = CleansingTask.query.filter_by(data_object_id=data_object_id).all()
    return [t.to_dict() for t in tasks]


def create_cleansing_task(obj_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Create a CleansingTask for a DataObject.

    Args:
        obj_id: Parent DataObject primary key.
        data: Validated input dict.

    Returns:
        Tuple of (serialized task, None) or (None, error dict).
    """
    obj = db.session.get(DataObject, obj_id)
    if not obj:
        return None, {"error": "DataObject not found", "status": 404}
    task = CleansingTask(
        data_object_id=obj_id,
        rule_type=data["rule_type"],
        rule_expression=data["rule_expression"],
        description=data.get("description"),
        status=data.get("status", "pending"),
    )
    db.session.add(task)
    db.session.commit()
    return task.to_dict(), None


def get_cleansing_task(task_id: int) -> tuple[dict | None, dict | None]:
    """Get a single CleansingTask by primary key.

    Args:
        task_id: CleansingTask primary key.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    task = db.session.get(CleansingTask, task_id)
    if not task:
        return None, {"error": "CleansingTask not found", "status": 404}
    return task.to_dict(), None


def update_cleansing_task(task_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a CleansingTask.

    Args:
        task_id: CleansingTask primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    task = db.session.get(CleansingTask, task_id)
    if not task:
        return None, {"error": "CleansingTask not found", "status": 404}
    for f in ("rule_type", "rule_expression", "description", "pass_count",
              "fail_count", "status"):
        if f in data:
            setattr(task, f, data[f])
    db.session.commit()
    return task.to_dict(), None


def delete_cleansing_task(task_id: int) -> dict | None:
    """Delete a CleansingTask.

    Args:
        task_id: CleansingTask primary key.

    Returns:
        Error dict if not found, None on success.
    """
    task = db.session.get(CleansingTask, task_id)
    if not task:
        return {"error": "CleansingTask not found", "status": 404}
    db.session.delete(task)
    db.session.commit()
    return None


def run_cleansing_task(task_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Simulate running a cleansing task (sets pass/fail counts + status).

    Args:
        task_id: CleansingTask primary key.
        data: Optional pass_count / fail_count overrides.

    Returns:
        Tuple of (serialized task, None) or (None, error dict).
    """
    task = db.session.get(CleansingTask, task_id)
    if not task:
        return None, {"error": "CleansingTask not found", "status": 404}
    task.status = "running"
    db.session.flush()

    task.pass_count = data.get("pass_count", task.pass_count or 0)
    task.fail_count = data.get("fail_count", task.fail_count or 0)
    task.status = "passed" if (task.fail_count or 0) == 0 else "failed"
    task.last_run_at = _utcnow()
    db.session.commit()
    return task.to_dict(), None


# ═════════════════════════════════════════════════════════════════════════
# LoadCycle CRUD + start / complete
# ═════════════════════════════════════════════════════════════════════════


def list_load_cycles(data_object_id: int) -> list[dict]:
    """List load cycles for a data object.

    Args:
        data_object_id: Parent DataObject primary key.

    Returns:
        List of serialized LoadCycle dicts.
    """
    cycles = LoadCycle.query.filter_by(data_object_id=data_object_id).order_by(LoadCycle.id.desc()).all()
    return [c.to_dict() for c in cycles]


def create_load_cycle(obj_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Create a LoadCycle for a DataObject.

    Args:
        obj_id: Parent DataObject primary key.
        data: Validated input dict.

    Returns:
        Tuple of (serialized cycle, None) or (None, error dict).
    """
    obj = db.session.get(DataObject, obj_id)
    if not obj:
        return None, {"error": "DataObject not found", "status": 404}
    cycle = LoadCycle(
        data_object_id=obj_id,
        wave_id=data.get("wave_id"),
        environment=data.get("environment", "DEV"),
        load_type=data.get("load_type", "initial"),
        status="pending",
    )
    db.session.add(cycle)
    db.session.commit()
    return cycle.to_dict(), None


def get_load_cycle_with_stats(lc_id: int) -> tuple[dict | None, dict | None]:
    """Get a LoadCycle with reconciliation summary.

    Args:
        lc_id: LoadCycle primary key.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return None, {"error": "LoadCycle not found", "status": 404}
    d = lc.to_dict()
    d["reconciliation_count"] = lc.reconciliations.count()
    return d, None


def update_load_cycle(lc_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a LoadCycle.

    Args:
        lc_id: LoadCycle primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return None, {"error": "LoadCycle not found", "status": 404}
    for f in ("wave_id", "environment", "load_type", "records_loaded",
              "records_failed", "status", "error_log"):
        if f in data:
            setattr(lc, f, data[f])
    db.session.commit()
    return lc.to_dict(), None


def delete_load_cycle(lc_id: int) -> dict | None:
    """Delete a LoadCycle.

    Args:
        lc_id: LoadCycle primary key.

    Returns:
        Error dict if not found, None on success.
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return {"error": "LoadCycle not found", "status": 404}
    db.session.delete(lc)
    db.session.commit()
    return None


def start_load_cycle(lc_id: int) -> tuple[dict | None, dict | None]:
    """Mark a load cycle as running.

    Args:
        lc_id: LoadCycle primary key.

    Returns:
        Tuple of (serialized cycle, None) or (None, error dict).
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return None, {"error": "LoadCycle not found", "status": 404}
    if lc.status not in ("pending", "failed"):
        return None, {"error": f"Cannot start from status '{lc.status}'", "status": 400}
    lc.status = "running"
    lc.started_at = _utcnow()
    db.session.commit()
    return lc.to_dict(), None


def complete_load_cycle(lc_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Mark a load cycle as completed or failed based on records_failed.

    Args:
        lc_id: LoadCycle primary key.
        data: Payload with records_loaded, records_failed, error_log.

    Returns:
        Tuple of (serialized cycle, None) or (None, error dict).
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return None, {"error": "LoadCycle not found", "status": 404}
    lc.records_loaded = data.get("records_loaded", lc.records_loaded or 0)
    lc.records_failed = data.get("records_failed", lc.records_failed or 0)
    lc.error_log = data.get("error_log", lc.error_log)
    lc.status = "failed" if (lc.records_failed or 0) > 0 else "completed"
    lc.completed_at = _utcnow()
    db.session.commit()
    return lc.to_dict(), None


# ═════════════════════════════════════════════════════════════════════════
# Reconciliation CRUD + calculate
# ═════════════════════════════════════════════════════════════════════════


def list_reconciliations(load_cycle_id: int) -> list[dict]:
    """List reconciliations for a load cycle.

    Args:
        load_cycle_id: Parent LoadCycle primary key.

    Returns:
        List of serialized Reconciliation dicts.
    """
    recons = Reconciliation.query.filter_by(load_cycle_id=load_cycle_id).all()
    return [r.to_dict() for r in recons]


def create_reconciliation(lc_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Create a Reconciliation for a LoadCycle.

    Args:
        lc_id: Parent LoadCycle primary key.
        data: Validated input dict.

    Returns:
        Tuple of (serialized reconciliation, None) or (None, error dict).
    """
    lc = db.session.get(LoadCycle, lc_id)
    if not lc:
        return None, {"error": "LoadCycle not found", "status": 404}
    recon = Reconciliation(
        load_cycle_id=lc_id,
        source_count=data.get("source_count", 0),
        target_count=data.get("target_count", 0),
        match_count=data.get("match_count", 0),
        status="pending",
    )
    db.session.add(recon)
    db.session.commit()
    return recon.to_dict(), None


def get_reconciliation(recon_id: int) -> tuple[dict | None, dict | None]:
    """Get a single Reconciliation by primary key.

    Args:
        recon_id: Reconciliation primary key.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    recon = db.session.get(Reconciliation, recon_id)
    if not recon:
        return None, {"error": "Reconciliation not found", "status": 404}
    return recon.to_dict(), None


def update_reconciliation(recon_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a Reconciliation.

    Args:
        recon_id: Reconciliation primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    recon = db.session.get(Reconciliation, recon_id)
    if not recon:
        return None, {"error": "Reconciliation not found", "status": 404}
    for f in ("source_count", "target_count", "match_count", "status", "notes"):
        if f in data:
            setattr(recon, f, data[f])
    db.session.commit()
    return recon.to_dict(), None


def delete_reconciliation(recon_id: int) -> dict | None:
    """Delete a Reconciliation.

    Args:
        recon_id: Reconciliation primary key.

    Returns:
        Error dict if not found, None on success.
    """
    recon = db.session.get(Reconciliation, recon_id)
    if not recon:
        return {"error": "Reconciliation not found", "status": 404}
    db.session.delete(recon)
    db.session.commit()
    return None


def calculate_reconciliation(recon_id: int) -> tuple[dict | None, dict | None]:
    """Calculate variance and update reconciliation status.

    Args:
        recon_id: Reconciliation primary key.

    Returns:
        Tuple of (serialized reconciliation, None) or (None, error dict).
    """
    recon = db.session.get(Reconciliation, recon_id)
    if not recon:
        return None, {"error": "Reconciliation not found", "status": 404}
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
    db.session.commit()
    return recon.to_dict(), None


# ═════════════════════════════════════════════════════════════════════════
# Dashboard
# ═════════════════════════════════════════════════════════════════════════


def compute_quality_score(program_id: int) -> dict:
    """Aggregate quality score across data objects for a program.

    Args:
        program_id: Program to aggregate for.

    Returns:
        Dict with total_objects, avg_quality_score, by_status, objects.
    """
    objects = DataObject.query.filter_by(program_id=program_id).all()
    if not objects:
        return {
            "total_objects": 0, "avg_quality_score": 0,
            "by_status": {}, "objects": [],
        }

    scores = [o.quality_score for o in objects if o.quality_score is not None]
    avg = round(sum(scores) / len(scores), 2) if scores else 0

    by_status: dict[str, int] = {}
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


def compute_cycle_comparison(program_id: int) -> dict:
    """Compare load cycles across environments for a program.

    Args:
        program_id: Program to compare for.

    Returns:
        Dict with environments breakdown and total_cycles.
    """
    obj_ids = [o.id for o in DataObject.query.filter_by(program_id=program_id).all()]
    if not obj_ids:
        return {"environments": {}, "total_cycles": 0}

    cycles = LoadCycle.query.filter(LoadCycle.data_object_id.in_(obj_ids)).all()

    by_env: dict[str, dict] = {}
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


# ═════════════════════════════════════════════════════════════════════════
# TestDataSet CRUD
# ═════════════════════════════════════════════════════════════════════════


def list_test_data_sets(
    program_id: int | None = None,
    status: str | None = None,
    environment: str | None = None,
) -> dict:
    """List test data sets with optional filters.

    Args:
        program_id: Filter by program.
        status: Filter by status string.
        environment: Filter by environment string.

    Returns:
        Dict with items list and total count.
    """
    q = TestDataSet.query
    if program_id:
        q = q.filter_by(program_id=program_id)
    if status:
        q = q.filter_by(status=status)
    if environment:
        q = q.filter_by(environment=environment)
    datasets = q.order_by(TestDataSet.updated_at.desc()).all()
    return {"items": [ds.to_dict() for ds in datasets], "total": len(datasets)}


def create_test_data_set(data: dict) -> dict:
    """Create a new TestDataSet.

    Args:
        data: Validated input dict from blueprint.

    Returns:
        Serialized TestDataSet dict.
    """
    ds = TestDataSet(
        program_id=data["program_id"],
        name=data["name"],
        version=data.get("version", "1.0"),
        description=data.get("description", ""),
        environment=data.get("environment", "QAS"),
        status="draft",
        refresh_strategy=data.get("refresh_strategy", "manual"),
    )
    db.session.add(ds)
    db.session.commit()
    return ds.to_dict()


def get_test_data_set_with_items(ds_id: int) -> tuple[dict | None, dict | None]:
    """Get a TestDataSet with its items.

    Args:
        ds_id: TestDataSet primary key.

    Returns:
        Tuple of (result dict, None) or (None, error dict).
    """
    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return None, {"error": "TestDataSet not found", "status": 404}
    result = ds.to_dict()
    result["items"] = [item.to_dict() for item in ds.items]
    return result, None


def update_test_data_set(ds_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a TestDataSet.

    Args:
        ds_id: TestDataSet primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return None, {"error": "TestDataSet not found", "status": 404}
    for field in ("name", "version", "description", "environment", "status",
                  "refresh_strategy"):
        if field in data:
            setattr(ds, field, data[field])
    db.session.commit()
    return ds.to_dict(), None


def delete_test_data_set(ds_id: int) -> dict | None:
    """Delete a TestDataSet (cascades to items).

    Args:
        ds_id: TestDataSet primary key.

    Returns:
        Error dict if not found, None on success.
    """
    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return {"error": "TestDataSet not found", "status": 404}
    db.session.delete(ds)
    db.session.commit()
    return None


# ═════════════════════════════════════════════════════════════════════════
# TestDataSetItem CRUD
# ═════════════════════════════════════════════════════════════════════════


def list_data_set_items(ds_id: int) -> tuple[list[dict] | None, dict | None]:
    """List items in a data set.

    Args:
        ds_id: Parent TestDataSet primary key.

    Returns:
        Tuple of (items list, None) or (None, error dict).
    """
    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return None, {"error": "TestDataSet not found", "status": 404}
    items = TestDataSetItem.query.filter_by(data_set_id=ds_id).all()
    return [i.to_dict() for i in items], None


def add_data_set_item(ds_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Add a DataObject reference to a data set.

    Args:
        ds_id: Parent TestDataSet primary key.
        data: Validated input dict.

    Returns:
        Tuple of (serialized item, None) or (None, error dict).
    """
    ds = db.session.get(TestDataSet, ds_id)
    if not ds:
        return None, {"error": "TestDataSet not found", "status": 404}
    item = TestDataSetItem(
        data_set_id=ds_id,
        data_object_id=data.get("data_object_id"),
        record_filter=data.get("record_filter"),
        expected_records=data.get("expected_records"),
        notes=data.get("notes", ""),
        status="pending",
    )
    db.session.add(item)
    db.session.commit()
    return item.to_dict(), None


def update_data_set_item(item_id: int, data: dict) -> tuple[dict | None, dict | None]:
    """Update a TestDataSetItem.

    Args:
        item_id: TestDataSetItem primary key.
        data: Fields to update.

    Returns:
        Tuple of (serialized dict, None) or (None, error dict).
    """
    item = db.session.get(TestDataSetItem, item_id)
    if not item:
        return None, {"error": "TestDataSetItem not found", "status": 404}
    for field in ("data_object_id", "record_filter",
                  "expected_records", "actual_records", "status",
                  "load_cycle_id", "notes"):
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return item.to_dict(), None


def delete_data_set_item(item_id: int) -> dict | None:
    """Remove an item from a data set.

    Args:
        item_id: TestDataSetItem primary key.

    Returns:
        Error dict if not found, None on success.
    """
    item = db.session.get(TestDataSetItem, item_id)
    if not item:
        return {"error": "TestDataSetItem not found", "status": 404}
    db.session.delete(item)
    db.session.commit()
    return None
