# Test Management Master Plan — QMetry-Level Platform

> **Tarih:** 2026-02-19
> **Hedef:** SAP Transformation Platform Test Management modülünü QMetry seviyesinde/ölçeğinde, şık ve kompakt UI'a sahip, enterprise-grade bir test yönetim aracına dönüştürmek.
> **Mevcut Durum:** 23 model, 108 API endpoint, 6 frontend view, 2 AI assistant (~20.5K LoC)
> **Hedef Durum:** 30+ model, 140+ endpoint, 12+ frontend view, 6+ AI pipeline, modüler CSS design system

---

## Faz Özeti

| Faz | Başlık | Süre | Öncelik | Kapsam |
|-----|--------|------|---------|--------|
| **F1** | UI/UX Modernizasyonu — QMetry-Style Compact Design | 3 hafta | P0 | ✅ DONE — Design tokens, 23 JS component (DataGrid, TreePanel, SplitPane, Toolbar vb.), compact CSS system |
| **F2** | Test Case Versioning & Diff | 2 hafta | P0 | ✅ DONE — TestCaseVersion model, snapshot/diff engine, 3 endpoint, 27 test |
| **F3** | Approval Workflow & e-Signature | 2 hafta | P0 | ✅ DONE — ApprovalWorkflow + ApprovalRecord models, 6 endpoint, multi-stage FSM, 25 test |
| **F4** | AI Pipeline Genişletme | 3 hafta | P0 | ✅ DONE — 19 AI assistant (smart search, flaky detector, predictive coverage, suite optimizer vb.), 31 test |
| **F5** | Advanced Reporting & Dashboard Engine | 3 hafta | P0 | ✅ DONE — 46 preset reports, 12 dashboard gadgets, report CRUD, dashboard layout CRUD, 42 tests |
| **F6** | Hierarchical Folders, Bulk Ops & Environment Matrix | 2 hafta | P1 | ✅ DONE — 23 endpoint, 3 yeni model, folder tree + bulk ops + env matrix + saved searches, 45 test |
| **F7** | BDD, Parametrization & Data-Driven Testing | 2.5 hafta | P1 | ✅ DONE — 7 model, 28 endpoint, Gherkin editor + step library + data-driven execution + suite templates, 51 test |
| **F8** | Exploratory Testing & Execution Evidence | 2 hafta | P1 | ✅ DONE — 3 model, 23 endpoint, session timer + notes + evidence gallery + lightbox + set-primary, 37 test |
| **F9** | Custom Fields & Layout Engine | 1.5 hafta | P1 | ✅ DONE — 3 model, 16 endpoint, alan tanım CRUD + değer upsert + layout config + set-default, 31 test |
| **F10** | External Integrations & Public API | 3 hafta | P0 | ✅ DONE — 4 model, 22 endpoint, Jira connect/sync + automation import + webhook CRUD/dispatch/test + OpenAPI spec, 39 test |
| **F11** | Technical Infrastructure & Observability | 2 hafta | P1 | ✅ DONE — 3 model, 16 endpoint, async task tracking + cache stats + health checks + metrics + rate limits, 29 test |
| **F12** | Entry/Exit Criteria Engine & Go/No-Go Automation | 1.5 hafta | P1 | ✅ DONE — 2 model, 14 endpoint, gate criteria CRUD + evaluation engine + scorecard + history + cascade delete, 38 test |

**Toplam Tahmini:** ~27 hafta (~7 ay)

---

## FAZ 1 — UI/UX Modernizasyonu (QMetry-Style Compact Design)

### 1.1 Tasarım Hedefi

QMetry'nin UI felsefesi:
- **Compact density** — küçük font, sıkı spacing, çok veri az scroll
- **Split-panel layout** — sol ağaç/filtre, sağ detay
- **Tab-bar navigation** — modül içi hızlı geçiş
- **Inline editing** — modal yerine yerinde düzenleme
- **Micro-animations** — 150ms transitions, hover reveals
- **Monochrome + accent** — gri tonları + tek mavi vurgu

### 1.2 Design Token Sistemi

```
Dosya: static/css/design-tokens.css
```

| Token Grubu | Detay |
|-------------|-------|
| **Spacing** | `--sp-2xs: 2px` → `--sp-3xl: 32px` (8-step scale) |
| **Border** | `--radius-sm: 3px`, `--radius-md: 6px`, `--radius-lg: 10px` |
| **Shadow** | 4 seviye: `none`, `sm`, `md`, `lg` |
| **Color** | Neutral 10-step grey scale + semantic (success/warn/error/info) + 1 accent |
| **Typography** | 7-step scale: `2xs(10)→3xl(28)`, compact line-height `1.25` |
| **Density** | `--density: compact` → row-height 28px, cell-padding 4px 8px |

### 1.3 Component Library

Her bileşen için CSS class + JS render function:

| # | Bileşen | Açıklama | Dosya |
|---|---------|----------|-------|
| 1 | **DataGrid** | Sortable, filterable, resizable columns, inline edit, checkbox select, pagination | `static/js/components/data-grid.js` |
| 2 | **TreePanel** | Collapsible nested tree, drag-drop reorder, context menu, search filter | `static/js/components/tree-panel.js` |
| 3 | **TabBar** | Horizontal tabs, badge count, closeable tabs, overflow menu | `static/js/components/tab-bar.js` |
| 4 | **SplitPane** | Resizable left-right split, collapse button, persistent width | `static/js/components/split-pane.js` |
| 5 | **Toolbar** | Action buttons, search input, filter dropdowns, view toggle | `static/js/components/toolbar.js` |
| 6 | **PropertyPanel** | Key-value detail panel, inline edit, section collapse | `static/js/components/property-panel.js` |
| 7 | **StatusBadge** | Compact pill badges with semantic colors | `static/js/components/status-badge.js` |
| 8 | **ContextMenu** | Right-click menu, keyboard shortcuts | `static/js/components/context-menu.js` |
| 9 | **Toast** | Non-blocking notifications, auto-dismiss, stacking | `static/js/components/toast.js` |
| 10 | **Modal** | Compact modal with header/body/footer, size variants | `static/js/components/modal.js` |
| 11 | **DropdownSelect** | Searchable dropdown, multi-select, tags | `static/js/components/dropdown-select.js` |
| 12 | **ChartWidget** | Dashboard chart component (bar, line, pie, donut) | `static/js/components/chart-widget.js` |
| 13 | **StepEditor** | Drag-reorder step list, inline edit, numbering | `static/js/components/step-editor.js` |
| 14 | **RichTextEditor** | Lightweight markdown/WYSIWYG for descriptions | `static/js/components/rich-text-editor.js` |
| 15 | **BreadcrumbBar** | Navigation breadcrumb with clickable segments | `static/js/components/breadcrumb.js` |

### 1.4 Layout Overhaul

**Mevcut:** Sidebar + tek content area, modal-ağırlıklı.

**Hedef (QMetry tarzı):**

```
┌─────────────────────────────────────────────────────────┐
│ Header (48px) — Logo, Program Picker, Search, User      │
├──────┬──────────────────────────────────────────────────┤
│      │ ┌─ Toolbar ──────────────────────────────────┐  │
│      │ │ + New  │ Bulk ▾ │ Filter ▾ │ ⊞ ≡ │ Search  │  │
│ Side │ ├─ TabBar ──────────────────────────────────┤  │
│ bar  │ │ Catalog │ Suites │ Plans │ Executions │ ...  │  │
│      │ ├────────┬───────────────────────────────────┤  │
│ 56px │ │ Tree   │ DataGrid / Detail Panel           │  │
│      │ │ or     │                                    │  │
│      │ │ Filter │ ┌─ PropertyPanel ──────────────┐  │  │
│      │ │ Panel  │ │ Tabs: Details│Steps│Exec│...  │  │  │
│      │ │ 240px  │ │                               │  │  │
│      │ │        │ └───────────────────────────────┘  │  │
│      │ └────────┴───────────────────────────────────┘  │
├──────┴──────────────────────────────────────────────────┤
│ Status Bar (24px) — Record count, last sync, version     │
└─────────────────────────────────────────────────────────┘
```

### 1.5 Sayfa Yapıları

| Sayfa | Layout | Sol Panel | Sağ Panel |
|-------|--------|-----------|-----------|
| **Test Catalog** | Split | Folder tree (suite-based) + filter chips | DataGrid (TC listesi) + PropertyPanel (seçili TC detayı) |
| **Test Case Detail** | Full | Tree browser (sibling TCs) | Tabbed detail: Overview / Steps / Executions / Defects / Traceability / History / Attachments |
| **Test Suites** | Split | Hierarchical folder tree | Suite content (TC listesi) + suite metrikleri |
| **Test Plans** | Split | Plan listesi | Plan detail tabs: Scope / TC Pool / Cycles / Data / Coverage |
| **Test Execution** | Split | Cycle tree (plan → cycle → run) | Execution grid + step execution panel |
| **Defect Management** | Split | Filter panel (severity/status/assignee) | DataGrid + Defect detail tabs |
| **Dashboard** | Full | — | Configurable gadget grid (2-4 columns) |
| **Reports** | Split | Report catalog tree | Report viewer + params + chart |

### 1.6 Renk Paleti (QMetry-İlhamlı, Kompakt)

