#!/usr/bin/env python3
"""
Automated metrics collection script.
Run after each sprint / commit to compare against the
summary table in PROGRESS_REPORT.md.

Usage:
    python scripts/collect_metrics.py          # JSON output
    python scripts/collect_metrics.py --check  # Compare with summary table
"""

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Project root directory
ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: str) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=ROOT
    )
    return result.stdout.strip()


def _count_lines(glob_pattern: str, base_dir: str = ".") -> int:
    """Count file lines matching the given glob pattern."""
    target = ROOT / base_dir
    total = 0
    for f in target.rglob(glob_pattern):
        if "__pycache__" in str(f) or ".venv" in str(f):
            continue
        try:
            total += sum(1 for _ in open(f, encoding="utf-8", errors="ignore"))
        except (OSError, UnicodeDecodeError):
            pass
    return total


def collect_metrics() -> dict:
    """Collect all project metrics."""
    metrics = {
        "date": str(date.today()),
    }

    # --- Database table count ---
    try:
        tbl_out = _run(
            f'{sys.executable} -c "'
            "from app import create_app; from app.models import db; "
            "app = create_app(); "
            "exec(\\\"with app.app_context():\\n"
            "    from sqlalchemy import inspect\\n"
            "    print(len(inspect(db.engine).get_table_names()))\\\")"
            '"'
        )
        metrics["tables"] = int(tbl_out.strip().split("\n")[-1])
    except Exception:
        metrics["tables"] = "N/A"

    # --- API endpoint count ---
    try:
        ep_out = _run(
            f'{sys.executable} -c "'
            "from app import create_app; app = create_app(); "
            "print(len([r for r in app.url_map.iter_rules() if r.endpoint != \\\"static\\\"]))\"",
        )
        metrics["api_endpoints"] = int(ep_out.strip().split("\n")[-1])
    except Exception:
        metrics["api_endpoints"] = "N/A"

    # --- Test count ---
    try:
        test_out = _run(f"{sys.executable} -m pytest tests/ --co -q 2>&1 | tail -1")
        match = re.search(r"(\d+)\s+test", test_out)
        metrics["tests"] = int(match.group(1)) if match else "N/A"
    except Exception:
        metrics["tests"] = "N/A"

    # --- LOC ---
    metrics["python_loc_app"] = _count_lines("*.py", "app")
    metrics["python_loc_scripts"] = _count_lines("*.py", "scripts")
    metrics["python_loc_tests"] = _count_lines("*.py", "tests")
    metrics["python_loc_total"] = (
        metrics["python_loc_app"]
        + metrics["python_loc_scripts"]
        + metrics["python_loc_tests"]
    )
    metrics["js_loc"] = _count_lines("*.js", "static/js")
    metrics["css_loc"] = _count_lines("*.css", "static/css")

    # --- File count ---
    file_count = 0
    for f in ROOT.rglob("*"):
        if f.is_file() and ".git" not in f.parts and ".venv" not in f.parts and "__pycache__" not in f.parts:
            file_count += 1
    metrics["total_files"] = file_count

    # --- Commit count ---
    try:
        commit_out = _run("git rev-list --count HEAD")
        metrics["commits"] = int(commit_out.strip())
    except Exception:
        metrics["commits"] = "N/A"

    # --- Alembic migration count ---
    migrations_dir = ROOT / "migrations" / "versions"
    if migrations_dir.exists():
        metrics["migrations"] = len(list(migrations_dir.glob("*.py")))
    else:
        metrics["migrations"] = 0

    return metrics


def check_against_report(metrics: dict) -> list[str]:
    """Compare with PROGRESS_REPORT.md summary table, return discrepancies."""
    report_path = ROOT / "PROGRESS_REPORT.md"
    if not report_path.exists():
        return ["PROGRESS_REPORT.md not found"]

    content = report_path.read_text(encoding="utf-8")
    issues = []

    def _check(label: str, real_value, pattern: str):
        match = re.search(pattern, content)
        if match:
            reported = match.group(1).replace(",", "").replace("+", "").replace("~", "")
            try:
                reported_int = int(reported)
                if isinstance(real_value, int) and reported_int != real_value:
                    issues.append(
                        f"⚠️  {label}: reported {reported_int}, actual {real_value}"
                    )
            except ValueError:
                pass

    _check("Commit", metrics.get("commits"), r"Total Commits\s*\|\s*(\d+)")
    _check("File", metrics.get("total_files"), r"Total Files\s*\|\s*(\d+)")
    _check("API Endpoint", metrics.get("api_endpoints"), r"API Endpoint\s*\|\s*~?(\d+)")
    _check("Test", metrics.get("tests"), r"Pytest Test\s*\|\s*(\d+)")
    _check("Table", metrics.get("tables"), r"DB Models\s*\|\s*(\d+)")
    _check("Migration", metrics.get("migrations"), r"Alembic Migration\s*\|\s*(\d+)")

    return issues


def main():
    metrics = collect_metrics()

    if "--check" in sys.argv:
        issues = check_against_report(metrics)
        print("=" * 60)
        print("PROGRESS_REPORT.md Verification Report")
        print("=" * 60)
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        print()
        if issues:
            print(f"❌ {len(issues)} discrepancies found:")
            for issue in issues:
                print(f"   {issue}")
            sys.exit(1)
        else:
            print("✅ All metrics are consistent with the report.")
            sys.exit(0)
    else:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
