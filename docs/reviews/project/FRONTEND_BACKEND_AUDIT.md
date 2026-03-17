# Frontend ↔ Backend Uyum Denetim Raporu

**Tarih:** 10 Şubat 2026
**Kapsam:** Sidebar navigasyonu, tüm frontend view dosyaları, 13 backend blueprint

---

## 1. Mevcut Durum Envanteri

### 1.1 Sidebar Yapısı (index.html)

| Grup | Menü Öğesi | data-view | JS View Dosyası | Satır |
|------|-----------|-----------|-----------------|-------|
| **Program Management** | Dashboard | `dashboard` | app.js (inline) | 265 |
| | Programs | `programs` | program.js | 817 |
| **Scope & Requirements** | Scenarios | `scenarios` | scenario.js | 842 |
| | Process Hierarchy | `process-hierarchy` | process_hierarchy.js | 350 |
| | Analysis Hub | `analysis` | analysis.js | 532 |
| | Requirements | `requirements` | requirement.js | 931 |
| **Explore Phase** | Explore Dashboard | `explore-dashboard` | explore_dashboard.js | 322 |
| | Process Hierarchy | `explore-hierarchy` | explore_hierarchy.js | 706 |
| | Workshops | `explore-workshops` | explore_workshops.js | 445 |
| | Requirements & OIs | `explore-requirements` | explore_requirements.js | 582 |
| **Delivery** | Backlog (WRICEF) | `backlog` | backlog.js | 1058 |
| | Test Hub | `testing` | testing.js | 1047 |
| | Integration Factory | `integration` | integration.js | 764 |
| | Data Factory | `data-factory` | ❌ placeholder | — |
| **Go-Live & Run** | Cutover Hub | `cutover` | ❌ placeholder | — |
| | RAID | `raid` | raid.js | 447 |
| | Reports | `reports` | ❌ placeholder | — |
| **AI Assistant** | AI Query | `ai-query` | ai_query.js | 293 |
| | AI Admin | `ai-admin` | ai_admin.js | 390 |

**Toplam:** 18 menü öğesi, 15'i implementasyonu var, 3'ü placeholder.

### 1.2 Frontend → Backend Endpoint Haritası