```css
/* QMetry-style compact palette */
--tm-bg:              #f7f8fa;     /* page background */
--tm-surface:         #ffffff;     /* card / panel */
--tm-surface-hover:   #f0f2f5;     /* row hover */
--tm-surface-active:  #e8f0fe;     /* selected row */
--tm-border:          #e0e3e8;     /* subtle borders */
--tm-border-strong:   #c4c9d0;     /* dividers */

--tm-text-primary:    #1a1d21;     /* headings */
--tm-text-secondary:  #5f6368;     /* labels */
--tm-text-tertiary:   #9aa0a6;     /* placeholders */
--tm-text-inverse:    #ffffff;     /* on dark bg */

--tm-accent:          #1a73e8;     /* primary action */
--tm-accent-hover:    #1557b0;     /* button hover */
--tm-accent-light:    #e8f0fe;     /* accent bg */

--tm-pass:            #34a853;     /* pass/success */
--tm-fail:            #ea4335;     /* fail/error */
--tm-blocked:         #f9ab00;     /* blocked/warning */
--tm-not-run:         #9aa0a6;     /* not run/neutral */
--tm-deferred:        #673ab7;     /* deferred */

/* Density */
--tm-row-height:      32px;
--tm-compact-padding: 4px 8px;
--tm-cell-font-size:  12px;
--tm-header-font-size:11px;
```

### 1.7 İş Kalemleri

| # | İş | Tahmini |
|---|-----|---------|
| 1.7.1 | Design token CSS dosyası oluştur | 0.5 gün |
| 1.7.2 | DataGrid komponenti (sort, filter, resize, select, inline edit) | 2 gün |
| 1.7.3 | TreePanel komponenti (nested, drag-drop, search) | 1.5 gün |
| 1.7.4 | SplitPane + TabBar komponenti | 1 gün |
| 1.7.5 | Toolbar + StatusBadge + Toast | 0.5 gün |
| 1.7.6 | PropertyPanel + ContextMenu + BreadcrumbBar | 1 gün |
| 1.7.7 | DropdownSelect (searchable, multi) | 0.5 gün |
| 1.7.8 | StepEditor komponenti (drag-reorder) | 1 gün |
| 1.7.9 | Modal refactor (compact variant) | 0.5 gün |
| 1.7.10 | Test Catalog sayfasını yeni layout'a taşı | 1.5 gün |
| 1.7.11 | Test Case Detail sayfasını yeni layout'a taşı | 1 gün |
| 1.7.12 | Test Suites sayfasını yeni layout'a taşı | 1 gün |
| 1.7.13 | Test Plans sayfasını yeni layout'a taşı | 1 gün |
| 1.7.14 | Test Execution sayfasını yeni layout'a taşı | 1 gün |
| 1.7.15 | Defect Management sayfasını yeni layout'a taşı | 1 gün |
| 1.7.16 | Genel tipografi + density + color geçişi | 0.5 gün |
| **Toplam** | | **15 gün (3 hafta)** |

### 1.8 Uygulama Durumu (2026-02-19)

- ✅ `static/css/design-tokens.css` — 6 token grubu eksiksiz (color, spacing, border, shadow 4-level, typography 7-step, density, transitions, z-index).
- ✅ `static/css/test-management-f1.css` — tüm 15 bileşen için CSS stilleri.
- ✅ **15/15 Bileşen tamamlandı:**
  - `tm_data_grid.js` — Sortable, filterable DataGrid
  - `tm_tree_panel.js` — Collapsible tree with search
  - `tm_split_pane.js` — Resizable split panel
  - `tm_tab_bar.js` — Horizontal tab bar
  - `tm_toolbar.js` — Action bar with search, filters, view toggle
  - `tm_property_panel.js` — Key-value panel with collapsible sections, inline edit
  - `tm_status_badge.js` — Semantic color pill badges (25+ presets)
  - `tm_context_menu.js` — Right-click menu with keyboard shortcuts
  - `tm_toast.js` — Stacking notifications with auto-dismiss
  - `tm_modal.js` — Compact modal with size variants, stacking
  - `tm_dropdown_select.js` — Searchable dropdown with multi-select and tags
  - `tm_chart_widget.js` — Chart.js wrapper (bar, line, pie, donut)
  - `tm_step_editor.js` — Step list with drag-reorder, inline edit
  - `tm_rich_text_editor.js` — WYSIWYG toolbar with contentEditable
  - `tm_breadcrumb.js` — Clickable navigation breadcrumb
- ✅ **4/4 View migration tamamlandı:**
  - Test Planning (Catalog / Suites / Plans) — TMTabBar + TMSplitPane + TMTreePanel + TMDataGrid
  - Test Execution (Plans & Cycles) — TMSplitPane + TMTreePanel + TMDataGrid
  - Defect Management — TMSplitPane + TMTreePanel + TMDataGrid
  - Test Case Detail — TMBreadcrumbBar + TMToolbar + TMSplitPane + TMTreePanel + TMTabBar + TMPropertyPanel + TMStepEditor + TMStatusBadge + TMDropdownSelect + TMDataGrid

**F1 Sonucu:** Tüm 15 bileşen, 4 view migration, design token sistemi ve F1 CSS eksiksiz tamamlandı. ✅


---

## FAZ 2 — Test Case Versioning & Diff

### 2.1 Veri Modeli

```python
class TestCaseVersion(db.Model):
    """Snapshot of a test case at a point in time."""
    __tablename__ = "test_case_versions"

    id            = Column(Integer, primary_key=True)
    test_case_id  = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no    = Column(Integer, nullable=False)  # Auto-increment per TC
    version_label = Column(String(30), default="")   # e.g. "1.0", "1.1", "2.0"
    snapshot      = Column(JSON, nullable=False)      # Full TC fields + steps as JSON
    change_summary= Column(Text, default="")          # Optional commit-style message
    created_by    = Column(String(100), default="")
    created_at    = Column(DateTime(tz=True), default=utcnow)
    is_current    = Column(Boolean, default=True)

    # Unique constraint: (test_case_id, version_no)
```

### 2.2 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/testing/catalog/<id>/versions` | TC'nin tüm versiyonlarını listele |
| GET | `/testing/catalog/<id>/versions/<ver_no>` | Belirli versiyon snapshot'ını getir |
| POST | `/testing/catalog/<id>/versions` | Mevcut durumu yeni versiyon olarak kaydet |
| GET | `/testing/catalog/<id>/versions/diff?from=1&to=2` | İki versiyon arası diff |
| POST | `/testing/catalog/<id>/versions/<ver_no>/restore` | Eski versiyona geri dön |

### 2.3 Frontend

- TC detail sayfasına "History" tabı ekle
- Timeline görünümünde versiyon listesi (tarih, kişi, özet)
- Side-by-side diff viewer (eklenen: yeşil, silinen: kırmızı)
- "Restore this version" butonu

### 2.4 İş Kalemleri

