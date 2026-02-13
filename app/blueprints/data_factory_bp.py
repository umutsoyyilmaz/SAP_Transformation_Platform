"""
Data Factory Blueprint — Sprint 10
31 routes for data migration lifecycle management.

Endpoints:
  DataObject:      GET/POST /data-factory/objects, GET/PUT/DELETE /data-factory/objects/<id>
  MigrationWave:   GET/POST /data-factory/waves, GET/PUT/DELETE /data-factory/waves/<id>
  CleansingTask:   GET/POST /data-factory/objects/<id>/tasks, GET/PUT/DELETE /data-factory/tasks/<id>
                   POST /data-factory/tasks/<id>/run
  LoadCycle:       GET/POST /data-factory/objects/<id>/loads, GET/PUT/DELETE /data-factory/loads/<id>
                   POST /data-factory/loads/<id>/start, POST /data-factory/loads/<id>/complete
  Reconciliation:  GET/POST /data-factory/loads/<id>/recons, GET/PUT/DELETE /data-factory/recons/<id>
                   POST /data-factory/recons/<id>/calculate
  Dashboard:       GET /data-factory/quality-score, GET /data-factory/cycle-comparison
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.models import db
from app.models.data_factory import (
    DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation,
)

data_factory_bp = Blueprint(
    "data_factory", __name__, url_prefix="/api/v1/data-factory",
)


def _utcnow():
    return datetime.now(timezone.utc)


def _get_or_404(model, pk, label="Resource"):
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{label} not found"}), 404)
    return obj, None


# ═════════════════════════════════════════════════════════════════════════
# DataObject CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects", methods=["GET"])
def list_data_objects():
    """List data objects, optionally filtered by program_id and status."""
    pid = request.args.get("program_id", type=int)
    status = request.args.get("status")
    q = DataObject.query
    if pid:
        q = q.filter_by(program_id=pid)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(DataObject.name)
    items = q.all()
    return jsonify({"items": [o.to_dict() for o in items], "total": len(items)})


@data_factory_bp.route("/objects", methods=["POST"])
def create_data_object():
    """Create a new data object."""
    data = request.get_json(silent=True) or {}
    required = ("program_id", "name", "source_system")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

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
    return jsonify(obj.to_dict()), 201


@data_factory_bp.route("/objects/<int:obj_id>", methods=["GET"])
def get_data_object(obj_id):
    """Get a data object with aggregated stats."""
    obj, err = _get_or_404(DataObject, obj_id, "DataObject")
    if err:
        return err
    d = obj.to_dict()
    d["task_count"] = obj.cleansing_tasks.count()
    d["load_count"] = obj.load_cycles.count()
    return jsonify(d)


@data_factory_bp.route("/objects/<int:obj_id>", methods=["PUT"])
def update_data_object(obj_id):
    """Update a data object."""
    obj, err = _get_or_404(DataObject, obj_id, "DataObject")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("name", "description", "source_system", "target_table",
              "record_count", "quality_score", "status", "owner", "owner_id"):
        if f in data:
            setattr(obj, f, data[f])
    db.session.commit()
    return jsonify(obj.to_dict())


@data_factory_bp.route("/objects/<int:obj_id>", methods=["DELETE"])
def delete_data_object(obj_id):
    """Delete a data object and its children."""
    obj, err = _get_or_404(DataObject, obj_id, "DataObject")
    if err:
        return err
    db.session.delete(obj)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════
# MigrationWave CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/waves", methods=["GET"])
def list_waves():
    """List migration waves, optionally filtered by program_id."""
    pid = request.args.get("program_id", type=int)
    q = MigrationWave.query
    if pid:
        q = q.filter_by(program_id=pid)
    q = q.order_by(MigrationWave.wave_number)
    items = q.all()
    return jsonify({"items": [w.to_dict() for w in items], "total": len(items)})


@data_factory_bp.route("/waves", methods=["POST"])
def create_wave():
    """Create a migration wave."""
    data = request.get_json(silent=True) or {}
    required = ("program_id", "wave_number", "name")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400

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
    return jsonify(wave.to_dict()), 201


@data_factory_bp.route("/waves/<int:wave_id>", methods=["GET"])
def get_wave(wave_id):
    """Get a wave with load cycle summary."""
    wave, err = _get_or_404(MigrationWave, wave_id, "MigrationWave")
    if err:
        return err
    d = wave.to_dict()
    cycles = wave.load_cycles.all()
    d["load_cycle_count"] = len(cycles)
    d["total_loaded"] = sum(c.records_loaded or 0 for c in cycles)
    d["total_failed"] = sum(c.records_failed or 0 for c in cycles)
    return jsonify(d)


@data_factory_bp.route("/waves/<int:wave_id>", methods=["PUT"])
def update_wave(wave_id):
    """Update a migration wave."""
    wave, err = _get_or_404(MigrationWave, wave_id, "MigrationWave")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("wave_number", "name", "description", "planned_start", "planned_end",
              "actual_start", "actual_end", "status"):
        if f in data:
            setattr(wave, f, data[f])
    db.session.commit()
    return jsonify(wave.to_dict())


@data_factory_bp.route("/waves/<int:wave_id>", methods=["DELETE"])
def delete_wave(wave_id):
    """Delete a migration wave."""
    wave, err = _get_or_404(MigrationWave, wave_id, "MigrationWave")
    if err:
        return err
    db.session.delete(wave)
    db.session.commit()
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════
# CleansingTask CRUD + run (6 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects/<int:obj_id>/tasks", methods=["GET"])
def list_cleansing_tasks(obj_id):
    """List cleansing tasks for a data object."""
    tasks = CleansingTask.query.filter_by(data_object_id=obj_id).all()
    return jsonify([t.to_dict() for t in tasks])


@data_factory_bp.route("/objects/<int:obj_id>/tasks", methods=["POST"])
def create_cleansing_task(obj_id):
    """Create a cleansing task."""
    obj, err = _get_or_404(DataObject, obj_id, "DataObject")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("rule_type") or not data.get("rule_expression"):
        return jsonify({"error": "rule_type and rule_expression are required"}), 400

    task = CleansingTask(
        data_object_id=obj_id,
        rule_type=data["rule_type"],
        rule_expression=data["rule_expression"],
        description=data.get("description"),
        status=data.get("status", "pending"),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@data_factory_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_cleansing_task(task_id):
    """Get a single cleansing task."""
    task, err = _get_or_404(CleansingTask, task_id, "CleansingTask")
    if err:
        return err
    return jsonify(task.to_dict())


@data_factory_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_cleansing_task(task_id):
    """Update a cleansing task."""
    task, err = _get_or_404(CleansingTask, task_id, "CleansingTask")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("rule_type", "rule_expression", "description", "pass_count",
              "fail_count", "status"):
        if f in data:
            setattr(task, f, data[f])
    db.session.commit()
    return jsonify(task.to_dict())


@data_factory_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_cleansing_task(task_id):
    """Delete a cleansing task."""
    task, err = _get_or_404(CleansingTask, task_id, "CleansingTask")
    if err:
        return err
    db.session.delete(task)
    db.session.commit()
    return jsonify({"deleted": True})


@data_factory_bp.route("/tasks/<int:task_id>/run", methods=["POST"])
def run_cleansing_task(task_id):
    """Simulate running a cleansing task (sets pass/fail counts)."""
    task, err = _get_or_404(CleansingTask, task_id, "CleansingTask")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    task.status = "running"
    db.session.commit()

    # Simulation: accept pass/fail from request or use defaults
    task.pass_count = data.get("pass_count", task.pass_count or 0)
    task.fail_count = data.get("fail_count", task.fail_count or 0)
    task.status = "passed" if (task.fail_count or 0) == 0 else "failed"
    task.last_run_at = _utcnow()
    db.session.commit()
    return jsonify(task.to_dict())


# ═════════════════════════════════════════════════════════════════════════
# LoadCycle CRUD + start/complete (7 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects/<int:obj_id>/loads", methods=["GET"])
def list_load_cycles(obj_id):
    """List load cycles for a data object."""
    cycles = LoadCycle.query.filter_by(data_object_id=obj_id).order_by(LoadCycle.id.desc()).all()
    return jsonify([c.to_dict() for c in cycles])


@data_factory_bp.route("/objects/<int:obj_id>/loads", methods=["POST"])
def create_load_cycle(obj_id):
    """Create a load cycle."""
    obj, err = _get_or_404(DataObject, obj_id, "DataObject")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    cycle = LoadCycle(
        data_object_id=obj_id,
        wave_id=data.get("wave_id"),
        environment=data.get("environment", "DEV"),
        load_type=data.get("load_type", "initial"),
        status="pending",
    )
    db.session.add(cycle)
    db.session.commit()
    return jsonify(cycle.to_dict()), 201


@data_factory_bp.route("/loads/<int:lc_id>", methods=["GET"])
def get_load_cycle(lc_id):
    """Get a load cycle with reconciliation summary."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    d = lc.to_dict()
    d["reconciliation_count"] = lc.reconciliations.count()
    return jsonify(d)