| # | Frontend Dosyası | Sidebar Grubu | API Endpoint Desenleri | Backend Blueprint | Uyum |
|---|-----------------|---------------|----------------------|-------------------|------|
| 1 | app.js (Dashboard) | Program Mgmt | `/programs/{pid}/testing/dashboard`, `/programs/{pid}/backlog/stats`, scenarios, requirements vb. | program_bp, testing_bp, backlog_bp, scenario_bp, requirement_bp | ✅ Çalışıyor |
| 2 | program.js | Program Mgmt | `/programs`, `/programs/{id}`, `/phases/{id}`, `/gates/{id}`, `/workstreams/{id}`, `/team/{id}`, `/committees/{id}` | program_bp | ✅ Çalışıyor |
| 3 | scenario.js | Scope & Req | `/programs/{pid}/scenarios`, `/scenarios/{id}`, `/workshops/{id}`, `/workshop-documents/{id}` | scenario_bp | ✅ Çalışıyor (eski model) |
| 4 | process_hierarchy.js | Scope & Req | `/programs/{pid}/process-hierarchy`, `/programs/{pid}/process-hierarchy/stats` | scope_bp | ✅ Çalışıyor (eski model) |
| 5 | analysis.js | Scope & Req | `/scenarios/{sid}/processes`, `/processes/{pid}`, `/processes/{pid}/analyses`, `/programs/{pid}/scope-matrix`, `/programs/{pid}/analysis-dashboard`, `/requirement-mappings` | scope_bp + scenario_bp | ✅ Çalışıyor (eski model) |
| 6 | requirement.js | Scope & Req | `/programs/{pid}/requirements`, `/requirements/{id}`, `/open-items/{id}`, `/requirement-traces/{id}`, `/traceability-matrix` | requirement_bp | ✅ Çalışıyor (eski model) |
| 7 | explore_dashboard.js | Explore Phase | `ExploreAPI.snapshots`, `ExploreAPI.levels`, `ExploreAPI.workshops.stats`, `ExploreAPI.requirements.stats`, `ExploreAPI.openItems.stats` | explore_bp | ✅ Düzeltildi |
| 8 | explore_hierarchy.js | Explore Phase | `ExploreAPI.levels.listL1-L4`, `ExploreAPI.signoff.performL3`, `ExploreAPI.scopeChangeRequests.create` | explore_bp | ✅ Düzeltildi |
| 9 | explore_workshops.js | Explore Phase | `ExploreAPI.workshops.list`, `ExploreAPI.workshops.stats`, `ExploreAPI.workshops.create` | explore_bp | ✅ Düzeltildi |
| 10 | explore_workshop_detail.js | Explore Phase | `ExploreAPI.workshops.get`, `ExploreAPI.decisions.*`, `ExploreAPI.fitDecisions.*`, `ExploreAPI.sessions.*`, `ExploreAPI.agenda.*`, `ExploreAPI.attendees.*` | explore_bp (+ client-side stubs) | ⚠️ Kısmen (6 stub) |
| 11 | explore_requirements.js | Explore Phase | `ExploreAPI.requirements.*`, `ExploreAPI.openItems.*` | explore_bp | ✅ Düzeltildi |
| 12 | backlog.js | Delivery | `/programs/{pid}/backlog/*`, `/config-items/*`, `/sprints/*`, `/traceability/*` | backlog_bp | ✅ Çalışıyor |
| 13 | testing.js | Delivery | `/programs/{pid}/testing/catalog`, `/testing/plans/*`, `/testing/cycles/*`, `/testing/executions/*`, `/testing/defects/*`, `/testing/dashboard`, `/testing/traceability-matrix` | testing_bp | ⚠️ Eski (Sprint 1-2-3 yok) |
| 14 | integration.js | Delivery | `/programs/{pid}/interfaces`, `/interfaces/*`, `/waves/*`, `/checklist/*`, `/switch-plans/*` | interface_factory_bp | ✅ Düzeltildi |
| 15 | raid.js | Go-Live | `/programs/{pid}/raid/*`, `/risks`, `/actions`, `/issues`, `/decisions` | raid_bp | ✅ Çalışıyor |
| 16 | ai_query.js | AI | `/ai/query/natural-language`, `/ai/query/execute-sql` | ai_bp | ✅ Çalışıyor |
| 17 | ai_admin.js | AI | `/ai/admin/dashboard`, `/ai/suggestions`, `/ai/usage`, `/ai/audit-log`, `/ai/embeddings/*`, `/ai/prompts` | ai_bp | ✅ Çalışıyor |

---

## 2. Çakışma Analizi

### 2.1 Process Hierarchy: SCOPE vs EXPLORE

| Boyut | Scope versiyonu | Explore versiyonu |
|-------|----------------|-------------------|
| **Sidebar** | "Process Hierarchy" (Scope & Req) | "Process Hierarchy" (Explore Phase) |
| **JS dosyası** | `process_hierarchy.js` (350 satır) | `explore_hierarchy.js` (706 satır) |
| **Backend** | `scope_bp` → `/programs/{pid}/process-hierarchy` | `explore_bp` → `/explore/process-levels?project_id={pid}` |
| **DB modeli** | `Process` → tablo: `processes` | `ProcessLevel` + `ProcessStep` → tablolar: `process_levels`, `process_steps` |
| **Özellikler** | Salt-okunur ağaç görünümü, temel istatistikler | Tam CRUD, fit consolidation, signoff, seed-from-catalog, L2 readiness, BPMN |
| **Olgunluk** | Sprint 3 seviyesi (basit) | Sprint 8+ seviyesi (tam yaşam döngüsü) |

**🔴 KARAR:** Scope versiyonu artık gereksiz. Explore versiyonu daha zengin ve gerçek iş sürecini temsil ediyor. Scope versiyonu kaldırılmalı veya Explore'a yönlendirilmeli.

### 2.2 Requirements: SCOPE vs EXPLORE

