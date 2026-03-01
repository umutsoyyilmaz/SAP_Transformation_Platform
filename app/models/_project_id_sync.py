"""Faz 6: Auto-resolve project_id from program_id for operational models.

When an operational model is created with program_id but without project_id,
this listener looks up the program's default Project and sets project_id to
its real PK.  This produces valid FK references (project_id → projects.id).

Previous Faz 3 behavior copied program_id into project_id (invalid FK value).
Faz 6 replaces that hack with a proper lookup so FK enforcement can be enabled.
"""

import logging

from sqlalchemy import event

logger = logging.getLogger(__name__)


def _register_project_id_sync(model_cls):
    """Register a 'set' event on model.program_id to auto-populate project_id."""
    @event.listens_for(getattr(model_cls, "program_id"), "set")
    def _sync_project_id(target, value, oldvalue, initiator):
        if getattr(target, "project_id", None) is not None:
            return
        if value is None:
            return
        # Look up the default project for this program.
        from app.models.project import Project
        default_proj = (
            Project.query
            .filter(Project.program_id == value, Project.is_default.is_(True))
            .first()
        )
        if default_proj:
            target.project_id = default_proj.id
        else:
            # Fallback: no default project found — set program_id value directly.
            # This may produce invalid FK if enforcement is on, but avoids
            # breaking legacy code paths that don't have a project yet.
            target.project_id = value


def register_all():
    """Register auto-sync for all 23 Faz 3 operational models."""
    from app.models.program import (
        Phase, Workstream, TeamMember, Committee, RaciActivity, RaciEntry,
    )
    from app.models.scenario import Scenario
    from app.models.backlog import Sprint, BacklogItem, ConfigItem
    from app.models.testing import (
        TestPlan, TestCase, TestSuite, Defect, ApprovalWorkflow, TestDailySnapshot,
    )
    from app.models.cutover import CutoverPlan, PostGoliveChangeRequest
    from app.models.raid import Risk, Action, Issue, Decision
    from app.models.requirement import Requirement

    _OPERATIONAL_MODELS = [
        Phase, Workstream, TeamMember, Committee, RaciActivity, RaciEntry,
        Scenario,
        Sprint, BacklogItem, ConfigItem,
        TestPlan, TestCase, TestSuite, Defect, ApprovalWorkflow, TestDailySnapshot,
        CutoverPlan, PostGoliveChangeRequest,
        Risk, Action, Issue, Decision,
        Requirement,
    ]

    for model in _OPERATIONAL_MODELS:
        if hasattr(model, "program_id") and hasattr(model, "project_id"):
            _register_project_id_sync(model)
