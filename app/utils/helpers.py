"""Shared utility functions — replaces 16 duplicate definitions across blueprints.

get_or_404:      8 copies → 1 (tuple-return pattern, NOT abort)
parse_date:      7 copies → 1 (returns None on bad input)
parse_date_input: 2 copies → 1 (raises ValueError on bad input, for explore)
"""
from datetime import date, datetime

from flask import jsonify

from app.models import db


def get_or_404(model, pk, label=None):
    """Fetch a model instance by primary key or return a 404 error tuple.

    Mevcut codebase pattern'ini birebir korur:
    - Başarılı: (obj, None)
    - Başarısız: (None, (jsonify_response, 404))

    Tüm 8 kopyada bu pattern kullanılıyor:
        obj, err = get_or_404(Program, pid)
        if err:
            return err

    NOT: abort(404) kullanılmıyor — mevcut pattern tuple-return.
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