@data_factory_bp.route("/loads/<int:lc_id>", methods=["PUT"])
def update_load_cycle(lc_id):
    """Update a load cycle."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("wave_id", "environment", "load_type", "records_loaded",
              "records_failed", "status", "error_log"):
        if f in data:
            setattr(lc, f, data[f])
    db.session.commit()
    return jsonify(lc.to_dict())


@data_factory_bp.route("/loads/<int:lc_id>", methods=["DELETE"])
def delete_load_cycle(lc_id):
    """Delete a load cycle."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    db.session.delete(lc)
    db.session.commit()
    return jsonify({"deleted": True})


@data_factory_bp.route("/loads/<int:lc_id>/start", methods=["POST"])
def start_load_cycle(lc_id):
    """Mark a load cycle as running."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    if lc.status not in ("pending", "failed"):
        return jsonify({"error": f"Cannot start from status '{lc.status}'"}), 400
    lc.status = "running"
    lc.started_at = _utcnow()
    db.session.commit()
    return jsonify(lc.to_dict())


@data_factory_bp.route("/loads/<int:lc_id>/complete", methods=["POST"])
def complete_load_cycle(lc_id):
    """Mark a load cycle as completed or failed."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    lc.records_loaded = data.get("records_loaded", lc.records_loaded or 0)
    lc.records_failed = data.get("records_failed", lc.records_failed or 0)
    lc.error_log = data.get("error_log", lc.error_log)
    lc.status = "failed" if (lc.records_failed or 0) > 0 else "completed"
    lc.completed_at = _utcnow()
    db.session.commit()
    return jsonify(lc.to_dict())


