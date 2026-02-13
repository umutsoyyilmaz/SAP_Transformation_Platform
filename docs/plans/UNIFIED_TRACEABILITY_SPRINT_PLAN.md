# 📋 Unified Traceability — Sprint Planı

**Kaynak:** `unified_traceability_prompt.md`  
**Tarih:** 2026-02-13  
**Öncelik:** P0  
**Toplam Tahmini Efor:** ~40 saat (5 iş günü)  
**Sprint Sayısı:** 4 Sprint

---

## 📊 Analiz Özeti

### Mevcut Durum (Kırık / Eksik)

| # | Sorun | Konum | Etki |
|---|-------|-------|------|
| 1 | Backlog Item traceability **404 hatası** | `backlog.js:881,925` → `GET /traceability/backlog_item/{id}` → endpoint YOK | Backlog izlenebilirliği tamamen kırık |
| 2 | Explore Requirement trace **sığ** (depth 2/4) | `trace_explore_requirement()` sadece downstream | Upstream (Workshop→Process→Scenario) eksik |
| 3 | `get_chain()` fonksiyonu var ama **route yok** | `traceability.py` 14 entity destekliyor ama hiçbir blueprint expose etmiyor | Tüm program-domain trace kullanılamaz |
| 4 | Frontend trace component **tek tip** | `trace-view.js` sadece `ExploreRequirement` destekliyor | Test Case, Defect, Config Item trace yok |
| 5 | Chain gap detection **yok** | Service'de coverage hesabı var ama gap tespiti yok | Kırık zincirler görünmez |

### Hedef Mimari

```
Level 1: Scope Item (1YG) / Scenario (O2C)
Level 2: L3 Process / Process Step → Workshop
Level 3: Requirement (REQ-014)
Level 4: WRICEF Item (ENH-009) / Config Item (CFG-003)
Level 5: Functional Spec → Technical Spec
Level 6: Test Case → Test Execution → Defect

Lateral: Open Items, Decisions, Interfaces, Connectivity Tests, Switch Plans
```

### Etkilenen Dosyalar

| Dosya | İşlem | Sprint |
|-------|-------|--------|
| `app/blueprints/traceability_bp.py` | **YENİ** — Unified endpoint | S1 |
| `app/__init__.py` | Değişiklik — Blueprint registrasyonu | S1 |
| `app/services/traceability.py` | **DEĞİŞMEYECEK** — Wrapper yaklaşım | — |
| `static/js/components/trace-chain.js` | **YENİ** — Visual chain component | S2 |
| `static/js/views/backlog.js` | Değişiklik — TraceChain entegrasyonu | S3 |
| `static/js/views/explore_requirements.js` | Değişiklik — TraceChain entegrasyonu | S3 |
| `static/js/views/test_execution.js` | Değişiklik — TraceChain entegrasyonu | S3 |
| `templates/index.html` | Değişiklik — Script include | S2 |
| `tests/test_traceability_unified.py` | **YENİ** — API contract tests | S4 |

---

## 🏃 Sprint 1: Backend Altyapı (Unified Endpoint)

**Süre:** 1.5 gün (~12 saat)  
**Bağımlılık:** Yok (ilk sprint)  
**Çıktı:** `curl` ile test edilebilir çalışan API

### Task 1.1 — `traceability_bp.py` Blueprint Oluşturma
| Alan | Detay |
|------|-------|
| Dosya | `app/blueprints/traceability_bp.py` (YENİ) |
| Efor | 4 saat |
| Açıklama | Tek unified endpoint: `GET /api/v1/traceability/<entity_type>/<entity_id>` |

**Kapsam:**
- 16 entity type desteği (scenario, workshop, process, analysis, requirement, explore_requirement, backlog_item, config_item, functional_spec, technical_spec, test_case, defect, interface, wave, connectivity_test, switch_plan)
- Query params: `depth` (default:10, max:20), `include_lateral` (default:true)
- `explore_requirement` → string ID desteği (ör. "REQ-014")
- Diğer entity'ler → integer ID
- Mevcut `get_chain()` ve `trace_explore_requirement()` fonksiyonlarını **wrap** eder, **değiştirmez**

