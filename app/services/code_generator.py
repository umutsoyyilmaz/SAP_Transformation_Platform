"""
Explore Phase — Auto-Code Generator Service

Generates sequential codes for:
  - Workshops:              WS-{area}-{seq}{letter}  (e.g. WS-SD-01, WS-FI-03A)
  - Requirements:           REQ-{seq}                (e.g. REQ-001, REQ-042)
  - Open Items:             OI-{seq}                 (e.g. OI-001, OI-137)
  - Decisions:              DEC-{seq}                (e.g. DEC-001, DEC-015)
  - Scope Change Requests:  SCR-{seq}                (e.g. SCR-001, SCR-008)

All codes are project-wide unique. Thread-safe via DB query + retry.
"""

from sqlalchemy import func

from app.models import db
from app.models.explore import (
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ScopeChangeRequest,
)

# ── Workshop code: WS-{area}-{seq}{letter} ──────────────────────────────────

def generate_workshop_code(project_id: int, process_area: str, session_number: int = 1) -> str:
    """
    Generate next workshop code for a given project + process area.
    Format: WS-{AREA}-{SEQ}{LETTER}
      - SEQ is 2-digit, area-scoped
      - LETTER is A/B/C for multi-session workshops (only if session_number > 1)

    Example: WS-SD-01, WS-FI-03A
    """
    area = process_area.upper()[:5]

    # Count existing workshops for this project+area
    count = (
        db.session.query(func.count(ExploreWorkshop.id))
        .filter(
            ExploreWorkshop.project_id == project_id,
            ExploreWorkshop.process_area == area,
            ExploreWorkshop.session_number == 1,  # count only first sessions
        )
        .scalar()
    ) or 0

    seq = count + 1
    code = f"WS-{area}-{seq:02d}"

    if session_number > 1:
        # A=1, B=2, C=3...
        letter = chr(64 + session_number)  # 65=A, but session 1 has no letter
        code += letter

    return code


# ── Sequential codes: prefix + 3-digit seq ──────────────────────────────────

def _generate_sequential_code(model_class, prefix: str, project_id: int) -> str:
    """Generate next sequential code: {PREFIX}-{SEQ:03d}."""
    # BacklogItem / ConfigItem use 'program_id' instead of 'project_id'
    id_col = getattr(model_class, "project_id", None) or getattr(model_class, "program_id")
    count = (
        db.session.query(func.count(model_class.id))
        .filter(id_col == project_id)
        .scalar()
    ) or 0

    seq = count + 1
    return f"{prefix}-{seq:03d}"


def generate_requirement_code(project_id: int) -> str:
    """Generate next requirement code: REQ-001, REQ-002, ..."""
    return _generate_sequential_code(ExploreRequirement, "REQ", project_id)


def generate_open_item_code(project_id: int) -> str:
    """Generate next open item code: OI-001, OI-002, ..."""
    return _generate_sequential_code(ExploreOpenItem, "OI", project_id)


def generate_decision_code(project_id: int) -> str:
    """Generate next decision code: DEC-001, DEC-002, ..."""
    return _generate_sequential_code(ExploreDecision, "DEC", project_id)


def generate_scope_change_code(project_id: int) -> str:
    """Generate next scope change request code: SCR-001, SCR-002, ..."""
    return _generate_sequential_code(ScopeChangeRequest, "SCR", project_id)


# ── Backlog / Config codes ───────────────────────────────────────────────────

_WRICEF_PREFIX = {
    "report": "RPT",
    "interface": "INT",
    "conversion": "CNV",
    "enhancement": "ENH",
    "form": "FRM",
    "workflow": "WFL",
}


def generate_backlog_item_code(project_id: int, wricef_type: str = "enhancement") -> str:
    """Generate next WRICEF backlog item code: ENH-001, INT-002, RPT-003, ..."""
    from app.models.backlog import BacklogItem  # lazy import — avoid circular
    prefix = _WRICEF_PREFIX.get(wricef_type, "ENH")
    return _generate_sequential_code(BacklogItem, prefix, project_id)


def generate_config_item_code(project_id: int) -> str:
    """Generate next config item code: CFG-001, CFG-002, ..."""
    from app.models.backlog import ConfigItem  # lazy import — avoid circular
    return _generate_sequential_code(ConfigItem, "CFG", project_id)
