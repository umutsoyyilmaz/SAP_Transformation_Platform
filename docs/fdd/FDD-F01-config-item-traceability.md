# FDD-F01: ConfigItem → TestCase Traceability

**Öncelik:** P1
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-01
**Effort:** S (3–5 gün)
**Faz Etkisi:** Realize, Deploy
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

`app/services/traceability.py` içindeki `trace_explore_requirement()` fonksiyonu **BacklogItem (WRICEF) → TestCase** zincirini iyi işliyor. Ancak **ConfigItem → TestCase** zinciri `traceability.py` içinde yok.

### Mevcut Durum

`app/models/backlog.py`:
- `ConfigItem` modeli var — `project_id`, `requirement_id`, `sap_module`, `config_status` alanları mevcut.
- `ConfigItem.test_cases` relationship: `app/models/backlog.py` içinde `ConfigItem`'da `TestCase` ilişkisi tanımlı mı kontrol edilmeli. Büyük ihtimalle yoktur veya kısmi.

`app/services/traceability.py`:
- `trace_explore_requirement()` → BacklogItem üzerinden TestCase'e gider.
- ConfigItem üzerinden TestCase'e giden bir fonksiyon YOK.

`TestCaseTraceLink` modeli (`app/models/testing.py`):
- `linked_type` alanı: `backlog_item | explore_requirement | config_item | ...` — config_item değeri desteklenebilir.

---

## 2. İş Değeri

- Configuration test'lerinin de traceability matrisinde görünmesini sağlar.
- "Hangi konfigürasyon kaleminin testi var, hangisinin yok?" sorusunu yanıtlar.
- SAP Realize fazında Config kalitesini ölçmeyi mümkün kılar.
- Fit-Gap raporuna "config coverage" metriği eklenmesine zemin hazırlar.

---

## 3. Teknik Tasarım

### 3.1 `ConfigItem` Modeline Relationship Ekleme
**Dosya:** `app/models/backlog.py` → `ConfigItem` sınıfı

Mevcut `ConfigItem` sınıfında `TestCaseTraceLink` ilişkisi yoksa ekle:

```python
# ConfigItem sınıfının sonuna ekle
trace_links = db.relationship(
    "TestCaseTraceLink",
    primaryjoin="and_(TestCaseTraceLink.linked_type=='config_item', "
                "foreign(TestCaseTraceLink.linked_id)==ConfigItem.id)",
    lazy="select",
    overlaps="trace_links",
    viewonly=True,
)
```

### 3.2 `traceability.py` — Yeni Fonksiyonlar
**Dosya:** `app/services/traceability.py`

```python
def trace_config_item(config_item_id: int) -> dict:
    """
    ConfigItem için downstream traceability zincirini döner.

    Zincir: ConfigItem → TestCaseTraceLink → TestCase → TestExecution → Defect

    Args:
        config_item_id: ConfigItem primary key (tenant_id zaten
                         config_item'ın project_id üzerinden izole).

    Returns:
        {
          "config_item": {...},
          "test_cases": [
            {
              "id": 1, "title": "...", "status": "...",
              "last_execution": {...},
              "open_defects": [...]
            }
          ],
          "coverage_summary": {
            "total_test_cases": 3,
            "passed": 2, "failed": 0, "not_run": 1
          }
        }
    """
    ...


def get_config_items_without_tests(project_id: int, tenant_id: int) -> list[dict]:
    """
    Hiç TestCase bağlantısı olmayan ConfigItem'ları döner.

    Kullanım: Coverage gap analizi — hangi config kalemleri test edilmemiş?

    Returns:
        [{"id": ..., "title": ..., "sap_module": ..., "config_status": ...}]
    """
    ...


def get_config_coverage_summary(project_id: int, tenant_id: int) -> dict:
    """
    Proje genelinde ConfigItem test coverage özetini döner.

    Returns:
        {
          "total_config_items": 45,
          "with_tests": 30,
          "without_tests": 15,
          "coverage_pct": 66.7,
          "by_module": {"FI": {"total": 10, "covered": 8}, ...}
        }
    """
    ...
```

### 3.3 `TestCaseTraceLink` — `linked_type` Düzeltmesi
**Dosya:** `app/models/testing.py` → `TestCaseTraceLink` sınıfı

`linked_type` alanının comment'ine `config_item` değerini ekle:
```python
linked_type = db.Column(
    db.String(50),
    nullable=False,
    comment="backlog_item | explore_requirement | config_item | process_step"
)
```

Yeni ConfigItem link oluşturmak için testing_bp veya backlog_bp'de endpoint açılmalı (bakınız §4).

---

## 4. API Endpoint'leri

### 4.1 Traceability Blueprint'e Ekle
**Dosya:** `app/blueprints/traceability_bp.py`