**Çıktı formatı:**
```json
{
  "entity": {"type": "backlog_item", "id": 1, "title": "..."},
  "upstream": [...],
  "downstream": [...],
  "lateral": {"interfaces": [...], "open_items": [...]},
  "chain_depth": 4,
  "gaps": [{"level": "downstream", "message": "No Test Cases created"}],
  "links_summary": {"requirement": 1, "test_case": 2},
  "coverage": {"backlog": 1, "config": 0, "test": 2, "defect": 0}
}
```

### Task 1.2 — Upstream Builder (Explore Requirement)
| Alan | Detay |
|------|-------|
| Dosya | `app/blueprints/traceability_bp.py` içinde |
| Efor | 2 saat |
| Açıklama | `_build_explore_upstream()` — ExploreRequirement → Workshop → Scenario/Process zinciri |

**Kapsam:**
- `ExploreRequirement.workshop_id` → Workshop detayları *(explore.py:866, FK→explore_workshops.id)*
- Workshop → `scenario_id` → Scenario detayları
- `process_step_id` → Process hiyerarşisi *(explore.py:860, FK→process_steps.id)* ✅ MEVCUT
- `process_level_id` → L4 seviye bilgisi *(explore.py:870, FK→process_levels.id)* ✅ MEVCUT
- `scope_item_id` → L3 Scope Item bilgisi *(explore.py:874, FK→process_levels.id)* ✅ MEVCUT

### Task 1.3 — Lateral Links & Gap Detection
| Alan | Detay |
|------|-------|
| Dosya | `app/blueprints/traceability_bp.py` içinde |
| Efor | 2 saat |
| Açıklama | `_build_explore_lateral()`, `_build_lateral_links()`, `_find_chain_gaps()`, `_find_gaps_in_chain()` |

