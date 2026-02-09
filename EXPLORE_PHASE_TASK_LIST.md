# Explore Phase Management System — Detaylı Task Listesi
## explore-phase-fs-ts.md v1.2 Analizi

**Hazırlayan:** ProjektCoPilot  
**Tarih:** 2026-02-10  
**Kaynak Doküman:** explore-phase-fs-ts.md (2787 satır, v1.2)

---

## Doküman Özeti

| Özellik | Değer |
|---------|-------|
| **Modüller** | 4 ana (A-D) + 1 dashboard (E) |
| **Toplam Tablo** | 25 (13 orijinal + 12 gap analysis) |
| **Modify Edilen Tablo** | 2 (process_level +11 alan, process_step +2 alan) |
| **API Endpoint Grupları** | 5 ana + 15+ gap ek endpoint |
| **Frontend Component** | ~45 component |
| **Business Rule** | 7 temel + 12 gap kuralı |
| **Enum Tanımları** | 20+ tip |
| **Integration Point** | 3 (Cloud ALM, Signavio, mevcut modüller) |
| **Acceptance Criteria** | 4 modül + 12 GAP = ~65 checklist item |

---

## Mevcut Kod Tabanı ile Karşılaştırma

| FS/TS Konsepti | Mevcut Kod | Durum |
|----------------|------------|-------|
| `process_level` (L1-L4 ağaç) | `Scenario` (L1) + `Process` (L2-L4 self-ref) in scope.py | **MIGRATION** — yeni şemaya taşınmalı |
| `workshop` | `Workshop` in scenario.py (basit model) | **EXTEND** — 10+ yeni alan eklenmeli |
| `workshop_document` | `WorkshopDocument` in scenario.py | **EXTEND** — type/format alanları |
| `requirement` | `Requirement` in requirement.py | **EXTEND** — lifecycle, ALM, effort alanları |
| `open_item` | `OpenItem` in requirement.py (req'a bağlı) | **REFACTOR** — bağımsız entity olacak |
| `decision` | `Decision` in raid.py (RAID bağlamında) | **NEW** — workshop step bağlamında ayrı model |
| `workshop_scope_item` | Yok (workshop→scenario tek FK) | **NEW** |
| `workshop_attendee` | Workshop.attendees (TEXT alanı) | **NEW** — ayrı tablo |
| `workshop_agenda_item` | Yok | **NEW** |
| `process_step` | Yok | **NEW** |
| `requirement_open_item_link` | Yok (OI req'a tek FK) | **NEW** |
| `requirement_dependency` | Yok | **NEW** |
| `open_item_comment` | Yok | **NEW** |
| `cloud_alm_sync_log` | Yok | **NEW** |

---

## Fazlama Özeti

| Faz | Kapsam | Tahmini Sprint |
|-----|--------|----------------|
| **Phase 0 — CRITICAL** | Base 4 modül + GAP-01 (L4 Seeding) + GAP-05 (Roller) + GAP-11 (L3 Konsolide) + GAP-12 (L2 Milestone) | 8-10 sprint |
| **Phase 1 — IMPORTANT** | GAP-03 (WS Bağımlılık) + GAP-04 (Reopen) + GAP-07 (Attachments) + GAP-09 (Scope Change) + GAP-10 (Multi-Session) | 5-6 sprint |
| **Phase 2 — ENHANCEMENT** | GAP-02 (BPMN) + GAP-06 (Minutes) + GAP-08 (Dashboard) | 4-5 sprint |

---

## BÖLÜM 1: VERİ KATMANI (Backend — Models & Migrations)

### 1.1 Base Modeller (Orijinal 13 Tablo)

#### T-001: `process_level` modeli oluştur
- **Dosya:** `app/models/explore.py` (yeni dosya)
- **Tablo:** `process_level`
- **Kolonlar:** id (UUID PK), project_id (FK→program), parent_id (self-ref FK), level (1-4), code (VARCHAR 20, UNIQUE per project), name (VARCHAR 200), description (TEXT), scope_status (ENUM: in_scope/out_of_scope/under_review), fit_status (ENUM: fit/gap/partial_fit/pending), scope_item_code (VARCHAR 10), bpmn_available (BOOL), bpmn_reference (VARCHAR 500), process_area_code (VARCHAR 5), wave (INT), sort_order (INT), created_at, updated_at
- **İndeksler:** idx_pl_project_parent, idx_pl_project_level, idx_pl_scope_item, idx_pl_code (UNIQUE)
- **Constraints:** level = parent.level + 1, scope_item_code required at L3, fit_status required at L3/L4
- **İlişkiler:** children (self-ref 1:N), parent, workshops (via workshop_scope_item), requirements, open_items
- **Gap-11 ek alanlar (L3):** consolidated_fit_decision, system_suggested_fit, consolidated_decision_override, consolidated_decision_rationale, consolidated_decided_by, consolidated_decided_at
- **Gap-12 ek alanlar (L2):** confirmation_status, confirmation_note, confirmed_by, confirmed_at, readiness_pct
- **Computed:** fit_summary (query), completion_pct (query)
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK (self-referential tree + computed fields + L2/L3 ek alanlar)

#### T-002: `workshop` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop`
- **Kolonlar:** id, project_id, code (auto: WS-{area}-{seq}{letter}), name, type (ENUM: fit_to_standard/deep_dive/follow_up/delta_design), status (ENUM: draft/scheduled/in_progress/completed/cancelled), date, start_time, end_time, facilitator_id (FK→user), process_area, wave, session_number, total_sessions, location, meeting_link, notes, summary, created_at, updated_at, started_at, completed_at
- **Gap-04 ek alanlar:** original_workshop_id (FK→workshop), reopen_count, reopen_reason, revision_number
- **İndeksler:** idx_ws_project_status, idx_ws_project_date, idx_ws_project_area, idx_ws_facilitator, idx_ws_code (UNIQUE)
- **İlişkiler:** scope_items (via workshop_scope_item), attendees, agenda_items, process_steps, documents, facilitator
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### T-003: `workshop_scope_item` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop_scope_item`
- **Kolonlar:** id, workshop_id (FK), process_level_id (FK, must be level=3), sort_order
- **Constraint:** UNIQUE (workshop_id, process_level_id), referenced process_level level=3
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### T-004: `workshop_attendee` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop_attendee`
- **Kolonlar:** id, workshop_id (FK), user_id (FK, nullable), name, role, organization (ENUM: customer/consultant/partner/vendor), attendance_status (ENUM), is_required (BOOL)
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### T-005: `workshop_agenda_item` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop_agenda_item`
- **Kolonlar:** id, workshop_id (FK), time, title, duration_minutes, type (ENUM: session/break/demo/discussion/wrap_up), sort_order, notes
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### T-006: `process_step` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `process_step`
- **Kolonlar:** id, workshop_id (FK), process_level_id (FK, must be level=4), sort_order, fit_decision (ENUM: fit/gap/partial_fit), notes, demo_shown (BOOL), bpmn_reviewed (BOOL), assessed_at, assessed_by (FK→user)
- **Gap-10 ek alanlar:** previous_session_step_id (FK→process_step), carried_from_session (INT)
- **Constraint:** UNIQUE (workshop_id, process_level_id), process_level must be level=4
- **Business Rule:** fit_decision set → propagate to process_level.fit_status
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### T-007: `decision` modeli oluştur (workshop context)
- **Dosya:** `app/models/explore.py`
- **Tablo:** `explore_decision` (raid.py'deki Decision'dan ayırt etmek için)
- **Kolonlar:** id, project_id, process_step_id (FK), code (auto: DEC-{seq}), text, decided_by, decided_by_user_id (FK), category (ENUM: process/technical/scope/organizational/data), status (ENUM: active/superseded/revoked), rationale, created_at
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### T-008: `open_item` modeli yeniden yapılandır
- **Dosya:** `app/models/explore.py`
- **Mevcut:** OpenItem (requirement.py'de Requirement FK'ye bağlı)
- **Yeni yapı:** Bağımsız entity — project_id, process_step_id (optional), workshop_id (optional), process_level_id (optional), code (auto: OI-{seq}), title, description, status (ENUM: open/in_progress/blocked/closed/cancelled), priority (P1-P4), category (ENUM: 6 tip), assignee_id, assignee_name, created_by_id, due_date, resolved_date, resolution, blocked_reason, process_area, wave, created_at, updated_at
- **İndeksler:** idx_oi_project_status, idx_oi_assignee_status, idx_oi_project_due (partial), idx_oi_workshop, idx_oi_code (UNIQUE)
- **Computed:** is_overdue, days_overdue
- **Faz:** Phase 0
- **Tahmini Süre:** 3h (migration dahil)

#### T-009: `requirement` modeli genişlet (Explore context)
- **Dosya:** `app/models/explore.py`
- **Mevcut:** Requirement (requirement.py — basit model)
- **Yeni alanlar:** process_step_id, workshop_id, process_level_id (L4), scope_item_id (L3), code (auto: REQ-{seq}), priority (P1-P4), type (ENUM: 6 tip), fit_status (gap/partial_fit), status (ENUM: 8 durum lifecycle), effort_hours, effort_story_points, complexity, created_by_id/name, approved_by_id/name/at, process_area, wave, alm_id, alm_synced, alm_synced_at, alm_sync_status, deferred_to_phase, rejection_reason
- **Status Lifecycle:** draft → under_review → approved → in_backlog → realized → verified (+ deferred, rejected)
- **10 valid transition:** submit_for_review, approve, reject, return_to_draft, defer, push_to_alm, mark_realized, verify, reactivate
- **İndeksler:** 7 indeks
- **Faz:** Phase 0
- **Tahmini Süre:** 4h (lifecycle engine dahil)
- **Karmaşıklık:** YÜKSEK

#### T-010: `requirement_open_item_link` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `requirement_open_item_link`
- **Kolonlar:** id, requirement_id (FK), open_item_id (FK), link_type (ENUM: blocks/related/triggers), created_at
- **Constraint:** UNIQUE (requirement_id, open_item_id)
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### T-011: `requirement_dependency` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `requirement_dependency`
- **Kolonlar:** id, requirement_id (FK), depends_on_id (FK), dependency_type (ENUM: blocks/related/extends), created_at
- **Constraint:** UNIQUE (requirement_id, depends_on_id), no self-reference
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### T-012: `open_item_comment` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `open_item_comment`
- **Kolonlar:** id, open_item_id (FK), user_id (FK), type (ENUM: comment/status_change/reassignment/due_date_change), content, created_at
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### T-013: `cloud_alm_sync_log` modeli oluştur
- **Dosya:** `app/models/explore.py`
- **Tablo:** `cloud_alm_sync_log`
- **Kolonlar:** id, requirement_id (FK), sync_direction (push/pull), sync_status (success/error/partial), alm_item_id, error_message, payload (JSON), created_at
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

### 1.2 Gap Analysis Modelleri (12 Ek Tablo)

#### T-014: `l4_seed_catalog` modeli oluştur [GAP-01]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `l4_seed_catalog`
- **Kolonlar:** id, scope_item_code, sub_process_code, sub_process_name, description, standard_sequence, bpmn_activity_id, sap_release
- **UNIQUE:** (scope_item_code, sub_process_code)
- **Not:** Proje bağımsız global katalog
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### T-015: `project_role` modeli oluştur [GAP-05]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `project_role`
- **Kolonlar:** id, project_id (FK), user_id (FK), role (ENUM: pm/module_lead/facilitator/bpo/tech_lead/tester/viewer), process_area (VARCHAR 5, nullable — NULL=all areas), created_at
- **UNIQUE:** (project_id, user_id, role, process_area)
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### T-016: `workshop_dependency` modeli oluştur [GAP-03]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop_dependency`
- **Kolonlar:** id, workshop_id (FK), depends_on_workshop_id (FK), dependency_type (ENUM: must_complete_first/information_needed/cross_module_review/shared_decision), description, status (active/resolved), created_by (FK), created_at, resolved_at
- **Constraint:** No self-reference, UNIQUE (workshop_id, depends_on_workshop_id)
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

#### T-017: `cross_module_flag` modeli oluştur [GAP-03]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `cross_module_flag`
- **Kolonlar:** id, process_step_id (FK), target_process_area, target_scope_item_code, description, status (open/discussed/resolved), resolved_in_workshop_id (FK), created_at
- **Faz:** Phase 1
- **Tahmini Süre:** 0.5h

#### T-018: `workshop_revision_log` modeli oluştur [GAP-04]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `workshop_revision_log`
- **Kolonlar:** id, workshop_id (FK), action (ENUM: reopened/delta_created/fit_decision_changed), previous_value (TEXT/JSON), new_value (TEXT/JSON), reason, changed_by (FK), created_at
- **Faz:** Phase 1
- **Tahmini Süre:** 0.5h

#### T-019: `attachment` modeli oluştur [GAP-07]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `attachment`
- **Kolonlar:** id, project_id (FK), entity_type (ENUM: workshop/process_step/requirement/open_item/decision/process_level), entity_id, file_name, file_path, file_size, mime_type, category (ENUM: 7 tip), description, uploaded_by (FK), created_at
- **İndeksler:** idx_attachment_entity, idx_attachment_project
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

#### T-020: `bpmn_diagram` modeli oluştur [GAP-02]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `bpmn_diagram`
- **Kolonlar:** id, process_level_id (FK), type (ENUM: signavio_embed/bpmn_xml/image), source_url, bpmn_xml, image_path, version, uploaded_by (FK), created_at
- **Faz:** Phase 2
- **Tahmini Süre:** 0.5h

#### T-021: `workshop_document` genişlet [GAP-06]
- **Mevcut:** WorkshopDocument (scenario.py — basit)
- **Yeni alanlar:** type (meeting_minutes/ai_summary/custom_report), format (markdown/docx/pdf), content, file_path, generated_by (manual/template/ai), generated_at, created_by (FK)
- **Faz:** Phase 2
- **Tahmini Süre:** 1h

#### T-022: `daily_snapshot` modeli oluştur [GAP-08]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `daily_snapshot`
- **Kolonlar:** id, project_id (FK), snapshot_date (DATE), metrics (JSON), created_at
- **UNIQUE:** (project_id, snapshot_date)
- **Faz:** Phase 2
- **Tahmini Süre:** 0.5h

#### T-023: `scope_change_request` modeli oluştur [GAP-09]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `scope_change_request`
- **Kolonlar:** id, project_id, code (auto: SCR-{seq}), process_level_id (FK), change_type (ENUM: 5 tip), current_value (JSON), proposed_value (JSON), justification, impact_assessment, status (ENUM: requested/under_review/approved/rejected/implemented), requested_by (FK), reviewed_by (FK), approved_by (FK), created_at, decided_at, implemented_at
- **Faz:** Phase 1
- **Tahmini Süre:** 1.5h

#### T-024: `scope_change_log` modeli oluştur [GAP-09]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `scope_change_log`
- **Kolonlar:** id, project_id, process_level_id (FK), field_changed, old_value, new_value, scope_change_request_id (FK, nullable), changed_by (FK), created_at
- **Faz:** Phase 1
- **Tahmini Süre:** 0.5h

#### T-025: `phase_gate` modeli oluştur [GAP-12]
- **Dosya:** `app/models/explore.py`
- **Tablo:** `phase_gate`
- **Kolonlar:** id, project_id (FK), phase (ENUM: explore/realize/deploy), gate_type (ENUM: area_confirmation/phase_closure), process_level_id (FK, nullable — L2), status (ENUM: pending/approved/approved_with_conditions/rejected), conditions, approved_by (FK), approved_at, notes, created_at
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

### 1.3 Migration

#### T-026: Alembic migration — Phase 0 tabloları
- **Dosya:** `migrations/versions/XXXXXX_explore_phase_0.py`
- **İçerik:** process_level, workshop (extended), workshop_scope_item, workshop_attendee, workshop_agenda_item, process_step, explore_decision, open_item (refactored), requirement (extended), requirement_open_item_link, requirement_dependency, open_item_comment, cloud_alm_sync_log, l4_seed_catalog, project_role, phase_gate
- **Toplam:** 16 tablo create + 2 alter (process_level L2/L3 alanları, process_step ek alanlar)
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK (mevcut veriden migration gerekebilir)

#### T-027: Alembic migration — Phase 1 tabloları
- **Dosya:** `migrations/versions/XXXXXX_explore_phase_1.py`
- **İçerik:** workshop_dependency, cross_module_flag, workshop_revision_log, attachment, scope_change_request, scope_change_log + workshop tablosuna reopen alanları + process_step ek alanları
- **Toplam:** 6 tablo + 2 alter
- **Faz:** Phase 1
- **Tahmini Süre:** 2h

#### T-028: Alembic migration — Phase 2 tabloları
- **Dosya:** `migrations/versions/XXXXXX_explore_phase_2.py`
- **İçerik:** bpmn_diagram, workshop_document (extend), daily_snapshot
- **Toplam:** 2 create + 1 alter
- **Faz:** Phase 2
- **Tahmini Süre:** 1h

#### T-029: Mevcut veri migration scripti
- **Dosya:** `scripts/migrate_explore_data.py`
- **İçerik:** Scenario → process_level L1, Process → process_level L2/L3/L4, Workshop → yeni workshop, RequirementProcessMapping → doğrudan FK, OpenItem → bağımsız entity
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK

---

## BÖLÜM 2: API KATMANI (Backend — Blueprints & Services)

### 2.1 Process Hierarchy API

#### A-001: `explore_bp.py` blueprint oluştur
- **Dosya:** `app/blueprints/explore_bp.py`
- **Prefix:** `/api/projects/<project_id>/`
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### A-002: GET /process-levels (tree + flat mode)
- **Query params:** level, scope_status, fit_status, process_area, wave, flat, include_stats
- **Response:** Nested tree with fit_summary aggregates (recursive CTE)
- **Computed:** fit_summary (L1/L2/L3), completion_pct
- **Faz:** Phase 0
- **Tahmini Süre:** 4h (recursive CTE + aggregation)
- **Karmaşıklık:** YÜKSEK

#### A-003: GET /process-levels/{id} — tek node + children
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-004: PUT /process-levels/{id} — güncelleme
- **Fields:** scope_status, fit_status, description, etc.
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-005: GET /scope-matrix — L3 flat tablo
- **Response:** L3 list + workshop/req/OI stats per row
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-006: POST /process-levels/{l3Id}/seed-from-catalog [GAP-01]
- **Business Logic:** l4_seed_catalog lookup → L4 kayıt oluştur, idempotent
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-007: POST /process-levels/{l3Id}/seed-from-bpmn [GAP-01]
- **Business Logic:** BPMN XML parse → L4 kayıt oluştur
- **Faz:** Phase 0
- **Tahmini Süre:** 3h (BPMN parsing)

#### A-008: POST /process-levels/{l3Id}/children — manuel L4 ekleme
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-009: POST /process-levels/{l3Id}/consolidate-fit [GAP-11]
- **Business Logic:** L4'lerden system suggestion → business decision (override)
- **Validation:** All L4 assessed, permission check
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### A-010: GET /process-levels/{l3Id}/consolidated-view [GAP-11]
- **Response:** L4 breakdown + blocking items + sign-off status + signoff_ready flag
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-011: POST /process-levels/{l3Id}/override-fit-status [GAP-11]
- **Business Logic:** Override + rationale (zorunlu) + permission check
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-012: POST /process-levels/{l3Id}/signoff [GAP-11]
- **Pre-conditions:** Tüm L4 assessed, P1 OI closed, REQ approved
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-013: GET /process-levels/l2-readiness [GAP-12]
- **Response:** Tüm L2 readiness durumu, L3 breakdown, completion_pct
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-014: POST /process-levels/{l2Id}/confirm [GAP-12]
- **Validation:** readiness_pct = 100, permission check
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### A-015: GET /area-milestones [GAP-12]
- **Response:** Process area milestone tracker data
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-016: GET /process-levels/{id}/bpmn [GAP-02]
- **Faz:** Phase 2
- **Tahmini Süre:** 0.5h

#### A-017: POST /process-levels/{id}/bpmn [GAP-02]
- **Faz:** Phase 2
- **Tahmini Süre:** 1h

#### A-018: GET /process-levels/{id}/change-history [GAP-09]
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

### 2.2 Workshop API

#### A-019: GET /workshops — liste (filtreleme, sıralama, sayfalama)
- **Query params:** status, process_area, wave, facilitator_id, date_from, date_to, scope_item_code, search, sort_by, sort_dir, page, per_page
- **Response:** + stats per workshop (steps_total, fit_count, gap_count, etc.)
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### A-020: GET /workshops/{id} — detay
- **Response:** Full detail: agenda, attendees, process_steps + nested decisions/OIs/reqs
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-021: POST /workshops — yeni workshop oluştur
- **Business Logic:** Code generation (WS-{area}-{seq}{letter})
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-022: PUT /workshops/{id} — güncelleme
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-023: POST /workshops/{id}/start — başlat
- **Side effects:** status → in_progress, started_at set, L4 children → process_step kayıtları
- **Validation:** scope item'ların L4 child'ları var mı? [GAP-01]
- **Multi-session logic [GAP-10]:** session_number > 1 ise previous session steps taşı
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK

#### A-024: POST /workshops/{id}/complete — tamamla
- **Validation:** Tüm steps fit_decision != NULL (son session'da zorunlu, ara session'da opsiyonel [GAP-10])
- **Side effects:** fit_decision → process_level propagation, L3 recalculate, L3 system_suggested_fit hesapla [GAP-11]
- **Warning:** Open items açık, notes boş, unresolved cross-module flags [GAP-03]
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK (propagation + validation + warnings)

#### A-025: GET /workshops/capacity — facilitator capacity
- **Response:** weekly load per facilitator, overloaded weeks
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-026: POST /workshops/{id}/reopen [GAP-04]
- **Business Logic:** completed → in_progress, reopen_count++, revision log
- **Faz:** Phase 1
- **Tahmini Süre:** 2h

#### A-027: POST /workshops/{id}/create-delta [GAP-04]
- **Business Logic:** Yeni delta_design workshop, step kopyalama
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

#### A-028: GET/POST /workshops/{id}/dependencies [GAP-03]
- **Faz:** Phase 1
- **Tahmini Süre:** 1.5h

#### A-029: POST /workshops/{id}/generate-minutes [GAP-06]
- **Response:** Markdown/DOCX/PDF minutes
- **Faz:** Phase 2
- **Tahmini Süre:** 4h

#### A-030: POST /workshops/{id}/ai-summary [GAP-06]
- **Business Logic:** AI API call → structured summary
- **Faz:** Phase 2
- **Tahmini Süre:** 3h

### 2.3 Process Step API

#### A-031: PUT /process-steps/{id} — fit_decision, notes güncelle
- **Side effect:** fit_decision → process_level.fit_status propagation
- **[GAP-04]:** revision log kaydı (fit_decision değişirse)
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-032: POST /process-steps/{id}/decisions — karar ekle
- **Business Logic:** DEC-{seq} code gen, auto-link workshop/project
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-033: POST /process-steps/{id}/open-items — OI oluştur
- **Business Logic:** OI-{seq} code gen, auto-assign workshop_id, process_level_id, process_area, wave
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### A-034: POST /process-steps/{id}/requirements — REQ oluştur
- **Business Logic:** REQ-{seq} code gen, auto-assign all context, status=draft
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### A-035: POST /process-steps/{id}/cross-module-flags [GAP-03]
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

### 2.4 Requirement API

#### A-036: GET /requirements — liste (filtreleme, gruplama, sayfalama)
- **Query params:** status, priority, type, process_area, wave, scope_item_code, workshop_id, alm_synced, search, group_by, sort_by, sort_dir, page, per_page
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### A-037: GET /requirements/{id} — detay + audit trail + linked OIs + dependencies
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-038: PUT /requirements/{id} — güncelleme
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-039: POST /requirements/{id}/transition — durum geçişi
- **10 valid action:** submit_for_review, approve, reject, return_to_draft, defer, push_to_alm, mark_realized, verify, reactivate
- **Side effects:** approve → set approved_by/at, reject → rejection_reason, push_to_alm → Cloud ALM call, defer → deferred_to_phase
- **[GAP-05]:** Permission check per action
- **[GAP-05]:** OI blocking check (approve blocked if blocking OIs open)
- **Faz:** Phase 0
- **Tahmini Süre:** 5h
- **Karmaşıklık:** ÇOK YÜKSEK (state machine + permissions + side effects)

#### A-040: POST /requirements/{id}/link-open-item
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### A-041: POST /requirements/{id}/add-dependency
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### A-042: POST /requirements/bulk-sync-alm — toplu ALM push
- **Validation:** Sadece approved REQ'lar
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### A-043: GET /requirements/stats — KPI aggregation
- **Response:** by_status, by_priority, by_type, by_area, total_effort, alm_synced_count
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### A-044: POST /requirements/batch-transition [GAP-05]
- **Business Logic:** Partial success allowed, per-item permission check
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

### 2.5 Open Item API

#### A-045: GET /open-items — liste (filtreleme, gruplama, sayfalama)
- **Query params:** status, priority, category, process_area, wave, assignee_id, workshop_id, overdue, search, group_by, sort_by, page, per_page
- **Faz:** Phase 0
- **Tahmini Süre:** 2.5h

#### A-046: PUT /open-items/{id} — güncelleme
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-047: POST /open-items/{id}/transition — durum geçişi
- **6 action:** start_progress, mark_blocked, unblock, close, cancel, reopen
- **Close side effect:** blocking OI → check all REQ links → notify if all closed
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### A-048: POST /open-items/{id}/reassign
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-049: POST /open-items/{id}/comments — activity log
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### A-050: GET /open-items/stats — KPI aggregation
- **Response:** by_status, by_priority, overdue_count, p1_open_count, avg_resolution_days, by_assignee, by_category
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

### 2.6 Cross-cutting API'ler

#### A-051: GET /cross-module-flags?status=open [GAP-03]
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

#### A-052: POST /scope-change-requests [GAP-09]
- **Business Logic:** Auto-calculate impact
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

#### A-053: POST /scope-change-requests/{id}/transition [GAP-09]
- **Faz:** Phase 1
- **Tahmini Süre:** 1.5h

#### A-054: POST /scope-change-requests/{id}/implement [GAP-09]
- **Side effects:** Update process_level, cancel workshops, notify
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

#### A-055: GET /scope-change-requests [GAP-09]
- **Faz:** Phase 1
- **Tahmini Süre:** 1h

#### A-056: Attachment CRUD API [GAP-07]
- **Endpoints:** POST upload, GET list, GET download, DELETE
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

#### A-057: GET /reports/steering-committee [GAP-08]
- **Response:** PPTX/PDF deck
- **Faz:** Phase 2
- **Tahmini Süre:** 5h

#### A-058: POST /internal/snapshots/capture [GAP-08]
- **Business Logic:** Daily metrics snapshot
- **Faz:** Phase 2
- **Tahmini Süre:** 2h

### 2.7 Service Katmanı

#### S-001: `FitPropagationService` — fit status propagation engine
- **İçerik:** L4→L3→L2→L1 propagation, system_suggested_fit calculation, override logic
- **Dosya:** `app/services/fit_propagation.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK

#### S-002: `CodeGeneratorService` — otomatik kod üretimi
- **İçerik:** WS-{area}-{seq}{letter}, REQ-{seq}, OI-{seq}, DEC-{seq}, SCR-{seq}
- **Dosya:** `app/services/code_generator.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### S-003: `RequirementLifecycleService` — durum makinesi
- **İçerik:** Transition validation, permission check, side effect execution
- **Dosya:** `app/services/requirement_lifecycle.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 4h
- **Karmaşıklık:** YÜKSEK

#### S-004: `OpenItemLifecycleService` — OI durum makinesi
- **İçerik:** Transition validation, blocking check, close side effects
- **Dosya:** `app/services/open_item_lifecycle.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### S-005: `PermissionService` — rol tabanlı yetki [GAP-05]
- **İçerik:** check_permission(project_id, user_id, action, context), PERMISSION_MATRIX
- **Dosya:** `app/services/permission.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### S-006: `CloudALMService` — SAP Cloud ALM integration
- **İçerik:** Push requirement, bulk sync, retry with backoff, field mapping
- **Dosya:** `app/services/cloud_alm.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 4h

#### S-007: `L3SignOffService` — L3 sign-off logic [GAP-11]
- **İçerik:** Pre-condition check, auto-status update, L2 readiness recalculation
- **Dosya:** `app/services/signoff.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### S-008: `WorkshopSessionService` — multi-session continuity [GAP-10]
- **İçerik:** Previous session step linking, carry-over logic
- **Dosya:** `app/services/workshop_session.py`
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

#### S-009: `MinutesGeneratorService` — meeting minutes [GAP-06]
- **İçerik:** Template engine, DOCX generation
- **Dosya:** `app/services/minutes_generator.py`
- **Faz:** Phase 2
- **Tahmini Süre:** 4h

#### S-010: `SnapshotService` — daily metrics [GAP-08]
- **İçerik:** Metric calculation, snapshot storage
- **Dosya:** `app/services/snapshot.py`
- **Faz:** Phase 2
- **Tahmini Süre:** 3h

---

## BÖLÜM 3: FRONTEND KATMANI

### 3.1 Module A — Process Hierarchy Manager

**Route:** `/projects/{id}/explore/hierarchy`

#### F-001: ProcessHierarchyPage — ana sayfa (Module A)
- **State:** viewMode, expandedNodes, selectedNodeId, searchQuery, filters, detailPanelTab
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-002: ProcessTree — recursive tree component
- **Her node:** level badge, code, name, fit badge, fit distribution bar, workshop indicator
- **Davranış:** expand/collapse, select, search highlight
- **Faz:** Phase 0
- **Tahmini Süre:** 5h
- **Karmaşıklık:** YÜKSEK (recursive rendering, performance with 500+ nodes)

#### F-003: ProcessNodeRow — tek satır
- **Indentation:** level * 24px
- **Click:** select, chevron: expand
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-004: FitDistributionBar — stacked bar
- **Renkler:** green(fit) + amber(partial) + red(gap) + indigo(pending)
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### F-005: ScopeMatrix — L3 flat table
- **Kolonlar:** code, name, area, wave, fit, workshop status, REQ count, OI count
- **Scope change request butonu [GAP-09]**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-006: DetailPanel — 350px sağ sidebar
- **Tabs:** Overview, Fit Analysis, Requirements, Workshop
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-007: KpiDashboard — Module A
- **Metrikler:** Total processes, fit/gap/partial/pending counts and %
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-008: L3ConsolidatedCard [GAP-11]
- **İçerik:** Effective fit status, sign-off badge, blocker list, sign-off/override butonları
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-009: L3SignOffDialog [GAP-11]
- **İçerik:** L4 özeti, blocker listesi, override seçeneği, comment
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-010: L4SeedingDialog [GAP-01]
- **3 mod:** Catalog / BPMN / Manual
- **Preview + import butonları**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

### 3.2 Module B — Workshop Hub

**Route:** `/projects/{id}/explore/workshops`

#### F-011: WorkshopHubPage — ana sayfa (Module B)
- **State:** viewMode, filters, groupBy, sortKey, sortDir, page
- **3 view:** table, kanban, capacity
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-012: WorkshopTable — sortable, groupable tablo
- **Kolonlar:** code, scope item, name, area, wave, date, status, facilitator, fit bar, DEC/OI/REQ counts
- **Gruplama:** wave, area, facilitator, status, date
- **Dependencies kolonu [GAP-03]**
- **Faz:** Phase 0
- **Tahmini Süre:** 5h
- **Karmaşıklık:** YÜKSEK (grouping, sorting, inline stats)

#### F-013: WorkshopKanban — 4-column board
- **Kolonlar:** Draft / Scheduled / In Progress / Completed
- **Drag-and-drop (optional)**
- **Faz:** Phase 0
- **Tahmini Süre:** 4h

#### F-014: CapacityView — facilitator capacity
- **Card grid per facilitator, weekly load bars, overload warning**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-015: FilterBar — search + status + wave + area + facilitator chips
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-016: KpiStrip — Module B
- **Total, progress%, active, scheduled, draft, open items, gaps, requirements**
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### F-017: AreaMilestoneTracker widget [GAP-12]
- **Her satır:** area code, progress dots, L3 ready count, target date, on-track indicator
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

### 3.3 Module C — Workshop Detail

**Route:** `/projects/{id}/explore/workshops/{workshopId}`

#### F-018: WorkshopDetailPage — ana sayfa (Module C)
- **State:** activeTab, expandedStepId, editingFitDecision
- **Tabs:** steps, decisions, openItems, requirements, agenda, attendees
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-019: WorkshopHeader — code, name, status, type, date/time, facilitator, scope items, actions
- **Actions:** Start, Complete, Reopen [GAP-04], Create Delta [GAP-04]
- **Dependencies section [GAP-03]**
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-020: SummaryStrip — Fit/Partial/Gap + DEC/OI/REQ counts
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-021: ProcessStepList — expandable cards
- **Per step:** L4 code, name, fit badge, counts
- **Previous session indicator [GAP-10]**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-022: ProcessStepCard — expandable
- **Expand:** notes, fit selector, decisions, OIs, reqs
- **Cross-module flag butonu [GAP-03]**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-023: FitDecisionSelector — 3-radio: Fit/Partial Fit/Gap
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-024: DecisionCard — purple accent
- **İçerik:** text, decided_by, category
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-025: OpenItemCard — orange accent
- **İçerik:** ID, priority, status, assignee, due date
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-026: RequirementCard — blue accent
- **İçerik:** ID, priority, type, status, effort
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-027: InlineAddForm — collapsible DEC/OI/REQ form
- **3 mod:** Decision, Open Item, Requirement oluşturma
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-028: AgendaTimeline — time-ordered agenda
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-029: AttendeeList — name, role, org badge, attendance
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### F-030: L3 Consolidated Decision section [GAP-11]
- **Workshop complete sonrası:** L4 breakdown + system suggestion + override UI
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

### 3.4 Module D — Requirement & Open Item Hub

**Route:** `/projects/{id}/explore/requirements`

#### F-031: RequirementHubPage — ana sayfa (Module D)
- **2 tab:** Requirements / Open Items
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-032: RequirementKpiStrip — Total, P1, draft, review, approved, backlog, realized, ALM synced, effort
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### F-033: RequirementRow — expandable satır
- **İçerik:** ID, priority pill, type pill, fit pill, title, scope item, area, effort, status flow, ALM icon
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-034: RequirementExpandedDetail — traceability + links + actions
- **İçerik:** Workshop, scope, step, created_by, approved_by, ALM ID, linked OIs, dependencies
- **Action butonları: Submit, Approve, Reject, Push to ALM, etc.**
- **Faz:** Phase 0
- **Tahmini Süre:** 3h

#### F-035: StatusFlowIndicator — horizontal lifecycle dots
- **8 durum:** draft → under_review → approved → in_backlog → realized → verified (+ deferred, rejected)
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-036: RequirementActionButtons — context-sensitive
- **Permission-based visibility [GAP-05]**
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-037: RequirementFilterBar — full filter set
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-038: OpenItemKpiStrip — Total, open, in progress, blocked, closed, overdue, P1 open
- **Faz:** Phase 0
- **Tahmini Süre:** 1.5h

#### F-039: OpenItemRow — expandable satır
- **İçerik:** ID, priority, status, category, title, assignee, due date (red if overdue), area
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-040: OpenItemExpandedDetail — traceability + linked REQ + actions
- **Faz:** Phase 0
- **Tahmini Süre:** 2.5h

#### F-041: OverdueToggle — red filter toggle
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-042: AssigneeDropdown — filter by unique assignees
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

### 3.5 Shared Components

#### F-043: Pill — generic pill component
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-044: FitBadge — fit/gap/partial_fit/pending badge
- **Renkler:** green/red/amber/indigo
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-045: FitBarMini — mini stacked bar
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-046: KpiBlock — reusable KPI card
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-047: FilterGroup — reusable filter chip group
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### F-048: ActionButton — styled action button
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### F-049: CountChip — inline count indicator
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

### 3.6 Module E — Dashboard [GAP-08]

#### F-050: ExploreDashboardPage — dashboard sayfası
- **Route:** `/projects/{id}/explore/dashboard`
- **Faz:** Phase 2
- **Tahmini Süre:** 2h

#### F-051: Workshop Completion Burndown — area chart
- **Faz:** Phase 2
- **Tahmini Süre:** 3h

#### F-052: Wave Progress Bars — horizontal bars per wave
- **Faz:** Phase 2
- **Tahmini Süre:** 2h

#### F-053: Fit/Gap Trend — stacked area chart
- **Faz:** Phase 2
- **Tahmini Süre:** 3h

#### F-054: Requirement Pipeline Funnel — funnel chart
- **Faz:** Phase 2
- **Tahmini Süre:** 2h

#### F-055: Open Item Aging — bar chart
- **Faz:** Phase 2
- **Tahmini Süre:** 2h

#### F-056: Gap Density Heatmap — process area x wave
- **Faz:** Phase 2
- **Tahmini Süre:** 3h

#### F-057: Scope Coverage Donut — assessed vs pending L4
- **Faz:** Phase 2
- **Tahmini Süre:** 1.5h

### 3.7 Routing & Navigation

#### F-058: Explore module router setup
- **Routes:** /explore/hierarchy, /explore/workshops, /explore/workshops/:id, /explore/requirements, /explore/dashboard
- **Cross-module navigation links (dokümandaki navigation flow)**
- **Faz:** Phase 0
- **Tahmini Süre:** 2h

#### F-059: BpmnViewer component [GAP-02]
- **2 mod:** iframe (Signavio) + bpmn-js viewer
- **Faz:** Phase 2
- **Tahmini Süre:** 4h

#### F-060: AttachmentSection component [GAP-07]
- **Upload dropzone, list, preview, download**
- **Faz:** Phase 1
- **Tahmini Süre:** 3h

---

## BÖLÜM 4: BUSINESS RULES & LOGIC

#### BR-001: Fit Status Propagation (L4→L3→L2→L1)
- **Kural:** L4 fit_decision → process_level.fit_status → L3 system_suggested_fit → L3 consolidated → L2 readiness → L1 summary
- **Ref:** Section 5.1 (revised), 13.11.3
- **Faz:** Phase 0
- **Tahmini Süre:** (S-001'de dahil)

#### BR-002: Code Generation Rules
- **Workshop:** WS-{AREA}-{SEQ}{SESSION} (A/B/C for multi-session)
- **Requirement:** REQ-{SEQ} (3-digit, project-wide)
- **Open Item:** OI-{SEQ} (3-digit, project-wide)
- **Decision:** DEC-{SEQ} (3-digit, project-wide)
- **Scope Change:** SCR-{SEQ}
- **Ref:** Section 5.2
- **Faz:** Phase 0
- **Tahmini Süre:** (S-002'de dahil)

#### BR-003: Workshop Completion Validation
- **Blocking:** Tüm process_steps fit_decision != NULL (son session)
- **Warning:** Open items açık, notes boş, unresolved cross-module flags
- **[GAP-10]:** Ara session'da NULL allowed
- **[GAP-03]:** Unresolved dependencies warning
- **Ref:** Section 5.3
- **Faz:** Phase 0

#### BR-004: Overdue Logic
- **status IN ('open', 'in_progress') AND due_date < CURRENT_DATE**
- **Ref:** Section 5.4
- **Faz:** Phase 0

#### BR-005: OI-to-Requirement Blocking
- **REQ approve blocked while blocking OI open**
- **OI close → check all REQ links → notify if all blocking OIs closed**
- **UI: "Blocked by N open items" badge**
- **Ref:** Section 5.5
- **Faz:** Phase 0

#### BR-006: Cloud ALM Sync Rules
- **Only approved REQ pushable**
- **Retry on error with exponential backoff**
- **Ref:** Section 5.6
- **Faz:** Phase 0

#### BR-007: L3 Sign-Off Pre-conditions [GAP-11]
- **Tüm L4 assessed + P1 OI closed + REQ approved**
- **Ref:** Section 13.11.3
- **Faz:** Phase 0

#### BR-008: L2 Readiness Auto-calculation [GAP-12]
- **readiness_pct = assessed_l3 / in_scope_l3 * 100**
- **Auto-status: not_ready → ready when 100%**
- **Ref:** Section 13.12.3
- **Faz:** Phase 0

#### BR-009: Multi-Session Fit Propagation [GAP-10]
- **Fit propagation SADECE son session'da**
- **Ara session'da propagation yapılmaz**
- **Ref:** Section 13.10.5
- **Faz:** Phase 1

#### BR-010: Scope Change Impact [GAP-09]
- **Auto-calculate: affected workshops, requirements, open items**
- **Implement: Update process_level, cancel draft/scheduled workshops**
- **Ref:** Section 13.9.3
- **Faz:** Phase 1

---

## BÖLÜM 5: TEST KATMANI

#### TEST-001: Model unit testleri — 25 tablo
- **Her model için:** create, read, update, delete, constraint validation, relationship loading
- **Tahmini:** 25 tablo × ~5 test = ~125 test
- **Faz:** Phase 0-2 (ilgili model ile birlikte)
- **Tahmini Süre:** 15h

#### TEST-002: API endpoint testleri — ~60 endpoint
- **Her endpoint için:** happy path, validation error, 404, permission denied [GAP-05]
- **Tahmini:** 60 endpoint × ~4 test = ~240 test
- **Faz:** Phase 0-2 (ilgili endpoint ile birlikte)
- **Tahmini Süre:** 30h

#### TEST-003: Business rule testleri
- **Fit propagation:** 10+ scenario (all fit, mixed, all gap, with override, multi-session)
- **State machine:** REQ lifecycle (10 transitions × valid/invalid = 20+ test), OI lifecycle (6 transitions)
- **Code generation:** Uniqueness, sequence, multi-session letter
- **Blocking logic:** OI blocks REQ, bulk approve with partial block
- **L3 sign-off:** Pre-condition combinations
- **L2 readiness:** Auto-calculation scenarios
- **Tahmini:** ~80 test
- **Faz:** Phase 0-2
- **Tahmini Süre:** 10h

#### TEST-004: Integration testleri
- **Workshop lifecycle:** create → schedule → start → assess → complete → L3 consolidate → L2 confirm
- **Requirement lifecycle:** create in workshop → submit → approve → ALM push → realize → verify
- **Scope change:** request → approve → implement → verify impact
- **Multi-session:** Session A → carry → Session B → complete → propagation
- **Tahmini:** ~20 integration test
- **Faz:** Phase 0-2
- **Tahmini Süre:** 8h

#### TEST-005: Frontend component testleri (Vitest)
- **Shared components:** Pill, FitBadge, FitBarMini, KpiBlock
- **Complex components:** ProcessTree, WorkshopTable, RequirementRow, StatusFlowIndicator
- **Tahmini:** ~40 component test
- **Faz:** Phase 0-2
- **Tahmini Süre:** 12h

#### TEST-006: E2E testleri (Playwright)
- **Workshop flow:** Hub → create → start → assess → complete
- **Requirement flow:** Create in workshop → lifecycle through Module D
- **Cross-module navigation:** A → B → C → D → A
- **Tahmini:** ~10 E2E test
- **Faz:** Phase 0
- **Tahmini Süre:** 8h

---

## BÖLÜM 6: SEED DATA & MIGRATION

#### SEED-001: L4 Seed Catalog data (SAP Best Practice)
- **İçerik:** scope_item_code × sub_process_code mapping
- **Kaynak:** SAP Best Practice dokümanları veya JSON export
- **Tahmini:** 200-500 L4 kayıt (50-100 scope item × 3-5 L4 each)
- **Dosya:** `scripts/seed_data/l4_catalog.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 4h

#### SEED-002: Demo data — Explore Phase
- **İçerik:** 5 L1, 10 L2, 50 L3, 200 L4, 20 workshop, 100 process_step, 50 decisions, 30 OI, 40 REQ
- **Dosya:** `scripts/seed_data/explore.py`
- **Faz:** Phase 0
- **Tahmini Süre:** 5h

#### SEED-003: Project roles demo data
- **İçerik:** 5-10 kullanıcı × farklı roller
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

---

## BÖLÜM 7: DEVOPS & CONFIG

#### DEV-001: Design tokens CSS variables
- **İçerik:** Section 9 design tokens → CSS custom properties
- **Dosya:** `static/css/explore-tokens.css`
- **Faz:** Phase 0
- **Tahmini Süre:** 1h

#### DEV-002: Explore module __init__.py registry
- **İçerik:** Blueprint registration, model imports
- **Faz:** Phase 0
- **Tahmini Süre:** 0.5h

#### DEV-003: API documentation (Swagger/OpenAPI)
- **İçerik:** ~60 endpoint documentation
- **Faz:** Phase 0 (incremental)
- **Tahmini Süre:** 4h

---

## TOPLAM ÖZET

### Faz Bazlı Task Sayısı

| Faz | Model Tasks | API Tasks | Frontend Tasks | Service Tasks | Test Tasks | Diğer | TOPLAM |
|-----|-------------|-----------|----------------|---------------|------------|-------|--------|
| **Phase 0** | 16 (T-001→T-015, T-025) | 38 (A-001→A-050 Phase 0) | 42 (F-001→F-049, F-058) | 7 (S-001→S-007) | 4 | 5 | **~112** |
| **Phase 1** | 5 (T-016→T-019, T-023-24) | 10 | 2 (F-060, partial) | 1 (S-008) | (dahil) | 1 | **~19** |
| **Phase 2** | 3 (T-020→T-022) | 5 | 9 (F-050→F-057, F-059) | 2 (S-009, S-010) | (dahil) | 0 | **~19** |

### Faz Bazlı Tahmini Effort

| Faz | Backend (Model+API+Service) | Frontend | Test | Seed/Migration | Toplam |
|-----|----------------------------|----------|------|----------------|--------|
| **Phase 0** | ~120h | ~95h | ~50h | ~18h | **~283h** |
| **Phase 1** | ~30h | ~6h | ~10h | ~2h | **~48h** |
| **Phase 2** | ~25h | ~25h | ~8h | ~0h | **~58h** |
| **GENEL TOPLAM** | **~175h** | **~126h** | **~68h** | **~20h** | **~389h** |

### Kritik Yol (Phase 0 Sıralaması)

```
1. Models (T-001→T-015, T-025) + Migration (T-026)
   ↓
2. Services (S-001→S-007) — özellikle FitPropagation, Lifecycle, Permission
   ↓
3. API Layer (A-001→A-050 Phase 0)
   ↓
4. Seed Data (SEED-001→SEED-003)
   ↓
5. Tests (TEST-001→TEST-004 Phase 0 kısmı)
   ↓
6. Frontend: Shared Components (F-043→F-049)
   ↓
7. Frontend: Module A (F-001→F-010)
   → Module B (F-011→F-017)
   → Module C (F-018→F-030)
   → Module D (F-031→F-042)
   ↓
8. E2E Tests (TEST-006)
```

---

*Doküman Versiyonu: 1.0*
*Oluşturulma: 2026-02-10*
*Kaynak: explore-phase-fs-ts.md v1.2 (2787 satır)*
