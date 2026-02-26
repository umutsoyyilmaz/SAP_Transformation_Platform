"""Scheduled data-quality checks for project scoping integrity (report-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa

from app.models import db


def _q(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _is_int_like(column_type: Any) -> bool:
    return "int" in str(column_type).lower()


def _pk_column(inspector: sa.Inspector, table_name: str) -> str | None:
    pk = inspector.get_pk_constraint(table_name) or {}
    cols = pk.get("constrained_columns") or []
    return cols[0] if cols else None


def _collect_count(sql: str) -> int:
    return int(db.session.execute(sa.text(sql)).scalar() or 0)


def _collect_samples(sql: str, limit: int = 5) -> list[dict]:
    rows = db.session.execute(sa.text(sql), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def _remediation_sql(table_name: str, pk_col: str | None) -> dict[str, str]:
    id_col = pk_col or "id"
    qt = _q(table_name)
    qid = _q(id_col)
    return {
        "find_null_project_id": f"SELECT {qid}, tenant_id, program_id FROM {qt} WHERE project_id IS NULL;",
        "find_invalid_project_fk": (
            f"SELECT t.{qid}, t.tenant_id, t.program_id, t.project_id "
            f"FROM {qt} t LEFT JOIN projects p ON p.id = t.project_id "
            f"WHERE t.project_id IS NOT NULL AND p.id IS NULL;"
        ),
        "find_program_project_mismatch": (
            f"SELECT t.{qid}, t.program_id, p.program_id AS expected_program_id, t.project_id "
            f"FROM {qt} t JOIN projects p ON p.id = t.project_id "
            f"WHERE t.program_id IS NOT NULL AND t.program_id <> p.program_id;"
        ),
        "find_cross_tenant_anomaly": (
            f"SELECT t.{qid}, t.tenant_id, p.tenant_id AS expected_tenant_id, t.project_id "
            f"FROM {qt} t JOIN projects p ON p.id = t.project_id "
            f"WHERE t.tenant_id IS NOT NULL AND t.tenant_id <> p.tenant_id;"
        ),
    }


def collect_project_scope_quality_report(
    *,
    report_only: bool = True,
    table_names: list[str] | None = None,
    sample_limit: int = 5,
) -> dict[str, Any]:
    """
    Scan scoped tables and report integrity issues.

    Checks:
    - Null or invalid project_id
    - Program/project mismatch
    - Cross-tenant anomalies
    """
    insp = sa.inspect(db.engine)
    all_tables = insp.get_table_names()
    candidates = table_names if table_names is not None else all_tables

    results = []
    totals = {
        "tables_scanned": 0,
        "tables_with_issues": 0,
        "null_project_id_rows": 0,
        "invalid_project_id_rows": 0,
        "program_project_mismatch_rows": 0,
        "cross_tenant_anomaly_rows": 0,
        "critical_rows": 0,
        "critical_tables": 0,
    }

    for table_name in candidates:
        if table_name == "projects":
            continue
        cols = {c["name"]: c for c in insp.get_columns(table_name)}
        required = {"tenant_id", "program_id", "project_id"}
        if not required.issubset(cols):
            continue
        if not _is_int_like(cols["project_id"]["type"]):
            continue

        qt = _q(table_name)
        pk_col = _pk_column(insp, table_name)
        qpk = _q(pk_col) if pk_col else None

        null_sql = f"SELECT COUNT(*) FROM {qt} t WHERE t.project_id IS NULL"
        invalid_sql = (
            f"SELECT COUNT(*) FROM {qt} t "
            f"LEFT JOIN projects p ON p.id = t.project_id "
            f"WHERE t.project_id IS NOT NULL AND p.id IS NULL"
        )
        program_mm_sql = (
            f"SELECT COUNT(*) FROM {qt} t "
            f"JOIN projects p ON p.id = t.project_id "
            f"WHERE t.program_id IS NOT NULL AND t.program_id <> p.program_id"
        )
        tenant_mm_sql = (
            f"SELECT COUNT(*) FROM {qt} t "
            f"JOIN projects p ON p.id = t.project_id "
            f"WHERE t.tenant_id IS NOT NULL AND t.tenant_id <> p.tenant_id"
        )

        null_count = _collect_count(null_sql)
        invalid_count = _collect_count(invalid_sql)
        program_mm_count = _collect_count(program_mm_sql)
        tenant_mm_count = _collect_count(tenant_mm_sql)

        issue_count = null_count + invalid_count + program_mm_count + tenant_mm_count
        critical_count = invalid_count + program_mm_count + tenant_mm_count

        samples = {}
        if issue_count > 0 and qpk:
            samples["null_project_id"] = _collect_samples(
                f"SELECT t.{qpk} AS row_id, t.tenant_id, t.program_id, t.project_id "
                f"FROM {qt} t WHERE t.project_id IS NULL LIMIT :limit",
                sample_limit,
            )
            samples["invalid_project_id"] = _collect_samples(
                f"SELECT t.{qpk} AS row_id, t.tenant_id, t.program_id, t.project_id "
                f"FROM {qt} t LEFT JOIN projects p ON p.id = t.project_id "
                f"WHERE t.project_id IS NOT NULL AND p.id IS NULL LIMIT :limit",
                sample_limit,
            )
            samples["program_project_mismatch"] = _collect_samples(
                f"SELECT t.{qpk} AS row_id, t.tenant_id, t.program_id, t.project_id, "
                f"p.program_id AS expected_program_id "
                f"FROM {qt} t JOIN projects p ON p.id = t.project_id "
                f"WHERE t.program_id IS NOT NULL AND t.program_id <> p.program_id LIMIT :limit",
                sample_limit,
            )
            samples["cross_tenant_anomaly"] = _collect_samples(
                f"SELECT t.{qpk} AS row_id, t.tenant_id, t.program_id, t.project_id, "
                f"p.tenant_id AS expected_tenant_id "
                f"FROM {qt} t JOIN projects p ON p.id = t.project_id "
                f"WHERE t.tenant_id IS NOT NULL AND t.tenant_id <> p.tenant_id LIMIT :limit",
                sample_limit,
            )

        table_result = {
            "table": table_name,
            "pk_column": pk_col,
            "counts": {
                "null_project_id": null_count,
                "invalid_project_id": invalid_count,
                "program_project_mismatch": program_mm_count,
                "cross_tenant_anomaly": tenant_mm_count,
            },
            "critical": critical_count > 0,
            "samples": samples,
            "remediation_sql": _remediation_sql(table_name, pk_col),
        }
        results.append(table_result)

        totals["tables_scanned"] += 1
        totals["null_project_id_rows"] += null_count
        totals["invalid_project_id_rows"] += invalid_count
        totals["program_project_mismatch_rows"] += program_mm_count
        totals["cross_tenant_anomaly_rows"] += tenant_mm_count
        totals["critical_rows"] += critical_count
        if issue_count > 0:
            totals["tables_with_issues"] += 1
        if critical_count > 0:
            totals["critical_tables"] += 1

    severity = "critical" if totals["critical_rows"] > 0 else ("warning" if totals["tables_with_issues"] > 0 else "ok")
    return {
        "mode": "report_only" if report_only else "apply",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {**totals, "severity": severity},
        "tables": results,
    }