# ═════════════════════════════════════════════════════════════════════════
# Reconciliation CRUD + calculate (6 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/loads/<int:lc_id>/recons", methods=["GET"])
def list_reconciliations(lc_id):
    """List reconciliations for a load cycle."""
    recons = Reconciliation.query.filter_by(load_cycle_id=lc_id).all()
    return jsonify([r.to_dict() for r in recons])


@data_factory_bp.route("/loads/<int:lc_id>/recons", methods=["POST"])
def create_reconciliation(lc_id):
    """Create a reconciliation record."""
    lc, err = _get_or_404(LoadCycle, lc_id, "LoadCycle")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    recon = Reconciliation(
        load_cycle_id=lc_id,
        source_count=data.get("source_count", 0),
        target_count=data.get("target_count", 0),
        match_count=data.get("match_count", 0),
        status="pending",
    )
    db.session.add(recon)
    db.session.commit()
    return jsonify(recon.to_dict()), 201


@data_factory_bp.route("/recons/<int:recon_id>", methods=["GET"])
def get_reconciliation(recon_id):
    """Get a reconciliation."""
    recon, err = _get_or_404(Reconciliation, recon_id, "Reconciliation")
    if err:
        return err
    return jsonify(recon.to_dict())


@data_factory_bp.route("/recons/<int:recon_id>", methods=["PUT"])
def update_reconciliation(recon_id):
    """Update a reconciliation."""
    recon, err = _get_or_404(Reconciliation, recon_id, "Reconciliation")
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for f in ("source_count", "target_count", "match_count", "status", "notes"):
        if f in data:
            setattr(recon, f, data[f])
    db.session.commit()
    return jsonify(recon.to_dict())


