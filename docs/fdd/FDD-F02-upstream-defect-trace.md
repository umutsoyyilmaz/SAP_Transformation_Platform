# FDD-F02: Upstream Defect Trace (Defect → L3 Process)

**Öncelik:** P1
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-02
**Effort:** S (3–5 gün)
**Faz Etkisi:** Realize, Deploy
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform mevcut traceability servisi **downstream** yönde çalışıyor:
```
ExploreRequirement → BacklogItem → TestCase → TestExecution → Defect
```

**Upstream** direction mevcut değil:
```
Defect → ? → TestCase → ? → BacklogItem/ConfigItem → ? → ExploreRequirement → ? → ProcessStep → L4 → L3
```

Bir defect incelendiğinde:
- Hangi requirement'tan kaynaklandığı bilinmiyor.
- Etkilenen L3 süreç görülemiyor.
- Impact assessment için tüm zinciri manuel takip etmek gerekiyor.

---

## 2. İş Değeri

- Defect root cause analysis için gereken süreyi ciddi ölçüde azaltır.
- "Bu defect hangi business process'i etkiliyor?" sorusu anında yanıtlanır.
- Test Manager'ın kritik L3 süreçleri etkileyen defect'leri önceliklendirmesini sağlar.
- SIT/UAT sırasında defect → process impact raporu proje sponsorına sunulabilir.

---

## 3. Mevcut Zincir Analizi

```
Defect (testing.py)
  └── linked via DefectLink.referenced_id (polymorphic)
        OR TestExecution.defects relationship
              └── TestExecution → TestCase
                        └── TestCase ← TestCaseTraceLink → BacklogItem | ExploreRequirement
                                    └── ExploreRequirement ← ExploreRequirement.process_step_id → ProcessStep
                                                └── ProcessStep.process_level_id → ProcessLevel (L4)
                                                          └── ProcessLevel.parent_id → L3 → L2 → L1
```

Tüm halkalar veritabanında mevcut. Eksik olan, bu zinciri traverse eden **tek bir API fonksiyonu**.

---

## 4. Teknik Tasarım

### 4.1 `traceability.py` — `trace_upstream_from_defect()`
**Dosya:** `app/services/traceability.py`

```python
def trace_upstream_from_defect(
    defect_id: int,
    project_id: int,
    tenant_id: int,
) -> dict:
    """
    Bir defect'ten geriye doğru tüm traceability zincirini traverse eder.

    Zincir (upstream):
    Defect → TestExecution → TestCase → [BacklogItem | ConfigItem | ExploreRequirement]
           → ExploreRequirement → ProcessStep (L4) → ProcessLevel (L3 → L2 → L1)

    Neden önemli: Defect root cause analysis'i için tüm zinciri tek sorguda
    sunmak, SIT/UAT yöneticisinin manuel takip etme yükünü ortadan kaldırır.

    Args:
        defect_id: Defect.id
        project_id: Tenant isolation için.
        tenant_id: Row-level izolasyon.

    Returns:
        {
          "defect": { "id": ..., "title": ..., "severity": ..., "status": ... },
          "test_execution": { "id": ..., "result": ..., "executed_at": ... },
          "test_case": { "id": ..., "title": ..., "type": ... },
          "linked_artifacts": [
            {
              "type": "backlog_item|config_item|explore_requirement",
              "id": ...,
              "title": ...,
              "wricef_type": "R|W|I|C|E|F" // BacklogItem için
            }
          ],
          "explore_requirement": { "id": ..., "title": ..., "classification": ..., "status": ... },
          "process_chain": [
            { "level": 1, "id": ..., "code": ..., "name": ... },  // L1
            { "level": 2, "id": ..., "code": ..., "name": ... },  // L2
            { "level": 3, "id": ..., "code": ..., "name": ... },  // L3
            { "level": 4, "id": ..., "code": ..., "name": ..., "fit_decision": "gap" }  // L4
          ],
          "workshop": { "id": ..., "title": ..., "status": ... },
          "impact_summary": {
            "affected_l3_processes": ["OTC-030 Order Processing"],
            "affected_sap_modules": ["SD", "FI"],
            "severity": "high",
            "is_critical_path": true  // L3 signed off ise kritik
          }
        }

    Raises:
        NotFoundError: defect proje kapsamında değilse.
    """
    ...
```

### 4.2 `trace_defects_by_process()`
```python
def trace_defects_by_process(
    project_id: int,
    tenant_id: int,
    process_level_id: int,
) -> list[dict]:
    """
    Belirli bir L3 (veya herhangi bir) ProcessLevel'a upstream bağlı tüm defect'leri döner.

    Kullanım: L3 panel içinde "Bu süreçle ilgili açık defect'ler" widget'ı.

    Returns: [{ "defect_id", "title", "severity", "status", "test_case_title" }]
    """
    ...
```

