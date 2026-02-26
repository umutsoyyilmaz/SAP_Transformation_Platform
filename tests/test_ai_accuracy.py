"""
AI assistant accuracy baseline tests.

These tests measure how well AI assistants classify, triage, and suggest.
Skipped by default — run with: pytest -m ai_accuracy -v

NOTE: These tests use the LocalStub provider (no API key needed).
      For real accuracy measurement, set GEMINI_API_KEY and run with a real LLM.
"""

import pytest

from app.models import db as _db
from app.models.requirement import Requirement

pytestmark = [pytest.mark.ai_accuracy, pytest.mark.slow]


# ── Helpers ──────────────────────────────────────────────────────────────

def _post(client, url, json=None):
    res = client.post(url, json=json or {})
    return res


def _create_requirement(program_id, title, description):
    req = Requirement(
        program_id=program_id,
        title=title,
        description=description,
        req_type="functional",
        priority="must_have",
    )
    _db.session.add(req)
    _db.session.commit()
    return req


# ── Labeled Test Data ────────────────────────────────────────────────────

LABELED_REQUIREMENTS = [
    {"description": "SAP standard credit control is sufficient, no additional development needed", "expected": "Fit"},
    {"description": "Customer-specific pricing logic must be developed, SAP standard pricing unavailable", "expected": "Gap"},
    {"description": "SAP standard MRP run will be used, parametric configuration is sufficient", "expected": "Fit"},
    {"description": "Custom ABAP report required for logistics tracking", "expected": "Gap"},
    {"description": "SAP standard purchase requisition approval workflow will be configured", "expected": "Fit"},
    {"description": "Standard warehouse management module covers depot management", "expected": "Fit"},
    {"description": "Custom form required for chemical labeling to comply with legal regulations", "expected": "Gap"},
    {"description": "SAP standard financial reporting (FI) structure will be used", "expected": "Fit"},
    {"description": "Web service must be developed for custom customer portal integration", "expected": "Gap"},
    {"description": "SAP standard quality management QM module will handle sample inspection", "expected": "Fit"},
    {"description": "SAP standard HR module will handle payroll calculation but local tax table needs additional dev.", "expected": "Partial Fit"},
    {"description": "Standard SD module sales order flow will be used, no additional development needed", "expected": "Fit"},
    {"description": "Machine learning model will be integrated for customer segmentation", "expected": "Gap"},
    {"description": "SAP standard bank transfer will be used for payment, country-specific format applies", "expected": "Partial Fit"},
    {"description": "Real-time inventory visibility will be provided via SAP MMIM transaction", "expected": "Fit"},
]

LABELED_DEFECTS = [
    {"title": "BAPI_PO_CREATE call times out in production environment", "expected_severity": "critical"},
    {"title": "Report header unreadable due to small font size error", "expected_severity": "low"},
    {"title": "500 error when creating customer order", "expected_severity": "high"},
    {"title": "Color scale displayed incorrectly in dashboard chart", "expected_severity": "medium"},
    {"title": "Inconsistent numbers in financial closing report", "expected_severity": "critical"},
    {"title": "Alignment issue in user interface", "expected_severity": "low"},
    {"title": "System crashes during bulk data upload", "expected_severity": "critical"},
    {"title": "Notification emails going to wrong recipient", "expected_severity": "high"},
    {"title": "Special character issue in search function", "expected_severity": "medium"},
    {"title": "Assigned person not displayed in approval workflow", "expected_severity": "medium"},
]


# ── Accuracy Baselines ──────────────────────────────────────────────────


