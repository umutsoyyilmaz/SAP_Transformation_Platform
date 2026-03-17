# FDD-F05: Requirement Coverage Raporlama

**Öncelik:** P1
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-05
**Effort:** S (3–5 gün)
**Faz Etkisi:** Realize, Deploy
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

`app/blueprints/metrics_bp.py` içinde bir `requirement_coverage` metriği var ancak:
- **Hangi requirement'ların test case'i olmadığı** ayrıca raporlanamıyor.
- **Coverage breakdown** (L3 bazında, classification bazında, priority bazında) yok.
- Tek sayı döndürmek yerine aksiyon alınabilir bir liste yok.

### Mevcut `metrics_bp.py` Durumu
`requirement_coverage` fonksiyonu toplam covered/total oranını döndürüyor.
Eksik: `uncovered_requirements`, `coverage_by_module`, `coverage_trend`.

---

## 2. İş Değeri

- Test Manager'ın "En önemli hangi requirement'lar test edilmemiş?" sorusunu cevaplaması.
- Quality gate kontrolü: Go-live öncesi kritik requirement'ların test coverage'ı %100 olmalı.
- Sprint planlamasında test case yazımını önceliklendirme.
- Müşteriye sunulabilir "Test Readiness Report" oluşturma zemini.

---

## 3. Teknik Tasarım

### 3.1 `app/services/metrics.py` — Yeni Fonksiyonlar

```python
def get_requirement_coverage_matrix(
    project_id: int,
    tenant_id: int,
    classification: str | None = None,
    priority: str | None = None,
    include_uncovered_only: bool = False,
) -> dict:
    """
    Requirement → TestCase coverage matrisini döner.

    Her requirement için:
    - Bağlı test case sayısı
    - Son test execution sonucu
    - Coverage durumu (covered / partial / uncovered)

    Args:
        project_id: Tenant-scoped proje.
        tenant_id: Row-level izolasyon.
        classification: Filtre — fit | partial_fit | gap | None (hepsi)
        priority: Filtre — critical | high | medium | low | None (hepsi)
        include_uncovered_only: True ise sadece test'siz requirement'lar

    Returns:
        {
          "summary": {
            "total": 120,
            "covered": 85,
            "partial": 12,
            "uncovered": 23,
            "coverage_pct": 70.8,
            "critical_uncovered": 3
          },
          "by_classification": {
            "fit": {"total": 40, "covered": 38, "pct": 95.0},
            "gap": {"total": 60, "covered": 35, "pct": 58.3},
            "partial_fit": {"total": 20, "covered": 12, "pct": 60.0}
          },
          "by_priority": {
            "critical": {"total": 15, "covered": 12, "pct": 80.0},
            "high": {"total": 30, "covered": 25, "pct": 83.3}
          },
          "requirements": [
            {
              "id": "REQ-042",
              "title": "...",
              "classification": "gap",
              "priority": "critical",
              "status": "approved",
              "coverage_status": "uncovered",
              "test_case_count": 0,
              "linked_backlog_item": {"id": ..., "type": "R", "title": "..."}
            }
          ]
        }
    """
    ...


def get_coverage_trend(
    project_id: int,
    tenant_id: int,
    days: int = 30,
) -> list[dict]:
    """
    Son N gündeki günlük coverage yüzdesini döner (trend grafik için).

    DailySnapshot tablosundan çekilir (explore/infrastructure.py).

    Returns:
        [{"date": "2026-02-01", "coverage_pct": 45.2}, ...]
    """
    ...


def get_quality_gate_coverage_status(
    project_id: int,
    tenant_id: int,
    threshold_pct: float = 100.0,
    scope: str = "critical",
) -> dict:
    """
    Quality gate: critical requirement'ların coverage'ı threshold'u geçiyor mu?

    Args:
        threshold_pct: Geçilmesi gereken yüzde (default %100 critical için)
        scope: "critical" | "all"

    Returns:
        {
          "gate_passed": False,
          "current_pct": 80.0,
          "required_pct": 100.0,
          "blocking_requirements": [{"id": ..., "title": ..., "priority": "critical"}]
        }
    """
    ...
```

---

## 4. API Endpoint'leri

**Dosya:** `app/blueprints/metrics_bp.py`

```
GET /api/v1/projects/<project_id>/metrics/requirement-coverage
    Query params:
      - classification: fit|gap|partial_fit (opsiyonel)
      - priority: critical|high|medium|low (opsiyonel)
      - uncovered_only: true|false (default false)
    Permission: metrics.view
    Response: get_requirement_coverage_matrix() çıktısı

GET /api/v1/projects/<project_id>/metrics/requirement-coverage/trend
    Query params: days=30 (default)
    Permission: metrics.view
    Response: get_coverage_trend() çıktısı

GET /api/v1/projects/<project_id>/metrics/requirement-coverage/quality-gate
    Query params: threshold_pct=100&scope=critical
    Permission: metrics.view
    Response: get_quality_gate_coverage_status() çıktısı
```

---

## 5. Frontend Değişiklikleri

