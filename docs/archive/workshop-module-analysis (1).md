# Workshop Modülü — Mimari Analiz & Karar Dokümanı

**Tarih:** 11 Şubat 2026
**Girdiler:** Operasyonel Model Dokümanı (PDF), Deep Research Report (MD), Mevcut Kod Analizi

---

## 1. Üç Kaynak Karşılaştırması

### 1.1 Dokümanların Önerdiği Zincir

Her iki doküman da aynı uçtan uca zinciri tanımlıyor:

```
L3 Process → Workshop → Requirement (Fit/Partial/Gap)
    → Conversion Engine → WRICEF / ConfigItem
        → FS / TS → Build → Unit Test → SIT → UAT
            → Defect → Go-Live Readiness
```

Operasyonel Model bunu 15 bölümde detaylandırırken, Deep Research Report aynı yapıyı SAP Activate, Cloud ALM ve akademik PMO literatürüyle destekliyor.

### 1.2 Kodda Ne Var?

Mevcut kod bu zincirin **iki adasını** inşa etmiş ama arayı bağlamamış:

```
ADA 1 — Explore (explore.py, explore_bp.py)
  ProcessLevel (L1-L4) → ExploreWorkshop → ProcessStep
    → ExploreDecision / ExploreOpenItem / ExploreRequirement

ADA 2 — Build & Test (backlog.py, testing.py)
  BacklogItem (WRICEF) → FunctionalSpec → TechnicalSpec
  TestPlan → TestCycle → TestCase → TestExecution → Defect
  ConfigItem → TestCase linkage
```

**Kopuk köprü:** Ada 1'den Ada 2'ye geçiş mekanizması (Conversion Engine) yok.

---

## 2. Entity Bazında Detaylı Karşılaştırma

### 2.1 ProcessLevel (L1-L4 Hierarchy) ✅ TAM

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| L1-L4 hiyerarşi | L1→L2→L3→L4 | parent_id recursive FK | ✅ |
| Scope status | in/out/under_review | scope_status column | ✅ |
| Fit status propagation | L4'ten yukarı | fit_status + confirmation_status | ✅ |
| SAP Best Practice ID | Scope Item ref | sap_process_id column | ✅ |

**Yorum:** Hierarchy modeli güçlü ve doğru tasarlanmış. Dokunmaya gerek yok.

### 2.2 ExploreWorkshop ✅ ZENGİN

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| Type (F2S/Delta/Review) | Evet | type column | ✅ |
| Status lifecycle | draft→scheduled→in_progress→completed | status column | ✅ |
| Multi-session | Evet | session_number, total_sessions, original_workshop_id | ✅ |
| Facilitator | Evet | facilitator_id | ✅ |
| Process area / Wave | Evet | process_area, wave | ✅ |
| ScopeItems (L3 bağı) | Workshop ↔ L3 | WorkshopScopeItem M2M | ✅ |
| Attendees | Evet | WorkshopAttendee | ✅ |
| Agenda | Evet | WorkshopAgendaItem | ✅ |
| Revision tracking | Evet | WorkshopRevisionLog, reopen_count | ✅ |
| Documents | Evet | ExploreWorkshopDocument | ✅ |
| Scenario type | Greenfield/Brownfield/Public | **YOK** | ⚠️ Minor |

**Yorum:** Workshop modeli zengin ve iyi düşünülmüş. Scenario type eksik ama program seviyesinde tanımlanabilir.

### 2.3 ProcessStep ✅ TAM

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| Workshop ↔ L4 bağı | Evet | workshop_id + process_level_id FK | ✅ |
| Fit decision (Fit/Partial/Gap) | Evet | fit_decision column | ✅ |
| Demo tracking | Show-and-tell | demo_shown, bpmn_reviewed | ✅ |
| Session carry-over | Evet | previous_session_step_id, carried_from_session | ✅ |

**Yorum:** ProcessStep modeli SAP Activate F2S akışına uygun. Dokunmaya gerek yok.

