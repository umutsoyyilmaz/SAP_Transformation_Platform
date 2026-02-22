"""
Explore Phase Management — Blueprint Package

Splits the monolithic explore_bp.py into cohesive sub-modules while
keeping a single Blueprint instance and preserving all URL routes.
"""

from flask import Blueprint

explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")

# Sub-module imports — each module registers routes on explore_bp
from app.blueprints.explore import workshops        # noqa: E402, F401
from app.blueprints.explore import process_levels   # noqa: E402, F401
from app.blueprints.explore import process_steps    # noqa: E402, F401
from app.blueprints.explore import requirements     # noqa: E402, F401
from app.blueprints.explore import open_items       # noqa: E402, F401
from app.blueprints.explore import supporting       # noqa: E402, F401
from app.blueprints.explore import catalog          # noqa: E402, F401
