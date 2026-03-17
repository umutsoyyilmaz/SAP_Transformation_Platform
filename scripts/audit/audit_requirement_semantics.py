"""Audit and normalize ExploreRequirement semantic fields.

Usage:
    .venv/bin/python scripts/audit/audit_requirement_semantics.py
    .venv/bin/python scripts/audit/audit_requirement_semantics.py --apply
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import select

if __name__ == "__main__" and __package__ is None:
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models import db
from app.models.explore.requirement import ExploreRequirement


def _derive_requirement_class(req: ExploreRequirement) -> str:
    return req.requirement_class or req.requirement_type or "functional"


def _derive_delivery_pattern(req: ExploreRequirement) -> str:
    if req.delivery_pattern:
        return req.delivery_pattern
    legacy_type_map = {
        "development": "wricef",
        "configuration": "configuration",
        "integration": "interface",
        "migration": "migration",
        "enhancement": "wricef",
        "workaround": "process_change",
        "functional": "configuration",
    }
    return legacy_type_map.get(req.type, "configuration")


def _derive_trigger_reason(req: ExploreRequirement) -> str | None:
    if req.trigger_reason:
        return req.trigger_reason
    fit_map = {
        "gap": "gap",
        "partial_fit": "partial_fit",
        "fit": "standard_observation",
        "standard": "standard_observation",
    }
    return fit_map.get(req.fit_status)


def _derive_delivery_status(req: ExploreRequirement) -> str:
    if req.delivery_status:
        return req.delivery_status
    if req.status == "verified":
        return "validated"
    if req.status == "realized":
        return "ready_for_test"
    if req.status == "in_backlog" or req.is_converted:
        return "mapped"
    return "not_mapped"


def _summarize_row(req: ExploreRequirement) -> dict:
    return {
        "id": req.id,
        "program_id": req.program_id,
        "project_id": req.project_id,
        "code": req.code,
        "title": req.title,
        "fit_status": req.fit_status,
        "status": req.status,
        "requirement_class": req.requirement_class,
        "delivery_pattern": req.delivery_pattern,
        "trigger_reason": req.trigger_reason,
        "delivery_status": req.delivery_status,
        "derived_requirement_class": _derive_requirement_class(req),
        "derived_delivery_pattern": _derive_delivery_pattern(req),
        "derived_trigger_reason": _derive_trigger_reason(req),
        "derived_delivery_status": _derive_delivery_status(req),
    }


def collect_requirement_semantics_report(*, sample_limit: int = 25) -> dict:
    rows = db.session.execute(
        select(ExploreRequirement).order_by(ExploreRequirement.created_at.asc())
    ).scalars().all()

    report = {
        "summary": {
            "total_rows": len(rows),
            "standard_fit_rows": 0,
            "missing_requirement_class": 0,
            "missing_delivery_pattern": 0,
            "missing_trigger_reason": 0,
            "missing_delivery_status": 0,
            "rows_needing_backfill": 0,
        },
        "samples": [],
    }

    for req in rows:
        sample = _summarize_row(req)
        standard_fit = sample["derived_trigger_reason"] == "standard_observation"
        missing_any = any(
            sample[key] is None
            for key in (
                "requirement_class",
                "delivery_pattern",
                "trigger_reason",
                "delivery_status",
            )
        )

        if standard_fit:
            report["summary"]["standard_fit_rows"] += 1
        if req.requirement_class is None:
            report["summary"]["missing_requirement_class"] += 1
        if req.delivery_pattern is None:
            report["summary"]["missing_delivery_pattern"] += 1
        if req.trigger_reason is None:
            report["summary"]["missing_trigger_reason"] += 1
        if req.delivery_status is None:
            report["summary"]["missing_delivery_status"] += 1
        if missing_any:
            report["summary"]["rows_needing_backfill"] += 1
            if len(report["samples"]) < sample_limit:
                sample["standard_fit_observation"] = standard_fit
                report["samples"].append(sample)

    return report


def normalize_requirement_semantics(*, apply: bool = False, sample_limit: int = 25) -> dict:
    report = collect_requirement_semantics_report(sample_limit=sample_limit)
    report["mode"] = "apply" if apply else "dry-run"
    report["updated_rows"] = 0

    if not apply:
        return report

    rows = db.session.execute(select(ExploreRequirement)).scalars().all()
    updated = 0
    for req in rows:
        changed = False
        if req.requirement_class is None:
            req.requirement_class = _derive_requirement_class(req)
            changed = True
        if req.delivery_pattern is None:
            req.delivery_pattern = _derive_delivery_pattern(req)
            changed = True
        if req.trigger_reason is None:
            req.trigger_reason = _derive_trigger_reason(req)
            changed = True
        if req.delivery_status is None:
            req.delivery_status = _derive_delivery_status(req)
            changed = True
        if changed:
            updated += 1

    db.session.commit()
    report["updated_rows"] = updated
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/backfill ExploreRequirement semantic fields.")
    parser.add_argument("--apply", action="store_true", help="Persist derived semantic fields")
    parser.add_argument("--sample-limit", type=int, default=25, help="Max sample rows in output")
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        result = normalize_requirement_semantics(apply=args.apply, sample_limit=args.sample_limit)
        print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