### 2.4 ExploreDecision ✅ TAM

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| Decision text | Evet | text column | ✅ |
| Decided by | Evet | decided_by, decided_by_user_id | ✅ |
| Category | Evet | category (config/customization/process_change/integration/other) | ✅ |
| Status | Evet | status (pending/approved/escalated/superseded) | ✅ |
| Rationale | Evet | rationale column | ✅ |
| Steering gerekebilir | Escalation | status = 'escalated' | ✅ |

**Yorum:** Decision modeli tam. Dokunmaya gerek yok.

### 2.5 ExploreOpenItem ✅ TAM

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| Title/Description | Evet | title, description | ✅ |
| Priority | Evet | priority (P1-P4) | ✅ |
| Status lifecycle | Evet | open→in_progress→blocked→closed→cancelled | ✅ |
| Assignee | Evet | assignee_id, assignee_name | ✅ |
| Due date / Aging | Evet | due_date, created_at (aging hesaplanabilir) | ✅ |
| Workshop + Step bağı | Evet | workshop_id, process_step_id FK | ✅ |

**Yorum:** OpenItem modeli tam. Aging KPI'ı frontend'de hesaplanabilir.

### 2.6 ExploreRequirement ⚠️ EKSİKLER VAR

| Özellik | Doküman İstiyor | Kod | Durum |
|---------|-----------------|-----|-------|
| Requirement ID (code) | Evet | code (REQ-001) | ✅ |
| Process L3 Ref | Evet | process_level_id, scope_item_id FK | ✅ |
| Workshop Ref | Evet | workshop_id FK | ✅ |
| Type (dev/config/integration...) | Evet | type column | ✅ |
| Fit status (gap/partial_fit) | Evet | fit_status column | ✅ |
| Priority | Evet | priority (P1-P4) | ✅ |
| Status lifecycle | Evet | draft→under_review→approved→in_backlog→realized→verified→deferred→rejected | ✅ |
| Effort | Evet | effort_hours, effort_story_points | ✅ |
| Complexity | Evet | complexity (low/medium/high/critical) | ✅ |
| **Impact** | High/Medium/Low | **YOK** | ❌ |
| **Module** | SD/MM/FI etc. | **YOK** | ❌ |
| **Integration Ref** | Varsa | **YOK** | ❌ |
| **Data Dependency** | Varsa | **YOK** | ❌ |
| **Business Criticality** | KPI impact | **YOK** | ❌ |
| **Convert Status** | Converted/Pending | **YOK** (backlog_item_id doluluk kontrolü ile türetilebilir) | ⚠️ |
| **WRICEF Candidate Flag** | Conversion input | **YOK** | ❌ |
| BacklogItem (WRICEF) bağı | FK | backlog_item_id FK | ✅ Var ama dolduran yok |
| ConfigItem bağı | FK | config_item_id FK | ✅ Var ama dolduran yok |
| ALM sync | Evet | alm_id, alm_synced, alm_sync_status | ✅ |

**Yorum:** Requirement modeli iskelet olarak güçlü ama dokümanın istediği 6 analitik alanı eksik. FK'lar (backlog_item_id, config_item_id) mevcut ama bunları dolduran Conversion Engine yok.

### 2.7 Conversion Engine ❌ YOK

| Özellik | Doküman İstiyor | Kod | Durum |
|---------|-----------------|-----|-------|
| Fit → ConfigItem dönüşümü | Otomatik | Sadece arşiv (requirement_bp.py) | ❌ |
| Partial/Gap → WRICEF dönüşümü | Otomatik | Sadece arşiv | ❌ |
| ExploreRequirement.convert endpoint | POST /requirements/<id>/convert | **YOK** | ❌ |
| Anti-WRICEF karar ağacı | 5 adımlı framework | **YOK** | ❌ |

**Yorum:** Bu zincirin en kritik eksik halkası. Eski model (requirement_bp.py → archive) içinde convert mantığı var ve doğru çalışıyor. ExploreRequirement için aynı mantık adapte edilmeli.