| Boyut | Scope versiyonu | Explore versiyonu |
|-------|----------------|-------------------|
| **Sidebar** | "Requirements" (Scope & Req) | "Requirements & OIs" (Explore Phase) |
| **JS dosyası** | `requirement.js` (931 satır) | `explore_requirements.js` (582 satır) |
| **Backend** | `requirement_bp` → `/programs/{pid}/requirements` | `explore_bp` → `/explore/requirements?project_id={pid}` |
| **DB modeli** | `Requirement` + `OpenItem` → tablolar: `requirements`, `open_items` | `ExploreRequirement` + `ExploreOpenItem` → tablolar: `explore_requirements`, `explore_open_items` |
| **Özellikler** | Ebeveyn-çocuk hiyerarşisi, trace'ler, convert→WRICEF, L3 oluşturma, AI analiz | Durum makinası (transition), ALM sync, batch transition, bağımlılıklar |

**🟡 KARAR:** Her iki versiyon da farklı güçlere sahip. Scope versiyonunun izlenebilirlik (traceability) özelliği önemli. Kısa vadede: Sidebar'dan Scope'u kaldır, Explore versiyonunun `requirement.js`'deki traceability özelliklerini absorbe etmesini planla.

### 2.3 Scenarios vs Explore Workshops

| Boyut | Scenarios (Scope) | Workshops (Explore) |
|-------|-------------------|---------------------|
| **Sidebar** | "Scenarios" (Scope & Req) | "Workshops" (Explore Phase) |
| **JS dosyası** | `scenario.js` (842 satır) | `explore_workshops.js` + `explore_workshop_detail.js` (1090 satır) |
| **Backend** | `scenario_bp` → `/scenarios`, `/workshops` | `explore_bp` → `/explore/workshops` |
| **DB modeli** | `Scenario` + `Workshop` → tablolar: `scenarios`, `workshops` | `ExploreWorkshop` → tablo: `explore_workshops` |
| **Özellikler** | Senaryo→Workshop ilişkisi, basit CRUD, doküman yönetimi | Tam yaşam döngüsü (start/complete), kapasite planlama, katılımcılar, gündem, scope items, bağımlılıklar, revizyon logları |

**🔴 KARAR:** Explore Workshops çok daha olgun. Scenario kavramı ise Explore'da doğrudan karşılığı yok — ProcessLevel L1/L2 eşleştirmesiyle kapatılabilir. Kaldırılmalı.

### 2.4 Analysis Hub

| Boyut | Detay |
|-------|-------|
| **Sidebar** | "Analysis Hub" (Scope & Req) |
| **JS dosyası** | `analysis.js` (532 satır) |
| **Backend** | `scope_bp` → `/processes/*/analyses`, `/analysis-dashboard`, `/scope-matrix` |
| **DB modeli** | `Analysis` → tablo: `analyses` (scope modülü) |
| **Explore karşılığı** | `ExploreHierarchyView` → fit/gap analizi doğrudan ProcessLevel/ProcessStep üzerinde |

**🟡 KARAR:** Analysis Hub'ın "Scope Matrix" ve "Fit/Gap Dashboard" özellikleri Explore Dashboard + Explore Hierarchy'de mevcut. Ancak "Analysis entity" (detaylı gap analiz kayıdı) Explore'da yok. Kısa vadede kaldırılabilir; ihtiyaç olursa Explore'a Analysis entity eklenebilir.

### 2.5 Çift Model (Dual Model) Sorunu — Veri İzolasyonu

**KRİTİK:** Eski ve Explore modülleri tamamen farklı DB tablolarına yazıyor. Aralarında senkronizasyon yok.

| Domain | Eski Tablo | Explore Tablo | Senkronizasyon |
|--------|-----------|---------------|----------------|
| Workshop | `workshops` | `explore_workshops` | ❌ Yok |
| Requirement | `requirements` | `explore_requirements` | ❌ Yok |
| Open Item | `open_items` | `explore_open_items` | ❌ Yok |
| Process tree | `processes` | `process_levels` + `process_steps` | ❌ Yok |
| Decision | — | `explore_decisions` | n/a |

**Risk:** Bir modülde girilen veri diğerinde görünmez. Kullanıcı her iki sidebar grubunu aktif kullanırsa veri kaybı/tutarsızlık yaşanır.

---

## 3. Test Hub Frontend Gap Analizi

### 3.1 Mevcut Durum

