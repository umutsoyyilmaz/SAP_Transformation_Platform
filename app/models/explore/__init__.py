"""
Explore Phase — Model Package

Re-exports all models from the five domain sub-modules so that existing
imports like ``from app.models.explore import ExploreWorkshop`` continue
to work without any change.
"""

from sqlalchemy import event

from app.models.explore.process import *          # noqa: F401,F403
from app.models.explore.workshop import *         # noqa: F401,F403
from app.models.explore.requirement import *      # noqa: F401,F403
from app.models.explore.governance import *       # noqa: F401,F403
from app.models.explore.infrastructure import *   # noqa: F401,F403

# Expose internal helpers that tests / scripts rely on
from app.models.explore.process import _uuid, _utcnow  # noqa: F401


# ── Faz 1.4: Transitional auto-sync project_id → program_id ─────────────────
# After Faz 1.4, project_id FK → projects.id (correct) and program_id FK →
# programs.id (correct). During the transition, many test fixtures and legacy
# code paths still create entities with project_id=<program_id_value>.
# Since SQLite doesn't enforce FK constraints, this works. The auto-sync
# copies the value into program_id so that .filter_by(program_id=X) queries
# continue to work. Will be removed in Faz 6 (cleanup) when all code paths
# properly set both columns independently.

def _register_program_id_sync(model_cls):
    """Register a 'set' event on model.project_id to auto-populate program_id."""
    @event.listens_for(getattr(model_cls, "project_id"), "set")
    def _sync(target, value, oldvalue, initiator):
        if getattr(target, "program_id", None) is None and value is not None:
            target.program_id = value


# Models with both project_id (FK → projects.id) and program_id (FK → programs.id):
_MODELS_WITH_DUAL_FK = [
    ProcessLevel,       # app/models/explore/process.py
    ExploreWorkshop,    # app/models/explore/workshop.py
    ExploreDecision,    # app/models/explore/requirement.py
    ExploreOpenItem,    # app/models/explore/requirement.py
    ExploreRequirement, # app/models/explore/requirement.py
    Attachment,         # app/models/explore/infrastructure.py
    ScopeChangeRequest, # app/models/explore/governance.py
    ScopeChangeLog,     # app/models/explore/governance.py
    ProjectRole,        # app/models/explore/governance.py
    PhaseGate,          # app/models/explore/governance.py
]

for _model in _MODELS_WITH_DUAL_FK:
    if hasattr(_model, "project_id") and hasattr(_model, "program_id"):
        _register_program_id_sync(_model)