### 2.8 BacklogItem (WRICEF) ✅ MODEL TAM

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| WRICEF ID / Code | Evet | code (W-0001, R-0001...) | ✅ |
| Type (W,R,I,C,E,F) | Evet | wricef_type | ✅ |
| Requirement Ref | FK | requirement_id FK | ✅ |
| Process Ref | FK | process_id FK | ✅ |
| Priority / Estimate | Evet | priority, estimated_hours, story_points | ✅ |
| Status lifecycle | Evet | open→in_progress→dev_complete→testing→done | ✅ |
| Test Coverage Flag | Evet | **YOK — türetilebilir** | ⚠️ |

**Yorum:** Model tam, ama requirement_id eski "requirements" tablosuna FK. ExploreRequirement ile bağlanmıyor.

### 2.9 FS / TS ✅ MODEL TAM

FunctionalSpec (backlog_item_id FK) → TechnicalSpec (functional_spec_id FK) zinciri doğru.

### 2.10 TestCase / TestExecution / Defect ✅ MODEL TAM ama FK UYUMSUZ

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| TestCase ↔ Requirement | FK | requirement_id → **requirements** (eski tablo) | ⚠️ FK uyumsuz |
| TestCase ↔ WRICEF | FK | backlog_item_id FK | ✅ |
| TestCase test_layer | Unit/SIT/UAT | unit/sit/uat/regression/performance/cutover | ✅ |
| Defect ↔ TestCase | FK | test_case_id FK | ✅ |
| Defect ↔ WRICEF | FK | backlog_item_id FK | ✅ |
| Defect ↔ Environment | Evet | environment (DEV/QAS/PRD) | ✅ |
| Defect ↔ Requirement | FK | linked_requirement_id → **requirements** (eski tablo) | ⚠️ FK uyumsuz |

**Yorum:** Test modeli zengin ve doğru. Tek sorun: FK'lar eski requirements tablosuna bakıyor, explore_requirements'a değil.

### 2.11 Risk ⚠️ AYRIK

| Özellik | Doküman | Kod | Durum |
|---------|---------|-----|-------|
| Risk modeli | Workshop çıktısı | Risk (raid.py) — bağımsız modül | ⚠️ |
| Workshop bağı | workshop_id FK | **YOK** | ❌ |

### 2.12 Coverage Engine / Go-Live Readiness ❌ YOK

Dokümanın tanımladığı KPI sorguları ve Go-Live algoritması henüz implemente edilmemiş.

---

## 3. Frontend UI Durumu

### 3.1 Dosyalar ve Boyutları

| Dosya | Satır | Rol |
|-------|-------|-----|
| explore_workshops.js | 527 | Workshop Hub (liste) |
| explore_workshop_detail.js | 720 | Workshop Detail (step/decision/OI/req inline) |
| explore_hierarchy.js | 764 | Process Hierarchy (L1-L4 tree) |
| explore_requirements.js | 657 | Requirements listesi |
| explore_dashboard.js | 381 | Dashboard |
| explore-api.js | 215 | API client |
| **Toplam** | **3,264** | |

### 3.2 Aktif UI Bug'ları

**BUG 1 (KRİTİK): renderPage() form değerlerini yok ediyor**

```javascript
// explore_workshop_detail.js, satır 538-543
async function submitInlineForm(type, stepId) {
    _inlineBusy = true;
    renderPage();  // ← main.innerHTML = ... → TÜM DOM SİLİNİYOR
    // form input'ları artık yok
    const text = document.getElementById('inlineDecText')?.value;  // → null
```

Kullanıcı Decision/OI/Requirement formunu doldurur → Save'e basar → `renderPage()` tüm DOM'u yeniden çizer → `getElementById` null döner → validation hatası gösterir. **3 inline form da kırık.**

**BUG 2: Delta butonu yanlış koşulda**