Test Hub frontend'i (testing.js, 1047 satır) temel 5 tab yapısına sahip:
1. 📋 **Catalog** — Test case CRUD ✅
2. 📅 **Plans & Cycles** — Plan/Cycle/Execution CRUD ✅
3. 🐛 **Defects** — Defect CRUD + AI triage ✅
4. 🔗 **Traceability** — Matris görünümü ✅
5. 📊 **Dashboard** — KPI/grafikler ✅

### 3.2 Backend'de Olup Frontend'te Olmayan Özellikler

#### TS-Sprint 1 — Test Suite & Step (11 route, 0 frontend)

| # | Backend Route | Özellik | Frontend Durumu | Öncelik |
|---|-------------|---------|----------------|---------|
| 1 | `GET /programs/{pid}/testing/suites` | Suite listesi | ❌ Yok | P1 |
| 2 | `POST /programs/{pid}/testing/suites` | Suite oluşturma | ❌ Yok | P1 |
| 3 | `GET /testing/suites/{id}` | Suite detay | ❌ Yok | P1 |
| 4 | `PUT /testing/suites/{id}` | Suite güncelleme | ❌ Yok | P2 |
| 5 | `DELETE /testing/suites/{id}` | Suite silme | ❌ Yok | P2 |
| 6 | `GET /testing/catalog/{id}/steps` | Step listesi | ❌ Yok | P1 |
| 7 | `POST /testing/catalog/{id}/steps` | Step oluşturma | ❌ Yok | P1 |
| 8 | `PUT /testing/steps/{id}` | Step güncelleme | ❌ Yok | P2 |
| 9 | `DELETE /testing/steps/{id}` | Step silme | ❌ Yok | P2 |
| 10 | `POST /testing/cycles/{id}/suites` | Cycle'a suite atama | ❌ Yok | P1 |
| 11 | `DELETE /testing/cycles/{id}/suites/{sid}` | Cycle'dan suite çıkarma | ❌ Yok | P2 |

#### TS-Sprint 2 — Test Run & Defect Detay (16 route, 0 frontend)

| # | Backend Route | Özellik | Frontend Durumu | Öncelik |
|---|-------------|---------|----------------|---------|
| 12 | `GET /testing/cycles/{id}/runs` | Test run listesi | ❌ Yok | P1 |
| 13 | `POST /testing/cycles/{id}/runs` | Test run başlatma | ❌ Yok | P1 |
| 14 | `GET /testing/runs/{id}` | Run detayı | ❌ Yok | P1 |
| 15 | `PUT /testing/runs/{id}` | Run güncelleme | ❌ Yok | P2 |
| 16 | `DELETE /testing/runs/{id}` | Run silme | ❌ Yok | P3 |
| 17 | `GET /testing/runs/{id}/step-results` | Adım sonuçları | ❌ Yok | P1 |
| 18 | `POST /testing/runs/{id}/step-results` | Adım sonucu kaydetme | ❌ Yok | P1 |
| 19 | `PUT /testing/step-results/{id}` | Sonuç güncelleme | ❌ Yok | P2 |
| 20 | `DELETE /testing/step-results/{id}` | Sonuç silme | ❌ Yok | P3 |
| 21 | `GET /testing/defects/{id}/comments` | Defect yorumları | ❌ Yok | P1 |
| 22 | `POST /testing/defects/{id}/comments` | Yorum ekleme | ❌ Yok | P1 |
| 23 | `DELETE /testing/defect-comments/{id}` | Yorum silme | ❌ Yok | P3 |
| 24 | `GET /testing/defects/{id}/history` | Defect geçmişi | ❌ Yok | P1 |
| 25 | `GET /testing/defects/{id}/links` | Defect bağlantıları | ❌ Yok | P2 |
| 26 | `POST /testing/defects/{id}/links` | Bağlantı ekleme | ❌ Yok | P2 |
| 27 | `DELETE /testing/defect-links/{id}` | Bağlantı silme | ❌ Yok | P3 |

#### TS-Sprint 3 — SLA, Go/No-Go, Generation (16 route, 0 frontend)