---

## 5. API Endpoint'leri

**Dosya:** `app/blueprints/traceability_bp.py`

```
GET /api/v1/projects/<project_id>/trace/defects/<defect_id>/upstream
    Permission: traceability.view
    Response: trace_upstream_from_defect() çıktısı

GET /api/v1/projects/<project_id>/trace/process-levels/<level_id>/defects
    Permission: traceability.view
    Query params: severity (opsiyonel), status (opsiyonel)
    Response: trace_defects_by_process() çıktısı
```

---

## 6. Frontend Değişiklikleri

### 6.1 `defect_management.js` — Defect Detay Paneli
Defect detay sayfasına "Impact Chain" tab'ı ekle:

```
[Defect Detail] [Test Case] [Impact Chain ←YENİ]

Impact Chain:
  🔴 DEFECT: Payment processing fails (High)
     └── TEST: TC-042 Payment reconciliation
          └── BACKLOG: R-015 Payment Report (WRICEF-R)
               └── REQUIREMENT: REQ-108 Payment document reconciliation
                    └── PROCESS: L4 → Payment Clearing ← [Fit: Gap]
                         └── L3 → Accounts Payable Process (OTC-030)
                              └── L2 → Financial Close
                                   └── L1 → Finance (FI)
```

### 6.2 `explore_workshop_detail.js` veya ProcessLevel view
L3 panel içine "Open Defects" badge'i ekle:
- Kırmızı sayı badge: "3 open defects"
- Tıklanınca `trace_defects_by_process` endpoint'ini çağır ve listele.

---

## 7. Test Gereksinimleri

```python
# tests/test_upstream_trace.py

def test_trace_upstream_returns_full_chain_from_defect():
def test_trace_upstream_handles_defect_with_multiple_test_cases():
def test_trace_upstream_handles_config_item_linked_test_case():
def test_trace_upstream_returns_404_for_wrong_project():
def test_trace_upstream_returns_empty_process_chain_if_no_requirement_linked():
def test_trace_defects_by_process_returns_all_open_defects():
def test_trace_defects_by_process_filters_by_severity():
def test_impact_summary_marks_is_critical_path_correctly():
def test_tenant_isolation_upstream_trace_cross_tenant_404():
```

---

## 8. Kabul Kriterleri

- [ ] `trace_upstream_from_defect(defect_id, project_id, tenant_id)` tam zinciri döndürüyor.
- [ ] L1→L4 process_chain doğru sırada ve doğru verilerle geliyor.
- [ ] `GET /trace/defects/<id>/upstream` endpoint'i çalışıyor.
- [ ] `GET /trace/process-levels/<id>/defects` endpoint'i çalışıyor.
- [ ] `defect_management.js` içinde "Impact Chain" tab'ı görünüyor.
- [ ] Tenant isolation korunuyor.
- [ ] Tüm testler geçiyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P1 — F-02 · Sprint 1 · Effort S
**Reviewer Kararı:** 🟡 ONAYLANIR — B-01 tamamlandıktan sonra implement edilmeli

### Tespit Edilen Bulgular

1. **Zincirde kırık halka riski — partial trace yönetimi.**
   `Defect → TestExecution → TestCase → ExploreRequirement → ProcessStep` zinciri her halkada kırılabilir (orphaned record, nullable FK). FDD bu durumdan bahsediyor ancak `trace_upstream_from_defect()` fonksiyonunun kırık zincirde ne döneceği net değil. 500 yerine `null` döndürmesi kabul kriterlerinde belirtilmiş ama implementation'da `selectinload` ile optional halkaların nasıl handle edileceği belirtilmeli.

2. **N+1 riski — `selectinload` yeterli olmayabilir.**
   Defect listesi üzerinde loop içinde `trace_upstream_from_defect()` çağrılırsa N+1 sorunu doğar. Bu fonksiyon tekil kullanım için tasarlanmış — docstring'e "bulk trace için ayrı endpoint kullanın" notu eklenmeli.

3. **B-01 bağımlılığı — ExploreRequirement canonical olmadan zincir güvenilmez.**
   Legacy `Requirement` modeli hâlâ aktifken bu upstream trace, bazı test case'ler için yanlış ya da eksik sonuç döndürecek. Sprint 1'de B-01 ile paralel yürütmek yerine B-01'i bloker olarak işaretlemek daha güvenli.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Kırık zincir senaryosunu docstring'e ve implementation'a ekle (partial trace response) | Coder | Sprint 1 |
| A2 | Bulk trace kullanım uyarısını docstring'e ekle | Coder | Sprint 1 |
| A3 | B-01 tamamlanana kadar bu feature'ı feature flag arkasında tut | Architect | Sprint 1 |
