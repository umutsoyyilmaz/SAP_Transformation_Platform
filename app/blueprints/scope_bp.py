"""
SAP Transformation Management Platform
Scope blueprint — Process, ScopeItem, Analysis CRUD endpoints.

Architecture blueprint for Sprint 3's Explore phase:
    Scenario → Process (L1/L2/L3) → ScopeItem → Analysis
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.scope import (
    Analysis,
    Process,
    ScopeItem,
    PROCESS_LEVELS,
    SCOPE_ITEM_STATUSES,
    ANALYSIS_STATUSES,
    ANALYSIS_TYPES,
)
from app.models.scenario import Scenario

scope_bp = Blueprint("scope", __name__, url_prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

def _parse_date(val):
    """Parse ISO date string → date or None."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  PROCESS  /api/v1/scenarios/<sid>/processes
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/scenarios/<int:sid>/processes", methods=["GET"])
def list_processes(sid):
    """List processes for a scenario, optionally tree-shaped."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    tree = request.args.get("tree", "false").lower() == "true"
    level = request.args.get("level")

    query = Process.query.filter_by(scenario_id=sid)
    if level:
        query = query.filter_by(level=level)
    if tree:
        query = query.filter_by(parent_id=None)

    processes = query.order_by(Process.order, Process.id).all()
    return jsonify([p.to_dict(include_children=tree) for p in processes])


@scope_bp.route("/scenarios/<int:sid>/processes", methods=["POST"])
def create_process(sid):
    """Create a process under a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    level = data.get("level", "L1")
    if level not in PROCESS_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {sorted(PROCESS_LEVELS)}"}), 400

    process = Process(
        scenario_id=sid,
        parent_id=data.get("parent_id"),
        name=data["name"],
        description=data.get("description", ""),
        level=level,
        process_id_code=data.get("process_id_code", ""),
        module=data.get("module", ""),
        order=data.get("order", 0),
    )
    db.session.add(process)
    db.session.commit()
    return jsonify(process.to_dict()), 201


@scope_bp.route("/processes/<int:pid>", methods=["GET"])
def get_process(pid):
    """Get single process with optional children tree."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404
    include = request.args.get("include_children", "false").lower() == "true"
    return jsonify(process.to_dict(include_children=include))


@scope_bp.route("/processes/<int:pid>", methods=["PUT"])
def update_process(pid):
    """Update a process."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "process_id_code", "module"):
        if field in data:
            setattr(process, field, data[field])
    if "level" in data:
        if data["level"] not in PROCESS_LEVELS:
            return jsonify({"error": f"Invalid level. Must be one of {sorted(PROCESS_LEVELS)}"}), 400
        process.level = data["level"]
    if "parent_id" in data:
        process.parent_id = data["parent_id"]
    if "order" in data:
        process.order = data["order"]

    db.session.commit()
    return jsonify(process.to_dict())


