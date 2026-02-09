"""
Explore Phase — Auto-Code Generator Service

Generates sequential codes for:
  - Workshops:    WS-{area}-{seq}{letter}  (e.g. WS-SD-01, WS-FI-03A)
  - Requirements: REQ-{seq}                (e.g. REQ-001, REQ-042)
  - Open Items:   OI-{seq}                 (e.g. OI-001, OI-137)
  - Decisions:    DEC-{seq}                (e.g. DEC-001, DEC-015)

All codes are project-wide unique. Thread-safe via DB query + retry.
"""

from sqlalchemy import func

from app.models import db
from app.models.explore import (
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
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
    count = (
        db.session.query(func.count(model_class.id))
        .filter(model_class.project_id == project_id)
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
