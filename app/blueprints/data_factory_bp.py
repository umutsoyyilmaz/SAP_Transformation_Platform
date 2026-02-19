"""Data Factory Blueprint — Sprint 10.

31 routes for data migration lifecycle management.
All ORM operations are delegated to data_factory_service.

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
  TestDataSet:     GET/POST /data-factory/test-data-sets, GET/PUT/DELETE /data-factory/test-data-sets/<id>
  TestDataSetItem: GET/POST /data-factory/test-data-sets/<id>/items
                   PUT/DELETE /data-factory/test-data-set-items/<id>
"""

from flask import Blueprint, jsonify, request

from app.services import data_factory_service

data_factory_bp = Blueprint(
    "data_factory", __name__, url_prefix="/api/v1/data-factory",
)


# ═════════════════════════════════════════════════════════════════════════
# DataObject CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects", methods=["GET"])
def list_data_objects():
    """List data objects, optionally filtered by program_id and status."""
    pid = request.args.get("program_id", type=int)
    status = request.args.get("status")
    result = data_factory_service.list_data_objects(program_id=pid, status=status)
    return jsonify(result)


@data_factory_bp.route("/objects", methods=["POST"])
def create_data_object():
    """Create a new data object."""
    data = request.get_json(silent=True) or {}
    required = ("program_id", "name", "source_system")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400
    result = data_factory_service.create_data_object(data)
    return jsonify(result), 201


@data_factory_bp.route("/objects/<int:obj_id>", methods=["GET"])
def get_data_object(obj_id):
    """Get a data object with aggregated stats."""
    result, err = data_factory_service.get_data_object_with_stats(obj_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/objects/<int:obj_id>", methods=["PUT"])
def update_data_object(obj_id):
    """Update a data object."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_data_object(obj_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/objects/<int:obj_id>", methods=["DELETE"])
def delete_data_object(obj_id):
    """Delete a data object and its children."""
    err = data_factory_service.delete_data_object(obj_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════
# MigrationWave CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/waves", methods=["GET"])
def list_waves():
    """List migration waves, optionally filtered by program_id."""
    pid = request.args.get("program_id", type=int)
    result = data_factory_service.list_waves(program_id=pid)
    return jsonify(result)


@data_factory_bp.route("/waves", methods=["POST"])
def create_wave():
    """Create a migration wave."""
    data = request.get_json(silent=True) or {}
    required = ("program_id", "wave_number", "name")
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"{f} is required"}), 400
    result = data_factory_service.create_wave(data)
    return jsonify(result), 201


@data_factory_bp.route("/waves/<int:wave_id>", methods=["GET"])
def get_wave(wave_id):
    """Get a wave with load cycle summary."""
    result, err = data_factory_service.get_wave_with_stats(wave_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/waves/<int:wave_id>", methods=["PUT"])
def update_wave(wave_id):
    """Update a migration wave."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_wave(wave_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/waves/<int:wave_id>", methods=["DELETE"])
def delete_wave(wave_id):
    """Delete a migration wave."""
    err = data_factory_service.delete_wave(wave_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"deleted": True})


# ═════════════════════════════════════════════════════════════════════════
# CleansingTask CRUD + run (6 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects/<int:obj_id>/tasks", methods=["GET"])
def list_cleansing_tasks(obj_id):
    """List cleansing tasks for a data object."""
    result = data_factory_service.list_cleansing_tasks(obj_id)
    return jsonify(result)


@data_factory_bp.route("/objects/<int:obj_id>/tasks", methods=["POST"])
def create_cleansing_task(obj_id):
    """Create a cleansing task."""
    data = request.get_json(silent=True) or {}
    if not data.get("rule_type") or not data.get("rule_expression"):
        return jsonify({"error": "rule_type and rule_expression are required"}), 400
    result, err = data_factory_service.create_cleansing_task(obj_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@data_factory_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_cleansing_task(task_id):
    """Get a single cleansing task."""
    result, err = data_factory_service.get_cleansing_task(task_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_cleansing_task(task_id):
    """Update a cleansing task."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_cleansing_task(task_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_cleansing_task(task_id):
    """Delete a cleansing task."""
    err = data_factory_service.delete_cleansing_task(task_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"deleted": True})


@data_factory_bp.route("/tasks/<int:task_id>/run", methods=["POST"])
def run_cleansing_task(task_id):
    """Simulate running a cleansing task (sets pass/fail counts)."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.run_cleansing_task(task_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════
# LoadCycle CRUD + start/complete (7 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/objects/<int:obj_id>/loads", methods=["GET"])
def list_load_cycles(obj_id):
    """List load cycles for a data object."""
    result = data_factory_service.list_load_cycles(obj_id)
    return jsonify(result)


@data_factory_bp.route("/objects/<int:obj_id>/loads", methods=["POST"])
def create_load_cycle(obj_id):
    """Create a load cycle."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.create_load_cycle(obj_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@data_factory_bp.route("/loads/<int:lc_id>", methods=["GET"])
def get_load_cycle(lc_id):
    """Get a load cycle with reconciliation summary."""
    result, err = data_factory_service.get_load_cycle_with_stats(lc_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/loads/<int:lc_id>", methods=["PUT"])
def update_load_cycle(lc_id):
    """Update a load cycle."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_load_cycle(lc_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/loads/<int:lc_id>", methods=["DELETE"])
def delete_load_cycle(lc_id):
    """Delete a load cycle."""
    err = data_factory_service.delete_load_cycle(lc_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"deleted": True})


