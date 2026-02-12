# Sprint Devam Planı v2 — 11 Şubat 2026

---

## 1. TD-Sprint 1 Doğrulama Sonucu

| # | ID | Görev | Durum | Not |
|---|------|-------|:-----:|-----|
| 1 | TD-1.1 | CHANGELOG 33 eksik commit | 🟡 | 150 entry var ama "Unreleased"da TS-3/S10 hala "Planlanmış" etiketli — commit hash'leri eksik |
| 2 | TD-1.2 | README güncel (77/336/916) | ✅ | Tüm metrikler doğru |
| 3 | TD-1.3 | project-inventory.md M10+§5.2 | 🟡 | M10 doğru, .bak dosyaları silinmiş ama §5.2 tablosu hala cleanup listesi gösteriyor |
| 4 | TD-1.4 | D5 plan başlık metrikleri | ✅ | 77 DB, 336 route, 916 test doğru |
| 5 | TD-1.5 | D6 progress report metrikleri | ✅ | Tüm metrikler güncel |
| 6 | TD-1.6 | D10 tarih + tech debt durum | ✅ | 2026-02-10, commit biraz eski ama kabul edilebilir |
| 7 | TD-1.7 | D4 eski architecture arşivle | ✅ | 2 dosya docs/archive/ |
| 8 | TD-1.8 | Makefile lint+format | ✅ | 12 hedef mevcut |
| 9 | TD-1.9 | .env.example GEMINI | ✅ | GEMINI_API_KEY= mevcut |

**Sonuç: 7/9 ✅ tamamlanmış | 2/9 🟡 minor (Unreleased commit hash + bak tablosu)**

> TD-Sprint 1 **büyük ölçüde tamamlanmış**. Kalan 2 minor item UI-Sprint sonrası T-DOC prompt'u içinde halledilebilir.

---

## 2. Kesinleşmiş Uygulama Sırası

```
┌─────────────────────────────────────┐
│  UI-Sprint: T → F → H → G + T-DOC  │  12.5h + 0.5h = ~13h
│  (~3 gün)                           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Sprint 13: Project Setup           │  ~15-18h
│  Completion                         │
│  (~2 hafta, 15-20h/week)           │
└─────────────────────────────────────┘
```

---

## 3. UI-Sprint Detay (Prompt Execution Order)

**Guncel Durum:**
- **T:** ✅ Tamamlandi
- **F-REV:** ✅ Tamamlandi
- **H:** ✅ Tamamlandi
- **G:** ✅ Tamamlandi
- **T-DOC:** ⬜ Bekliyor

| Gün | Prompt | Kapsam | Effort | Dosyalar |
|:---:|:------:|--------|:------:|----------|
| **1** | **T** ✅ | Typography: Inter font + type scale + 44 rem→var() + 18 JS rem→px | 3.5h | index.html, main.css, explore-tokens.css, integration.js, program.js |
| **2** | **F-REV** ✅ | KPI Standardization: metricBar + emoji kaldır + 6 sayfa | 3h | explore-shared.js, explore-tokens.css, 6 view JS |
| **2-3** | **H** ✅ | Hierarchy UI: compact KPI + hover actions | 2h | explore_hierarchy.js, explore-tokens.css |
| **3** | **G** ✅ | Backlog Redesign: filterBar + badges + 4 tab | 4h | backlog.js, main.css |
| **3** | **T-DOC** | 3 doküman güncelle + TD-1.1/1.3 minor fix | 0.5h | PROGRESS_REPORT, architecture_v2, Plan_v2 |

---

## 4. Sprint 13: Project Setup Completion

### 4.1 Mevcut Durum Analizi

**Backend (Prompt A) — ✅ TAMAMLANDI:**
- `POST /process-levels` (create single) ✅
- `POST /process-levels/bulk` ✅
- `POST /process-levels/import-template` ✅
- `DELETE /process-levels/<id>` (cascade) ✅
- `GET/PUT/DELETE` CRUD ✅
- `ExploreAPI.levels.*` frontend API client ✅

**Frontend (project_setup.js — 1142 satır) — ✅ HIERARCHY TAB TAMAMLANDI:**
- Tree view + table view ✅
- Inline create/edit/delete ✅
- Bulk entry (grid + paste from Excel) ✅
- Template import (5 SAP L1 template) ✅
- Search + filter bar ✅
- KPI row ✅