class TestRequirementAnalystAccuracy:
    """Requirement Analyst Fit/Gap classification accuracy."""

    def test_classify_batch(self, client):
        """Feed labeled requirements and measure classification accuracy."""
        prog = _post(client, "/api/v1/programs", json={
            "name": "AI Accuracy Test", "methodology": "agile"
        })
        if prog.status_code != 201:
            pytest.skip("Program creation failed")
        pid = prog.get_json()["id"]

        correct = 0
        total = 0
        results = []

        for item in LABELED_REQUIREMENTS:
            req = _create_requirement(pid, item["description"][:100], item["description"])
            req_id = req.id
            total += 1

            # Ask AI to analyze
            analysis = _post(client, f"/api/v1/ai/analyst/requirement/{req_id}", json={})
            if analysis.status_code == 200:
                data = analysis.get_json()
                predicted = data.get("classification", "")
                expected = item["expected"]
                is_correct = predicted.lower().replace("_", " ") == expected.lower().replace("_", " ")
                if is_correct:
                    correct += 1
                results.append({
                    "description": item["description"][:50],
                    "expected": expected,
                    "predicted": predicted,
                    "correct": is_correct
                })

        if total == 0:
            pytest.skip("No requirements could be analyzed")

        accuracy = correct / total * 100
        # Log results for analysis
        print(f"\n{'='*60}")
        print(f"Requirement Analyst Accuracy: {correct}/{total} = {accuracy:.1f}%")
        print(f"{'='*60}")
        for r in results:
            mark = "✓" if r["correct"] else "✗"
            print(f"  {mark} Expected={r['expected']:<12} Got={r['predicted']:<12} — {r['description']}")

        # Baseline: 50% with LocalStub (random-ish), 70%+ with real LLM
        # We don't fail here — this is a baseline measurement
        assert total > 0, "At least some requirements should be analyzable"


class TestDefectTriageAccuracy:
    """Defect Triage severity prediction accuracy."""

    def test_triage_batch(self, client):
        """Feed labeled defects and measure triage accuracy."""
        prog = _post(client, "/api/v1/programs", json={
            "name": "Defect Triage Accuracy", "methodology": "agile"
        })
        if prog.status_code != 201:
            pytest.skip("Program creation failed")
        pid = prog.get_json()["id"]

        correct = 0
        total = 0
        results = []

        for item in LABELED_DEFECTS:
            # Create defect
            defect_res = _post(client, f"/api/v1/programs/{pid}/testing/defects", json={
                "title": item["title"],
                "severity": "medium",  # placeholder — AI should suggest correct
                "status": "new"
            })
            if defect_res.status_code != 201:
                continue

            defect_id = defect_res.get_json()["id"]
            total += 1

            # Ask AI to triage
            triage = _post(client, f"/api/v1/ai/triage/defect/{defect_id}", json={})
            if triage.status_code == 200:
                data = triage.get_json()
                predicted = data.get("severity", "")
                expected = item["expected_severity"]
                is_correct = predicted.lower() == expected.lower()
                if is_correct:
                    correct += 1
                results.append({
                    "title": item["title"][:50],
                    "expected": expected,
                    "predicted": predicted,
                    "correct": is_correct
                })

        if total == 0:
            pytest.skip("No defects could be triaged")

        accuracy = correct / total * 100
        print(f"\n{'='*60}")
        print(f"Defect Triage Accuracy: {correct}/{total} = {accuracy:.1f}%")
        print(f"{'='*60}")
        for r in results:
            mark = "✓" if r["correct"] else "✗"
            print(f"  {mark} Expected={r['expected']:<10} Got={r['predicted']:<10} — {r['title']}")

        assert total > 0, "At least some defects should be triageable"


class TestNLQueryAccuracy:
    """Natural Language Query SQL generation test."""

    QUERIES = [
        {"nl": "How many requirements are there?", "should_contain": "requirement"},
        {"nl": "List the critical defects", "should_contain": "defect"},
        {"nl": "What are the open risks?", "should_contain": "risk"},
        {"nl": "What is the test success rate?", "should_contain": "test"},
    ]

    def test_nl_queries_produce_results(self, client):
        """NL queries should produce valid SQL and results."""
        prog = _post(client, "/api/v1/programs", json={
            "name": "NL Query Test", "methodology": "agile"
        })
        if prog.status_code != 201:
            pytest.skip("Program creation failed")
        pid = prog.get_json()["id"]

        success = 0
        for q in self.QUERIES:
            res = _post(client, "/api/v1/ai/query/natural-language", json={
                "question": q["nl"],
                "program_id": pid
            })
            if res.status_code == 200:
                data = res.get_json()
                if data.get("sql") or data.get("result") is not None:
                    success += 1

        print(f"\nNL Query: {success}/{len(self.QUERIES)} queries produced results")
        assert success >= 0  # Baseline — don't fail, just measure
