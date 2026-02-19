"""
F4 — Predictive Coverage Assistant.

Builds a risk heat-map from:
  - Defect density per module/test_layer
  - Recent change frequency (updated test cases)
  - Execution gap (test cases never / not recently executed)

Output: ordered risk list per module × layer with score + coverage gaps.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.testing import TestCase, TestExecution, Defect

logger = logging.getLogger(__name__)

SEVERITY_WEIGHT = {"S1": 4, "S2": 3, "S3": 2, "S4": 1}
RECENCY_WINDOW_DAYS = 30


class PredictiveCoverage:
    """Risk heat-map builder for test coverage planning."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway

    def analyze(self, program_id: int, *, window_days: int = RECENCY_WINDOW_DAYS) -> dict:
        """Generate risk heat-map for a program.

        Returns dict with heat_map list, uncovered list, summary.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        test_cases = TestCase.query.filter_by(program_id=program_id).all()
        defects = Defect.query.filter_by(program_id=program_id).all()

        # ── Defect density per (module, layer) ──
        defect_density = defaultdict(float)
        for d in defects:
            tc = db.session.get(TestCase, d.test_case_id) if d.test_case_id else None
            mod = (tc.module if tc else d.module) or "UNKNOWN"
            layer = tc.test_layer if tc else "unknown"
            weight = SEVERITY_WEIGHT.get(d.severity, 1)
            # boost recent defects
            if d.created_at and d.created_at.replace(tzinfo=timezone.utc) >= cutoff:
                weight *= 2
            defect_density[(mod, layer)] += weight

        # ── Change frequency (TC updated recently) ──
        change_freq = defaultdict(int)
        for tc in test_cases:
            if tc.updated_at and tc.updated_at.replace(tzinfo=timezone.utc) >= cutoff:
                change_freq[(tc.module or "UNKNOWN", tc.test_layer or "unknown")] += 1

        # ── Execution gap ──
        tc_ids = {tc.id for tc in test_cases}
        executed_recently = set()
        if tc_ids:
            recent_execs = (
                TestExecution.query
                .filter(TestExecution.test_case_id.in_(tc_ids))
                .filter(TestExecution.executed_at >= cutoff)
                .all()
            )
            executed_recently = {e.test_case_id for e in recent_execs}

        never_executed = []
        stale_executed = []
        for tc in test_cases:
            if tc.id not in executed_recently:
                last = (
                    TestExecution.query
                    .filter_by(test_case_id=tc.id)
                    .order_by(TestExecution.executed_at.desc())
                    .first()
                )
                entry = {
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "title": tc.title,
                    "module": tc.module,
                    "test_layer": tc.test_layer,
                }
                if last:
                    entry["last_executed"] = last.executed_at.isoformat() if last.executed_at else None
                    stale_executed.append(entry)
                else:
                    never_executed.append(entry)

        # ── Build heat map ──
        all_keys = set(defect_density.keys()) | set(change_freq.keys())
        # Also include all (module, layer) combos from test cases
        for tc in test_cases:
            all_keys.add((tc.module or "UNKNOWN", tc.test_layer or "unknown"))

        heat_map = []
        for (mod, layer) in sorted(all_keys):
            dd = defect_density.get((mod, layer), 0)
            cf = change_freq.get((mod, layer), 0)
            tc_count = sum(1 for tc in test_cases if (tc.module or "UNKNOWN") == mod and (tc.test_layer or "unknown") == layer)
            exec_count = sum(1 for tc in test_cases if (tc.module or "UNKNOWN") == mod and (tc.test_layer or "unknown") == layer and tc.id in executed_recently)
            coverage_pct = round((exec_count / tc_count * 100) if tc_count else 0, 1)

            risk_score = round(dd * 2 + cf * 1.5 + max(0, (100 - coverage_pct)) * 0.3, 1)

            heat_map.append({
                "module": mod,
                "test_layer": layer,
                "risk_score": risk_score,
                "defect_density": round(dd, 1),
                "change_frequency": cf,
                "test_case_count": tc_count,
                "recently_executed": exec_count,
                "coverage_pct": coverage_pct,
            })

        heat_map.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "heat_map": heat_map,
            "never_executed": never_executed[:50],
            "stale_executed": stale_executed[:50],
            "summary": {
                "total_test_cases": len(test_cases),
                "total_defects": len(defects),
                "never_executed_count": len(never_executed),
                "stale_executed_count": len(stale_executed),
                "high_risk_areas": len([h for h in heat_map if h["risk_score"] > 50]),
                "window_days": window_days,
            },
        }