```
GET /api/v1/projects/<project_id>/trace/config-items/<config_item_id>
    Permission: traceability.view
    Response: trace_config_item() çıktısı

GET /api/v1/projects/<project_id>/trace/config-items/coverage-summary
    Permission: traceability.view
    Response: get_config_coverage_summary() çıktısı

GET /api/v1/projects/<project_id>/trace/config-items/without-tests
    Permission: traceability.view
    Response: get_config_items_without_tests() çıktısı
```

### 4.2 TestCase'e ConfigItem Bağlama
**Dosya:** `app/blueprints/testing_bp.py` — mevcut `POST /test-cases/<id>/trace-links` endpoint'ine `config_item` type'ı ekle.

```python
# Mevcut endpoint body validation'ına eklenecek allowed type'lar:
VALID_LINKED_TYPES = {
    "backlog_item",
    "explore_requirement",
    "config_item",   # ← YENİ
    "process_step",
}
```

---

## 5. Frontend Değişiklikleri

### 5.1 `backlog.js` — ConfigItem Detay Paneli
ConfigItem detay modalına "Linked Tests" tab'ı ekle:
- Test case listesi (title, status, last run date)
- "Not tested" badge eğer hiç test bağlı değilse
- "Add Test Link" butonu

### 5.2 Coverage Dashboard Widget
`explore_dashboard.js` veya `reports.js` içine Config Coverage özet kartı ekle:
```
Configuration Coverage: 30/45 (%66)
[████████████░░░░] FI: 8/10 | MM: 12/15 | SD: 10/20
```

---

## 6. Test Gereksinimleri

```python
# tests/test_config_traceability.py

def test_trace_config_item_returns_linked_test_cases():
def test_trace_config_item_returns_empty_list_when_no_tests():
def test_trace_config_item_includes_last_execution_status():
def test_trace_config_item_returns_404_for_wrong_project():
def test_get_config_items_without_tests_returns_unlinked_items():
def test_get_config_coverage_summary_correct_percentages():
def test_config_coverage_by_sap_module_breakdown():
def test_tenant_isolation_config_trace_cross_tenant_returns_404():
def test_create_testcase_trace_link_with_config_item_type():
```

---

## 7. Kabul Kriterleri

- [ ] `trace_config_item(config_item_id)` fonksiyonu çalışıyor ve doğru veri döndürüyor.
- [ ] `GET /trace/config-items/<id>` endpoint'i 200 döndürüyor.
- [ ] `GET /trace/config-items/coverage-summary` SAP modül bazında breakdown döndürüyor.
- [ ] `get_config_items_without_tests()` test'siz config item'ları doğru listeli yor.
- [ ] `backlog.js`'deki ConfigItem detay panelinde "Linked Tests" tab'ı görünüyor.
- [ ] Tüm testler geçiyor, tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P1 — F-01 · Sprint 1 · Effort S
**Reviewer Kararı:** 🟡 ONAYLANIR — Aşağıdaki notlar sprint başında ele alınmalı

### Tespit Edilen Bulgular

1. **B-01 bağımlılığı — iki sistemde duplicate konfigürasyon riski.**
   `ConfigItem.requirement_id` şu an legacy `Requirement` modeline mi yoksa `ExploreRequirement`'a mı bağlı olduğu belirsiz. B-01 (requirement consolidation) tamamlanmadan bu traceability chain'i implement etmek, B-01 sonrasında yeniden yazılmasına yol açabilir. Önce B-01 kararı alınmalı.

2. **`TestCaseTraceLink` polymorphic FK — tenant izolasyonu doğrulanmalı.**
   `linked_type='config_item'` ile `TraceLink.linked_id = ConfigItem.id` kullanılıyor. Bu polymorphic join'de `ConfigItem.tenant_id` filtrelemesi otomatik gelmiyor. `trace_config_item()` fonksiyonunda tenant scope manuel olarak ConfigItem sorgusuna eklenmeli.

3. **Nullable relationship `overlaps` uyarısı — SQLAlchemy uyarısı bastırılmamalı.**
   `overlaps="trace_links"` parametresi SQLAlchemy'nin ilişki çakışma uyarısını bastırıyor. Bu uyarı genellikle gerçek bir veri inconsistency'ye işaret eder. `viewonly=True` tek çözüm değil — relationship tanımı gözden geçirilmeli.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `ConfigItem.requirement_id` — B-01 kararı beklensin, sonra FK hedefi kesinleştirilsin | Architect | Sprint 1 |
| A2 | `trace_config_item()` içinde `tenant_id` scope kontrolü ekle | Coder | Sprint 1 |
| A3 | `overlaps` kullanımını SQLAlchemy dokümantasyonu ile justify et veya relationship'i yeniden tasarla | Coder | Sprint 1 |
