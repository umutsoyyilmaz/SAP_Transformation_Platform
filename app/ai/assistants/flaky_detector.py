"""
F4 — Flaky Test Detector.

Algorithm per §4.3:
  1. For each test case, get last N executions (default 10)
  2. Compute status oscillation (pass→fail or fail→pass transitions)
  3. Flakiness score = oscillation / (N-1) × 100
  4. Score > threshold (40%) → flag as flaky
  5. Environment correlation check
  6. Return ranked list with scores + recommended actions
"""

import logging
from collections import defaultdict

from app.models import db
from app.models.testing import TestCase, TestExecution

logger = logging.getLogger(__name__)

DEFAULT_WINDOW = 10
FLAKY_THRESHOLD = 40  # percent


class FlakyTestDetector:
    """Detects flaky tests by analysing execution history oscillation."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway

    def analyze(
        self,
        program_id: int,
        *,
        window: int = DEFAULT_WINDOW,
        threshold: float = FLAKY_THRESHOLD,
    ) -> dict:
        """Analyze all test cases for flakiness.

        Returns:
            dict with flaky_tests list, total_analyzed, threshold
        """
        test_cases = TestCase.query.filter_by(program_id=program_id).all()
        flaky = []
        total = 0

        for tc in test_cases:
            executions = (
                TestExecution.query
                .filter_by(test_case_id=tc.id)
                .order_by(TestExecution.executed_at.desc())
                .limit(window)
                .all()
            )
            if len(executions) < 2:
                continue

            total += 1
            results = [e.result for e in reversed(executions)]  # chronological
            score, oscillations = self._compute_flakiness(results)

            if score >= threshold:
                env_corr = self._environment_correlation(executions)
                flaky.append({
                    "test_case_id": tc.id,
                    "code": tc.code,
                    "title": tc.title,
                    "module": tc.module,
                    "test_layer": tc.test_layer,
                    "flakiness_score": round(score, 1),
                    "oscillations": oscillations,
                    "execution_count": len(executions),
                    "result_sequence": results,
                    "environment_correlation": env_corr,
                    "recommendation": self._recommend(score, env_corr),
                })

        flaky.sort(key=lambda x: x["flakiness_score"], reverse=True)

        return {
            "flaky_tests": flaky,
            "total_analyzed": total,
            "flaky_count": len(flaky),
            "threshold": threshold,
            "window": window,
        }

    @staticmethod
    def _compute_flakiness(results: list[str]) -> tuple[float, int]:
        """Compute oscillation-based flakiness score."""
        if len(results) < 2:
            return 0.0, 0
        oscillations = 0
        for i in range(1, len(results)):
            prev, curr = results[i - 1], results[i]
            # Count pass↔fail transitions (ignore not_run/blocked/deferred)
            effective = {"pass", "fail"}
            if prev in effective and curr in effective and prev != curr:
                oscillations += 1
        score = (oscillations / (len(results) - 1)) * 100
        return score, oscillations

    @staticmethod
    def _environment_correlation(executions: list) -> dict | None:
        """Check if failures correlate with a specific environment."""
        env_results = defaultdict(lambda: {"pass": 0, "fail": 0, "other": 0})
        for e in executions:
            env = getattr(e, "environment", None) or "unknown"
            r = e.result or "other"
            if r in ("pass", "fail"):
                env_results[env][r] += 1
            else:
                env_results[env]["other"] += 1

        if len(env_results) < 2:
            return None

        # Find environment with highest fail ratio
        worst = None
        worst_ratio = 0
        for env, counts in env_results.items():
            total = counts["pass"] + counts["fail"]
            if total == 0:
                continue
            fail_ratio = counts["fail"] / total
            if fail_ratio > worst_ratio:
                worst_ratio = fail_ratio
                worst = env

        if worst and worst_ratio > 0.5:
            return {"environment": worst, "fail_ratio": round(worst_ratio, 2)}
        return None

    @staticmethod
    def _recommend(score: float, env_corr: dict | None) -> str:
        if env_corr:
            return f"Investigate environment '{env_corr['environment']}' — {int(env_corr['fail_ratio'] * 100)}% failure rate there"
        if score >= 70:
            return "High flakiness — quarantine this test and review for test data dependencies"
        if score >= 50:
            return "Moderate flakiness — add retry logic or investigate timing issues"
        return "Mild flakiness — monitor over next sprint"
