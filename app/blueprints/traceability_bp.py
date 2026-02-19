"""
SAP Transformation Management Platform
Unified Traceability API — Full SAP Activate Chain.

Single endpoint for all entity types:
    GET /api/v1/traceability/<entity_type>/<entity_id>

Supported entity_type values:
    scenario, workshop, process, analysis, requirement,
    explore_requirement, backlog_item, config_item,
    functional_spec, technical_spec, test_case, defect,
    interface, wave, connectivity_test, switch_plan

Wraps the existing get_chain() and trace_explore_requirement() service
functions — does NOT modify them.
"""

from flask import Blueprint, jsonify, request

from app.services.traceability import (
    build_explore_lateral,
    build_lateral_links,
    get_chain,
    trace_explore_requirement,
)

traceability_bp = Blueprint("traceability", __name__, url_prefix="/api/v1")


# ── Main endpoint ────────────────────────────────────────────────────────────

@traceability_bp.route("/traceability/<entity_type>/<entity_id>", methods=["GET"])
def unified_trace(entity_type, entity_id):
    """
    Unified traceability endpoint.

    Returns the full upstream + downstream chain for any entity,
    plus lateral links, chain depth (1-6), and gap detection.

    Query params:
        depth          — max traversal depth (default 10, max 20)
        include_lateral — include Open Items, Decisions, Interfaces (default true)
    """
    try:
        max_depth = min(int(request.args.get("depth", 10)), 20)
    except (ValueError, TypeError):
        max_depth = 10

    include_lateral = request.args.get("include_lateral", "true").lower() == "true"

    # ── ExploreRequirement (string IDs like "REQ-014") ───────────────────
    if entity_type == "explore_requirement":
        return _handle_explore_requirement(entity_id, include_lateral)

    # ── Standard entities (integer IDs) ──────────────────────────────────
    try:
        eid = int(entity_id)
    except (ValueError, TypeError):
        return jsonify({"error": f"Invalid entity_id: {entity_id}"}), 400

    chain = get_chain(entity_type, eid)
    if chain is None:
        return jsonify({"error": f"{entity_type} with id {eid} not found"}), 404

    # ── Backlog Item: enrich upstream with ExploreRequirement chain ───────
    if entity_type in ("backlog_item", "config_item"):
        _enrich_backlog_upstream(entity_type, eid, chain)

    # Enhance with lateral links
    if include_lateral:
        chain["lateral"] = _build_lateral_links(entity_type, eid)

    # Chain depth & gap detection
    chain["chain_depth"] = _calculate_chain_depth(chain)
    chain["gaps"] = _find_gaps_in_chain(entity_type, eid, chain)

    return jsonify(chain), 200


# ══════════════════════════════════════════════════════════════════════════════
# Explore Requirement handler
# ══════════════════════════════════════════════════════════════════════════════