**Kapsam:**
- **Lateral links:** Open Items (M:N via RequirementOpenItemLink), Decisions *(ExploreDecision modeli explore.py:599'da MEVCUT — `process_step_id` FK ile bağlı)*, Interfaces
- **Gap detection:** Eksik WRICEF/Config (Level 2), eksik Test Case (Level 4), eksik Defect (Level 5), eksik upstream (Level 0)
- **Chain depth hesabı:** 1-6 ölçeği (Requirement-only=1, Full SAP chain=6)

> **NOT:** `ExploreDecision` modeli mevcuttur (`explore.py:599`). Prompt'taki try/except koruması gereksiz ama zararsızdır — tercihen direkt import kullanılabilir.

### Task 1.4 — Blueprint Registrasyonu
| Alan | Detay |
|------|-------|
| Dosya | `app/__init__.py` |
| Efor | 0.5 saat |
| Açıklama | Mevcut pattern'e uygun register |

**Yapılacak:**
```python
from app.blueprints.traceability_bp import traceability_bp
app.register_blueprint(traceability_bp, url_prefix="/api/v1")
```
> ⚠️ Mevcut 16 blueprint'in registrasyon pattern'i kontrol edilecek (line 151-166)

### Task 1.5 — Curl ile Smoke Test + API Prefix Doğrulama
| Alan | Detay |
|------|-------|
| Efor | 1.5 saat |
| Açıklama | 5 endpoint testi + error handling + **frontend API prefix doğrulama** |

**Test senaryoları:**
```
✅ GET /api/v1/traceability/backlog_item/1        → 200 (önceden 404 idi!)
✅ GET /api/v1/traceability/explore_requirement/REQ-001 → 200
✅ GET /api/v1/traceability/scenario/1             → 200
✅ GET /api/v1/traceability/test_case/1            → 200
✅ GET /api/v1/traceability/defect/1               → 200
✅ GET /api/v1/traceability/invalid_type/1         → 404
✅ GET /api/v1/traceability/backlog_item/abc       → 400
```

**API Prefix doğrulama (Sprint 3'ü beklemeden):**
```bash
# ✅ DOĞRULANDI: static/js/api.js satır 7 → const BASE = '/api/v1'
# Frontend API.get('/traceability/backlog_item/1') çağrısı
# otomatik olarak '/api/v1/traceability/backlog_item/1' olur.
grep -n "BASE\|baseURL\|API_BASE" static/js/api.js
```

### Sprint 1 Kabul Kriterleri
- [ ] `curl /api/v1/traceability/backlog_item/1` → 200 döner (önceden 404 idi)
- [ ] Response'da `upstream`, `downstream`, `lateral`, `chain_depth`, `gaps` alanları var
- [ ] `explore_requirement` string ID ile çalışır
- [ ] 16 entity type desteklenir
- [ ] Invalid type/ID → uygun HTTP status code (400/404)
- [ ] Mevcut `trace-view.js` ve `audit_bp.py` endpointleri bozulmadı
- [ ] **Frontend API prefix doğrulandı:** `API.get()` → `BASE = '/api/v1'` (api.js:7)

---

## 🏃 Sprint 2: Frontend Component (TraceChain.js)

**Süre:** 1.5 gün (~12 saat)  
**Bağımlılık:** Sprint 1 tamamlanmış olmalı  
**Çıktı:** Çalışan modal + inline trace görselleştirme

### Task 2.1 — TraceChain Core Component
| Alan | Detay |
|------|-------|
| Dosya | `static/js/components/trace-chain.js` (YENİ) |
| Efor | 6 saat |
| Açıklama | IIFE pattern ile `TraceChain` global object |

**Public API:**
```javascript
TraceChain.show(entityType, entityId)         // Modal açar
TraceChain.renderInTab(entityType, entityId, container)  // Inline render
TraceChain.close()                            // Modal kapatır
```

**Visual Design:**
- **Flow diagram:** Upstream ← Current Entity → Downstream
- **Renk kodlaması:**
  | Entity Type | Renk | Hex |
  |-------------|------|-----|
  | Scenario/Process | Mavi | `#3B82F6` |
  | Workshop | Mor | `#8B5CF6` |
  | Requirement (Fit) | Yeşil | `#10B981` |
  | Requirement (Gap) | Kırmızı | `#EF4444` |
  | Requirement (Partial) | Amber | `#F59E0B` |
  | WRICEF/Config | Perga Gold | `#C08B5C` |
  | FS/TS | Gri | `#6B7280` |
  | Test (Pass) | Yeşil | `#10B981` |
  | Test (Fail) | Kırmızı | `#EF4444` |
  | Defect (Critical) | Kırmızı | `#EF4444` |
  | Defect (High) | Amber | `#F59E0B` |
  | Open Item | Turuncu | `#F97316` |
  | Interface | Cyan | `#06B6D4` |

- **Chain depth bar:** `█████░` 5/6 formatında progress bar
- **Gaps section:** `⚠️ Missing: No Functional Spec written`
- **Clickable nodes:** Her kutu tıklanabilir → `showView()` ile navigasyon

### Task 2.2 — Modal HTML Yapısı
| Alan | Detay |
|------|-------|
| Dosya | `trace-chain.js` içinde dynamically generated |
| Efor | 2 saat |
| Açıklama | Modal overlay + panel + header + chain-flow + lateral + gaps |

**Yapı:**
```
┌─ Modal Overlay ──────────────────────────────────────┐
│ ┌─ Modal Panel (max-width:900px) ──────────────────┐ │
│ │ Header: 🔗 Traceability Chain [entity code] [✕]  │ │
│ │                                                    │ │
│ │ Chain Depth: █████░ 5/6 — Missing: FS/TS          │ │
│ │                                                    │ │
│ │ ┌────┐ → ┌────┐ → ┌────┐ → ┌────┐ → ┌────┐     │ │
│ │ │Scn │   │Proc│   │ WS │   │Req │   │WRIC│     │ │
│ │ └────┘   └────┘   └────┘   └────┘   └────┘     │ │
│ │                                 │                  │ │
│ │                           Open Items (2)           │ │
│ │                                                    │ │
│ │ ⚠️ Gaps: No Test Cases created                    │ │
│ └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Task 2.3 — Script Include
| Alan | Detay |
|------|-------|
| Dosya | `templates/index.html` |
| Efor | 0.5 saat |
| Açıklama | `trace-chain.js` dosyasını mevcut `trace-view.js` SONRASINA ekle |

**Yapılacak:**
```html
<script src="/static/js/components/trace-chain.js"></script>
```
> ⚠️ `trace-view.js` korunacak — fallback olarak kalacak

### Task 2.4 — Error Handling & Loading States
| Alan | Detay |
|------|-------|
| Dosya | `trace-chain.js` içinde |
| Efor | 1.5 saat |
| Açıklama | Loading spinner, error mesajları, empty state |

**Durumlar:**
- **Loading:** "Traceability chain yükleniyor..." spinner
- **Error:** "Veri yüklenemedi" + retry butonu
- **Empty:** "Bu entity için bağlantı bulunamadı"
- **404:** "Entity bulunamadı"

### Sprint 2 Kabul Kriterleri
- [ ] `TraceChain.show('backlog_item', 1)` → modal açılır, chain görünür
- [ ] `TraceChain.renderInTab('explore_requirement', 'REQ-001', container)` → inline render
- [ ] Renk kodlaması entity type'a göre doğru
- [ ] Chain depth bar doğru seviyeyi gösterir
- [ ] Gap uyarıları görünür
- [ ] Her node tıklanabilir
- [ ] Modal ESC/✕ ile kapatılabilir
- [ ] Mevcut `TraceView` component bozulmadı

---

## 🏃 Sprint 3: Frontend Entegrasyon (Wiring)

**Süre:** 1 gün (~8 saat)  
**Bağımlılık:** Sprint 1 + Sprint 2 tamamlanmış olmalı  
**Çıktı:** Tüm view'larda çalışan trace button/tab

### Task 3.1 — Backlog Detail Traceability Tab
| Alan | Detay |
|------|-------|
| Dosya | `static/js/views/backlog.js` (~line 921) |
| Efor | 2 saat |
| Açıklama | `_renderDetailTrace()` fonksiyonunu TraceChain ile güncelle |

**Değişiklik:**
```javascript
// Eski: Direkt API.get → 404 hatası
// Yeni: TraceChain.renderInTab('backlog_item', item.id, container)
// Fallback: Direkt API call (günceli çalışan endpoint ile)
```

> ⚠️ `backlog.js` satır 881 ve 925'teki `API.get('/traceability/backlog_item/${i.id}')` çağrıları kontrol edilecek
> ⚠️ `API.get()` prefix'i doğrulanacak: `grep "baseURL\|API_BASE" static/js/api.js`

### Task 3.2 — Explore Requirements Trace Button
| Alan | Detay |
|------|-------|
| Dosya | `static/js/views/explore_requirements.js` (~line 239) |
| Efor | 1.5 saat |
| Açıklama | Trace butonunu TraceChain'e yönlendir |

**Değişiklik:**
```javascript
// Eski: TraceView.showForRequirement('${r.id}')
// Yeni: TraceChain.show('explore_requirement', '${r.id}')
// Fallback: TraceView hala çalışır
```

### Task 3.3 — Explore Requirements Detail Panel Trace
| Alan | Detay |
|------|-------|
| Dosya | `static/js/views/explore_requirements.js` (~line 174) |
| Efor | 1.5 saat |
| Açıklama | Detail panel'deki "Traceability" section'ını TraceChain.renderInTab ile güncelle |

### Task 3.4 — Test Execution Traceability Tab
| Alan | Detay |
|------|-------|
| Dosya | `static/js/views/test_execution.js` (~line 51) |
| Efor | 1.5 saat |
| Açıklama | Traceability tab'ını TraceChain ile güncelle |

**Değişiklik:**
```javascript
case 'traceability':
    if (typeof TraceChain !== 'undefined') {
        await TraceChain.renderInTab('test_case', testCaseId, container);
    } else {
        await renderTraceability(); // mevcut fallback
    }
    break;
```

### Task 3.5 — API Prefix Doğrulama & Fix
| Alan | Detay |
|------|-------|
| Dosya | `static/js/api.js` veya ilgili dosya |
| Efor | 1.5 saat |
| Açıklama | `API.get()` fonksiyonunun `/api/v1` prefix'ini otomatik ekleyip eklemediğini doğrula |

**Kontrol:**
- `API.get('/traceability/backlog_item/1')` → gerçekte `GET /api/v1/traceability/backlog_item/1` mi yapıyor?
- Eğer prefix otomatik değilse, frontend çağrılarını düzelt

### Sprint 3 Kabul Kriterleri
- [ ] Backlog item detail → Traceability tab → chain görünür (önceden "Could not load" idi)
- [ ] Explore Requirements → Trace butonu → TraceChain modal açılır
- [ ] Explore Requirements → Detail panel → Traceability section inline render
- [ ] Test Execution → Traceability tab → çalışır
- [ ] Mevcut TraceView fallback olarak korunuyor
- [ ] Console'da 404 hatası yok

---

## 🏃 Sprint 4: Test, Validasyon & Dokümantasyon

**Süre:** 1 gün (~8 saat)  
**Bağımlılık:** Sprint 1 + 2 + 3 tamamlanmış olmalı  
**Çıktı:** Tam test coverage, doğrulanmış entegrasyon

### Task 4.1 — API Contract Test Suite
| Alan | Detay |
|------|-------|
| Dosya | `tests/test_traceability_unified.py` (YENİ) |
| Efor | 3 saat |
| Açıklama | pytest ile unified endpoint testi |

**Test senaryoları:**
```python
# Pozitif testler
test_backlog_item_trace_returns_200()
test_explore_requirement_trace_with_string_id()
test_scenario_full_downstream_chain()
test_test_case_upstream_trace()
test_defect_upstream_trace()
test_response_has_required_fields()  # upstream, downstream, chain_depth, gaps
test_lateral_links_included()
test_chain_depth_calculation()
test_gap_detection_missing_test_cases()

# Negatif testler
test_invalid_entity_type_returns_404()
test_invalid_entity_id_returns_400()
test_nonexistent_entity_returns_404()
test_depth_parameter_max_20()
test_include_lateral_false()
```

### Task 4.2 — Shell-Based Smoke Test Script
| Alan | Detay |
|------|-------|
| Dosya | `scripts/smoke_test_traceability.sh` (YENİ) |
| Efor | 1 saat |
| Açıklama | curl ile tüm entity type'ları test eden bash script |

### Task 4.3 — Manuel Frontend Doğrulama
| Alan | Detay |
|------|-------|
| Efor | 2 saat |
| Açıklama | 6 senaryo ile E2E manuel test |

| # | Test | Adımlar | Beklenen |
|---|------|---------|----------|
| 1 | Backlog trace yüklenir | WRICEF item aç → Traceability tab | Chain render ("Could not load" DEĞİL) |
| 2 | Requirement trace | Requirements → Trace butonu | Modal: full chain + upstream |
| 3 | Chain depth doğru | WRICEF + Test bağlı REQ | Depth 4/6 veya üzeri |
| 4 | Gap'ler gösterilir | WRICEF var ama Test yok | ⚠️ "No Test Cases" uyarısı |
| 5 | Tıklanabilir node'lar | Chain'de bir kutuya tıkla | O entity'nin detail page'ine git |
| 6 | Lateral linkler | Open Item bağlı REQ | Open Items lateral branch görünür |

### Task 4.4 — Regresyon Testi
| Alan | Detay |
|------|-------|
| Efor | 1 saat |
| Açıklama | Mevcut testlerin hepsinin geçtiğini doğrula |

```bash
# Mevcut 1593+ test'in hepsi geçmeli
python -m pytest tests/ -x --tb=short -q

# Özellikle bu dosyaların kırılmadığını kontrol et:
python -m pytest tests/test_audit_trace.py -v
python -m pytest tests/test_api_backlog.py -v
python -m pytest tests/test_api_testing.py -v
```

### Task 4.5 — Git Commit & Changelog
| Alan | Detay |
|------|-------|
| Efor | 1 saat |
| Açıklama | Commit message + CHANGELOG güncelleme |

**Commit message:**
```
feat: Unified traceability endpoint + visual chain component

- New: GET /api/v1/traceability/<entity_type>/<entity_id>
- Supports 16 entity types with full upstream/downstream/lateral traversal
- Full SAP Activate chain: Scenario → Process → Workshop → Req → WRICEF → FS/TS → Test → Defect
- Chain depth indicator (1-6 scale)
- Gap detection (missing links highlighted)
- New TraceChain.js visual component with flow diagram
- Fixes: Backlog item traceability 404 error
- Fixes: Requirement trace shallow depth (was 2/4, now 6/6)
```

### Sprint 4 Kabul Kriterleri
- [ ] `test_traceability_unified.py` — tüm testler geçer
- [ ] `smoke_test_traceability.sh` — 5/5 entity type OK
- [ ] Manuel test 6/6 senaryo geçer
- [ ] Mevcut 1593+ test kırılmadı (regresyon OK)
- [ ] Git commit yapıldı

---

## 📅 Sprint Takvimi (Özet)

```
Sprint 1 ─── Backend Altyapı ───────────────── 1.5 gün ──── Bağımlılık: Yok
  │ T1.1 Blueprint oluşturma          (4h)
  │ T1.2 Upstream builder             (2h)
  │ T1.3 Lateral + Gap detection      (2h)
  │ T1.4 Blueprint registrasyonu      (0.5h)
  │ T1.5 Curl smoke test              (1.5h)
  ▼
Sprint 2 ─── Frontend Component ─────────────── 1.5 gün ──── Bağımlılık: S1
  │ T2.1 TraceChain core component    (6h)
  │ T2.2 Modal HTML yapısı            (2h)
  │ T2.3 Script include               (0.5h)
  │ T2.4 Error/loading states         (1.5h)
  ▼
Sprint 3 ─── Frontend Entegrasyon ───────────── 1 gün ────── Bağımlılık: S1+S2
  │ T3.1 Backlog detail tab           (2h)
  │ T3.2 Explore trace button         (1.5h)
  │ T3.3 Explore detail panel         (1.5h)
  │ T3.4 Test execution tab           (1.5h)
  │ T3.5 API prefix doğrulama         (1.5h)
  ▼
Sprint 4 ─── Test & Validasyon ──────────────── 1 gün ────── Bağımlılık: S1+S2+S3
    T4.1 API contract test suite      (3h)
    T4.2 Shell smoke test script      (1h)
    T4.3 Manuel frontend doğrulama    (2h)
    T4.4 Regresyon testi              (1h)
    T4.5 Git commit & changelog       (1h)
```

---

## ⚠️ Kritik Kurallar

| # | Kural | Neden |
|---|-------|-------|
| 1 | ❌ `trace-view.js` silinmeyecek | Fallback olarak kalacak |
| 2 | ❌ `traceability.py` service değiştirilmeyecek | Yeni endpoint **wrapper** yaklaşım kullanır |
| 3 | ✅ Mevcut `get_chain()` ve `trace_explore_requirement()` kullanılacak | Kanıtlanmış, test edilmiş fonksiyonlar |
| 4 | ✅ Yeni blueprint dosyası oluşturulacak | `audit_bp.py` veya `testing_bp.py` değiştirilmez |
| 5 | ✅ API prefix pattern doğrulanacak | Frontend çağrılarının doğru URL'ye gitmesi kritik |
| 6 | ✅ Perga brand renkleri kullanılacak | Navy `#0B1623`, Gold `#C08B5C`, Marble `#F7F5F0` |
| 7 | ✅ Her sprint sonunda curl/test ile doğrulama | İncremental verification |

---

## 🎯 Risk & Hafifletme

| Risk | Etki | Olasılık | Hafifletme |
|------|------|----------|------------|
| ~~`API.get()` prefix uyumsuzluğu~~ | — | — | **ÇÖZÜLDÜ:** `static/js/api.js:7` → `const BASE = '/api/v1'` olduğu doğrulandı. Frontend'den `API.get('/traceability/...')` çağrısı otomatik olarak `/api/v1/traceability/...` olur. Sprint 3 Task 3.5 hâlâ doğrulama amaçlı kalıyor. |
| ~~`ExploreDecision` model henüz yok~~ | — | — | **ÇÖZÜLDÜ:** `app/models/explore.py:599` → `class ExploreDecision(db.Model)` mevcut. `process_step_id` FK ile `process_steps` tablosuna bağlı. try/except kaldırılabilir, direkt import güvenli. |
| ~~`process_step_id` ExploreRequirement'da yok~~ | — | — | **ÇÖZÜLDÜ:** `app/models/explore.py:860` → `process_step_id = db.Column(String(36), FK→process_steps.id)` mevcut. Ayrıca `workshop_id`, `scope_item_id`, `process_level_id` alanları da var. `hasattr()` koruması gereksiz ama zararsız. |
| Mevcut testlerin kırılması | Yüksek | Düşük | Sprint 4'te regresyon testi; yeni dosyalar mevcut kodla çakışmaz |
| Modal z-index çakışması | Düşük | Düşük | Mevcut modal pattern incelenip uyumlu z-index kullanılacak |
