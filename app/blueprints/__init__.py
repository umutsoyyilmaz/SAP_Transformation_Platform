"""
SAP Transformation Management Platform
Blueprint registry.
"""

from flask import request


def paginate_query(query, default_limit=200, max_limit=1000):
    """Apply limit/offset pagination to a SQLAlchemy query.

    Query params:
        limit  — max items (default 200, capped at max_limit)
        offset — starting position (default 0)

    Returns:
        (items_list, total_count)
    """
    total = query.count()
    try:
        limit = min(int(request.args.get("limit", default_limit)), max_limit)
    except (ValueError, TypeError):
        limit = default_limit
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        offset = 0
    items = query.limit(limit).offset(offset).all()
    return items, total