```javascript
// satır 83, 109
const canComplete = w.status === 'in_progress';
${canComplete ? ...'Create Delta'... : ''}  // in_progress'te gösteriliyor
```

Backend `completed` istiyor → "Can only create delta from completed workshops" hatası.

### 3.3 Backend API Durumu

- **90 endpoint** (explore_bp.py, 3,392 satır)
- Step-based create endpoint'leri (`/process-steps/<id>/decisions`, `/open-items`, `/requirements`) doğru çalışıyor
- Frontend API client (explore-api.js) `processSteps.addDecision/addOpenItem/addRequirement` ile doğru URL'leri kullanıyor
- `/workshops/<id>/full` aggregate endpoint var ve çalışıyor
- `/workshops/<id>/create-delta` dedicated endpoint var

---

## 4. Karar: Silip Baştan mı, Düzeltme mi?

### 4.1 Silip Baştan Yazma Analizi

**Avantajları:**
- Temiz, tutarlı mimari
- FK uyumsuzlukları olmaz
- Naming convention'lar tutarlı olur

**Dezavantajları:**
- 90 backend endpoint yeniden yazılır (~3,400 satır)
- 3,264 satır frontend yeniden yazılır
- Mevcut çalışan özellikler (hierarchy, workshop lifecycle, multi-session, revision tracking) riske girer
- Tahmini süre: 40-60 saat
- Test verileri ve migration riski

**Sonuç: ÖNERİLMİYOR.** Mevcut modeller %80 doğru tasarlanmış. Sorunlar yapısal değil, bağlantısal.

### 4.2 Hedefli Düzeltme Analizi

**Sorunlar ve çözüm maliyetleri:**

| # | Sorun | Çözüm | Süre |
|---|-------|-------|------|
| A | renderPage() DOM yok etme bug'ı | Form değerlerini renderPage'den ÖNCE oku | 0.5h |
| B | Delta butonu yanlış koşul | `canComplete` → `w.status === 'completed'` | 0.25h |
| C | ExploreRequirement'a 6 eksik alan ekleme | Migration + model update | 1h |
| D | Conversion Engine (Req→WRICEF/Config) | Yeni endpoint: POST /explore/requirements/<id>/convert | 3h |
| E | FK uyumsuzluğu (TestCase↔ExploreReq) | explore_requirement_id ek FK veya dual-link | 2h |
| F | Coverage Engine KPI queries | Dashboard endpoint'leri | 3h |
| G | Risk ↔ Workshop bağı | Risk modeline workshop_id FK ekle | 1h |
| **Toplam** | | | **~11h** |

**Sonuç: ÖNERİLİYOR.** 11 saatlik hedefli çalışma ile tüm kopukluklar giderilir.

---

## 5. Önerilen Yol Haritası — 7 Prompt Dizisi

### Prompt W-1: Inline Form Bug Fix (0.75h)
**Dosyalar:** explore_workshop_detail.js
**İçerik:**
- BUG 1 Fix: Form değerlerini `renderPage()` çağrılmadan ÖNCE oku, değişkenlere ata
- BUG 2 Fix: Delta butonunu `w.status === 'completed'` koşuluna bağla
**Test:** Decision/OI/Requirement inline form'ları çalışır, Delta butonu sadece completed'da görünür

