"""
SAP Transformation Management Platform
Scope blueprint — Process (L2/L3) & Analysis CRUD endpoints.

Refactored hierarchy:
    Scenario (=L1) → Process L2 → Process L3 (scope/fit-gap) → Analysis
    ScopeItem table removed — L3 Process now carries scope attributes.
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models import db
from app.models.scope import (
    Analysis,
    Process,
    RequirementProcessMapping,
    PROCESS_LEVELS,
    SCOPE_DECISIONS,
    FIT_GAP_RESULTS,
    ANALYSIS_STATUSES,
    ANALYSIS_TYPES,
    COVERAGE_TYPES,
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
        # Only root-level (L2) processes — children loaded via relationship
        query = query.filter_by(parent_id=None)

    processes = query.order_by(Process.order, Process.id).all()
    return jsonify([p.to_dict(include_children=tree) for p in processes])


@scope_bp.route("/scenarios/<int:sid>/processes", methods=["POST"])
def create_process(sid):
    """Create a process (L2 or L3) under a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    level = data.get("level", "L2")
    if level not in PROCESS_LEVELS:
        return jsonify({"error": f"Invalid level. Must be one of {sorted(PROCESS_LEVELS)}"}), 400

    process = Process(
        scenario_id=sid,
        parent_id=data.get("parent_id"),
        name=data["name"],
        description=data.get("description", ""),
        level=level,
        process_id_code=data.get("process_id_code", ""),
        module=data.get("module", scenario.sap_module or ""),
        order=data.get("order", 0),
        # L3-specific fields
        code=data.get("code", ""),
        scope_decision=data.get("scope_decision", ""),
        fit_gap=data.get("fit_gap", ""),
        sap_tcode=data.get("sap_tcode", ""),
        sap_reference=data.get("sap_reference", ""),
        priority=data.get("priority", ""),
        notes=data.get("notes", ""),
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
    result = process.to_dict(include_children=include)

    # For L3, include analyses and requirement mappings
    if process.level == "L3":
        result["analyses"] = [a.to_dict() for a in process.analyses]
        result["requirement_mappings"] = [
            {**m.to_dict(), "requirement_code": m.requirement.code if m.requirement else "",
             "requirement_title": m.requirement.title if m.requirement else ""}
            for m in process.requirement_mappings
        ]

    return jsonify(result)


@scope_bp.route("/processes/<int:pid>", methods=["PUT"])
def update_process(pid):
    """Update a process."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "process_id_code", "module",
                  "code", "sap_tcode", "sap_reference", "priority", "notes"):
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
    if "scope_decision" in data:
        if data["scope_decision"] and data["scope_decision"] not in SCOPE_DECISIONS:
            return jsonify({"error": f"Invalid scope_decision. Must be one of {sorted(SCOPE_DECISIONS)}"}), 400
        process.scope_decision = data["scope_decision"]
    if "fit_gap" in data:
        if data["fit_gap"] and data["fit_gap"] not in FIT_GAP_RESULTS:
            return jsonify({"error": f"Invalid fit_gap. Must be one of {sorted(FIT_GAP_RESULTS)}"}), 400
        process.fit_gap = data["fit_gap"]

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
    by_scope = {}
    by_fit_gap = {}
    for p in procs:
        by_level.setdefault(p.level, 0)
        by_level[p.level] += 1
        if p.level == "L3":
            if p.scope_decision:
                by_scope[p.scope_decision] = by_scope.get(p.scope_decision, 0) + 1
            if p.fit_gap:
                by_fit_gap[p.fit_gap] = by_fit_gap.get(p.fit_gap, 0) + 1

    return jsonify({
        "total_processes": len(procs),
        "by_level": by_level,
        "by_scope_decision": by_scope,
        "by_fit_gap": by_fit_gap,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYSIS  /api/v1/processes/<pid>/analyses  (L3 process steps)
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/processes/<int:pid>/analyses", methods=["GET"])
def list_analyses(pid):
    """List analyses for a process (L3)."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404
    analyses = Analysis.query.filter_by(process_id=pid).order_by(Analysis.id).all()
    return jsonify([a.to_dict() for a in analyses])


@scope_bp.route("/processes/<int:pid>/analyses", methods=["POST"])
def create_analysis(pid):
    """Create an analysis under a process (L3)."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    analysis_type = data.get("analysis_type", "fit_gap")
    if analysis_type not in ANALYSIS_TYPES:
        return jsonify({"error": f"Invalid analysis_type. Must be one of {sorted(ANALYSIS_TYPES)}"}), 400

    status = data.get("status", "planned")
    if status not in ANALYSIS_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of {sorted(ANALYSIS_STATUSES)}"}), 400

    analysis = Analysis(
        process_id=pid,
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
    """Summary of analyses across all L3 processes in a scenario."""
    scenario = db.session.get(Scenario, sid)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404

    analyses = (
        Analysis.query
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
#  REQUIREMENT ↔ PROCESS MAPPING  (N:M junction)
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/processes/<int:pid>/requirement-mappings", methods=["GET"])
def list_requirement_mappings(pid):
    """List requirement mappings for an L3 process step."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404
    mappings = RequirementProcessMapping.query.filter_by(process_id=pid).all()
    result = []
    for m in mappings:
        d = m.to_dict()
        if m.requirement:
            d["requirement_code"] = m.requirement.code
            d["requirement_title"] = m.requirement.title
        result.append(d)
    return jsonify(result)


@scope_bp.route("/processes/<int:pid>/requirement-mappings", methods=["POST"])
def create_requirement_mapping(pid):
    """Map a requirement to an L3 process step."""
    process = db.session.get(Process, pid)
    if not process:
        return jsonify({"error": "Process not found"}), 404

    data = request.get_json(silent=True) or {}
    req_id = data.get("requirement_id")
    if not req_id:
        return jsonify({"error": "requirement_id is required"}), 400

    from app.models.requirement import Requirement
    req = db.session.get(Requirement, req_id)
    if not req:
        return jsonify({"error": "Requirement not found"}), 404

    coverage = data.get("coverage_type", "full")
    if coverage not in COVERAGE_TYPES:
        return jsonify({"error": f"Invalid coverage_type. Must be one of {sorted(COVERAGE_TYPES)}"}), 400

    # Check for duplicate
    existing = RequirementProcessMapping.query.filter_by(
        requirement_id=req_id, process_id=pid
    ).first()
    if existing:
        return jsonify({"error": "Mapping already exists"}), 409

    mapping = RequirementProcessMapping(
        requirement_id=req_id,
        process_id=pid,
        coverage_type=coverage,
        notes=data.get("notes", ""),
    )
    db.session.add(mapping)
    db.session.commit()
    return jsonify(mapping.to_dict()), 201


@scope_bp.route("/requirement-mappings/<int:mid>", methods=["PUT"])
def update_requirement_mapping(mid):
    """Update a requirement-process mapping."""
    mapping = db.session.get(RequirementProcessMapping, mid)
    if not mapping:
        return jsonify({"error": "Mapping not found"}), 404

    data = request.get_json(silent=True) or {}
    if "coverage_type" in data:
        if data["coverage_type"] not in COVERAGE_TYPES:
            return jsonify({"error": f"Invalid coverage_type. Must be one of {sorted(COVERAGE_TYPES)}"}), 400
        mapping.coverage_type = data["coverage_type"]
    if "notes" in data:
        mapping.notes = data["notes"]

    db.session.commit()
    return jsonify(mapping.to_dict())


@scope_bp.route("/requirement-mappings/<int:mid>", methods=["DELETE"])
def delete_requirement_mapping(mid):
    """Remove a requirement-process mapping."""
    mapping = db.session.get(RequirementProcessMapping, mid)
    if not mapping:
        return jsonify({"error": "Mapping not found"}), 404
    db.session.delete(mapping)
    db.session.commit()
    return jsonify({"message": "Mapping deleted"}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM-LEVEL — Scope Matrix & Analysis Dashboard
# ═══════════════════════════════════════════════════════════════════════════

@scope_bp.route("/programs/<int:pid>/scope-matrix", methods=["GET"])
def scope_matrix(pid):
    """Flat L3 process-step matrix across all scenarios in a program.

    Returns every L3 process step with its parent L2, scenario name,
    and latest analysis result — used by the Analysis Hub Scope Matrix tab.
    """
    from app.models.program import Program
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    # All L3 processes under this program's scenarios
    rows = (
        db.session.query(Process, Scenario)
        .join(Scenario, Process.scenario_id == Scenario.id)
        .filter(Scenario.program_id == pid, Process.level == "L3")
        .order_by(Scenario.name, Process.order, Process.id)
        .all()
    )

    result = []
    for proc, scen in rows:
        # Get parent L2 name
        parent_l2 = db.session.get(Process, proc.parent_id) if proc.parent_id else None
        # Analyses for this L3
        analyses = Analysis.query.filter_by(process_id=proc.id)\
            .order_by(Analysis.id.desc()).all()
        latest = analyses[0] if analyses else None
        result.append({
            **proc.to_dict(),
            "parent_l2_name": parent_l2.name if parent_l2 else "",
            "parent_l2_id": parent_l2.id if parent_l2 else None,
            "scenario_id": scen.id,
            "scenario_name": scen.name,
            "sap_module": scen.sap_module or proc.module,
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

    # All L3 process steps
    l3_procs = (
        Process.query
        .join(Scenario, Process.scenario_id == Scenario.id)
        .filter(Scenario.program_id == pid, Process.level == "L3")
        .all()
    )

    total_l3 = len(l3_procs)
    analyzed = 0
    by_module = {}
    by_module_analyzed = {}
    by_scope = {}
    by_fit_gap_l3 = {}

    for p in l3_procs:
        mod = p.module or "Unassigned"
        by_module[mod] = by_module.get(mod, 0) + 1
        if p.scope_decision:
            by_scope[p.scope_decision] = by_scope.get(p.scope_decision, 0) + 1
        if p.fit_gap:
            by_fit_gap_l3[p.fit_gap] = by_fit_gap_l3.get(p.fit_gap, 0) + 1

        has_analysis = Analysis.query.filter_by(process_id=p.id)\
            .filter(Analysis.status == "completed").first()
        if has_analysis:
            analyzed += 1
            by_module_analyzed[mod] = by_module_analyzed.get(mod, 0) + 1

    # All analyses
    all_analyses = (
        Analysis.query
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

    # Open items count
    from app.models.requirement import Requirement, OpenItem
    total_open_items = (
        OpenItem.query
        .join(Requirement)
        .filter(Requirement.program_id == pid, OpenItem.status.in_(["open", "in_progress"]))
        .count()
    )
    blocker_count = (
        OpenItem.query
        .join(Requirement)
        .filter(Requirement.program_id == pid, OpenItem.blocker == True, OpenItem.status == "open")
        .count()
    )

    return jsonify({
        "total_l3_steps": total_l3,
        "analyzed_l3_steps": analyzed,
        "coverage_pct": round((analyzed / total_l3 * 100), 1) if total_l3 > 0 else 0,
        "total_analyses": len(all_analyses),
        "total_workshops": len(all_workshops),
        "by_fit_gap": by_fit_gap,
        "by_scope_decision": by_scope,
        "by_fit_gap_l3": by_fit_gap_l3,
        "by_module": by_module,
        "by_module_analyzed": by_module_analyzed,
        "by_analysis_type": by_analysis_type,
        "by_analysis_status": by_analysis_status,
        "by_workshop_status": ws_by_status,
        "pending_decisions": pending_decisions,
        "total_open_items": total_open_items,
        "blocker_open_items": blocker_count,
    }), 200