### 5.1 `reports.js` — Coverage Matrix Raporu
Yeni rapor sayfası veya mevcut reports sayfasına tab ekle:

```
Requirement Coverage Matrix
─────────────────────────────────────────────
Total: 120 | Covered: 85 | Uncovered: 23 | ⚠️ 3 CRITICAL UNCOVERED

Filter: [All Classes ▾] [All Priorities ▾] [Uncovered Only ☐]

Classification Breakdown:
  Fit:         ████████████████████░  95% (38/40)
  Gap:         ████████████░░░░░░░░░  58% (35/60)
  Partial Fit: ████████████░░░░░░░░░  60% (12/20)

Priority Breakdown:
  Critical: ████████████████░░░░  80% (12/15) ← ⚠️ BELOW THRESHOLD
  High:     █████████████████░░░  83% (25/30)

Uncovered Requirements:
┌──────────┬────────────────────────────┬────────────┬──────────┐
│ ID       │ Title                      │ Class      │ Priority │
├──────────┼────────────────────────────┼────────────┼──────────┤
│ REQ-042  │ Payment reconciliation     │ Gap        │ Critical │
│ REQ-055  │ Vendor master import       │ Partial    │ High     │
└──────────┴────────────────────────────┴────────────┴──────────┘
```

### 5.2 `executive_cockpit.js` — Quality Gate Widget
Mevcut executive cockpit'e:
```
Test Readiness
Coverage: 70.8%  ⚠️ Quality Gate: FAIL
Critical uncovered: 3 requirements
[View Details →]
```

### 5.3 `explore_requirements.js` — Satır Üstü Coverage Badge
Her requirement satırının yanına badge:
- 🟢 "3 tests" — test var ve geçiyor
- 🟡 "2 tests (failed)" — test var ama başarısız
- 🔴 "No tests" — test yok

---

## 6. Test Gereksinimleri

```python
# tests/test_coverage_reporting.py

def test_coverage_matrix_returns_correct_total_and_covered_counts():
def test_coverage_matrix_filter_by_classification_gap_only():
def test_coverage_matrix_filter_by_priority_critical_only():
def test_coverage_matrix_uncovered_only_returns_zero_test_count_reqs():
def test_coverage_by_classification_breakdown_sums_to_total():
def test_quality_gate_passes_when_all_critical_reqs_have_tests():
def test_quality_gate_fails_when_critical_req_has_no_test():
def test_quality_gate_returns_blocking_requirements_list():
def test_coverage_trend_returns_daily_snapshots_for_n_days():
def test_tenant_isolation_coverage_matrix_cross_tenant_404():
```

---

## 7. Kabul Kriterleri

- [ ] `GET /metrics/requirement-coverage` endpoint'i classification ve priority breakdown içeriyor.
- [ ] `uncovered_only=true` parametresi yalnızca test'siz requirement'ları döndürüyor.
- [ ] Quality gate endpoint'i `gate_passed: false` döndürdüğünde `blocking_requirements` listosi dolu.
- [ ] `critical_uncovered` sayısı executive cockpit'te görünüyor.
- [ ] `explore_requirements.js`'deki her satırda coverage badge var.
- [ ] Tüm testler geçiyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P1 — F-05 · Sprint 2 · Effort S
**Reviewer Kararı:** 🟡 ONAYLANIR — B-01 tamamlanmadan `critical_uncovered` sayısı yanlış olabilir

### Tespit Edilen Bulgular

1. **B-01 bağımlılığı — iki kaynak double-count riski.**
   B-01 tamamlanmadan hem `Requirement` hem `ExploreRequirement` tablosunda kayıtlar var. `get_requirement_coverage_matrix()` hangi tabloyu sorguladığı açıkça belirtilmeli. Yanlış tablo sorgulanırsa coverage sayıları yanıltıcı olur ve quality gate kararları hatalı temele dayanır.

2. **Cache invalidation — 4 farklı tetikleyici.**
   Coverage cache'i sadece TestCase değişiminde değil, `ExploreRequirement` oluşturma/silme işlemlerinde de invalidate edilmeli. FDD bunu belirtiyor ama servis katmanında `cache.delete_pattern(f"coverage:{tenant_id}:{project_id}:*")` çağrısı her write operasyonunda unutulursa stale data sorunu çıkar.

3. **`critical_uncovered` quality gate — false positive riski.**
   "Critical" priority requirements'ın test edilmemiş olması gate'i fail etmeli. Ancak bir requirement'ın `priority='critical'` ve `status='cancelled'` olması durumunda bu requirement `uncovered` sayılmamalı. Cancelled/obsolete requirement'lar coverage hesabının dışında tutulmalı.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Hangi tablodan sorgu yapıldığını (ExploreRequirement) fonksiyon docstring'ine yaz | Coder | Sprint 2 |
| A2 | Cache invalidation'ı `ExploreRequirement` write'larına da bağla | Coder | Sprint 2 |
| A3 | `status='cancelled'` olan requirement'ları coverage hesabından çıkar | Coder | Sprint 2 |