@data_factory_bp.route("/loads/<int:lc_id>/start", methods=["POST"])
def start_load_cycle(lc_id):
    """Mark a load cycle as running."""
    result, err = data_factory_service.start_load_cycle(lc_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/loads/<int:lc_id>/complete", methods=["POST"])
def complete_load_cycle(lc_id):
    """Mark a load cycle as completed or failed."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.complete_load_cycle(lc_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════
# Reconciliation CRUD + calculate (6 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/loads/<int:lc_id>/recons", methods=["GET"])
def list_reconciliations(lc_id):
    """List reconciliations for a load cycle."""
    result = data_factory_service.list_reconciliations(lc_id)
    return jsonify(result)


@data_factory_bp.route("/loads/<int:lc_id>/recons", methods=["POST"])
def create_reconciliation(lc_id):
    """Create a reconciliation record."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.create_reconciliation(lc_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@data_factory_bp.route("/recons/<int:recon_id>", methods=["GET"])
def get_reconciliation(recon_id):
    """Get a reconciliation."""
    result, err = data_factory_service.get_reconciliation(recon_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/recons/<int:recon_id>", methods=["PUT"])
def update_reconciliation(recon_id):
    """Update a reconciliation."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_reconciliation(recon_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/recons/<int:recon_id>", methods=["DELETE"])
def delete_reconciliation(recon_id):
    """Delete a reconciliation."""
    err = data_factory_service.delete_reconciliation(recon_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"deleted": True})


@data_factory_bp.route("/recons/<int:recon_id>/calculate", methods=["POST"])
def calculate_reconciliation(recon_id):
    """Calculate variance and update status."""
    result, err = data_factory_service.calculate_reconciliation(recon_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


# ═════════════════════════════════════════════════════════════════════════
# Dashboard endpoints (2 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/quality-score", methods=["GET"])
def quality_score_dashboard():
    """Aggregate quality score across data objects for a program."""
    pid = request.args.get("program_id", type=int)
    if not pid:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(data_factory_service.compute_quality_score(pid))


@data_factory_bp.route("/cycle-comparison", methods=["GET"])
def cycle_comparison_dashboard():
    """Compare load cycles across environments for a program."""
    pid = request.args.get("program_id", type=int)
    if not pid:
        return jsonify({"error": "program_id is required"}), 400
    return jsonify(data_factory_service.compute_cycle_comparison(pid))


# ═════════════════════════════════════════════════════════════════════════
# TestDataSet CRUD (5 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/test-data-sets", methods=["GET"])
def list_test_data_sets():
    """List test data sets with optional filters."""
    pid = request.args.get("program_id", type=int)
    status = request.args.get("status")
    environment = request.args.get("environment")
    result = data_factory_service.list_test_data_sets(
        program_id=pid, status=status, environment=environment,
    )
    return jsonify(result)


@data_factory_bp.route("/test-data-sets", methods=["POST"])
def create_test_data_set():
    """Create a new test data set."""
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("program_id"):
        return jsonify({"error": "name and program_id are required"}), 400
    result = data_factory_service.create_test_data_set(data)
    return jsonify(result), 201


@data_factory_bp.route("/test-data-sets/<int:ds_id>", methods=["GET"])
def get_test_data_set(ds_id):
    """Get data set detail with items."""
    result, err = data_factory_service.get_test_data_set_with_items(ds_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/test-data-sets/<int:ds_id>", methods=["PUT"])
def update_test_data_set(ds_id):
    """Update data set metadata or status."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_test_data_set(ds_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/test-data-sets/<int:ds_id>", methods=["DELETE"])
def delete_test_data_set(ds_id):
    """Delete a data set (cascades to items)."""
    err = data_factory_service.delete_test_data_set(ds_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"message": "Data set deleted"}), 200


# ═════════════════════════════════════════════════════════════════════════
# TestDataSetItem CRUD (4 routes)
# ═════════════════════════════════════════════════════════════════════════

@data_factory_bp.route("/test-data-sets/<int:ds_id>/items", methods=["GET"])
def list_data_set_items(ds_id):
    """List items in a data set."""
    result, err = data_factory_service.list_data_set_items(ds_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/test-data-sets/<int:ds_id>/items", methods=["POST"])
def add_data_set_item(ds_id):
    """Add a DataObject reference to data set."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.add_data_set_item(ds_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result), 201


@data_factory_bp.route("/test-data-set-items/<int:item_id>", methods=["PUT"])
def update_data_set_item(item_id):
    """Update data set item (status, actual_records, etc.)."""
    data = request.get_json(silent=True) or {}
    result, err = data_factory_service.update_data_set_item(item_id, data)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify(result)


@data_factory_bp.route("/test-data-set-items/<int:item_id>", methods=["DELETE"])
def delete_data_set_item(item_id):
    """Remove item from data set."""
    err = data_factory_service.delete_data_set_item(item_id)
    if err:
        return jsonify({"error": err["error"]}), err["status"]
    return jsonify({"message": "Item removed"}), 200