### Prompt W-2: ExploreRequirement Model Enrichment (1h)
**Dosyalar:** explore.py (model), explore_bp.py (endpoint'ler)
**İçerik:**
- 6 yeni alan ekle: impact, module, integration_ref, data_dependency, business_criticality, wricef_candidate_flag
- to_dict() güncelle
- create/update endpoint'lerini bu alanları kabul edecek şekilde güncelle
- Inline form'lara opsiyonel olarak impact ve module dropdown'ları ekle
**Test:** Requirement oluştururken yeni alanlar kaydedilir ve okunur

### Prompt W-3: Conversion Engine (3h)
**Dosyalar:** explore_bp.py (yeni endpoint), explore-api.js (yeni method), explore_requirements.js (UI buton)
**İçerik:**
- POST /explore/requirements/<id>/convert endpoint'i (arşivdeki mantıktan adapte)
- Kural: Fit → ConfigItem, Partial/Gap → BacklogItem (WRICEF)
- Frontend'de Requirement satırında "Convert" butonu
- Convert sonrası requirement.status → 'in_backlog', backlog_item_id/config_item_id dolu
**Test:** Gap requirement'ı WRICEF'e dönüşür, Fit requirement'ı ConfigItem'a dönüşür, FK'lar dolar

### Prompt W-4: Test Traceability FK (2h)
**Dosyalar:** testing.py (model), testing_bp.py (endpoint'ler)
**İçerik:**
- TestCase'e explore_requirement_id FK ekle (eski requirement_id'yi bozmadan)
- Defect'e explore_requirement_id FK ekle
- TestCase oluştururken explore_requirement_id kabul et
- Requirements view'da "Test Coverage" göstergesi
**Test:** ExploreRequirement'tan TestCase'e traceability çalışır

### Prompt W-5: Coverage Engine KPI (3h)
**Dosyalar:** explore_bp.py (KPI endpoint'leri), explore_dashboard.js (UI)
**İçerik:**
- GET /explore/coverage-stats endpoint'i:
  - Kaç Requirement test edildi (test coverage %)
  - Kaç WRICEF test coverage aldı
  - Kaç Gap UAT'ta patladı
  - Süreç bazında defect dağılımı
- Go-Live Readiness skoru (dokümanın algoritması)
- Dashboard'da KPI kartları
**Test:** Dashboard'da gerçek veriye dayalı KPI'lar görünür

### Prompt W-6: Risk ↔ Workshop Linkage (1h)
**Dosyalar:** raid.py (model), raid_bp.py (endpoint)
**İçerik:**
- Risk modeline workshop_id FK ekle
- Workshop detail'da Risk tab'ı ekle veya mevcut RAID view'dan bağla
**Test:** Workshop'tan Risk oluşturulabilir, Risk listesinde workshop ref görünür

### Prompt W-7: Documentation & Validation (1h)
**Dosyalar:** CHANGELOG.md, PROGRESS_REPORT.md, project-inventory.md
**İçerik:**
- Tüm değişikliklerin dokümantasyonu
- Uçtan uca akış testi: L3 → Workshop → Requirement → Convert → WRICEF → TestCase
- Entity relationship diyagramı güncellemesi
**Test:** Tam zincir çalışır, dokümanlar güncel

---

## 6. Zincir Tamamlandığında

W-1'den W-7'ye kadar tamamlandığında:

```
L3 Process (ProcessLevel)
  → Workshop (ExploreWorkshop) — inline Decision/OI/Requirement ✅
    → Requirement (ExploreRequirement) — enriched fields ✅
      → Conversion Engine ✅
        → WRICEF (BacklogItem) ← FK bağlı ✅
        → ConfigItem ← FK bağlı ✅
          → FS / TS ← FK zinciri mevcut ✅
            → TestCase ← explore_requirement_id FK ✅
              → TestExecution ← mevcut ✅
                → Defect ← tüm FK'lar bağlı ✅
                  → Coverage KPI ✅
                    → Go-Live Readiness ✅
```

Dokümanın istediği 15 bileşenin tamamı bağlanmış olur.

---

## 7. Özet

| Kriter | Silip Baştan | Hedefli Düzeltme |
|--------|-------------|-----------------|
| Risk | Yüksek (çalışan kod bozulur) | Düşük (artımlı) |
| Süre | 40-60 saat | ~11 saat |
| Sonuç kalitesi | Temiz ama aynı seviye | Aynı seviye + mevcut zenginlik korunur |
| Test edilebilirlik | Her şey sıfırdan test | Her prompt sonrası test |

**Tavsiye:** Hedefli düzeltme, W-1'den başlayarak.