@data_factory_bp.route("/recons/<int:recon_id>", methods=["DELETE"])
def delete_reconciliation(recon_id):
    """Delete a reconciliation."""
    recon, err = _get_or_404(Reconciliation, recon_id, "Reconciliation")
    if err:
        return err
    db.session.delete(recon)
    db.session.commit()
    return jsonify({"deleted": True})


@data_factory_bp.route("/recons/<int:recon_id>/calculate", methods=["POST"])
def calculate_reconciliation(recon_id):
    """Calculate variance and update status."""
    recon, err = _get_or_404(Reconciliation, recon_id, "Reconciliation")
    if err:
        return err
    recon.variance = recon.source_count - recon.target_count
    if recon.source_count > 0:
        recon.variance_pct = round(abs(recon.variance) / recon.source_count * 100, 2)
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
    return jsonify(recon.to_dict())


# ═════════════════════════════════════════════════════════════════════════
# Dashboard endpoints (2 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/quality-score", methods=["GET"])
def quality_score_dashboard():
    """Aggregate quality score across data objects for a program."""
    pid = request.args.get("program_id", type=int)
    if not pid:
        return jsonify({"error": "program_id is required"}), 400

    objects = DataObject.query.filter_by(program_id=pid).all()
    if not objects:
        return jsonify({
            "total_objects": 0, "avg_quality_score": 0,
            "by_status": {}, "objects": [],
        })

    scores = [o.quality_score for o in objects if o.quality_score is not None]
    avg = round(sum(scores) / len(scores), 2) if scores else 0

    by_status = {}
    for o in objects:
        by_status.setdefault(o.status, 0)
        by_status[o.status] += 1

    return jsonify({
        "total_objects": len(objects),
        "avg_quality_score": avg,
        "by_status": by_status,
        "objects": [
            {"id": o.id, "name": o.name, "quality_score": o.quality_score, "status": o.status}
            for o in objects
        ],
    })


@data_factory_bp.route("/cycle-comparison", methods=["GET"])
def cycle_comparison_dashboard():
    """Compare load cycles across environments for a program."""
    pid = request.args.get("program_id", type=int)
    if not pid:
        return jsonify({"error": "program_id is required"}), 400

    obj_ids = [o.id for o in DataObject.query.filter_by(program_id=pid).all()]
    if not obj_ids:
        return jsonify({"environments": {}, "total_cycles": 0})

    cycles = LoadCycle.query.filter(LoadCycle.data_object_id.in_(obj_ids)).all()

    by_env = {}
    for c in cycles:
        env = c.environment or "UNKNOWN"
        if env not in by_env:
            by_env[env] = {"total": 0, "completed": 0, "failed": 0,
                           "records_loaded": 0, "records_failed": 0}
        by_env[env]["total"] += 1
        if c.status == "completed":
            by_env[env]["completed"] += 1
        elif c.status == "failed":
            by_env[env]["failed"] += 1
        by_env[env]["records_loaded"] += c.records_loaded or 0
        by_env[env]["records_failed"] += c.records_failed or 0

    return jsonify({
        "environments": by_env,
        "total_cycles": len(cycles),
    })
