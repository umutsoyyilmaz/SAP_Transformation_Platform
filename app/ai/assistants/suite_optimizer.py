"""
F4 — Suite Optimizer.

Per §4.4:
  For each test case, compute risk score from:
    - Defect density: recent defect count × severity weight
    - Change frequency: recently updated related items
    - Execution cost: duration × priority weight

  Sort by risk DESC → recommend minimal execution set.
  "Recommended minimal set for this cycle: N/M TC (pass confidence: X%)"
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.testing import TestCase, TestCycle, TestExecution, Defect

logger = logging.getLogger(__name__)

SEVERITY_WEIGHT = {"S1": 4, "S2": 3, "S3": 2, "S4": 1}
PRIORITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
DEFAULT_WINDOW_DAYS = 30
DEFAULT_CONFIDENCE_TARGET = 0.90


class SuiteOptimizer:
    """Risk-based test suite selection optimizer."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway

    def optimize(
        self,
        cycle_id: int,
        *,
        window_days: int = DEFAULT_WINDOW_DAYS,
        confidence_target: float = DEFAULT_CONFIDENCE_TARGET,
        max_tc: int | None = None,
    ) -> dict:
        """Compute optimized test case selection for a cycle.

        Returns dict with recommended set, full ranking, summary.
        """
        cycle = db.session.get(TestCycle, cycle_id)
        if not cycle:
            return {"error": f"Cycle {cycle_id} not found"}

        # Navigate to program via plan
        plan = cycle.plan if hasattr(cycle, "plan") else None
        program_id = plan.program_id if plan else None
        plan_id = cycle.plan_id if hasattr(cycle, "plan_id") else None

        # Fallback: all TCs in program
        if program_id:
            test_cases = TestCase.query.filter_by(program_id=program_id).all()
        else:
            test_cases = []

        if not test_cases:
            return {"error": "No test cases found for this cycle", "recommended": [], "ranking": []}

        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        # ── Defect scores ──
        defect_scores = defaultdict(float)
        defects = Defect.query.filter(
            Defect.program_id == program_id,
            Defect.created_at >= cutoff,
        ).all() if program_id else []

        for d in defects:
            if d.test_case_id:
                w = SEVERITY_WEIGHT.get(d.severity, 1)
                defect_scores[d.test_case_id] += w

        # ── Execution history (pass confidence) ──
        pass_rates = {}
        for tc in test_cases:
            execs = (
                TestExecution.query
                .filter_by(test_case_id=tc.id)
                .order_by(TestExecution.executed_at.desc())
                .limit(5)
                .all()
            )
            if execs:
                p = sum(1 for e in execs if e.result == "pass")
                pass_rates[tc.id] = p / len(execs)
            else:
                pass_rates[tc.id] = 0.0  # never executed → high risk

        # ── Build risk ranking ──
        ranking = []
        for tc in test_cases:
            defect_risk = defect_scores.get(tc.id, 0)
            prio_w = PRIORITY_WEIGHT.get(tc.priority, 2)
            change_score = 1.0 if (tc.updated_at and tc.updated_at.replace(tzinfo=timezone.utc) >= cutoff) else 0.0
            pass_rate = pass_rates.get(tc.id, 0.0)
            fail_risk = 1.0 - pass_rate

            risk_score = round(
                defect_risk * 3.0
                + change_score * 2.0
                + fail_risk * 2.5
                + prio_w * 1.0,
                2,
            )

            ranking.append({
                "test_case_id": tc.id,
                "code": tc.code,
                "title": tc.title,
                "module": tc.module,
                "test_layer": tc.test_layer,
                "priority": tc.priority,
                "risk_score": risk_score,
                "defect_risk": round(defect_risk, 1),
                "change_risk": round(change_score, 1),
                "fail_risk": round(fail_risk, 2),
                "pass_rate": round(pass_rate, 2),
            })

        ranking.sort(key=lambda x: x["risk_score"], reverse=True)

        # ── Select recommended set ──
        total = len(ranking)
        if max_tc:
            recommended = ranking[:max_tc]
        else:
            # Select enough TCs to reach confidence target
            # Logic: include high-risk first, stop when cumulative "confident coverage" meets target
            cumulative = 0.0
            recommended = []
            for r in ranking:
                recommended.append(r)
                cumulative += 1.0 / total
                if cumulative >= confidence_target:
                    break

        rec_count = len(recommended)
        confidence = round(min(1.0, rec_count / total) * 100, 1) if total else 0

        return {
            "cycle_id": cycle_id,
            "recommended": recommended,
            "ranking": ranking,
            "summary": {
                "total_test_cases": total,
                "recommended_count": rec_count,
                "confidence_pct": confidence,
                "message": f"Recommended minimal set: {rec_count}/{total} TC (pass confidence: {confidence}%)",
            },
        }
