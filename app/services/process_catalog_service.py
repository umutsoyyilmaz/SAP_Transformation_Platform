"""Service for SAP 1YG Process Catalog — load, browse, and seed.

This service manages the global (tenant-independent) SAP process catalog consisting
of L1→L2→L3→L4 hierarchy nodes. It provides three capabilities:

1. **Catalog loading** — upsert L1/L2/L3/L4 seed records from packaged JSON files.
   Idempotent: running twice produces no duplicates (upsert by code).

2. **Catalog browsing** — list available modules with step counts; return full tree.

3. **Project seeding** — map catalog entries to project ProcessLevel rows, enabling
   a one-click "Quick Start" that populates the entire process hierarchy for selected
   SAP modules.

FDD Reference: FDD-I07-sap-1yg-seed-catalog.md
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select, func

from app.models import db
from app.models.explore.process import (
    L1SeedCatalog,
    L2SeedCatalog,
    L3SeedCatalog,
    L4SeedCatalog,
    ProcessLevel,
)
from app.models.explore import _utcnow, _uuid

logger = logging.getLogger(__name__)

# Directory where packaged JSON catalog files live.
_CATALOG_DIR = Path(__file__).parent.parent / "data" / "sap_process_catalog"

# Ordered list of bundled catalog files included in Sprint 7.
BUNDLED_CATALOG_FILES: list[str] = [
    "fi_ap.json",
    "fi_gl.json",
    "fi_ar.json",
    "fi_aa.json",
    "mm_pur.json",
    "mm_inv.json",
]


# ─── Internal helpers ──────────────────────────────────────────────────────────


def _upsert_l1(data: dict) -> L1SeedCatalog:
    """Upsert L1SeedCatalog by code. Returns the persisted instance (no commit)."""
    existing = db.session.execute(
        select(L1SeedCatalog).where(L1SeedCatalog.code == data["code"])
    ).scalar_one_or_none()

    if existing:
        existing.name = data["name"]
        existing.sap_module_group = data["sap_module_group"]
        existing.description = data.get("description", "")
        existing.sort_order = data.get("sort_order", 0)
        return existing

    obj = L1SeedCatalog(
        code=data["code"],
        name=data["name"],
        sap_module_group=data["sap_module_group"],
        description=data.get("description", ""),
        sort_order=data.get("sort_order", 0),
    )
    db.session.add(obj)
    return obj


def _upsert_l2(data: dict, l1_id: int) -> L2SeedCatalog:
    """Upsert L2SeedCatalog by code. Returns the persisted instance (no commit)."""
    existing = db.session.execute(
        select(L2SeedCatalog).where(L2SeedCatalog.code == data["code"])
    ).scalar_one_or_none()

    if existing:
        existing.name = data["name"]
        existing.sap_module = data.get("sap_module", "")
        existing.description = data.get("description", "")
        existing.sort_order = data.get("sort_order", 0)
        existing.is_s4_mandatory = data.get("is_s4_mandatory", False)
        existing.parent_l1_id = l1_id
        return existing

    obj = L2SeedCatalog(
        code=data["code"],
        name=data["name"],
        sap_module=data.get("sap_module", ""),
        description=data.get("description", ""),
        sort_order=data.get("sort_order", 0),
        is_s4_mandatory=data.get("is_s4_mandatory", False),
        parent_l1_id=l1_id,
    )
    db.session.add(obj)
    return obj


def _upsert_l3(data: dict, l2_id: int) -> L3SeedCatalog:
    """Upsert L3SeedCatalog by code. Returns the persisted instance (no commit)."""
    existing = db.session.execute(
        select(L3SeedCatalog).where(L3SeedCatalog.code == data["code"])
    ).scalar_one_or_none()

    if existing:
        existing.name = data["name"]
        existing.description = data.get("description", "")
        existing.sap_scope_item_id = data.get("sap_scope_item_id")
        existing.typical_complexity = data.get("typical_complexity", "medium")
        existing.sort_order = data.get("sort_order", 0)
        existing.parent_l2_id = l2_id
        return existing

    obj = L3SeedCatalog(
        code=data["code"],
        name=data["name"],
        description=data.get("description", ""),
        sap_scope_item_id=data.get("sap_scope_item_id"),
        typical_complexity=data.get("typical_complexity", "medium"),
        sort_order=data.get("sort_order", 0),
        parent_l2_id=l2_id,
    )
    db.session.add(obj)
    return obj


def _upsert_l4(data: dict, l3_id: int, scope_item_code: str) -> tuple[L4SeedCatalog, bool]:
    """Upsert L4SeedCatalog by sub_process_code. Returns (instance, was_created).

    Args:
        data: L4 dict from JSON with sub_process_code, sub_process_name, etc.
        l3_id: FK to L3SeedCatalog parent.
        scope_item_code: Denormalized scope item code from the L3 (required by the
                         existing nullable=False column — use L3.code as fallback
                         when L3.sap_scope_item_id is None).
    """
    existing = db.session.execute(
        select(L4SeedCatalog).where(L4SeedCatalog.sub_process_code == data["sub_process_code"])
    ).scalar_one_or_none()

    if existing:
        existing.sub_process_name = data["sub_process_name"]
        existing.description = data.get("description", "")
        existing.typical_fit_decision = data.get("typical_fit_decision")
        existing.is_customer_facing = data.get("is_customer_facing", False)
        existing.standard_sequence = data.get("standard_sequence", 0)
        existing.parent_l3_id = l3_id
        return existing, False

    obj = L4SeedCatalog(
        scope_item_code=scope_item_code,
        sub_process_code=data["sub_process_code"],
        sub_process_name=data["sub_process_name"],
        description=data.get("description", ""),
        typical_fit_decision=data.get("typical_fit_decision"),
        is_customer_facing=data.get("is_customer_facing", False),
        standard_sequence=data.get("standard_sequence", 0),
        parent_l3_id=l3_id,
    )
    db.session.add(obj)
    return obj, True


# ─── Public API ────────────────────────────────────────────────────────────────


def load_catalog_from_json(json_file_path: str | Path) -> dict[str, Any]:
    """Load and upsert catalog data from a single JSON file.

    Idempotent: calling twice with the same file produces no duplicates.
    All changes are committed in a single transaction.

    Args:
        json_file_path: Absolute or relative path to a catalog JSON file.

    Returns:
        Dict with counts: {"created": {"l1":N, "l2":N, "l3":N, "l4":N},
                           "updated": {"l1":N, "l2":N, "l3":N, "l4":N}}

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the JSON structure is invalid.
    """
    path = Path(json_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Catalog file not found: {path}")

    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    required_top_keys = {"l1", "l2", "l3_list"}
    missing = required_top_keys - set(data.keys())
    if missing:
        raise ValueError(f"Catalog JSON missing required keys: {missing}")

    counts: dict[str, dict[str, int]] = {
        "created": {"l1": 0, "l2": 0, "l3": 0, "l4": 0},
        "updated": {"l1": 0, "l2": 0, "l3": 0, "l4": 0},
    }

    # L1
    l1_existing = db.session.execute(
        select(L1SeedCatalog).where(L1SeedCatalog.code == data["l1"]["code"])
    ).scalar_one_or_none()
    l1 = _upsert_l1(data["l1"])
    db.session.flush()  # obtain l1.id before FK reference
    if l1_existing:
        counts["updated"]["l1"] += 1
    else:
        counts["created"]["l1"] += 1

    # L2
    l2_existing = db.session.execute(
        select(L2SeedCatalog).where(L2SeedCatalog.code == data["l2"]["code"])
    ).scalar_one_or_none()
    l2 = _upsert_l2(data["l2"], l1.id)
    db.session.flush()
    if l2_existing:
        counts["updated"]["l2"] += 1
    else:
        counts["created"]["l2"] += 1

    for l3_data in data.get("l3_list", []):
        l3_existing = db.session.execute(
            select(L3SeedCatalog).where(L3SeedCatalog.code == l3_data["code"])
        ).scalar_one_or_none()
        l3 = _upsert_l3(l3_data, l2.id)
        db.session.flush()
        if l3_existing:
            counts["updated"]["l3"] += 1
        else:
            counts["created"]["l3"] += 1

        for l4_data in l3_data.get("l4_list", []):
            # Derive scope_item_code from L3's sap_scope_item_id, falling back to L3.code.
            # This satisfies the NOT NULL constraint on the existing L4 model column.
            l3_scope_code = l3_data.get("sap_scope_item_id") or l3_data["code"]
            _, was_created = _upsert_l4(l4_data, l3.id, l3_scope_code)
            key = "created" if was_created else "updated"
            counts[key]["l4"] += 1

    db.session.commit()
    logger.info(
        "Catalog loaded from %s — rows_created=%s rows_updated=%s",
        path.name,
        counts["created"],
        counts["updated"],
    )
    return counts


def load_all_bundled_catalogs() -> dict[str, Any]:
    """Load all bundled catalog JSON files shipped with the application.

    Idempotent — safe to call on every startup or migration run.

    Returns:
        Dict with aggregate counts per file:
        {"files_processed": N, "total_created": {...}, "total_updated": {...}}
    """
    total_created: dict[str, int] = {"l1": 0, "l2": 0, "l3": 0, "l4": 0}
    total_updated: dict[str, int] = {"l1": 0, "l2": 0, "l3": 0, "l4": 0}
    files_processed = 0

    for filename in BUNDLED_CATALOG_FILES:
        file_path = _CATALOG_DIR / filename
        if not file_path.exists():
            logger.warning("Bundled catalog file not found, skipping: %s", filename)
            continue
        result = load_catalog_from_json(file_path)
        for level in ("l1", "l2", "l3", "l4"):
            total_created[level] += result["created"].get(level, 0)
            total_updated[level] += result["updated"].get(level, 0)
        files_processed += 1

    logger.info(
        "All bundled catalogs loaded — files=%s rows_created=%s rows_updated=%s",
        files_processed,
        total_created,
        total_updated,
    )
    return {
        "files_processed": files_processed,
        "total_created": total_created,
        "total_updated": total_updated,
    }


def get_catalog_modules() -> list[dict[str, Any]]:
    """Return L1 groups with nested L2 modules and L4 step counts.

    Used by the Quick Start wizard to show module selection with step counts
    so project teams know how many activities they are committing to import.

    Returns:
        List of L1 dicts, each containing a "modules" list of L2 dicts with
        "step_count" (total L4 steps under that L2).
    """
    l1_rows = db.session.execute(
        select(L1SeedCatalog).order_by(L1SeedCatalog.sort_order, L1SeedCatalog.code)
    ).scalars().all()

    result = []
    for l1 in l1_rows:
        modules = []
        l2_rows = db.session.execute(
            select(L2SeedCatalog)
            .where(L2SeedCatalog.parent_l1_id == l1.id)
            .order_by(L2SeedCatalog.sort_order, L2SeedCatalog.code)
        ).scalars().all()

        for l2 in l2_rows:
            # Count L4 steps under this L2 via L3 join
            step_count = db.session.execute(
                select(func.count(L4SeedCatalog.id))
                .join(L3SeedCatalog, L4SeedCatalog.parent_l3_id == L3SeedCatalog.id)
                .where(L3SeedCatalog.parent_l2_id == l2.id)
            ).scalar_one()

            modules.append({
                "code": l2.code,
                "name": l2.name,
                "sap_module": l2.sap_module,
                "is_s4_mandatory": l2.is_s4_mandatory,
                "sort_order": l2.sort_order,
                "step_count": step_count,
            })

        result.append({
            "code": l1.code,
            "name": l1.name,
            "sap_module_group": l1.sap_module_group,
            "sort_order": l1.sort_order,
            "modules": modules,
        })

    return result


def get_catalog_tree(sap_module: str | None = None) -> list[dict[str, Any]]:
    """Return the full L1→L2→L3→L4 catalog tree, optionally filtered by SAP module.

    Args:
        sap_module: Optional SAP module code (e.g. "FI", "MM").
                    When provided, only L2 entries with matching sap_module are returned.

    Returns:
        List of L1 dicts with nested children all the way to L4.
    """
    l1_stmt = select(L1SeedCatalog).order_by(L1SeedCatalog.sort_order, L1SeedCatalog.code)
    l1_rows = db.session.execute(l1_stmt).scalars().all()

    result = []
    for l1 in l1_rows:
        l2_stmt = (
            select(L2SeedCatalog)
            .where(L2SeedCatalog.parent_l1_id == l1.id)
            .order_by(L2SeedCatalog.sort_order, L2SeedCatalog.code)
        )
        if sap_module:
            l2_stmt = l2_stmt.where(L2SeedCatalog.sap_module == sap_module.upper())
        l2_rows = db.session.execute(l2_stmt).scalars().all()

        if not l2_rows:
            continue

        l2_list = []
        for l2 in l2_rows:
            l3_rows = db.session.execute(
                select(L3SeedCatalog)
                .where(L3SeedCatalog.parent_l2_id == l2.id)
                .order_by(L3SeedCatalog.sort_order, L3SeedCatalog.code)
            ).scalars().all()

            l3_list = []
            for l3 in l3_rows:
                l4_rows = db.session.execute(
                    select(L4SeedCatalog)
                    .where(L4SeedCatalog.parent_l3_id == l3.id)
                    .order_by(L4SeedCatalog.standard_sequence)
                ).scalars().all()

                l3_list.append({
                    "code": l3.code,
                    "name": l3.name,
                    "description": l3.description,
                    "sap_scope_item_id": l3.sap_scope_item_id,
                    "typical_complexity": l3.typical_complexity,
                    "sort_order": l3.sort_order,
                    "l4_steps": [
                        {
                            "id": str(s.id),
                            "sub_process_code": s.sub_process_code,
                            "sub_process_name": s.sub_process_name,
                            "description": s.description,
                            "typical_fit_decision": s.typical_fit_decision,
                            "is_customer_facing": s.is_customer_facing,
                            "standard_sequence": s.standard_sequence,
                        }
                        for s in l4_rows
                    ],
                })

            l2_list.append({
                "code": l2.code,
                "name": l2.name,
                "sap_module": l2.sap_module,
                "is_s4_mandatory": l2.is_s4_mandatory,
                "sort_order": l2.sort_order,
                "l3_list": l3_list,
            })

        result.append({
            "code": l1.code,
            "name": l1.name,
            "sap_module_group": l1.sap_module_group,
            "sort_order": l1.sort_order,
            "l2_list": l2_list,
        })

    return result


def seed_project_from_catalog(
    tenant_id: int | None,
    project_id: int,
    selected_modules: list[str],
    importer_id: int,
) -> dict[str, Any]:
    """Seed a project's process hierarchy from the SAP seed catalog.

    Maps catalog entries to ProcessLevel rows:
      L1SeedCatalog  → ProcessLevel(level=1, code=L1.code, process_area_code=L1.sap_module_group)
      L2SeedCatalog  → ProcessLevel(level=2, code=L2.code, process_area_code=L2.sap_module)
      L3SeedCatalog  → ProcessLevel(level=3, code=L3.code, scope_item_code=L3.sap_scope_item_id)
      L4SeedCatalog  → ProcessLevel(level=4, code=L4.sub_process_code, fit_status=L4.typical_fit_decision)

    Idempotent: existing ProcessLevel rows with matching (project_id, code) are skipped.
    A single db.session.commit() is issued at the end (all-or-nothing transaction).

    Business rule: selected_modules is a list of L2 sap_module codes (e.g. ["FI", "MM"]).
    The function walks up to find the L1 parent and creates it once regardless of how
    many L2 children under the same L1 are selected.

    Args:
        tenant_id: Owning tenant — stored on ProcessLevel for data isolation.
        project_id: Target project (programs.id).
        selected_modules: L2 sap_module codes to import (e.g. ["FI", "MM"]).
        importer_id: User ID initiating the import (for audit logging).

    Returns:
        {
            "created": {"l1": N, "l2": N, "l3": N, "l4": N},
            "skipped": {"l1": N, "l2": N, "l3": N, "l4": N},
            "elapsed_ms": N
        }

    Raises:
        ValueError: If selected_modules is empty or contains unknown module codes.
    """
    if not selected_modules:
        raise ValueError("selected_modules must not be empty.")

    upper_modules = [m.upper() for m in selected_modules]
    start = time.perf_counter()

    created: dict[str, int] = {"l1": 0, "l2": 0, "l3": 0, "l4": 0}
    skipped: dict[str, int] = {"l1": 0, "l2": 0, "l3": 0, "l4": 0}

    # Index of already-created ProcessLevel ids keyed by catalog code,
    # so L2/L3/L4 can reference their parent's UUID.
    created_pl_id: dict[str, str] = {}

    # Helper: look up existing ProcessLevel by (project_id, code)
    def _existing_pl_id(code: str) -> str | None:
        row = db.session.execute(
            select(ProcessLevel.id).where(
                ProcessLevel.project_id == project_id,
                ProcessLevel.code == code,
            )
        ).scalar_one_or_none()
        return row

    # ── Fetch all matching L2 entries for selected modules ──
    l2_rows = db.session.execute(
        select(L2SeedCatalog)
        .where(L2SeedCatalog.sap_module.in_(upper_modules))
        .order_by(L2SeedCatalog.sort_order, L2SeedCatalog.code)
    ).scalars().all()

    if not l2_rows:
        raise ValueError(
            f"No catalog entries found for modules: {upper_modules}. "
            "Run load_all_bundled_catalogs() first."
        )

    # Build set of required L1 IDs
    needed_l1_ids = {l2.parent_l1_id for l2 in l2_rows}

    l1_rows = db.session.execute(
        select(L1SeedCatalog).where(L1SeedCatalog.id.in_(needed_l1_ids))
    ).scalars().all()
    l1_by_id = {l1.id: l1 for l1 in l1_rows}

    # ── Create L1 ProcessLevels ──
    for l1 in l1_by_id.values():
        existing_id = _existing_pl_id(l1.code)
        if existing_id:
            created_pl_id[l1.code] = existing_id
            skipped["l1"] += 1
            continue

        pl = ProcessLevel(
            id=_uuid(),
            tenant_id=tenant_id,
            program_id=project_id,
            project_id=project_id,
            parent_id=None,
            level=1,
            code=l1.code,
            name=l1.name,
            description=l1.description or "",
            process_area_code=l1.sap_module_group,
            scope_status="under_review",
            sort_order=l1.sort_order,
        )
        db.session.add(pl)
        db.session.flush()
        created_pl_id[l1.code] = pl.id
        created["l1"] += 1

    # ── Create L2 ProcessLevels ──
    for l2 in l2_rows:
        existing_id = _existing_pl_id(l2.code)
        if existing_id:
            created_pl_id[l2.code] = existing_id
            skipped["l2"] += 1
            continue

        l1 = l1_by_id[l2.parent_l1_id]
        pl = ProcessLevel(
            id=_uuid(),
            tenant_id=tenant_id,
            program_id=project_id,
            project_id=project_id,
            parent_id=created_pl_id.get(l1.code),
            level=2,
            code=l2.code,
            name=l2.name,
            description=l2.description or "",
            process_area_code=l2.sap_module,
            scope_status="under_review",
            sort_order=l2.sort_order,
        )
        db.session.add(pl)
        db.session.flush()
        created_pl_id[l2.code] = pl.id
        created["l2"] += 1

    # Build set of L2 IDs to query L3 children
    l2_ids = {l2.id for l2 in l2_rows}
    l3_rows = db.session.execute(
        select(L3SeedCatalog)
        .where(L3SeedCatalog.parent_l2_id.in_(l2_ids))
        .order_by(L3SeedCatalog.sort_order, L3SeedCatalog.code)
    ).scalars().all()

    l2_by_id = {l2.id: l2 for l2 in l2_rows}

    # ── Create L3 ProcessLevels ──
    for l3 in l3_rows:
        existing_id = _existing_pl_id(l3.code)
        if existing_id:
            created_pl_id[l3.code] = existing_id
            skipped["l3"] += 1
            continue

        l2 = l2_by_id[l3.parent_l2_id]
        pl = ProcessLevel(
            id=_uuid(),
            tenant_id=tenant_id,
            program_id=project_id,
            project_id=project_id,
            parent_id=created_pl_id.get(l2.code),
            level=3,
            code=l3.code,
            name=l3.name,
            description=l3.description or "",
            scope_item_code=l3.sap_scope_item_id,
            scope_status="under_review",
            sort_order=l3.sort_order,
        )
        db.session.add(pl)
        db.session.flush()
        created_pl_id[l3.code] = pl.id
        created["l3"] += 1

    # Build set of L3 IDs to query L4 children
    l3_ids = {l3.id for l3 in l3_rows}
    l4_rows = db.session.execute(
        select(L4SeedCatalog)
        .where(L4SeedCatalog.parent_l3_id.in_(l3_ids))
        .order_by(L4SeedCatalog.standard_sequence)
    ).scalars().all()

    l3_by_id = {l3.id: l3 for l3 in l3_rows}

    # ── Create L4 ProcessLevels ──
    for l4 in l4_rows:
        existing_id = _existing_pl_id(l4.sub_process_code)
        if existing_id:
            skipped["l4"] += 1
            continue

        l3 = l3_by_id[l4.parent_l3_id]
        pl = ProcessLevel(
            id=_uuid(),
            tenant_id=tenant_id,
            program_id=project_id,
            project_id=project_id,
            parent_id=created_pl_id.get(l3.code),
            level=4,
            code=l4.sub_process_code,
            name=l4.sub_process_name,
            description=l4.description or "",
            fit_status=l4.typical_fit_decision,
            scope_status="under_review",
            sort_order=l4.standard_sequence,
        )
        db.session.add(pl)
        created["l4"] += 1

    db.session.commit()

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        "Project seeded from catalog — project=%s tenant=%s modules=%s rows_created=%s elapsed_ms=%s",
        project_id,
        tenant_id,
        upper_modules,
        created,
        elapsed_ms,
    )

    return {"created": created, "skipped": skipped, "elapsed_ms": elapsed_ms}