def _handle_explore_requirement(requirement_id, include_lateral):
    """Handle explore_requirement trace with upstream + lateral enrichment."""
    try:
        graph = trace_explore_requirement(requirement_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    # Enrich with upstream context (Workshop → ProcessLevel → Scenario)
    graph["upstream"] = _build_explore_upstream(requirement_id)

    # Lateral links
    if include_lateral:
        graph["lateral"] = _build_explore_lateral(requirement_id)

    # Full chain depth & gap detection
    graph["chain_depth"] = _calculate_explore_depth(graph)
    graph["gaps"] = _find_explore_gaps(graph)

    return jsonify(graph), 200


# ══════════════════════════════════════════════════════════════════════════════
# Backlog → Explore Requirement upstream enrichment
# ══════════════════════════════════════════════════════════════════════════════

def _enrich_backlog_upstream(entity_type, eid, chain):
    """
    If a BacklogItem/ConfigItem has an explore_requirement_id, prepend the full
    Explore upstream chain: Requirement → Workshop → ProcessStep → L4→L3→L2→L1.

    This bridges the gap between the Realize-phase backlog world and
    the Explore-phase requirement/workshop world.
    """
    from app.models import db
    from app.models.backlog import BacklogItem, ConfigItem
    from app.models.explore import ExploreRequirement

    Model = BacklogItem if entity_type == "backlog_item" else ConfigItem
    item = db.session.get(Model, eid)
    if not item:
        return

    req_id = getattr(item, "explore_requirement_id", None)
    if not req_id:
        return

    req = db.session.get(ExploreRequirement, req_id)
    if not req:
        return

    # Build the explore requirement node
    explore_upstream = [{
        "type": "explore_requirement",
        "id": req.id,
        "title": req.title,
        "code": req.code,
        "status": req.status,
        "priority": req.priority,
        "requirement_type": req.type,
    }]

    # Build the workshop → process level hierarchy
    explore_upstream.extend(_build_explore_upstream(req.id))

    # Prepend explore chain before existing upstream
    existing_upstream = chain.get("upstream", [])
    chain["upstream"] = explore_upstream + existing_upstream


# ══════════════════════════════════════════════════════════════════════════════
# Upstream builder — ExploreRequirement → Workshop → ProcessLevel hierarchy
# ══════════════════════════════════════════════════════════════════════════════

def _build_explore_upstream(requirement_id):
    """
    Build upstream context for an ExploreRequirement.

    Chain: ExploreRequirement
            → Workshop (explore_workshops)
            → ProcessStep → ProcessLevel (L4 → L3 → L2 → L1)
            → Scope Item (L3 denormalized)
    """
    from app.models import db
    from app.models.explore import ExploreRequirement, ExploreWorkshop, ProcessStep, ProcessLevel

    req = db.session.get(ExploreRequirement, requirement_id)
    if not req:
        return []

    upstream = []

    # ── Workshop link ────────────────────────────────────────────────────
    if req.workshop_id:
        ws = db.session.get(ExploreWorkshop, req.workshop_id)
        if ws:
            upstream.append({
                "type": "workshop",
                "id": ws.id,
                "title": ws.name,
                "code": ws.code,
                "status": ws.status,
                "process_area": ws.process_area,
            })

    # ── Process Step → Process Level hierarchy ───────────────────────────
    if req.process_step_id:
        ps = db.session.get(ProcessStep, req.process_step_id)
        if ps:
            upstream.append({
                "type": "process_step",
                "id": ps.id,
                "title": ps.process_level.name if ps.process_level else f"Step {ps.id[:8]}",
                "fit_decision": ps.fit_decision,
            })
            # Walk up ProcessLevel hierarchy: L4 → L3 → L2 → L1
            if ps.process_level_id:
                _walk_process_level_hierarchy(ps.process_level_id, upstream)

    elif req.process_level_id:
        # Direct L4 link (no process step)
        _walk_process_level_hierarchy(req.process_level_id, upstream)

    # ── Scope Item (L3 denormalized) ─────────────────────────────────────
    if req.scope_item_id and req.scope_item_id != req.process_level_id:
        pl = db.session.get(ProcessLevel, req.scope_item_id)
        if pl:
            # Only add if not already in upstream
            existing_ids = {item.get("id") for item in upstream}
            if pl.id not in existing_ids:
                upstream.append({
                    "type": "scope_item",
                    "id": pl.id,
                    "title": pl.name,
                    "code": pl.code,
                    "level": pl.level,
                    "scope_item_code": pl.scope_item_code,
                })

    return upstream


def _walk_process_level_hierarchy(process_level_id, upstream):
    """Walk up Process Level tree: L4 → L3 → L2 → L1."""
    from app.models import db
    from app.models.explore import ProcessLevel

    seen = set()
    current_id = process_level_id

    while current_id and current_id not in seen:
        seen.add(current_id)
        pl = db.session.get(ProcessLevel, current_id)
        if not pl:
            break

        existing_ids = {item.get("id") for item in upstream}
        if pl.id not in existing_ids:
            upstream.append({
                "type": f"process_l{pl.level}" if pl.level else "process_level",
                "id": pl.id,
                "title": pl.name,
                "code": pl.code,
                "level": pl.level,
                "scope_status": pl.scope_status,
                "fit_status": pl.fit_status,
            })

        current_id = pl.parent_id


# ══════════════════════════════════════════════════════════════════════════════
# Lateral links — Open Items, Decisions, Interfaces
# ══════════════════════════════════════════════════════════════════════════════

def _build_explore_lateral(requirement_id):
    """Delegate to service layer — kept for backward-compatibility with existing callers."""
    return build_explore_lateral(requirement_id)


def _build_lateral_links(entity_type, entity_id):
    """Delegate to service layer — kept for backward-compatibility with existing callers."""
    return build_lateral_links(entity_type, entity_id)


# ══════════════════════════════════════════════════════════════════════════════
# Chain depth calculation (1-6 SAP Activate scale)
# ══════════════════════════════════════════════════════════════════════════════

def _calculate_explore_depth(graph):
    """
    Calculate chain depth for an ExploreRequirement graph (1-6 scale).

    1 = Requirement only
    2 = + WRICEF / Config items
    3 = + FS/TS (not tracked via explore trace, so skip)
    4 = + Test Cases
    5 = + Defects
    6 = Full chain with upstream (Workshop / ProcessLevel)
    """
    depth = 1
    if graph.get("backlog_items") or graph.get("config_items"):
        depth = 2
    if graph.get("test_cases"):
        depth = max(depth, 4)
    if graph.get("defects"):
        depth = max(depth, 5)
    if graph.get("upstream"):
        depth = max(depth, 6)
    return depth


def _calculate_chain_depth(chain):
    """Calculate chain depth from a standard get_chain() result."""
    types_found = set()
    for item in chain.get("upstream", []) + chain.get("downstream", []):
        types_found.add(item.get("type"))

    depth = 1
    if "backlog_item" in types_found or "config_item" in types_found:
        depth = max(depth, 2)
    if "functional_spec" in types_found or "technical_spec" in types_found:
        depth = max(depth, 3)
    if "test_case" in types_found:
        depth = max(depth, 4)
    if "defect" in types_found:
        depth = max(depth, 5)
    # Standard scenarios or explore hierarchy = full upstream depth
    if ("scenario" in types_found or "process" in types_found
            or "explore_requirement" in types_found
            or "workshop" in types_found
            or any(t.startswith("process_l") for t in types_found)):
        depth = max(depth, 6)
    return depth


# ══════════════════════════════════════════════════════════════════════════════
# Gap detection — identify missing links in the chain
# ══════════════════════════════════════════════════════════════════════════════

def _find_explore_gaps(graph):
    """Identify where the chain breaks for an ExploreRequirement."""
    gaps = []

    if not graph.get("backlog_items") and not graph.get("config_items"):
        gaps.append({
            "level": 2,
            "message": "No WRICEF or Config items linked",
        })

    if (graph.get("backlog_items") or graph.get("config_items")) and not graph.get("test_cases"):
        gaps.append({
            "level": 4,
            "message": "No test cases found for linked items",
        })

    if graph.get("test_cases") and not graph.get("defects"):
        gaps.append({
            "level": 5,
            "message": "No defects recorded (may be expected if tests pass)",
        })

    if not graph.get("upstream"):
        gaps.append({
            "level": 0,
            "message": "Missing upstream context (Workshop / Process Level)",
        })

    return gaps


def _find_gaps_in_chain(entity_type, entity_id, chain):
    """Find gaps in a standard entity chain."""
    gaps = []
    types_found = set(
        item.get("type")
        for item in chain.get("upstream", []) + chain.get("downstream", [])
    )

    if entity_type in ("backlog_item", "config_item"):
        has_req = ("requirement" in types_found or "explore_requirement" in types_found)
        if not has_req:
            gaps.append({"level": "upstream", "message": "Not linked to a Requirement"})
        if "test_case" not in types_found:
            gaps.append({"level": "downstream", "message": "No Test Cases created"})
        if "functional_spec" not in types_found:
            gaps.append({"level": "downstream", "message": "No Functional Spec written"})

    elif entity_type == "requirement":
        if "backlog_item" not in types_found and "config_item" not in types_found:
            gaps.append({"level": "downstream", "message": "Not converted to WRICEF or Config item"})
        if "scenario" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Scenario"})

    elif entity_type == "test_case":
        if "requirement" not in types_found and "backlog_item" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Requirement or Backlog item"})

    elif entity_type == "functional_spec":
        if "backlog_item" not in types_found and "config_item" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a WRICEF or Config item"})
        if "technical_spec" not in types_found:
            gaps.append({"level": "downstream", "message": "No Technical Spec created"})

    elif entity_type == "interface":
        if "backlog_item" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Backlog item"})
        if "connectivity_test" not in types_found:
            gaps.append({"level": "downstream", "message": "No connectivity tests executed"})

    return gaps