| # | Backend Route | Özellik | Frontend Durumu | Öncelik |
|---|-------------|---------|----------------|---------|
| 28 | `GET /testing/defects/{id}/sla` | SLA hesabı | ❌ Yok | P2 |
| 29 | `GET /programs/{pid}/testing/dashboard/go-no-go` | Go/No-Go değerlendirme | ❌ Yok | P1 |
| 30 | `POST /testing/cycles/{id}/validate-entry` | Entry criteria kontrolü | ❌ Yok | P2 |
| 31 | `POST /testing/cycles/{id}/validate-exit` | Exit criteria kontrolü | ❌ Yok | P2 |
| 32 | `POST /testing/suites/{id}/generate-from-wricef` | WRICEF'ten otomatik test | ❌ Yok | P1 |
| 33 | `POST /testing/suites/{id}/generate-from-process` | Process'ten otomatik test | ❌ Yok | P1 |
| 34 | `GET /testing/cycles/{id}/uat-signoffs` | UAT sign-off listesi | ❌ Yok | P2 |
| 35 | `POST /testing/cycles/{id}/uat-signoffs` | UAT sign-off oluşturma | ❌ Yok | P2 |
| 36 | `GET /testing/uat-signoffs/{id}` | Sign-off detay | ❌ Yok | P3 |
| 37 | `PUT /testing/uat-signoffs/{id}` | Sign-off güncelleme | ❌ Yok | P2 |
| 38 | `DELETE /testing/uat-signoffs/{id}` | Sign-off silme | ❌ Yok | P3 |
| 39 | `GET /testing/catalog/{id}/perf-results` | Performans sonuçları | ❌ Yok | P2 |
| 40 | `POST /testing/catalog/{id}/perf-results` | Performans kaydı | ❌ Yok | P2 |
| 41 | `DELETE /testing/perf-results/{id}` | Performans silme | ❌ Yok | P3 |
| 42 | `GET /programs/{pid}/testing/snapshots` | Test snapshot listesi | ❌ Yok | P3 |
| 43 | `POST /programs/{pid}/testing/snapshots` | Snapshot oluşturma | ❌ Yok | P3 |

### 3.3 Özet

| Kategori | Backend Route | Frontend'te Var | Eksik | Kapsam |
|----------|:------------:|:--------------:|:-----:|:------:|
| Mevcut (Plan/Cycle/Catalog/Exec/Defect) | 28 | 25 | 3 | %89 |
| TS-Sprint 1 (Suite + Step) | 11 | 0 | **11** | %0 |
| TS-Sprint 2 (Run + StepResult + Defect detail) | 16 | 0 | **16** | %0 |
| TS-Sprint 3 (SLA + GoNoGo + Generate + UAT) | 16 | 0 | **16** | %0 |
| **TOPLAM** | **71** | **25** | **46** | **%35** |

**Backend'in %65'i frontend tarafından kullanılmıyor.**

---

## 4. Sidebar Yapılandırma Önerisi

### 4.1 Önerilen Sidebar (temizlenmiş)

```
PROGRAM MANAGEMENT
  ├── 📊 Dashboard                (mevcut — kalsın)
  └── 📋 Programs                 (mevcut — kalsın)

EXPLORE PHASE
  ├── 📊 Explore Dashboard        (mevcut — kalsın)
  ├── 🏗️ Process Hierarchy        (explore_bp → kalsın)
  ├── 📋 Workshops                (mevcut — kalsın)
  └── 📝 Requirements & OIs       (mevcut — kalsın)

DELIVERY
  ├── ⚙️ Backlog (WRICEF)         (mevcut — kalsın)
  ├── 🧪 Test Hub                 (mevcut — güncellenmeli ⚠️)
  └── 🔌 Integration Factory      (mevcut — kalsın)

GO-LIVE & RUN
  ├── 🗄️ Data Factory             (placeholder — Sprint 10)
  ├── 🚀 Cutover Hub              (placeholder — Sprint 13)
  ├── ⚠️ RAID                     (mevcut — kalsın)
  └── 📈 Reports                  (placeholder — Sprint 11)

AI ASSISTANT
  ├── 🤖 AI Query                 (mevcut — kalsın)
  └── ⚙️ AI Admin                 (mevcut — kalsın)
```