**Eksik (3 Placeholder Tab):**

| Tab | Mevcut Durum | Backend | İhtiyaç |
|-----|-------------|---------|---------|
| **Team** | 🧩 "Coming soon" placeholder | ✅ program_bp: team CRUD (GET/POST/PUT/DELETE) | UI yazılacak |
| **Phases** | 🧩 "Coming soon" placeholder | ✅ program_bp: phases+gates CRUD (6 endpoint) | UI yazılacak |
| **Settings** | 🧩 "Coming soon" placeholder | 🟡 Program model'de field'lar var, dedicated endpoint yok | UI + belki backend |

### 4.2 Sprint 13 Task Listesi

| # | Task | Açıklama | Effort | Bağımlılık |
|---|------|----------|:------:|-----------|
| **13.1** | **Team Tab UI** | Team member listesi + CRUD modal + role/workstream assignment | 3h | program_bp ✅ |
| **13.2** | **Phases Tab UI** | Phase listesi + gates görünümü + create/edit modal | 3h | program_bp ✅ |
| **13.3** | **Settings Tab UI** | Project type, methodology, dates, SAP product, go-live config | 2h | Program model ✅ |
| **13.4** | **PhaseGate entegrasyonu** | Explore PhaseGate model → Phases tab'da "Formal Gate Check" butonu | 2h | explore PhaseGate ✅ |
| **13.5** | **Workstream Tab** (opsiyonel) | Phases içinde veya ayrı tab olarak workstream yönetimi | 2h | program_bp ✅ |
| **13.6** | **Committee Tab** (opsiyonel) | Steering committee + governance CRUD | 1.5h | program_bp ✅ |
| **13.7** | **Cross-tab navigation** | Team üyesine tıkla → workstream; Phase'e tıkla → gate check | 1h | 13.1-13.4 |
| **13.8** | **Dashboard KPI strip** | Project Setup özet: hierarchy count + team size + phase progress | 1h | Tüm tablar |
| | **Sprint 13 Toplam** | | **~15.5h** | |

### 4.2.1 Sprint 13 To-Do (Project Setup + Cutover Hub)

