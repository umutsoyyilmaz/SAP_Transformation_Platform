"""Shared utility functions — replaces 16 duplicate definitions across blueprints.

get_or_404:          8 copies → 1 (tuple-return pattern, NOT abort)
parse_date:          7 copies → 1 (returns None on bad input)
parse_date_input:    2 copies → 1 (raises ValueError on bad input, for explore)
db_commit_or_error:  Sprint 4 — replaces 148 uniform except-Exception blocks
"""
import logging
from datetime import date, datetime

from flask import jsonify

from app.models import db

logger = logging.getLogger(__name__)


def get_or_404(model, pk, label=None):
    """Fetch a model instance by primary key or return a 404 error tuple.

    Preserves the existing codebase pattern exactly:
    - Success: (obj, None)
    - Failure: (None, (jsonify_response, 404))

    This pattern is used in all 8 copies:
        obj, err = get_or_404(Program, pid)
        if err:
            return err

    NOTE: abort(404) is not used — the existing pattern is tuple-return.
    """
    label = label or model.__name__
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{label} not found"}), 404)
    return obj, None


def parse_date(value):
    """Parse a date string (ISO or DD.MM.YYYY) to a date object.

    Returns None for empty/invalid input. Supports:
    - YYYY-MM-DD (ISO format)
    - YYYY-MM-DDTHH:MM:SS (datetime ISO → .date())
    - DD.MM.YYYY (Turkish/European format)

    Replaces:
    - _parse_date() in backlog, testing, program, integration (date.fromisoformat)
    - _parse_date() in raid, scope (datetime.fromisoformat → .date())
    """
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        pass
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(str(value), "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None


def parse_date_input(value):
    """Parse a date string, raising ValueError on bad input.

    Same as parse_date() but raises ValueError instead of returning None.
    Used by explore blueprints where callers catch ValueError for 400 responses.

    Supports: YYYY-MM-DD, DD.MM.YYYY, date objects.
    """
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError as exc:
            raise ValueError(
                "Invalid date format. Use YYYY-MM-DD or DD.MM.YYYY."
            ) from exc


# ── Database commit helper ───────────────────────────────────────────────────

def db_commit_or_error():
    """Commit the current SQLAlchemy session, returning an error response on failure.

    Returns:
        None on success.
        (response, status_code) tuple on failure — ready for ``return``.

    Usage::

        err = db_commit_or_error()
        if err:
            return err

    Replaces the common 6-line try/except pattern found 148 times across
    blueprints:

        try:
            db.session.commit()
        except Exception:
            logger.exception("...")
            db.session.rollback()
            return jsonify({"error": "Database error"}), 500

    IntegrityError → 409 (duplicate / constraint violation)
    OperationalError → 500 (connection / lock issues)
    Other → 500 (unexpected)
    """
    from sqlalchemy.exc import IntegrityError, OperationalError

    try:
        db.session.commit()
        return None
    except IntegrityError as exc:
        db.session.rollback()
        logger.warning("Integrity error on commit: %s", exc.orig)
        return jsonify({"error": "Duplicate or constraint violation"}), 409
    except OperationalError:
        db.session.rollback()
        logger.exception("Database operational error on commit")
        return jsonify({"error": "Database error"}), 500
    except Exception:
        db.session.rollback()
        logger.exception("Unexpected database error on commit")
        return jsonify({"error": "Database error"}), 500
