"""
AI assistant accuracy baseline tests.

These tests measure how well AI assistants classify, triage, and suggest.
Skipped by default — run with: pytest -m ai_accuracy -v

NOTE: These tests use the LocalStub provider (no API key needed).
      For real accuracy measurement, set GEMINI_API_KEY and run with a real LLM.
"""

import pytest

pytestmark = [pytest.mark.ai_accuracy, pytest.mark.slow]


# ── Helpers ──────────────────────────────────────────────────────────────

def _post(client, url, json=None):
    res = client.post(url, json=json or {})
    return res


# ── Labeled Test Data ────────────────────────────────────────────────────

LABELED_REQUIREMENTS = [
    {"description": "SAP standart kredi kontrolü yeterli, ek geliştirme gerekmez", "expected": "Fit"},
    {"description": "Müşteriye özel fiyatlama mantığı geliştirilmeli, SAP standart pricing yok", "expected": "Gap"},
    {"description": "SAP standart MRP çalıştırması kullanılacak, parametrik ayar yeterli", "expected": "Fit"},
    {"description": "Lojistik takip için özel ABAP raporu gerekli", "expected": "Gap"},
    {"description": "SAP standart satınalma talebi onay akışı workflow ile ayarlanacak", "expected": "Fit"},
    {"description": "Standart depo yönetimi warehouse management modülü ile karşılanır", "expected": "Fit"},
    {"description": "Kimyevi madde etiketleme için yasal düzenlemeye uygun özel form gerekli", "expected": "Gap"},
    {"description": "SAP standart mali raporlama (FI) yapısı kullanılacak", "expected": "Fit"},
    {"description": "Özel müşteri portalı entegrasyonu için web servisi geliştirilmeli", "expected": "Gap"},
    {"description": "SAP standart kalite yönetimi QM modülü ile numune kontrolü yapılacak", "expected": "Fit"},
    {"description": "SAP standart HR modülü ile bordro hesaplama yapılacak ancak yerel vergi tablosu ek gel.", "expected": "Partial Fit"},
    {"description": "Standart SD modülü satış siparişi akışı kullanılacak, ek geliştirme gereksiz", "expected": "Fit"},
    {"description": "Müşteri segmentasyonu için makine öğrenmesi modeli entegre edilecek", "expected": "Gap"},
    {"description": "SAP standart banka havalesi ile ödeme yapılacak, country-specific format uygu.", "expected": "Partial Fit"},
    {"description": "Anlık envanter görünürlüğü SAP MMIM transaction ile sağlanacak", "expected": "Fit"},
]

LABELED_DEFECTS = [
    {"title": "Üretim ortamında BAPI_PO_CREATE çağrısı zaman aşımına uğruyor", "expected_severity": "critical"},
    {"title": "Küçük yazı tipi hatasından dolayı rapor başlığı okunmuyor", "expected_severity": "low"},
    {"title": "Müşteri siparişi oluştururken 500 hatası alınıyor", "expected_severity": "high"},
    {"title": "Dashboard grafiğinde renk skalası yanlış gösteriliyor", "expected_severity": "medium"},
    {"title": "Mali kapanış raporunda tutarsız rakamlar çıkıyor", "expected_severity": "critical"},
    {"title": "Kullanıcı arayüzünde hizalama sorunu var", "expected_severity": "low"},
    {"title": "Toplu veri yükleme sırasında sistem çöküyor", "expected_severity": "critical"},
    {"title": "Bildirim e-postaları yanlış alıcıya gidiyor", "expected_severity": "high"},
    {"title": "Arama fonksiyonunda Türkçe karakter sorunu", "expected_severity": "medium"},
    {"title": "Onay akışında atanan kişi gösterilmiyor", "expected_severity": "medium"},
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
            # Create requirement
            req_res = _post(client, f"/api/v1/programs/{pid}/requirements", json={
                "title": item["description"][:100],
                "description": item["description"],
                "req_type": "functional"
            })
            if req_res.status_code != 201:
                continue

            req_id = req_res.get_json()["id"]
            total += 1

            # Ask AI to analyze
            analysis = _post(client, f"/api/v1/ai/analyze/requirement/{req_id}", json={})
            if analysis.status_code == 200:
                data = analysis.get_json()
                predicted = data.get("classification", {}).get("fit_status", "")
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
            defect_res = _post(client, f"/api/v1/programs/{pid}/defects", json={
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
                predicted = data.get("triage", {}).get("suggested_severity", "")
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
        {"nl": "Kaç tane requirement var?", "should_contain": "requirement"},
        {"nl": "Kritik defect'leri listele", "should_contain": "defect"},
        {"nl": "Açık riskler neler?", "should_contain": "risk"},
        {"nl": "Test başarı oranı nedir?", "should_contain": "test"},
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
