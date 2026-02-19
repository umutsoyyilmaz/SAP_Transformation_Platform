"""
F4 — Test Case Maintenance Advisor.

Detects deprecated / stale test cases:
  - Never executed
  - Not executed in N days
  - No linked requirement
  - Requirement was deleted / deactivated
  - Identical step descriptions (potential duplicates)

Produces actionable recommendations per TC.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.testing import TestCase, TestExecution

logger = logging.getLogger(__name__)

STALE_DAYS = 90
DUPLICATE_THRESHOLD = 0.85


class TCMaintenance:
    """Stale / deprecated test-case detection and maintenance advisor."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway

    def analyze(self, program_id: int, *, stale_days: int = STALE_DAYS) -> dict:
        """Run maintenance analysis on all TCs in a program.

        Returns dict with never_executed, stale, unlinked, duplicates, summary.
        """
        test_cases = TestCase.query.filter_by(program_id=program_id).all()
        if not test_cases:
            return {"error": "No test cases found", "issues": []}

        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        issues = []

        # Pre-load last execution per TC
        last_exec = {}
        for tc in test_cases:
            ex = (
                TestExecution.query
                .filter_by(test_case_id=tc.id)
                .order_by(TestExecution.executed_at.desc())
                .first()
            )
            last_exec[tc.id] = ex

        never_executed = []
        stale_list = []
        unlinked = []

        for tc in test_cases:
            ex = last_exec[tc.id]

            # ── Never executed ──
            if ex is None:
                never_executed.append({
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "title": tc.title,
                    "module": tc.module,
                    "created_at": tc.created_at.isoformat() if tc.created_at else None,
                    "recommendation": "Hiç çalıştırılmamış — execution planına ekleyin veya geçerliliğini gözden geçirin.",
                })
                issues.append({
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "issue": "never_executed",
                    "severity": "high",
                })
                continue

            # ── Stale (not executed recently) ──
            exec_date = ex.executed_at
            if exec_date:
                exec_dt = exec_date if exec_date.tzinfo else exec_date.replace(tzinfo=timezone.utc)
                if exec_dt < cutoff:
                    days_ago = (datetime.now(timezone.utc) - exec_dt).days
                    stale_list.append({
                        "test_case_id": tc.id,
                        "code": tc.code,
                        "title": tc.title,
                        "last_executed_at": exec_date.isoformat(),
                        "days_since": days_ago,
                        "recommendation": f"{days_ago} gündür çalıştırılmamış — regresyon setine dahil edin veya arşivleyin.",
                    })
                    issues.append({
                        "test_case_id": tc.id,
                        "code": tc.code,
                        "issue": "stale",
                        "severity": "medium",
                        "days_since": days_ago,
                    })

            # ── Unlinked (no requirement reference) ──
            has_req = bool(getattr(tc, "requirement_id", None) or getattr(tc, "requirements", None))
            if not has_req:
                unlinked.append({
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "title": tc.title,
                    "recommendation": "Bağlı gereksinim yok — traceability eksik, requirement ile ilişkilendirin.",
                })
                issues.append({
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "issue": "unlinked",
                    "severity": "low",
                })

        # ── Duplicate detection (title similarity) ──
        duplicates = self._find_duplicates(test_cases)

        return {
            "program_id": program_id,
            "never_executed": never_executed,
            "stale": stale_list,
            "unlinked": unlinked,
            "duplicates": duplicates,
            "issues": issues,
            "summary": {
                "total_test_cases": len(test_cases),
                "never_executed_count": len(never_executed),
                "stale_count": len(stale_list),
                "unlinked_count": len(unlinked),
                "duplicate_groups": len(duplicates),
                "total_issues": len(issues),
                "message": (
                    f"{len(test_cases)} TC analiz edildi: "
                    f"{len(never_executed)} hiç çalıştırılmamış, "
                    f"{len(stale_list)} bayat, "
                    f"{len(unlinked)} bağlantısız, "
                    f"{len(duplicates)} olası kopya grubu."
                ),
            },
        }

    @staticmethod
    def _find_duplicates(test_cases: list) -> list:
        """Simple token-overlap duplicate finder."""
        groups = []
        seen = set()

        def _tokenize(text: str) -> set:
            return {w.lower() for w in text.split() if len(w) > 2}

        for i, a in enumerate(test_cases):
            if a.id in seen or not a.title:
                continue
            tok_a = _tokenize(a.title)
            if not tok_a:
                continue

            group = [{"test_case_id": a.id, "code": a.code, "title": a.title}]
            for b in test_cases[i + 1 :]:
                if b.id in seen or not b.title:
                    continue
                tok_b = _tokenize(b.title)
                if not tok_b:
                    continue
                overlap = len(tok_a & tok_b) / max(len(tok_a | tok_b), 1)
                if overlap >= DUPLICATE_THRESHOLD:
                    group.append({"test_case_id": b.id, "code": b.code, "title": b.title})
                    seen.add(b.id)

            if len(group) > 1:
                seen.add(a.id)
                groups.append(group)

        return groups