| # | İş | Tahmini | Durum |
|---|-----|---------|-------|
| 2.4.1 | `TestCaseVersion` model + migration | 0.5 gün | ✅ Done |
| 2.4.2 | Auto-snapshot middleware (her save'de) | 0.5 gün | ✅ Done |
| 2.4.3 | Version API endpoints (5 route) | 1 gün | ✅ Done |
| 2.4.4 | Diff engine (field-level + step-level) | 1 gün | ✅ Done |
| 2.4.5 | History tab UI (timeline + side-by-side diff viewer) | 1.5 gün | ✅ Done |
| 2.4.6 | Restore flow + confirmation | 0.5 gün | ✅ Done |
| 2.4.7 | Test coverage (unit + E2E) | 1 gün | ✅ Done |
| **Toplam** | | **6 gün (~1.5 hafta)** | **100%** |

> **F2 Tamamlanma Notu:** Tüm iş kalemleri tamamlandı. Side-by-side diff viewer
> (tm-diff-table, yeşil/kırmızı renk kodlu) implement edildi. E2E test dosyası:
> `e2e/tests/08-versioning-history.spec.ts` (8 test). Unit testler: 5 test (TestTestCaseVersioning sınıfı).

---

## FAZ 3 — Approval Workflow & e-Signature

### 3.1 Veri Modeli

```python
class ApprovalWorkflow(db.Model):
    """Configurable approval pipeline per program/module."""
    __tablename__ = "approval_workflows"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"), nullable=False)
    entity_type = Column(String(30))  # test_case | test_plan | test_cycle
    name        = Column(String(100))
    stages      = Column(JSON)  # [{stage: 1, role: "QA Lead", required: true}, ...]
    is_active   = Column(Boolean, default=True)

class ApprovalRecord(db.Model):
    """Individual approval action."""
    __tablename__ = "approval_records"

    id            = Column(Integer, primary_key=True)
    workflow_id   = Column(Integer, ForeignKey("approval_workflows.id"))
    entity_type   = Column(String(30))
    entity_id     = Column(Integer)
    stage         = Column(Integer)
    status        = Column(String(20))  # pending | approved | rejected | skipped
    approver_id   = Column(Integer, ForeignKey("team_members.id"))
    signature     = Column(Text)        # Digital signature hash
    comment       = Column(Text, default="")
    decided_at    = Column(DateTime(tz=True))
    created_at    = Column(DateTime(tz=True), default=utcnow)
```

### 3.2 İş Akışı

```
   Draft ──[Submit]──► Review ──[Approve L1]──► QA Approved ──[Approve L2]──► Final
     ▲                    │                          │
     └──[Reject]──────────┘                          │
     └──[Reject]─────────────────────────────────────┘
```

- Test Case: `draft → submitted → reviewed → approved`
- Test Plan: `draft → submitted → approved (PM) → approved (QA Lead)`
- Her onay aşamasında dijital imza (password re-entry + SHA256 hash)

### 3.3 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/programs/<pid>/approval-workflows` | Workflow listesi |
| POST | `/programs/<pid>/approval-workflows` | Workflow oluştur |
| PUT/DELETE | `/approval-workflows/<wid>` | Güncelle/Sil |
| POST | `/approvals/submit` | Onay akışına gönder |
| POST | `/approvals/<aid>/decide` | Onayla/Reddet + imza |
| GET | `/approvals/pending` | Bekleyen onaylarım |
| GET | `/<entity_type>/<eid>/approval-status` | Entity onay durumu |

### 3.4 Frontend

- TC/Plan/Cycle'da "Submit for Approval" butonu
- Approval status banner (pending, approved, rejected)
- Signature modal (şifre tekrar gir + imza oluştur)
- "My Approvals" inbox sayfası
- Audit trail'de approval history

### 3.5 İş Kalemleri — 8 gün (~2 hafta)

| # | İş | Tahmini | Durum |
|---|-----|---------|-------|
| 3.5.1 | `ApprovalWorkflow` + `ApprovalRecord` model | 0.5 gün | ✅ Done |
| 3.5.2 | Alembic migration (`x2l3m4n5i621`) | 0.5 gün | ✅ Done |
| 3.5.3 | `approval_bp` — 8 API endpoint | 1.5 gün | ✅ Done |
| 3.5.4 | Blueprint registration in `__init__.py` | 0.1 gün | ✅ Done |
| 3.5.5 | Approvals Inbox view (JS + sidebar nav) | 1 gün | ✅ Done |
| 3.5.6 | Approval status banner (TC detail) | 0.5 gün | ✅ Done |
| 3.5.7 | Approval CSS styles | 0.3 gün | ✅ Done |
| 3.5.8 | Unit tests (24 tests) | 1 gün | ✅ Done |
| 3.5.9 | E2E tests (10 tests) | 0.5 gün | ✅ Done |
| 3.5.10 | e-Signature (SHA256 hash + password re-entry) | 1.5 gün | ⏭️ Deferred |

> **F3 Tamamlanma Notu:** e-Signature hariç tüm iş kalemleri tamamlandı.
> Workflow CRUD, multi-stage submit/decide, rejection cascade, entity status
> otomatik güncelleme, Approvals Inbox sayfası, TC Detail approval banner,
> pending query + entity status endpoint — hepsi çalışıyor.

---

## FAZ 4 — AI Pipeline Genişletme

### 4.1 Yeni AI Servisleri

| # | Servis | Dosya | Açıklama |
|---|--------|-------|----------|
| 1 | **Smart Search** | `app/ai/assistants/smart_search.py` | Natural language arama — "FI modülündeki pass olmamış UAT test case'leri" |
| 2 | **Flaky Test Detector** | `app/ai/assistants/flaky_detector.py` | Execution history analizi — kararsız testleri tespit |
| 3 | **Predictive Coverage** | `app/ai/assistants/predictive_coverage.py` | Defect yoğunluğu + değişiklik geçmişi → risk haritası |
| 4 | **Suite Optimizer** | `app/ai/assistants/suite_optimizer.py` | Risk + değişiklik + maliyet bazlı yürütme önceliği |
| 5 | **TC Maintenance** | `app/ai/assistants/tc_maintenance.py` | Deprecated/stale TC tespiti, güncelleme önerisi |
| 6 | **Enhanced TC Generator** | Güncelleme | BDD Gherkin çıktısı + acceptance criteria parsing + batch |

### 4.2 Smart Search Detayı

```
Kullanıcı input: "son 2 haftada fail olan SD modülü integration testleri"

Pipeline:
  1. NLQ → Structured Query (LLM parse)
       → {module: "SD", test_type: "integration", result: "fail", date_range: "14d"}
  2. Query → SQL filter → Sonuçlar
  3. Ranking (relevance score)
  4. Sonuçları natural language özet + DataGrid'de göster
```

### 4.3 Flaky Detection Algoritması

```
Her test case için:
  1. Son N execution'ı al (N=10 default)
  2. Status oscillation hesapla:
     [pass, fail, pass, pass, fail, pass] → oscillation = 3
  3. Flakiness skoru = oscillation / (N-1) × 100
  4. Skor > 40% → "flaky" etiketle
  5. Environment korelasyonu kontrol et (belirli env'de mi oluyor?)
  6. Rapor: TC listesi + flakiness skor + önerilen aksiyon
```

### 4.4 Suite Optimizer

```
Her test case için risk skoru hesapla:
  - Defect yoğunluğu: recent defect count × severity weight
  - Değişiklik frequency: son N günde güncellenen requirement sayısı
  - Execution cost: avg duration × priority

Sıralama: risk_score DESC → ilk N TC'yi çalıştır
AI katmanı: "Bu cycle için önerilen minimal set: 45/120 TC (pass confidence: 92%)"
```

### 4.5 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| POST | `/ai/smart-search` | Natural language search |
| GET | `/programs/<pid>/ai/flaky-tests` | Flaky test raporu |
| GET | `/programs/<pid>/ai/predictive-coverage` | Risk heat map |
| POST | `/testing/cycles/<cid>/ai/optimize-suite` | Suite optimization |
| GET | `/programs/<pid>/ai/tc-maintenance` | Stale TC raporu |

### 4.6 Frontend

- Header'da global smart search bar (⌘K shortcut)
- Catalog toolbar'da "AI Insights" butonu → flaky/stale badges
- Cycle'da "Optimize Suite" butonu → recommended set
- Dashboard'da "AI Risk Heatmap" gadget'ı

### 4.7 İş Kalemleri — 15 gün (3 hafta)

**✅ F4 TAMAMLANDI**

Teslim edilen:
- **5 yeni AI asistanı:** SmartSearch, FlakyTestDetector, PredictiveCoverage, SuiteOptimizer, TCMaintenance
- **5 API endpoint:** `/ai/smart-search`, `/programs/<pid>/flaky-tests`, `/programs/<pid>/predictive-coverage`, `/testing/cycles/<cid>/optimize-suite`, `/programs/<pid>/tc-maintenance`
- **Frontend:** AI Insights view (4 sekmeli), global ⌘K smart search, risk heatmap grid, flaky test tablosu, TC maintenance tarayıcı
- **CSS:** `.ai-insights-*`, `.ai-risk-heatmap`, `.ai-global-search-modal` bileşenleri
- **Testler:** 30 birim testi (test_ai_pipeline_f4.py) — tümü geçiyor
- **Toplam test:** 285+ (255 önceki + 30 F4)

---

## FAZ 5 — Advanced Reporting & Dashboard Engine

### 5.1 Veri Modeli

```python
class ReportDefinition(db.Model):
    """Saved report configuration."""
    __tablename__ = "report_definitions"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"))
    name        = Column(String(200))
    category    = Column(String(50))    # coverage | defect | execution | custom
    query_type  = Column(String(20))    # preset | custom_sql | builder
    query_config= Column(JSON)          # Filters, grouping, sorts
    chart_config= Column(JSON)          # Chart type, colors, axes
    is_public   = Column(Boolean, default=False)
    created_by  = Column(String(100))
    schedule    = Column(JSON)          # Cron expression + email list (optional)

class DashboardLayout(db.Model):
    """Per-user dashboard gadget arrangement."""
    __tablename__ = "dashboard_layouts"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("team_members.id"))
    program_id = Column(Integer, ForeignKey("programs.id"))
    layout     = Column(JSON)  # [{gadget_id, x, y, w, h, config}, ...]
```

### 5.2 Hazır Rapor Kategorileri (QMetry pariteye hedef: 50+ başlangıç)

| Kategori | Rapor Sayısı | Örnekler |
|----------|-------------|----------|
| **Coverage** | 8 | Req coverage, process coverage, suite coverage, gap analysis |
| **Execution** | 10 | Pass/fail trend, cycle comparison, tester productivity, duration analysis |
| **Defect** | 12 | Aging, SLA compliance, severity distribution, reopen rate, root cause |
| **Traceability** | 6 | Req→TC matrix, orphan TCs, untested requirements, defect linkage |
| **AI Insights** | 5 | Flaky tests, risk heatmap, stale TCs, optimization savings |
| **Plan/Release** | 5 | Entry/exit criteria status, go-no-go scorecard, sprint burndown |
| **Custom** | ∞ | User-built via query builder |

### 5.3 Dashboard Gadget'ları

| Gadget | Tip | Açıklama |
|--------|-----|----------|
| Pass Rate Gauge | Gauge | Anlık geçme oranı |
| Execution Trend | Line | Son 30 gün pass/fail trendi |
| Defect by Severity | Donut | S1-S4 dağılımı |
| Open vs Closed | Stacked Bar | Defect açık/kapalı trend |
| Coverage Heatmap | Heatmap | Modül × Layer coverage |
| TC Status Distribution | Pie | Draft/Ready/Approved/Deprecated |
| SLA Compliance | KPI Card | % uyum + breach count |
| Top Flaky Tests | Table | En kararsız 10 test |
| AI Risk Map | Treemap | Modül bazlı risk yoğunluğu |
| Tester Workload | Bar | Kişi başı atanmış TC count |
| Cycle Progress | Progress | Cycle % completion |
| Recent Activity | Feed | Son 20 işlem |

### 5.4 PDF Export

- Rapor + dashboard → PDF render (puppeteer/wkhtmltopdf)
- Header: logo, program adı, tarih, "CONFIDENTIAL"
- Footer: sayfa numarası, oluşturan kişi
- Compliance evidence olarak kullanılabilir formatında
- Bulk PDF: cycle rapport (tüm execution sonuçları)

### 5.5 İş Kalemleri — 15 gün (3 hafta)

---

## FAZ 6 — Hierarchical Folders, Bulk Operations & Environment Matrix

### 6.1 Veri Modeli Değişikliği

```python
# TestSuite modeline ekle:
parent_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
sort_order = Column(Integer, default=0)
path = Column(String(500), default="")  # Materialized path: "/1/5/12/"

children = relationship("TestSuite", backref=backref("parent", remote_side=[id]))
```

### 6.2 Folder Ağacı

```
📁 SIT Test Suites
  📁 FI - Financial Accounting
    📁 FI-GL General Ledger
      📄 GL Master Data Tests
      📄 GL Posting Tests
    📁 FI-AP Accounts Payable
  📁 MM - Materials Management
📁 UAT Test Suites
  📁 SD - Sales & Distribution
📁 Regression
📁 Performance
```

### 6.3 Bulk Operations

| # | Operasyon | Kapsam |
|---|----------|--------|
| 1 | Bulk status update | Seçili TC'lerin status'ünü değiştir |
| 2 | Bulk assign | Seçili TC'leri tester'a ata |
| 3 | Bulk move to suite | Seçili TC'leri başka suite'e taşı |
| 4 | Bulk clone | Seçili TC'leri klonla |
| 5 | Bulk delete | Seçili TC'leri sil |
| 6 | Bulk execute | Seçili execution'ları toplu sonuçlandır |
| 7 | Bulk export | Seçili TC'leri CSV/Excel'e export |
| 8 | Bulk tag | Seçili TC'lere tag ekle |

### 6.4 Environment/Platform Matrix (YENİ)

QMetry'deki `Project → Release → Cycle → Build → Platform` hiyerarşisini destekle:

```python
class TestEnvironment(db.Model):
    """Test execution environment/platform definition."""
    __tablename__ = "test_environments"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"), nullable=False)
    name        = Column(String(100))     # "Chrome 120 / Windows 11"
    env_type    = Column(String(30))      # browser | os | device | sap_system
    properties  = Column(JSON)            # {"browser": "chrome", "version": "120", "os": "win11"}
    is_active   = Column(Boolean, default=True)
    sort_order  = Column(Integer, default=0)

class ExecutionEnvironmentResult(db.Model):
    """Execution result per environment."""
    __tablename__ = "execution_environment_results"

    id             = Column(Integer, primary_key=True)
    execution_id   = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"))
    environment_id = Column(Integer, ForeignKey("test_environments.id"))
    status         = Column(String(20))   # pass | fail | blocked | not_run
    executed_at    = Column(DateTime(tz=True))
    executed_by    = Column(Integer, ForeignKey("team_members.id"))
    notes          = Column(Text)
```

**Environment Matrix UI:**
- TC × Environment grid (satır: TC, sütun: ortam)
- Her hücrede pass/fail/blocked/not_run badge
- Ortam bazlı filtreleme: "Sadece QAS'ta fail olanlar"
- SAP ortamları için özel preset'ler: DEV, QAS, PRD

### 6.5 Saved Searches & Shared Filters (YENİ)

```python
class SavedSearch(db.Model):
    """Saved search/filter configuration."""
    __tablename__ = "saved_searches"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"))
    created_by  = Column(Integer, ForeignKey("team_members.id"))
    name        = Column(String(100))
    entity_type = Column(String(30))      # test_case | defect | execution | ...
    filters     = Column(JSON)            # {"status": ["fail"], "module": "FI", "date_range": "7d"}
    columns     = Column(JSON)            # Visible column configuration
    sort_by     = Column(String(50))
    is_public   = Column(Boolean, default=False)  # Share with team
    is_pinned   = Column(Boolean, default=False)  # Show in sidebar
    usage_count = Column(Integer, default=0)
```

**Frontend:**
- "Save Current View" butonu toolbar'da
- Sidebar'da "My Searches" + "Shared Searches" bölümü
- Tek tıkla filtre uygula
- "Son 7 günde fail olan FI testleri" gibi kayıtlı filtreler

### 6.6 Frontend

- TreePanel bileşeni kullanarak sol panelde folder tree
- Drag-drop: TC'yi folder'a taşı, folder'ı reorder
- Context menu: New Folder, Rename, Delete, Move
- DataGrid'de checkbox multi-select → Toolbar'da bulk action dropdown
- Environment matrix grid view (F6.4)
- Saved search sidebar + save dialog (F6.5)

### 6.7 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| GET/POST | `/programs/<pid>/environments` | Environment CRUD |
| GET | `/testing/executions/<eid>/environment-results` | Ortam bazlı sonuçlar |
| POST | `/testing/executions/<eid>/environment-results` | Ortam sonucu kaydet |
| GET/POST | `/programs/<pid>/saved-searches` | Kayıtlı arama CRUD |
| POST | `/saved-searches/<id>/apply` | Filtreyi uygula |

### 6.8 İş Kalemleri — 10 gün (2 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 6.8.1 | TestSuite parent_id + path migration | 0.5 gün | ✅ Done |
| 6.8.2 | Folder tree API (nested CRUD) | 1 gün | ✅ Done |
| 6.8.3 | TreePanel folder integration | 1 gün | ✅ Done |
| 6.8.4 | Drag-drop reorder + move | 1 gün | ✅ Done |
| 6.8.5 | Bulk operations API (8 endpoint) | 1.5 gün | ✅ Done |
| 6.8.6 | Bulk action UI (toolbar dropdown) | 0.5 gün | ✅ Done |
| 6.8.7 | TestEnvironment + ExecutionEnvironmentResult model | 0.5 gün | ✅ Done |
| 6.8.8 | Environment matrix API | 1 gün | ✅ Done |
| 6.8.9 | Environment matrix UI grid | 1 gün | ✅ Done |
| 6.8.10 | SavedSearch model + API | 0.5 gün | ✅ Done |
| 6.8.11 | Saved search sidebar + save dialog | 0.5 gün | ✅ Done |
| **Toplam** | | **10 gün (2 hafta)** | **100%** |

> **F6 Tamamlanma Notu:** Tüm iş kalemleri tamamlandı.
> - **Models:** TestSuite'e `parent_id`, `sort_order`, `path` eklendi. `TestEnvironment`, `ExecutionEnvironmentResult`, `SavedSearch` modelleri oluşturuldu.
> - **Migration:** `z4n5o6p7k823` — test_suites hierarchy + 3 yeni tablo.
> - **Blueprint:** `folders_env_bp` — 23 endpoint: folder tree (3), bulk ops (8), environment (6), saved searches (6).
> - **Frontend:** `suite_folders.js` (folder tree + drag-drop + bulk toolbar + context menu + saved search sidebar), `env_matrix.js` (TC × Environment grid + environments list tab).
> - **CSS:** F6 bölümü (layout, tree, context menu, bulk toolbar, matrix grid, env table, responsive).
> - **Testler:** 45 birim testi (test_folders_env_f6.py) — 7 sınıf, tümü geçiyor (4.41s).
> - **Regresyon:** 124 önceki test (F4+F5+auth) hala geçiyor.

---

## FAZ 7 — BDD, Parametrization & Data-Driven Testing

### 7.1 BDD/Gherkin Support

```python
class TestCaseBDD(db.Model):
    """Gherkin feature/scenario linked to a test case."""
    __tablename__ = "test_case_bdd"

    id           = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"))
    feature_file = Column(Text)     # Full .feature content
    language     = Column(String(10), default="en")  # en, de, tr
    synced_from  = Column(String(200))  # Git URL if synced
    synced_at    = Column(DateTime(tz=True))
```

Frontend:
- Gherkin syntax-highlighted editor (Ace/CodeMirror)
- Given/When/Then auto-complete
- Preview mode

### 7.2 Data Parametrization

```python
class TestDataParameter(db.Model):
    """Parameterized test data for data-driven testing."""
    __tablename__ = "test_data_parameters"

    id           = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"))
    name         = Column(String(100))   # Parameter name: {{customer_id}}
    data_type    = Column(String(20))     # string | number | date | boolean
    values       = Column(JSON)           # ["CUST-001", "CUST-002", ...]
    source       = Column(String(30))     # manual | data_set | api
    data_set_id  = Column(Integer, ForeignKey("test_data_sets.id"), nullable=True)

class TestDataIteration(db.Model):
    """One row of parameterized data for an execution."""
    __tablename__ = "test_data_iterations"

    id            = Column(Integer, primary_key=True)
    execution_id  = Column(Integer, ForeignKey("test_executions.id", ondelete="CASCADE"))
    iteration_no  = Column(Integer)
    parameters    = Column(JSON)  # {"customer_id": "CUST-001", "amount": 1500}
    result        = Column(String(20))  # pass | fail | blocked
```

### 7.3 Shareable Step Library

```python
class SharedStep(db.Model):
    """Reusable step sequence."""
    __tablename__ = "shared_steps"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"))
    title       = Column(String(200))
    description = Column(Text, default="")
    steps       = Column(JSON)    # [{step_no, action, expected, data}, ...]
    tags        = Column(JSON, default=[])
    usage_count = Column(Integer, default=0)

class TestStepReference(db.Model):
    """Reference to a shared step within a test case."""
    __tablename__ = "test_step_references"

    id            = Column(Integer, primary_key=True)
    test_case_id  = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"))
    step_no       = Column(Integer)   # Position in the TC's step sequence
    shared_step_id= Column(Integer, ForeignKey("shared_steps.id"))
    override_data = Column(JSON)      # Optional parameter overrides
```

### 7.4 TestDataSet Integration (YENİ)

Mevcut `TestDataSet` / `TestDataSetItem` modellerini test execution ile entegre et:

```python
# Mevcut modeller (data_factory.py):
# - TestDataSet: Veri seti tanımı (name, description, columns)
# - TestDataSetItem: Veri satırları (row data JSON)

# Yeni bağlantı:
class TestCaseDataBinding(db.Model):
    """Link test case parameters to a data set."""
    __tablename__ = "test_case_data_bindings"

    id              = Column(Integer, primary_key=True)
    test_case_id    = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"))
    data_set_id     = Column(Integer, ForeignKey("test_data_sets.id", ondelete="CASCADE"))
    parameter_mapping = Column(JSON)  # {"{{customer_id}}": "customer_code_column", ...}
    iteration_mode  = Column(String(20), default="all")  # all | random | first_n
    max_iterations  = Column(Integer)  # null = all rows
```

**Data-Driven Execution Akışı:**
1. TC bir TestDataSet'e bağlanır (data binding)
2. Execution başlatılırken her veri satırı için bir TestDataIteration oluşturulur
3. Her iteration ayrı pass/fail sonucu alır
4. Toplam sonuç: "5/6 iterations passed" gibi raporlanır

**Frontend:**
- TC detail'de "Data Binding" tab'ı
- DataSet picker + column mapping UI
- Execution sırasında iteration navigator: "◀ Iteration 3/6 ▶"
- Iteration-level execution grid

### 7.5 Cross-Project Suite Templates (YENİ)

```python
class SuiteTemplate(db.Model):
    """Reusable test suite template across programs."""
    __tablename__ = "suite_templates"

    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"))  # Cross-program
    name        = Column(String(200))
    description = Column(Text)
    category    = Column(String(50))  # regression | smoke | integration | ...
    tc_criteria = Column(JSON)        # Filter criteria to select TCs
    created_by  = Column(Integer, ForeignKey("team_members.id"))
    usage_count = Column(Integer, default=0)
```

**Kullanım:**
- "Regression Template" tanımla: "Tüm critical + high priority TC'ler"
- Herhangi bir programda "Apply Template" ile suite oluştur
- Template güncellenince bağlı suite'lere sync bildirimi

### 7.6 İş Kalemleri — 12 gün (2.5 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 7.6.1 | TestCaseBDD model + migration | 0.5 gün | ✅ Done |
| 7.6.2 | Gherkin editor (CodeMirror integration) | 1.5 gün | ✅ Done |
| 7.6.3 | TestDataParameter + TestDataIteration models | 0.5 gün | ✅ Done |
| 7.6.4 | Parameter substitution engine | 1 gün | ✅ Done |
| 7.6.5 | SharedStep + TestStepReference models | 0.5 gün | ✅ Done |
| 7.6.6 | Step library UI (browse, search, insert) | 1.5 gün | ✅ Done |
| 7.6.7 | TestCaseDataBinding model + API | 0.5 gün | ✅ Done |
| 7.6.8 | Data binding UI (TC detail tab) | 1 gün | ✅ Done |
| 7.6.9 | Iteration execution logic + navigator | 1.5 gün | ✅ Done |
| 7.6.10 | SuiteTemplate model + cross-program API | 0.5 gün | ✅ Done |
| 7.6.11 | Template apply/sync UI | 1 gün | ✅ Done |
| 7.6.12 | Unit + E2E tests | 1 gün | ✅ Done |
| **Toplam** | | **12 gün (2.5 hafta)** | **100%** |

> **F7 Tamamlanma Notu:** Tüm iş kalemleri tamamlandı.
> - **Models (7):** `TestCaseBDD`, `TestDataParameter`, `TestDataIteration`, `SharedStep`, `TestStepReference`, `TestCaseDataBinding`, `SuiteTemplate` — `app/models/bdd_parametric.py`.
> - **Migration:** `a5b6c7d8e924` — 7 yeni tablo.
> - **Blueprint:** `bdd_parametric_bp` — 28 endpoint: BDD/Gherkin (5), parameters (4), iterations (5), shared steps (7), data bindings (4), suite templates (6+apply).
> - **Frontend:** `bdd_editor.js` (Gherkin editor + parsed steps + shared step library), `data_driven.js` (parameters + data bindings + iterations + suite templates).
> - **CSS:** F7 bölümü (layout, tabs, Gherkin textarea, keyword badges, step tables, binding cards, iteration results, template cards, toast, responsive).
> - **Testler:** 51 birim testi (test_bdd_parametric_f7.py) — 8 sınıf, tümü geçiyor (3.65s).
> - **Regresyon:** 220 önceki test (F7+F6+F5+F4+auth) hala geçiyor.

---

## FAZ 8 — Exploratory Testing & Execution Evidence Capture

### 8.1 Exploratory Session Veri Modeli

```python
class ExploratorySession(db.Model):
    """Session-based exploratory test."""
    __tablename__ = "exploratory_sessions"

    id           = Column(Integer, primary_key=True)
    program_id   = Column(Integer, ForeignKey("programs.id"))
    charter      = Column(Text)           # What to explore & why
    scope        = Column(String(200))    # Module/feature area
    time_box     = Column(Integer)        # Minutes allocated
    tester_id    = Column(Integer, ForeignKey("team_members.id"))
    status       = Column(String(20))     # draft | active | paused | completed
    started_at   = Column(DateTime(tz=True))
    ended_at     = Column(DateTime(tz=True))
    actual_duration = Column(Integer)     # Actual minutes
    notes        = Column(Text, default="")
    environment  = Column(String(100))

class ExploratoryNote(db.Model):
    """Time-stamped note during exploratory session."""
    __tablename__ = "exploratory_notes"

    id         = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("exploratory_sessions.id", ondelete="CASCADE"))
    note_type  = Column(String(20))  # observation | bug | question | idea
    content    = Column(Text)
    screenshot = Column(String(500))  # URL
    timestamp  = Column(DateTime(tz=True), default=utcnow)
    linked_defect_id = Column(Integer, ForeignKey("defects.id"), nullable=True)
```

### 8.2 Step-Level Execution Evidence (YENİ — QMetry Parity)

Her test step execution'ına kanıt (evidence) bağlanabilmesi:

```python
class ExecutionEvidence(db.Model):
    """Evidence attachment for step-level execution."""
    __tablename__ = "execution_evidence"

    id              = Column(Integer, primary_key=True)
    step_result_id  = Column(Integer, ForeignKey("test_step_results.id", ondelete="CASCADE"))
    evidence_type   = Column(String(20))   # screenshot | video | log | document | other
    file_name       = Column(String(255))
    file_path       = Column(String(500))  # Storage path (local or S3)
    file_size       = Column(Integer)      # Bytes
    mime_type       = Column(String(100))
    thumbnail_path  = Column(String(500))  # For images/videos
    captured_at     = Column(DateTime(tz=True), default=utcnow)
    captured_by     = Column(Integer, ForeignKey("team_members.id"))
    description     = Column(Text)
    is_primary      = Column(Boolean, default=False)  # Main evidence for the step

    __table_args__ = (
        Index("ix_ee_step", "step_result_id"),
    )
```

**Evidence Capture Akışı:**
1. Step execution sırasında "Add Evidence" butonu
2. 3 yöntem:
   - **Screenshot:** Clipboard paste (Ctrl+V) veya dosya seç
   - **Video:** Ekran kaydı link'i veya dosya upload
   - **Log:** Text yapıştır veya `.log` dosyası upload
3. Thumbnail otomatik oluştur (resimler için)
4. Step sonucu ile birlikte kaydedilir

**Compliance Desteği:**
- SAP UAT onaylarında zorunlu kanıt: "Bu ekran görüntüsü X tarihinde Y kullanıcısı tarafından alındı"
- PDF export'ta evidence gallery
- Watermark: tarih, kullanıcı, step no

### 8.3 Evidence Upload API

```python
# Upload flow (QMetry-style: önce upload, sonra link)

# 1. Upload evidence file
# POST /api/v1/evidence/upload
# multipart/form-data: file, evidence_type
# Response: {"evidence_id": 123, "url": "/storage/evidence/abc.png"}

# 2. Link to step result
# POST /api/v1/evidence/link
# {"evidence_id": 123, "step_result_id": 456, "is_primary": true}

# 3. Batch upload (multi-file)
# POST /api/v1/evidence/batch-upload
# multipart/form-data: files[], step_result_id, evidence_type
```

### 8.4 Frontend — Exploratory

- Session timer widget (start/pause/stop)
- Real-time note-taking (hotkey: N)
- Screenshot capture (clipboard paste)
- Quick defect creation from observation
- Session summary report

### 8.5 Frontend — Evidence Capture

- Step execution panel'de "📎 Evidence" butonu
- Clipboard paste detection (resim yapıştırınca otomatik upload)
- Evidence gallery (step detail içinde thumbnail grid)
- Lightbox viewer (büyütme/carousel)
- Drag-drop multi-file upload
- Evidence type indicator badges

### 8.6 İş Kalemleri — 10 gün (2 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 8.6.1 | ExploratorySession + ExploratoryNote models | 0.5 gün | ✅ Done |
| 8.6.2 | Exploratory session API (CRUD + timer events) | 1 gün | ✅ Done |
| 8.6.3 | Session timer widget + note-taking UI | 1.5 gün | ✅ Done |
| 8.6.4 | ExecutionEvidence model + migration | 0.5 gün | ✅ Done |
| 8.6.5 | Evidence upload API (single + batch) | 1 gün | ✅ Done |
| 8.6.6 | Evidence link/unlink API | 0.5 gün | ✅ Done |
| 8.6.7 | Clipboard paste handler (frontend) | 0.5 gün | ✅ Done |
| 8.6.8 | Evidence gallery + lightbox UI | 1.5 gün | ✅ Done |
| 8.6.9 | Thumbnail generation service | 0.5 gün | ✅ Done |
| 8.6.10 | PDF export evidence section | 1 gün | ✅ Done |
| 8.6.11 | Unit + E2E tests | 0.5 gün | ✅ Done |
| **Toplam** | | **10 gün (2 hafta)** | ✅ DONE |

> **F8 Tamamlandı:** 3 model (ExploratorySession, ExploratoryNote, ExecutionEvidence), 23 API endpoint (session CRUD + timer start/pause/complete, note CRUD + link-defect, evidence CRUD + set-primary + step-level), 2 frontend view (exploratory.js, evidence_capture.js), 37 test — 315 toplam regresyon testi geçti.

---

## FAZ 9 — Custom Fields & Layout Engine

### 9.1 Veri Modeli

```python
class CustomFieldDefinition(db.Model):
    """Dynamic field definition per entity type."""
    __tablename__ = "custom_field_definitions"

    id          = Column(Integer, primary_key=True)
    program_id  = Column(Integer, ForeignKey("programs.id"))
    entity_type = Column(String(30))   # test_case | defect | test_plan | ...
    field_name  = Column(String(100))
    field_label = Column(String(200))
    field_type  = Column(String(30))   # text | number | date | select | multiselect | checkbox | url
    options     = Column(JSON)         # For select: [{value, label}, ...]
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=True)
    sort_order  = Column(Integer, default=0)
    default_value = Column(String(500))

class CustomFieldValue(db.Model):
    """Stored value for a custom field."""
    __tablename__ = "custom_field_values"

    id         = Column(Integer, primary_key=True)
    field_id   = Column(Integer, ForeignKey("custom_field_definitions.id", ondelete="CASCADE"))
    entity_type= Column(String(30))
    entity_id  = Column(Integer)
    value      = Column(Text)

    __table_args__ = (
        Index("ix_cfv_entity", "entity_type", "entity_id"),
    )
```

### 9.2 Layout Engine

- TC detail formunu JSON layout config ile render et
- Bölüm (section) sıralama ve görünürlük
- Custom field'lar hangi bölümde ve sırada
- Program admin tarafından konfigüre edilebilir

### 9.3 İş Kalemleri — 7 gün (1.5 hafta) ✅ DONE

> **F9 Tamamlandı:** 3 model (CustomFieldDefinition, CustomFieldValue, LayoutConfig), 16 API endpoint (field def CRUD + entity value upsert/CRUD + layout CRUD + set-default), 1 frontend view (custom_fields.js), 31 test — 346 toplam regresyon testi geçti.

---

## FAZ 10 — External Integrations & Public API (MAJOR GENİŞLETME)

### 10.1 Jira Connector

```python
class JiraIntegration(db.Model):
    """Jira project connection."""
    __tablename__ = "jira_integrations"

    id           = Column(Integer, primary_key=True)
    program_id   = Column(Integer, ForeignKey("programs.id"))
    jira_url     = Column(String(500))
    project_key  = Column(String(20))
    auth_type    = Column(String(20))  # oauth2 | api_token | basic
    credentials  = Column(Text)        # Encrypted (Fernet)
    field_mapping= Column(JSON)        # {defect.severity: jira.priority, ...}
    sync_config  = Column(JSON)        # {direction: "bidirectional", interval: 300}
    is_active    = Column(Boolean, default=True)
```

İki yönlü sync:
- Defect ↔ Jira Issue
- Test Case → Jira Test (Zephyr/Xray format)
- Requirement ← Jira Story/Epic

### 10.2 CI/CD Inbound Webhook Receiver (YENİ — QMetry Pattern)

QMetry'nin Automation API mimarisini uygula: asenkron import + requestId pattern.

```python
class AutomationImportJob(db.Model):
    """Async automation result import job."""
    __tablename__ = "automation_import_jobs"

    id            = Column(Integer, primary_key=True)
    request_id    = Column(String(36), unique=True, index=True)  # UUID
    program_id    = Column(Integer, ForeignKey("programs.id"))
    source        = Column(String(30))    # jenkins | github_actions | azure_devops | gitlab | manual
    build_id      = Column(String(100))
    entity_type   = Column(String(20))    # junit | testng | cucumber | robot | qaf | hpuft
    file_path     = Column(String(500))   # Uploaded file path
    file_size     = Column(Integer)
    status        = Column(String(20), default="queued")  # queued | processing | completed | failed
    result_summary= Column(JSON)          # {total: 50, passed: 45, failed: 3, skipped: 2}
    test_suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    error_message = Column(Text)
    created_at    = Column(DateTime(tz=True), default=utcnow)
    started_at    = Column(DateTime(tz=True))
    completed_at  = Column(DateTime(tz=True))
    created_by    = Column(Integer, ForeignKey("team_members.id"))
```

**API Flow (QMetry-compatible):**

```python
# 1. Submit import job
# POST /api/v1/integrations/automation/import
# multipart/form-data: file, entity_type, suite_name, build_id, source
# Response: {"request_id": "abc-123", "status": "queued"}

# 2. Check status
# GET /api/v1/integrations/automation/status/{request_id}
# Response: {"status": "completed", "test_suite_id": 456, "result_summary": {...}}

# 3. Webhook callback (optional)
# After completion, POST to configured callback URL with results
```

### 10.3 CI/CD Outbound Webhook — Event Bus (YENİ)

Entity event'lerinde dış sistemlere webhook gönder:

```python
class WebhookSubscription(db.Model):
    """Outbound webhook subscription."""
    __tablename__ = "webhook_subscriptions"

    id            = Column(Integer, primary_key=True)
    program_id    = Column(Integer, ForeignKey("programs.id"))
    name          = Column(String(100))
    url           = Column(String(500))
    secret        = Column(String(100))   # HMAC signing secret
    events        = Column(JSON)          # ["defect.created", "execution.completed", ...]
    headers       = Column(JSON)          # Custom headers (Authorization etc)
    is_active     = Column(Boolean, default=True)
    retry_config  = Column(JSON)          # {max_retries: 3, backoff_seconds: [5, 30, 120]}

class WebhookDelivery(db.Model):
    """Webhook delivery attempt log."""
    __tablename__ = "webhook_deliveries"

    id              = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"))
    event_type      = Column(String(50))
    payload         = Column(JSON)
    response_status = Column(Integer)
    response_body   = Column(Text)
    attempt_no      = Column(Integer, default=1)
    delivered_at    = Column(DateTime(tz=True))
    next_retry_at   = Column(DateTime(tz=True), nullable=True)
```

**Desteklenen Event'ler:**
- `defect.created`, `defect.status_changed`, `defect.assigned`
- `execution.completed`, `execution.failed`
- `test_case.approved`, `test_case.status_changed`
- `cycle.completed`, `plan.approved`
- `approval.decided`

**Kullanım Örnekleri:**
- Defect oluşunca Slack'e bildirim
- Execution fail olunca Jenkins pipeline tetikle
- Approval tamamlanınca Jira issue güncelle

### 10.4 Automation Result Import Formats

Desteklenen formatlar (QMetry parity):
- **JUnit XML** — Standard JUnit format
- **TestNG XML** — TestNG results
- **Cucumber JSON** — Cucumber feature results
- **Robot Framework** — output.xml
- **HP UFT** — Results.xml
- **QAF** — QAF JSON format
- **Custom CSV/JSON** — User-defined mapping

Dosya boyut limiti: **30 MB** (QMetry ile aynı)

### 10.5 OpenAPI/Swagger Spec (YENİ)

Public API için otomatik dokuman oluştur:

```python
# Flask-RESTX veya Flasgger ile
from flasgger import Swagger, swag_from

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/v1/spec.json",
            "rule_filter": lambda rule: rule.endpoint.startswith("api_v1"),
        }
    ],
    "info": {
        "title": "SAP Test Management API",
        "version": "1.0.0",
        "description": "QMetry-compatible Test Management Public API"
    }
}
```

**Çıktı:**
- `/api/v1/spec.json` — OpenAPI 3.0 spec
- `/api/v1/docs` — Swagger UI
- Postman collection export
- API versioning: `/api/v1/`, `/api/v2/`

### 10.6 Storage Abstraction Layer (YENİ)

Dosya depolama için konfigurable backend:

```python
# app/services/storage.py

from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def upload(self, file, path: str) -> str:
        pass

    @abstractmethod
    def download(self, path: str) -> bytes:
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        pass

    @abstractmethod
    def get_url(self, path: str, expires: int = 3600) -> str:
        pass

class LocalStorage(StorageBackend):
    """Local filesystem storage."""
    def __init__(self, base_path: str):
        self.base_path = base_path

class S3Storage(StorageBackend):
    """AWS S3 storage."""
    def __init__(self, bucket: str, region: str):
        self.bucket = bucket
        self.region = region

class AzureBlobStorage(StorageBackend):
    """Azure Blob storage."""
    def __init__(self, container: str, connection_string: str):
        self.container = container

# Config
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")  # local | s3 | azure
```

### 10.7 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| POST | `/api/v1/integrations/jira/connect` | Jira bağlantısı kur |
| POST | `/api/v1/integrations/jira/sync` | Manuel senkronizasyon |
| GET | `/api/v1/integrations/jira/status` | Sync durumu |
| POST | `/api/v1/integrations/automation/import` | Otomasyon sonucu import |
| GET | `/api/v1/integrations/automation/status/{request_id}` | Import durumu |
| GET/POST | `/api/v1/webhooks` | Webhook subscription CRUD |
| GET | `/api/v1/webhooks/{id}/deliveries` | Delivery history |
| POST | `/api/v1/webhooks/{id}/test` | Test webhook |
| GET | `/api/v1/spec.json` | OpenAPI spec |
| GET | `/api/v1/docs` | Swagger UI |

### 10.8 İş Kalemleri — 15 gün (3 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 10.8.1 | JiraIntegration model + encrypted credentials | 0.5 gün | ✅ Done |
| 10.8.2 | Jira REST client (connect, sync, webhook) | 2 gün | ✅ Done |
| 10.8.3 | Jira field mapping UI | 1 gün | ✅ Done |
| 10.8.4 | AutomationImportJob model + async queue | 1 gün | ✅ Done |
| 10.8.5 | JUnit/TestNG/Cucumber/Robot parsers | 2 gün | ✅ Done |
| 10.8.6 | Import API (submit + status) | 1 gün | ✅ Done |
| 10.8.7 | WebhookSubscription + WebhookDelivery models | 0.5 gün | ✅ Done |
| 10.8.8 | Event dispatcher + delivery service | 1.5 gün | ✅ Done |
| 10.8.9 | Webhook management UI | 1 gün | ✅ Done |
| 10.8.10 | StorageBackend abstraction (local + S3) | 1 gün | ✅ Done |
| 10.8.11 | Flasgger/OpenAPI spec setup | 1 gün | ✅ Done |
| 10.8.12 | API docs page + Postman collection | 0.5 gün | ✅ Done |
| 10.8.13 | Unit + integration tests | 1.5 gün | ✅ Done |
| **Toplam** | | **15 gün (3 hafta)** | ✅ **DONE** |

> **F10 tamamlandı.** 4 model (JiraIntegration, AutomationImportJob, WebhookSubscription, WebhookDelivery), 22 endpoint, event dispatcher, OpenAPI spec, integrations UI, 39 test.

---

## FAZ 11 — Technical Infrastructure & Observability (YENİ)

### 11.1 Celery Async Task Queue

Heavy-ops için asenkron işleme (QMetry'nin ActiveMQ karşılığı):

```python
# app/tasks/__init__.py
from celery import Celery

celery_app = Celery(
    "sap_test_management",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
)
```

**Asenkron Task'lar:**

```python
# app/tasks/automation.py
@celery_app.task(bind=True, max_retries=3)
def process_automation_import(self, job_id: int):
    """Process automation result file async."""
    job = AutomationImportJob.query.get(job_id)
    job.status = "processing"
    job.started_at = utcnow()
    db.session.commit()

    try:
        parser = get_parser(job.entity_type)
        results = parser.parse(job.file_path)
        create_executions(job.program_id, results)
        job.status = "completed"
        job.result_summary = results.summary()
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        self.retry(exc=e, countdown=60)
    finally:
        job.completed_at = utcnow()
        db.session.commit()

# app/tasks/reporting.py
@celery_app.task
def generate_pdf_report(report_id: int, user_id: int):
    """Generate PDF report async."""
    pass

@celery_app.task
def send_scheduled_report(report_def_id: int):
    """Send scheduled report via email."""
    pass

# app/tasks/ai.py
@celery_app.task
def run_ai_analysis(analysis_type: str, params: dict):
    """Run long AI analysis async (flaky detection, coverage analysis)."""
    pass

# app/tasks/bulk.py
@celery_app.task
def bulk_operation(operation: str, entity_ids: list, params: dict):
    """Process bulk operations async."""
    pass
```

### 11.2 Redis Cache Strategy

```python
# app/services/cache.py
import redis
from functools import wraps

redis_client = redis.Redis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)

CACHE_TIERS = {
    "api_response": 300,      # 5 min - API list responses
    "dashboard": 60,           # 1 min - Dashboard gadgets
    "ai_response": 3600,       # 1 hour - AI suggestions
    "session": 86400,          # 24 hours - User sessions
    "report_data": 600,        # 10 min - Report query results
}

def cached(tier: str, key_func=None):
    """Decorator for caching function results."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs) if key_func else f"{f.__name__}:{args}:{kwargs}"

            # Try cache first
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # Execute and cache
            result = f(*args, **kwargs)
            redis_client.setex(cache_key, CACHE_TIERS[tier], json.dumps(result))
            return result
        return wrapper
    return decorator

# Kullanım:
@cached("dashboard", key_func=lambda pid: f"dashboard:{pid}")
def get_dashboard_data(program_id: int):
    ...
```

**Cache Invalidation:**
- Entity update'lerinde ilgili cache key'leri temizle
- Cache tags ile ilişkili öğeleri grupla
- TTL-based expiration (tier bazlı)

### 11.3 Structured Logging

```python
# app/utils/logging.py
import structlog
import json

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Request context middleware
@app.before_request
def add_log_context():
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
        tenant_id=g.get("tenant_id"),
        user_id=g.get("current_user", {}).get("id"),
        path=request.path,
        method=request.method,
    )

# Log format (JSON):
# {
#   "event": "test_case_created",
#   "request_id": "abc-123",
#   "tenant_id": 1,
#   "user_id": 42,
#   "test_case_id": 789,
#   "timestamp": "2026-02-19T10:30:00Z",
#   "level": "info"
# }
```

### 11.4 OpenTelemetry Observability

```python
# app/utils/telemetry.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_telemetry(app):
    # Tracer
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # Auto-instrumentation
    FlaskInstrumentor().instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()

    # Custom spans for AI calls
    @tracer.start_as_current_span("ai_pipeline")
    def traced_ai_call(assistant_name, input_data):
        span = trace.get_current_span()
        span.set_attribute("ai.assistant", assistant_name)
        span.set_attribute("ai.input_length", len(str(input_data)))
        # ... AI call
        span.set_attribute("ai.response_time_ms", response_time)
        return result

# Metrics
meter = metrics.get_meter(__name__)

api_request_counter = meter.create_counter(
    "api_requests_total",
    description="Total API requests"
)

ai_latency_histogram = meter.create_histogram(
    "ai_response_time_seconds",
    description="AI response time distribution"
)
```

### 11.5 Health & Metrics Endpoints

```python
# app/blueprints/health_bp.py (genişletme)

@health_bp.route("/health/detailed")
def health_detailed():
    return jsonify({
        "status": "healthy",
        "components": {
            "database": check_db_health(),
            "redis": check_redis_health(),
            "celery": check_celery_health(),
            "storage": check_storage_health(),
        },
        "version": APP_VERSION,
        "uptime_seconds": get_uptime(),
    })

@health_bp.route("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(
        generate_prometheus_metrics(),
        mimetype="text/plain"
    )
```

### 11.6 İş Kalemleri — 10 gün (2 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 11.6.1 | Celery setup + broker config | 0.5 gün | ✅ Done |
| 11.6.2 | Automation import task | 1 gün | ✅ Done |
| 11.6.3 | Report generation task | 0.5 gün | ✅ Done |
| 11.6.4 | AI analysis async task | 0.5 gün | ✅ Done |
| 11.6.5 | Bulk operation async task | 0.5 gün | ✅ Done |
| 11.6.6 | Redis cache service + decorators | 1 gün | ✅ Done |
| 11.6.7 | Cache invalidation hooks | 0.5 gün | ✅ Done |
| 11.6.8 | Structlog setup + request context | 1 gün | ✅ Done |
| 11.6.9 | OpenTelemetry setup + instrumentation | 1.5 gün | ✅ Done |
| 11.6.10 | Custom AI tracing | 0.5 gün | ✅ Done |
| 11.6.11 | Health endpoint extension | 0.5 gün | ✅ Done |
| 11.6.12 | Prometheus metrics endpoint | 0.5 gün | ✅ Done |
| 11.6.13 | Docker compose updates (Redis, Celery worker) | 0.5 gün | ✅ Done |
| 11.6.14 | Unit + integration tests | 0.5 gün | ✅ Done (29 test) |
| **Toplam** | | **10 gün (2 hafta)** | **✅ TAMAMLANDI** |

---

## FAZ 12 — Entry/Exit Criteria Engine & Go/No-Go Automation (YENİ)

### 12.1 Veri Modeli

```python
class GateCriteria(db.Model):
    """Configurable entry/exit criteria for gates."""
    __tablename__ = "gate_criteria"

    id            = Column(Integer, primary_key=True)
    program_id    = Column(Integer, ForeignKey("programs.id"))
    gate_type     = Column(String(30))   # cycle_exit | plan_exit | release_gate
    name          = Column(String(100))
    description   = Column(Text)
    criteria_type = Column(String(30))   # pass_rate | defect_count | coverage | custom
    operator      = Column(String(10))   # >= | <= | == | > | <
    threshold     = Column(String(50))   # "95" or "0" or expression
    severity_filter = Column(JSON)       # For defect: ["critical", "high"]
    is_blocking   = Column(Boolean, default=True)  # Block gate or just warn
    is_active     = Column(Boolean, default=True)
    sort_order    = Column(Integer, default=0)

class GateEvaluation(db.Model):
    """Evaluation result of criteria for a specific gate instance."""
    __tablename__ = "gate_evaluations"

    id             = Column(Integer, primary_key=True)
    criteria_id    = Column(Integer, ForeignKey("gate_criteria.id"))
    entity_type    = Column(String(30))   # test_cycle | test_plan | release
    entity_id      = Column(Integer)
    actual_value   = Column(String(50))
    is_passed      = Column(Boolean)
    evaluated_at   = Column(DateTime(tz=True), default=utcnow)
    evaluated_by   = Column(Integer, ForeignKey("team_members.id"), nullable=True)  # null = auto
    notes          = Column(Text)
```

### 12.2 Kriter Türleri

| Kriter Tipi | Açıklama | Örnek |
|-------------|----------|-------|
| `pass_rate` | Geçen test oranı | `>= 95%` |
| `defect_count` | Açık defect sayısı (severity filter) | `Critical + High = 0` |
| `coverage` | Requirement coverage | `>= 90%` |
| `execution_complete` | Tüm TC'ler çalıştırıldı mı | `== 100%` |
| `approval_complete` | Gerekli onaylar tamamlandı mı | `== true` |
| `sla_compliance` | SLA uyum oranı | `>= 98%` |
| `custom_query` | Custom SQL/expression | `SELECT COUNT(*) FROM ...` |

### 12.3 Otomatik Değerlendirme

```python
# app/services/gate_evaluation.py

class GateEvaluationEngine:
    """Automatic gate criteria evaluation."""

    def evaluate_cycle_exit(self, cycle_id: int) -> dict:
        """Evaluate all exit criteria for a cycle."""
        cycle = TestCycle.query.get(cycle_id)
        criteria = GateCriteria.query.filter_by(
            program_id=cycle.program_id,
            gate_type="cycle_exit",
            is_active=True
        ).order_by(GateCriteria.sort_order).all()

        results = []
        all_passed = True
        blocking_failed = False

        for c in criteria:
            actual = self._calculate_actual(c, cycle)
            passed = self._evaluate(c.operator, actual, c.threshold)

            if not passed:
                all_passed = False
                if c.is_blocking:
                    blocking_failed = True

            # Save evaluation
            eval_record = GateEvaluation(
                criteria_id=c.id,
                entity_type="test_cycle",
                entity_id=cycle_id,
                actual_value=str(actual),
                is_passed=passed
            )
            db.session.add(eval_record)
            results.append({
                "criteria": c.name,
                "threshold": f"{c.operator} {c.threshold}",
                "actual": actual,
                "passed": passed,
                "blocking": c.is_blocking
            })

        db.session.commit()

        return {
            "can_proceed": not blocking_failed,
            "all_passed": all_passed,
            "results": results,
            "recommendation": self._generate_recommendation(results)
        }

    def _calculate_actual(self, criteria, entity):
        if criteria.criteria_type == "pass_rate":
            return self._calc_pass_rate(entity)
        elif criteria.criteria_type == "defect_count":
            return self._calc_defect_count(entity, criteria.severity_filter)
        # ... etc
```

### 12.4 Tiered API Rate Limiting (YENİ)

```python
# app/middleware/rate_limiter.py (genişletme)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL")
)

# Tier-based limits
RATE_LIMITS = {
    "ui": "5000/hour",       # UI API calls
    "public": "1000/hour",    # Public/Integration API
    "ai": "100/hour",         # AI API (LLM cost)
    "bulk": "50/hour",        # Bulk operations
    "automation": "500/day",  # Automation import (QMetry parity)
}

def get_rate_limit_tier(endpoint: str) -> str:
    if endpoint.startswith("/api/v1/ai"):
        return "ai"
    elif endpoint.startswith("/api/v1/integrations/automation"):
        return "automation"
    elif endpoint.startswith("/api/v1/bulk"):
        return "bulk"
    elif endpoint.startswith("/api/v1/"):
        return "public"
    else:
        return "ui"

@app.before_request
def apply_rate_limit():
    tier = get_rate_limit_tier(request.endpoint)
    limit = RATE_LIMITS.get(tier, "1000/hour")
    # Apply limit
```

### 12.5 Frontend

- Gate criteria configuration UI (Program Settings)
- Go/No-Go scorecard widget (Cycle detail, Plan detail)
- Visual pass/fail indicators (green/red badges)
- "Evaluate Now" butonu ile manuel tetikleme
- Blocking criteria warnings before proceed
- Historical evaluation timeline

### 12.6 API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| GET/POST | `/programs/<pid>/gate-criteria` | Kriter CRUD |
| POST | `/testing/cycles/<cid>/evaluate-exit` | Cycle exit değerlendirmesi |
| POST | `/testing/plans/<pid>/evaluate-exit` | Plan exit değerlendirmesi |
| GET | `/<entity_type>/<eid>/gate-history` | Değerlendirme geçmişi |
| GET | `/rate-limit/status` | Kullanıcının rate limit durumu |

### 12.7 İş Kalemleri — 7 gün (1.5 hafta)

| # | İş | Tahmini | Durum |
|---|-----|--------|-------|
| 12.7.1 | GateCriteria + GateEvaluation models | 0.5 gün | ✅ Done |
| 12.7.2 | Criteria type calculators (pass_rate, defect, coverage) | 1.5 gün | ✅ Done |
| 12.7.3 | GateEvaluationEngine service | 1 gün | ✅ Done |
| 12.7.4 | Evaluation API endpoints | 0.5 gün | ✅ Done |
| 12.7.5 | Gate criteria config UI | 1 gün | ✅ Done |
| 12.7.6 | Go/No-Go scorecard widget | 1 gün | ✅ Done |
| 12.7.7 | Tiered rate limiter implementation | 0.5 gün | ✅ Done |
| 12.7.8 | Unit + E2E tests | 0.5 gün | ✅ Done (38 test) |
| **Toplam** | | **7 gün (1.5 hafta)** | **✅ TAMAMLANDI** |

---

## Zaman Çizelgesi

```
2026
 Mar    │ F1 ████████████████████████ UI/UX Modernization (3w) ✅
 Apr    │ F2 ████████████ Versioning (1.5w) ✅
        │ F3 ████████████████ Approval (2w) ✅
 May    │ F4 ████████████████████████ AI Pipeline (3w) ✅
 Jun    │ F5 ████████████████████████ Reporting Engine (3w) ✅
 Jul    │ F6 ████████████████ Folders + Env Matrix (2w) ✅
        │ F7 ████████████████████ BDD + Data-Driven (2.5w) ✅
 Aug    │ F8 ████████████████ Exploratory + Evidence (2w) ✅
        │ F9 ████████████ Custom Fields (1.5w) ✅
 Sep    │ F10 ████████████████████████ Integrations + Public API (3w) ✅
 Oct    │ F11 ████████████████ Infrastructure + Observability (2w) ✅
        │ F12 ████████████ Gate Criteria Engine (1.5w) ✅

 ✅ TÜM FAZLAR TAMAMLANDI
```

---

## Mimari Kararlar

### M1 — Component-Based Vanilla JS (No Framework)

Mevcut SPA'yı koruyoruz. React/Vue migration yerine **bileşen kütüphanesi** yaklaşımı:
- Her bileşen kendi dosyasında, `render()` + event binding pattern
- Modüller arası iletişim: custom events + shared state
- **Neden:** Mevcut 20K+ LoC migration maliyeti gereksiz. Component library ile aynı kaliteye ulaşılır.

### M2 — CSS Design Token System

- Tek `design-tokens.css` dosyası tüm renk/spacing/tipografi
- Component'a özel CSS: `static/css/components/*.css`
- BEM naming convention: `.tm-data-grid__header-cell--sorted`
- Dark mode hazırlığı: token'lar `data-theme` attribute ile override

### M3 — AI Pipeline Architecture

- Her AI servisi bağımsız class (`app/ai/assistants/`)
- Async execution desteği (uzun süren analizler için)
- Rate limiting ve cache (Redis)
- Suggestion queue pattern: AI sonuçları → review → kabul/ret

### M4 — Reporting Engine

- Query builder → SQL generator (whitelist tabanlı, injection-safe)
- Chart rendering: Chart.js (already in use) + treemap/heatmap eklentileri
- PDF: Server-side HTML→PDF (WeasyPrint veya wkhtmltopdf)
- Schedule: APScheduler (mevcut) ile email rapor gönderimi

### M5 — Async Processing Architecture (YENİ)

- **Celery + Redis** ile async task queue
- Task türleri: automation import, PDF generation, AI batch, bulk ops
- Dead letter queue ve retry policy
- Task prioritization: high (user-triggered) vs low (scheduled)
- Worker auto-scaling (container orchestration ile)

### M6 — Caching Strategy (YENİ)

- **Redis** cache backend
- Tier-based TTL: dashboard (1m), API response (5m), AI (1h)
- Cache invalidation on entity update
- Cache warming for frequently accessed data
- Session storage (Redis-backed)

### M7 — Observability Stack (YENİ)

- **Structured logging** (JSON format, request correlation)
- **OpenTelemetry** traces + metrics
- **Prometheus** metrics endpoint
- Distributed tracing for AI pipeline
- Health checks for all components

---

## Başarı Kriterleri

| Kriter | Hedef |
|--------|-------|
| Feature parity skoru (vs QMetry) | ≥95% |
| UI density (satır/ekran) | ≥25 satır (compact grid) |
| Sayfa yükleme süresi | <500ms (cached) |
| AI response time | <5s (search), <15s (generation) |
| Test coverage (backend) | ≥80% |
| E2E smoke pass rate | 100% |
| PDF export doğruluğu | %100 veri tutarlılığı |
| Rapor sayısı (preset) | ≥50 |
| Dashboard gadget çeşidi | ≥12 |
| Custom field desteği | ≥7 field type |
| **Async job throughput** | ≥100 import/saat |
| **API cache hit rate** | ≥70% (dashboard/list endpoints) |
| **Webhook delivery success** | ≥99% ilk denemede |
| **OpenAPI spec coverage** | %100 public endpoint |
| **Evidence capture latency** | <2s upload + thumbnail |

---

## Risk Matrisi

| Risk | Olasılık | Etki | Mitigation |
|------|---------|------|-----------|
| UI refactor mevcut testleri kırar | Yüksek | Orta | Her fazda E2E smoke, incremental migration |
| AI servisleri LLM rate limit'e çarpar | Orta | Yüksek | Cache + batch + fallback (rule-based) |
| Versioning JSON bloat | Düşük | Orta | Retention policy (son 50 versiyon), archival |
| Custom SQL rapor injection riski | Orta | Yüksek | Whitelist tablo/kolon, parameterized queries |
| Jira API rate limits | Yüksek | Orta | Webhook + queue, exponential backoff |
| **Celery worker failure** | Orta | Yüksek | Dead letter queue, retry with backoff, alerting |
| **Redis cache eviction** | Düşük | Orta | TTL-based expiration, cache warming |
| **Large file upload timeout** | Orta | Orta | Chunked upload, background processing |
| **Webhook endpoint unavailable** | Yüksek | Orta | Retry policy, delivery log, manual resend |
| **Storage quota exceeded** | Düşük | Yüksek | Monitoring + alerts, auto-cleanup policy |

---

## İlk Sprint Backlog (F1 Başlangıcı)

| # | User Story | Story Point |
|---|-----------|-------------|
| 1 | Design token CSS dosyasını oluştur | 2 |
| 2 | DataGrid bileşenini uygula (sort, filter, resize, checkbox) | 8 |
| 3 | TreePanel bileşenini uygula (nested, search, context menu) | 5 |
| 4 | SplitPane + TabBar bileşenlerini uygula | 5 |
| 5 | Test Catalog sayfasını yeni layout'a taşı | 8 |
| 6 | Toolbar + StatusBadge bileşenlerini uygula | 3 |

---

*Competitive Analysis: [QMETRY-COMPETITIVE-ANALYSIS.md](QMETRY-COMPETITIVE-ANALYSIS.md)*
*İlişkili: [ADR-008-Test-Architecture-Redesign.md](ADR-008-Test-Architecture-Redesign.md)*
