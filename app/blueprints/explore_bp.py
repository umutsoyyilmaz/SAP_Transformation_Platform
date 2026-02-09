"""
Explore Phase Management — API Blueprint (Phase 0 scaffold)

Will house all endpoints for:
  Module A: Process Hierarchy (GET/POST/PATCH/DELETE /process-levels/...)
  Module B: Workshop Hub (GET/POST/PATCH /workshops/...)
  Module C: Workshop Detail (process-steps, decisions within workshop)
  Module D: Requirements & Open Items (GET/POST/PATCH ...)
  Supplementary: Roles, Phase Gates, L4 Seed Catalog

Currently provides only health-check / metadata endpoints.
Full endpoint implementation follows EXPLORE_PHASE_TASK_LIST.md tasks A-001 → A-058.
"""

from flask import Blueprint, jsonify

explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")


@explore_bp.route("/health", methods=["GET"])
def explore_health():
    """Health check for Explore Phase module."""
    return jsonify({
        "module": "explore_phase",
        "status": "ok",
        "version": "0.1.0",
        "phase": 0,
    })