**Project Setup Completion**
- 13.1 Team Tab UI (liste + CRUD modal + role/workstream assignment)
- 13.2 Phases Tab UI (phase cards + gates view + create/edit)
- 13.3 Settings Tab UI (project type, methodology, dates, SAP product, go-live)
- 13.4 PhaseGate entegrasyonu (Phases tab'da Formal Gate Check butonu)
- 13.5 Workstream Tab (opsiyonel)
- 13.6 Committee Tab (opsiyonel)
- 13.7 Cross-tab navigation (Team -> Workstream, Phase -> Gate check)
- 13.8 Dashboard KPI strip (hierarchy count + team size + phase progress)

**Cutover Hub**
- 13.9 Modeller: CutoverPlan, RunbookTask, Rehearsal
- 13.10 API: Runbook CRUD + task dependency + rehearsal tracking
- 13.11 Go/No-Go readiness aggregation (tüm modullerden status)
- 13.12 UI: runbook list, task management, rehearsal comparison
- 13.13 Seed data (demo cutover/runbook tasks)
- 13.14 Testler: cutover API/UI testleri

**Bagimliliklar**
- Project Setup UI: program_bp + explore PhaseGate backend mevcut
- Cutover Hub UI: modeller + API tamamlandiktan sonra

**Dogrulama Checklist**
- Project Setup sayfasi 4 tab tam calisiyor (Hierarchy + Team + Phases + Settings)
- Team/Phases/Settings CRUD akislari API ile calisiyor
- Phases tab'da Formal Gate Check butonu gorunuyor ve state kaydediyor
- KPI strip: hierarchy count + team size + phase progress dogru
- Cutover Hub: runbook list + task dependency + rehearsal ekranlari calisiyor
- Go/No-Go readiness ozetleri modullerden veri cekiyor
- Seed data problemsiz yukleniyor; cutover testleri geciyor

### 4.3 Her Tab İçin Detay

#### Tab: Team (13.1)

```
┌──────────────────────────────────────────────────────────┐
│ ┌─────┬─────┬──────┬──────────┬──────────┬─────────┐    │
│ │ Name│ Role│ Email│ Workstream│ Active   │ Actions │    │
│ ├─────┼─────┼──────┼──────────┼──────────┼─────────┤    │
│ │ ...  │ PM  │ ... │ FI       │ ✅       │ ✏️ 🗑️   │    │
│ └─────┴─────┴──────┴──────────┴──────────┴─────────┘    │
│                                     [+ Add Team Member]  │
└──────────────────────────────────────────────────────────┘
```

**Data source:** `GET /programs/{id}/team`
**Create:** `POST /programs/{id}/team`
**Update:** `PUT /team/{id}`
**Delete:** `DELETE /team/{id}`
**Roles:** PM, Functional Lead, Technical Lead, Developer, Tester, Business Owner, Data Lead, Integration Lead, Change Manager

#### Tab: Phases & Gates (13.2)

```
┌──────────────────────────────────────────────────────────┐
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ Discover    │→│ Explore     │→│ Realize     │→ ...    │
│ │ ✅ Complete │ │ 🟡 Active   │ │ ⬜ Planned  │        │
│ │ Gate: ✅    │ │ Gate: ⬜    │ │ Gate: —     │        │
│ │ 2025-12-01  │ │ 2026-01-15  │ │ 2026-04-01  │        │
│ └─────────────┘ └─────────────┘ └─────────────┘        │
│                                                          │
│ ── Explore Phase Detail ──                               │
│ Gates: ☐ Scope Freeze  ☐ Fit-Gap Sign-off  ☐ WRICEF OK │
│                                     [+ Add Phase]        │
└──────────────────────────────────────────────────────────┘
```

**Data source:** `GET /programs/{id}/phases` (with nested gates)
**Create:** `POST /programs/{id}/phases` + `POST /phases/{id}/gates`

#### Tab: Settings (13.3)

```
┌──────────────────────────────────────────────────────────┐
│  Project Configuration                                    │
│                                                          │
│  Project Type:    [Greenfield ▼]                         │
│  Methodology:     [SAP Activate ▼]                       │
│  SAP Product:     [S/4HANA ▼]                            │
│  Deployment:      [On-Premise ▼]                         │
│                                                          │
│  Timeline                                                │
│  Start Date:      [2025-10-01]                           │
│  Go-Live Date:    [2026-09-01]                           │
│  End Date:        [2026-12-01]                           │
│                                                          │
│  Status:          [Active ▼]                             │
│  Priority:        [High ▼]                               │
│                                                          │
│                              [💾 Save Changes]           │
└──────────────────────────────────────────────────────────┘
```

**Data source:** `GET /programs/{id}` (mevcut Program model field'ları)
**Update:** `PUT /programs/{id}`

---

## 5. Güncellenmiş Genel Zaman Çizelgesi

```
Şubat 2026
11  12  13  14  15  16  17  18  19  20  21  22  23  24  25  26  27  28
│   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │
├── UI-Sprint ─────────────┤   │   │   │   │   │   │   │   │   │   │
│  T  │  F  │ H+G │ T-DOC │   │   │   │   │   │   │   │   │   │   │
│     │     │     │       │   │   │   │   │   │   │   │   │   │   │
│     │     │     │       ├── Sprint 13: Project Setup ────────────┤
│     │     │     │       │  Team │Phases│Settings│ Polish │       │
│     │     │     │       │       │      │        │        │       │
│     │     │     │       │       │      │        │   ★ S13 Gate   │
▼     ▼     ▼     ▼       ▼       ▼      ▼        ▼        ▼       ▼
```

---

## 6. Sprint 13 Sonrası: Sıradaki Ne?

Sprint 13 tamamlandığında "Project Setup" sayfası tam fonksiyonel olacak (4 tab: Hierarchy + Team + Phases + Settings).

Sonraki adım seçenekleri:

| Seçenek | Sprint | Açıklama | Effort |
|---------|--------|----------|:------:|
| A | S14 | Security: JWT + row-level | ~15h |
| B | S13+ | Cutover Hub (orijinal plan sırası) | ~37h |
| C | TD-Sprint 2 | Kalan teknik borç (CODE items) | ~20h |
| D | Test Hub UI | Frontend redesign (testing sayfaları) | ~15h |

> Sprint 13 bittiğinde tekrar değerlendiririz.