### 4.2 Kaldırılan / Birleştirilen Ekranlar

| # | Eski Ekran | Karar | Gerekçe |
|---|-----------|-------|---------|
| 1 | 🎯 **Scenarios** (Scope & Req) | **🔴 KALDIR** | Explore Workshops daha olgun. Scenario→Workshop ilişkisi ProcessLevel L1/L2 ile temsil ediliyor. Eski `scenarios` tablosu kullanılmaya devam ederse veri izolasyonu riski. |
| 2 | 🗺️ **Process Hierarchy** (Scope & Req) | **🔴 KALDIR** | Explore Process Hierarchy aynı işlevi yapıyor — üstelik fit consolidation, signoff, BPMN gibi ekstra özelliklerle. İki ayrı ağaç (Process vs ProcessLevel) kullanıcıyı şaşırtır. |
| 3 | 🔬 **Analysis Hub** (Scope & Req) | **🟡 KALDIR (koşullu)** | Scope Matrix ve Fit/Gap Dashboard Explore'da mevcut. Detaylı "Analysis entity" ihtiyacı olursa Explore'a eklenebilir. Kaldırılabilir. |
| 4 | 📝 **Requirements** (Scope & Req) | **🔴 KALDIR** | Explore Requirements & OIs daha zengin (transition, ALM sync, batch). Traceability özelliği Explore'a taşınmalı (ayrı iş kalemi). |

### 4.3 Frontend Dosya Etkileri

Sidebar temizliğinden sonra kullanılmayacak dosyalar:

| Dosya | Satır | Durum |
|-------|------:|-------|
| `static/js/views/scenario.js` | 842 | Kaldırılabilir |
| `static/js/views/process_hierarchy.js` | 350 | Kaldırılabilir |
| `static/js/views/analysis.js` | 532 | Kaldırılabilir |
| `static/js/views/requirement.js` | 931 | Kaldırılabilir (traceability taşındıktan sonra) |
| **Toplam** | **2655** | — |

Kaldırılacak backend blueprint'ler (opsiyonel — API geriye dönük uyumluluk için kalabilir):

| Blueprint | Dosya | Durum |
|-----------|-------|-------|
| `scope_bp` | `app/blueprints/scope_bp.py` | Pasifleştirilebilir |
| `scenario_bp` | `app/blueprints/scenario_bp.py` | Pasifleştirilebilir |
| `requirement_bp` | `app/blueprints/requirement_bp.py` | Pasifleştirilebilir (traceability taşındıktan sonra) |

---

## 5. Explore Phase Client-Side Stub Listesi

Bu endpoint'ler `explore-api.js`'de stub (Promise.resolve) olarak tanımlı — backend'de karşılığı yok:

| # | Stub Grup | Metotlar | Backend Endpoint | Aksiyon |
|---|----------|---------|-----------------|--------|
| 1 | `sessions` | list, get, create, update | `/explore/workshops/{wsId}/sessions/*` | Backend'e session CRUD ekle |
| 2 | `fitDecisions` | list, create, update | `/explore/workshops/{wsId}/fit-decisions/*` | Backend'e fit-decision CRUD ekle |
| 3 | `decisions` | list, create, update, delete | `/explore/workshops/{wsId}/decisions/*` | Backend'e decision CRUD ekle (not: process-step seviyesinde mevcut) |
| 4 | `agenda` | list, create, update, delete | `/explore/workshops/{wsId}/agenda-items/*` | Backend'e agenda CRUD ekle |
| 5 | `attendees` | list, create, update, delete | `/explore/workshops/{wsId}/attendees/*` | Backend'e attendee CRUD ekle |
| 6 | `fitPropagation` | propagate | `/explore/fit-propagation/propagate` | Backend'e propagation endpoint ekle |

---

## 6. Effort Tahmini

### 6.1 Sidebar Temizliği

| İş Kalemi | Dosyalar | Effort |
|-----------|---------|--------|
| Sidebar'dan 4 eski menü öğesini kaldır | `index.html` | 0.5 saat |
| `app.js` view registry'den kaldır | `app.js` | 0.5 saat |
| Eski JS dosyalarını arşivle/sil | 4 dosya | 0.5 saat |
| Eski blueprint'leri deaktive et | `__init__.py` | 0.5 saat |
| Dashboard KPI'ları güncelle (eski model referansları) | `app.js` | 1 saat |
| **Alt toplam** | | **3 saat** |