@scope_bp.route("/processes/<int:pid>", methods=["DELETE"])
def delete_process(pid):
    """Delete a process and its children (cascading)."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404
    db.session.delete(process)
    db.session.commit()
    return jsonify({"message": "Process deleted"}), 200


# ── Process stats
@scope_bp.route("/scenarios/<int:sid>/processes/stats", methods=["GET"])
def process_stats(sid):
    """Aggregate stats for processes under a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    procs = Process.query.filter_by(scenario_id=sid).all()
    by_level = {}
    for p in procs:
        by_level.setdefault(p.level, 0)
        by_level[p.level] += 1

    total_scope = ScopeItem.query.join(Process).filter(Process.scenario_id == sid).count()
    return jsonify({
        "total_processes": len(procs),
        "by_level": by_level,
        "total_scope_items": total_scope,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  SCOPE ITEMS  /api/v1/processes/<pid>/scope-items
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/processes/<int:pid>/scope-items", methods=["GET"])
def list_scope_items(pid):
    """List scope items under a process, optionally enriched with latest analysis."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404
    status = request.args.get("status")
    include_analysis = request.args.get("include_analysis", "false").lower() == "true"
    query = ScopeItem.query.filter_by(process_id=pid)
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(ScopeItem.id).all()

    results = []
    for si in items:
        d = si.to_dict()
        if include_analysis:
            latest = (
                Analysis.query.filter_by(scope_item_id=si.id)
                .order_by(Analysis.updated_at.desc())
                .first()
            )
            d["latest_fit_gap"] = latest.fit_gap_result if latest else None
            d["latest_analysis_status"] = latest.status if latest else None
            d["analysis_count"] = si.analyses.count()
        results.append(d)
    return jsonify(results)


@scope_bp.route("/processes/<int:pid>/scope-items", methods=["POST"])
def create_scope_item(pid):
    """Create a scope item under a process."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    status = data.get("status", "in_scope")
    if status not in SCOPE_ITEM_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of {sorted(SCOPE_ITEM_STATUSES)}"}), 400

    item = ScopeItem(
        process_id=pid,
        code=data.get("code", ""),
        name=data["name"],
        description=data.get("description", ""),
        sap_reference=data.get("sap_reference", ""),
        status=status,
        priority=data.get("priority", "medium"),
        module=data.get("module", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@scope_bp.route("/scope-items/<int:siid>", methods=["GET"])
def get_scope_item(siid):
    """Get a single scope item with its analyses."""
    item = db.session.get(ScopeItem, siid)
    if not item:
        return jsonify({"error": "Scope item not found"}), 404
    result = item.to_dict()
    result["analyses"] = [a.to_dict() for a in item.analyses]
    return jsonify(result)


@scope_bp.route("/scope-items/<int:siid>", methods=["PUT"])
def update_scope_item(siid):
    """Update a scope item."""
    item = db.session.get(ScopeItem, siid)
    if not item:
        return jsonify({"error": "Scope item not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("code", "name", "description", "sap_reference", "priority", "module", "notes"):
        if field in data:
            setattr(item, field, data[field])
    if "status" in data:
        if data["status"] not in SCOPE_ITEM_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of {sorted(SCOPE_ITEM_STATUSES)}"}), 400
        item.status = data["status"]

    db.session.commit()
    return jsonify(item.to_dict())


@scope_bp.route("/scope-items/<int:siid>", methods=["DELETE"])
def delete_scope_item(siid):
    """Delete a scope item and its analyses (cascading)."""
    item = db.session.get(ScopeItem, siid)
    if not item:
        return jsonify({"error": "Scope item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Scope item deleted"}), 200


# ── Scope-item stats across a scenario
@scope_bp.route("/scenarios/<int:sid>/scope-items/summary", methods=["GET"])
def scope_item_summary(sid):
    """Summary of scope items across all processes in a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    items = (ScopeItem.query.join(Process).filter(Process.scenario_id == sid).all())
    by_status = {}
    by_module = {}
    by_priority = {}
    for i in items:
        by_status[i.status] = by_status.get(i.status, 0) + 1
        if i.module:
            by_module[i.module] = by_module.get(i.module, 0) + 1
        by_priority[i.priority] = by_priority.get(i.priority, 0) + 1

    return jsonify({
        "total": len(items),
        "by_status": by_status,
        "by_module": by_module,
        "by_priority": by_priority,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYSIS  /api/v1/scope-items/<siid>/analyses
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/scope-items/<int:siid>/analyses", methods=["GET"])
def list_analyses(siid):
    """List analyses for a scope item."""
    item = db.session.get(ScopeItem, siid)
    if not item:
        return jsonify({"error": "Scope item not found"}), 404
    analyses = Analysis.query.filter_by(scope_item_id=siid).order_by(Analysis.id).all()
    return jsonify([a.to_dict() for a in analyses])


@scope_bp.route("/scope-items/<int:siid>/analyses", methods=["POST"])
def create_analysis(siid):
    """Create an analysis / workshop under a scope item."""
    item = db.session.get(ScopeItem, siid)
    if not item:
        return jsonify({"error": "Scope item not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    analysis_type = data.get("analysis_type", "workshop")
    if analysis_type not in ANALYSIS_TYPES:
        return jsonify({"error": f"Invalid analysis_type. Must be one of {sorted(ANALYSIS_TYPES)}"}), 400

    status = data.get("status", "planned")
    if status not in ANALYSIS_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of {sorted(ANALYSIS_STATUSES)}"}), 400

    analysis = Analysis(
        scope_item_id=siid,
        name=data["name"],
        description=data.get("description", ""),
        analysis_type=analysis_type,
        status=status,
        fit_gap_result=data.get("fit_gap_result", ""),
        decision=data.get("decision", ""),
        attendees=data.get("attendees", ""),
        date=_parse_date(data.get("date")),
        notes=data.get("notes", ""),
        workshop_id=data.get("workshop_id"),
    )
    db.session.add(analysis)
    db.session.commit()
    return jsonify(analysis.to_dict()), 201


@scope_bp.route("/analyses/<int:aid>", methods=["GET"])
def get_analysis(aid):
    """Get a single analysis."""
    analysis = db.session.get(Analysis, aid)
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    return jsonify(analysis.to_dict())


@scope_bp.route("/analyses/<int:aid>", methods=["PUT"])
def update_analysis(aid):
    """Update an analysis."""
    analysis = db.session.get(Analysis, aid)
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "fit_gap_result", "decision", "attendees", "notes"):
        if field in data:
            setattr(analysis, field, data[field])
    if "analysis_type" in data:
        if data["analysis_type"] not in ANALYSIS_TYPES:
            return jsonify({"error": f"Invalid analysis_type. Must be one of {sorted(ANALYSIS_TYPES)}"}), 400
        analysis.analysis_type = data["analysis_type"]
    if "status" in data:
        if data["status"] not in ANALYSIS_STATUSES:
            return jsonify({"error": f"Invalid status. Must be one of {sorted(ANALYSIS_STATUSES)}"}), 400
        analysis.status = data["status"]
    if "date" in data:
        analysis.date = _parse_date(data["date"])
    if "workshop_id" in data:
        analysis.workshop_id = data["workshop_id"] if data["workshop_id"] else None

    db.session.commit()
    return jsonify(analysis.to_dict())


@scope_bp.route("/analyses/<int:aid>", methods=["DELETE"])
def delete_analysis(aid):
    """Delete an analysis."""
    analysis = db.session.get(Analysis, aid)
    if not analysis:
        return jsonify({"error": "Analysis not found"}), 404
    db.session.delete(analysis)
    db.session.commit()
    return jsonify({"message": "Analysis deleted"}), 200


# ── Analysis stats
@scope_bp.route("/scenarios/<int:sid>/analyses/summary", methods=["GET"])
def analysis_summary(sid):
    """Summary of analyses across all scope items in a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    analyses = (
        Analysis.query
        .join(ScopeItem)
        .join(Process)
        .filter(Process.scenario_id == sid)
        .all()
    )
    by_status = {}
    by_type = {}
    by_result = {}
    for a in analyses:
        by_status[a.status] = by_status.get(a.status, 0) + 1
        by_type[a.analysis_type] = by_type.get(a.analysis_type, 0) + 1
        if a.fit_gap_result:
            by_result[a.fit_gap_result] = by_result.get(a.fit_gap_result, 0) + 1

    return jsonify({
        "total": len(analyses),
        "by_status": by_status,
        "by_type": by_type,
        "by_fit_gap_result": by_result,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM-LEVEL — Scope Matrix & Analysis Dashboard
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/programs/<int:pid>/scope-matrix", methods=["GET"])
def scope_matrix(pid):
    """Flat scope-item matrix across all scenarios in a program.

    Returns every scope item with its parent process, scenario name,
    and latest analysis result — used by the Analysis Hub Scope Matrix tab.
    """
    from app.models.program import Program
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    # All processes under this program's scenarios
    rows = (
        db.session.query(ScopeItem, Process, Scenario)
        .join(Process, ScopeItem.process_id == Process.id)
        .join(Scenario, Process.scenario_id == Scenario.id)
        .filter(Scenario.program_id == pid)
        .order_by(Scenario.name, Process.level, Process.order, ScopeItem.id)
        .all()
    )

    result = []
    for si, proc, scen in rows:
        # Get analyses for this scope item
        analyses = Analysis.query.filter_by(scope_item_id=si.id)\
            .order_by(Analysis.id.desc()).all()
        latest = analyses[0] if analyses else None
        result.append({
            **si.to_dict(),
            "process_name": proc.name,
            "process_level": proc.level,
            "process_id_code": proc.process_id_code,
            "scenario_id": scen.id,
            "scenario_name": scen.name,
            "sap_module": scen.sap_module or si.module,
            "analysis_count": len(analyses),
            "latest_fit_gap": latest.fit_gap_result if latest else None,
            "latest_analysis_status": latest.status if latest else None,
            "analyses": [a.to_dict() for a in analyses],
        })

    return jsonify(result), 200


@scope_bp.route("/programs/<int:pid>/analysis-dashboard", methods=["GET"])
def analysis_dashboard(pid):
    """Aggregated KPIs for the Analysis Hub dashboard tab."""
    from app.models.program import Program
    from app.models.scenario import Workshop
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    # All scope items
    all_items = (
        db.session.query(ScopeItem, Process, Scenario)
        .join(Process, ScopeItem.process_id == Process.id)
        .join(Scenario, Process.scenario_id == Scenario.id)
        .filter(Scenario.program_id == pid)
        .all()
    )

    total_items = len(all_items)
    analyzed = 0
    by_module = {}
    by_module_analyzed = {}
    by_status = {}

    for si, proc, scen in all_items:
        mod = scen.sap_module or si.module or "Unassigned"
        by_module[mod] = by_module.get(mod, 0) + 1
        by_status[si.status] = by_status.get(si.status, 0) + 1

        has_analysis = Analysis.query.filter_by(scope_item_id=si.id)\
            .filter(Analysis.status == "completed").first()
        if has_analysis:
            analyzed += 1
            by_module_analyzed[mod] = by_module_analyzed.get(mod, 0) + 1

    # All analyses
    all_analyses = (
        Analysis.query
        .join(ScopeItem)
        .join(Process)
        .join(Scenario)
        .filter(Scenario.program_id == pid)
        .all()
    )

    by_fit_gap = {}
    by_analysis_type = {}
    by_analysis_status = {}
    pending_decisions = 0

    for a in all_analyses:
        if a.fit_gap_result:
            by_fit_gap[a.fit_gap_result] = by_fit_gap.get(a.fit_gap_result, 0) + 1
        by_analysis_type[a.analysis_type] = by_analysis_type.get(a.analysis_type, 0) + 1
        by_analysis_status[a.status] = by_analysis_status.get(a.status, 0) + 1
        if a.status == "completed" and not a.decision:
            pending_decisions += 1

    # All workshops
    all_workshops = (
        Workshop.query
        .join(Scenario)
        .filter(Scenario.program_id == pid)
        .all()
    )
    ws_by_status = {}
    for w in all_workshops:
        ws_by_status[w.status] = ws_by_status.get(w.status, 0) + 1

    # Gap items without requirements
    gap_analyses = [a for a in all_analyses if a.fit_gap_result == "gap"]
    # Count requirements linked to workshops
    from app.models.requirement import Requirement
    gap_no_req = 0
    for ga in gap_analyses:
        scope_item = db.session.get(ScopeItem, ga.scope_item_id)
        if scope_item:
            # Check if any requirement references this scope item through workshop
            req_count = Requirement.query.filter_by(workshop_id=ga.workshop_id).count() if ga.workshop_id else 0
            if req_count == 0:
                gap_no_req += 1

    return jsonify({
        "total_scope_items": total_items,
        "analyzed_scope_items": analyzed,
        "coverage_pct": round((analyzed / total_items * 100), 1) if total_items > 0 else 0,
        "total_analyses": len(all_analyses),
        "total_workshops": len(all_workshops),
        "by_fit_gap": by_fit_gap,
        "by_module": by_module,
        "by_module_analyzed": by_module_analyzed,
        "by_scope_status": by_status,
        "by_analysis_type": by_analysis_type,
        "by_analysis_status": by_analysis_status,
        "by_workshop_status": ws_by_status,
        "pending_decisions": pending_decisions,
        "gap_without_requirement": gap_no_req,
    }), 200