### 6.2 Test Hub Frontend Güncellemesi

| İş Kalemi | Detay | Effort |
|-----------|-------|--------|
| **Suite tab ekleme** | Suite listesi, CRUD modal, cycle-suite assignment | 6 saat |
| **Step UI (case detail içinde)** | `test_steps` textarea yerine yapısal step listesi | 4 saat |
| **Test Run tab/panel** | Run listesi, başlat/durdur, step-result tablo | 8 saat |
| **Defect Comments** | Defect detay modalına yorum thread'i | 3 saat |
| **Defect History** | Defect detay modalına audit trail | 2 saat |
| **Defect Links** | Link ekleme/listeleme paneli | 2 saat |
| **SLA badge** | Defect kart/satırına SLA göstergesi | 2 saat |
| **Go/No-Go panel** | Dashboard tab'ına Go/No-Go scorecard | 4 saat |
| **Generate butonları** | Suite detayında "Generate from WRICEF/Process" | 2 saat |
| **UAT Sign-off** | Cycle detayına sign-off paneli | 3 saat |
| **Performance Results** | Case detayına performans sonuç tablosu | 2 saat |
| **Test Snapshots** | Dashboard'a snapshot capture/list | 2 saat |
| **Entry/Exit Criteria** | Cycle detayında validation butonları | 2 saat |
| **Alt toplam** | | **42 saat** |

### 6.3 Explore Phase Stub → Backend

| İş Kalemi | Detay | Effort |
|-----------|-------|--------|
| Workshop sessions CRUD | 4 route (model mevcut?) | 3 saat |
| Fit decisions CRUD (workshop-scoped) | 3 route | 2 saat |
| Workshop decisions CRUD | 4 route | 2 saat |
| Agenda items CRUD | 4 route | 2 saat |
| Attendees CRUD | 4 route | 2 saat |
| Fit propagation | 1 route | 1 saat |
| **Alt toplam** | | **12 saat** |

### 6.4 Diğer

| İş Kalemi | Detay | Effort |
|-----------|-------|--------|
| Traceability'yi Explore'a taşıma | explore_requirements.js'e trace desteği | 6 saat |
| Eski veri migration (opsiyonel) | workshops → explore_workshops, requirements → explore_requirements | 8 saat |
| **Alt toplam** | | **14 saat** |

### 6.5 Toplam Effort

| Kategori | Saat |
|----------|:----:|
| Sidebar Temizliği | 3 |
| Test Hub Frontend | 42 |
| Explore Phase Stub→Backend | 12 |
| Diğer (traceability, migration) | 14 |
| **GENEL TOPLAM** | **71 saat** |

---

## 7. Öncelik Sıralaması

| Sıra | İş | Etki | Effort | Önerilen Sprint |
|:----:|-----------|------|:------:|:---------------:|
| 1 | Sidebar temizliği (4 eski ekranı kaldır) | Kullanıcı karışıklığını önler | 3s | Hemen |
| 2 | Test Hub — Suite + Step UI | Sprint 1 backend'ini açar | 10s | Sonraki sprint |
| 3 | Test Hub — Run + StepResult | Sprint 2 backend'ini açar | 10s | Sonraki sprint |
| 4 | Explore stub → backend (sessions, decisions, attendees) | Workshop detail tam çalışır | 12s | Sonraki sprint |
| 5 | Test Hub — Defect detail (comments, history, links) | Sprint 2 tamamlanır | 7s | Sprint +2 |
| 6 | Test Hub — Go/No-Go + SLA + Generate | Sprint 3 backend'ini açar | 10s | Sprint +2 |
| 7 | Test Hub — UAT + Perf + Snapshot + Entry/Exit | Sprint 3 tamamlanır | 9s | Sprint +3 |
| 8 | Traceability → Explore taşıma | Tam geçiş | 6s | Sprint +3 |
| 9 | Eski veri migration (opsiyonel) | Veri bütünlüğü | 8s | Planlama gerekli |
