# Cerrahi Rebuild Planı — Workshop Module

**Tarih:** 2026-02-12
**Yaklaşım:** Seçenek C — Cerrahi Rebuild (modeller ve servisler korunur, endpoint'ler bölünür, frontend cerrahi düzeltilir)

---

## Mevcut Durum Özeti

| Katman | Dosya | Satır | Durum |
|--------|-------|-------|-------|
| **Models** | `app/models/explore.py` | 1,942 | ✅ SAĞLAM — 15 model, dokunulmayacak |
| **Models** | `app/models/backlog.py` | ~500 | ✅ SAĞLAM — BacklogItem, ConfigItem |
| **Services** | 7 dosya (lifecycle, permission, fit_propagation...) | ~1,861 | ✅ SAĞLAM — dokunulmayacak |
| **Blueprint** | `app/blueprints/explore_bp.py` | 3,671 | 🔴 **95 endpoint TEK dosya** — bölünecek |
| **Frontend API** | `static/js/explore-api.js` | 194 | ⚠️ Küçük düzeltmeler |
| **Frontend Views** | 5 dosya | 3,376 | ⚠️ workshop_detail yeniden yazılacak |
| **Tests** | `tests/test_workshop_integration_mapping.py` | ~500 | ✅ 24 test korunacak |

---

## KESİN KORUMA — Dokunulmayacak Dosyalar

| Dosya | Neden |
|-------|-------|
| `app/models/explore.py` (15 model) | Sağlam, tüm FK/relationship'ler doğru |
| `app/models/backlog.py` | BacklogItem + ConfigItem conversion hedefi |
| `app/services/requirement_lifecycle.py` | transition_requirement, convert, batch — çalışıyor |
| `app/services/open_item_lifecycle.py` | transition_open_item, reassign — çalışıyor |
| `app/services/fit_propagation.py` | propagate_fit_from_step, recalculate — çalışıyor |
| `app/services/permission.py` | RBAC — çalışıyor (skip_permission ile bypass) |
| `app/services/signoff.py` | L3 signoff — çalışıyor |
| `app/services/code_generator.py` | Auto-code gen — çalışıyor |
| `app/services/cloud_alm.py` | ALM sync — çalışıyor |
| `app/services/workshop_docs.py` | Doc generation — çalışıyor |
| `app/services/snapshot.py` | Snapshot capture — çalışıyor |

---

## FAZ 1: Backend Split (~4 prompt)

`explore_bp.py` (3,671 satır, 95 endpoint) → 7 dosya + `__init__.py`:

```
app/blueprints/explore/
├── __init__.py              # Blueprint registration, shared imports (~50 satır)
├── workshops.py             # 13 endpoint — CRUD + lifecycle (~700 satır)
├── process_levels.py        # 20 endpoint — Scope hierarchy (~870 satır)
├── process_steps.py         # 7 endpoint — Steps + fit decisions (~250 satır)
├── requirements.py          # 13 endpoint — Req CRUD + transitions (~550 satır)
├── open_items.py            # 8 endpoint — OI CRUD + transitions (~310 satır)
└── supporting.py            # 34 endpoint — Deps, flags, attachments, scope changes,
                             #   attendees, agenda, decisions, docs, snapshots (~820 satır)
```

### Kritik Kurallar
- URL prefix `/api/v1/explore` DEĞİŞMEYECEK
- Tüm endpoint path'leri birebir aynı kalacak
- Frontend'in hiçbir API çağrısı bozulmayacak
- `app/__init__.py` import: `from app.blueprints.explore import explore_bp`

### Endpoint Dağılımı

#### `workshops.py` — 13 endpoint

| # | Kaynak Satır | Method + Route | Fonksiyon |
|---|-------------|----------------|-----------|
| 1 | L1593 | GET `/workshops` | `list_workshops` |
| 2 | L1671 | GET `/workshops/<ws_id>` | `get_workshop` |
| 3 | L1695 | GET `/workshops/<ws_id>/full` | `get_workshop_full` |
| 4 | L1788 | POST `/workshops` | `create_workshop` |
| 5 | L1844 | PUT `/workshops/<ws_id>` | `update_workshop` |
| 6 | L1876 | GET `/workshops/<ws_id>/steps` | `list_workshop_steps` |
| 7 | L1914 | POST `/workshops/<ws_id>/start` | `start_workshop` |
| 8 | L1980 | POST `/workshops/<ws_id>/complete` | `complete_workshop` |
| 9 | L2049 | GET `/workshops/capacity` | `workshop_capacity` |
| 10 | L2091 | GET `/workshops/stats` | `workshop_stats` |
| 11 | L347 | POST `/workshops/<id>/reopen` | `reopen_workshop` |
| 12 | L392 | POST `/workshops/<id>/create-delta` | `create_delta_workshop` |
| 13 | L3512 | GET `/workshops/<ws_id>/sessions` | `list_workshop_sessions` |

#### `process_levels.py` — 20 endpoint

| # | Kaynak Satır | Method + Route | Fonksiyon |
|---|-------------|----------------|-----------|
| 1 | L799 | GET `/process-levels` | `list_process_levels` |
| 2 | L873 | POST `/process-levels/import-template` | `import_process_template` |
| 3 | L953 | POST `/process-levels/bulk` | `bulk_create_process_levels` |
| 4 | L1081 | POST `/process-levels` | `create_process_level` |
| 5 | L1157 | DELETE `/process-levels/<pl_id>` | `delete_process_level` |
| 6 | L1194 | GET `/process-levels/<pl_id>` | `get_process_level` |
| 7 | L1213 | PUT `/process-levels/<pl_id>` | `update_process_level` |
| 8 | L1250 | GET `/scope-matrix` | `get_scope_matrix` |
| 9 | L1286 | POST `/process-levels/<l3_id>/seed-from-catalog` | `seed_from_catalog` |
| 10 | L1346 | POST `/process-levels/<l3_id>/children` | `add_l4_child` |
| 11 | L1391 | POST `/process-levels/<l3_id>/consolidate-fit` | `consolidate_fit` |
| 12 | L1417 | GET `/process-levels/<l3_id>/consolidated-view` | `get_consolidated_view_endpoint` |
| 13 | L1429 | POST `/process-levels/<l3_id>/override-fit-status` | `override_fit_endpoint` |
| 14 | L1450 | POST `/process-levels/<l3_id>/signoff` | `signoff_endpoint` |
| 15 | L1472 | GET `/process-levels/l2-readiness` | `l2_readiness` |
| 16 | L1512 | POST `/process-levels/<l2_id>/confirm` | `confirm_l2` |
| 17 | L1547 | GET `/area-milestones` | `area_milestones` |
| 18 | L772 | GET `/process-levels/<pl_id>/change-history` | `get_process_level_change_history` |
| 19 | L3175 | GET `/process-levels/<level_id>/bpmn` | `get_bpmn` |
| 20 | L3189 | POST `/process-levels/<level_id>/bpmn` | `create_bpmn` |

#### `process_steps.py` — 7 endpoint

| # | Kaynak Satır | Method + Route | Fonksiyon |
|---|-------------|----------------|-----------|
| 1 | L2132 | PUT `/process-steps/<step_id>` | `update_process_step` |
| 2 | L2184 | POST `/process-steps/<step_id>/decisions` | `create_decision` |
| 3 | L2217 | POST `/process-steps/<step_id>/open-items` | `create_open_item` |
| 4 | L2257 | POST `/process-steps/<step_id>/requirements` | `create_requirement` |
| 5 | L3553 | GET `/workshops/<ws_id>/fit-decisions` | `list_fit_decisions` |
| 6 | L3575 | POST `/workshops/<ws_id>/fit-decisions` | `set_fit_decision_bulk` |
| 7 | L3608 | POST `/fit-propagation/propagate` | `run_fit_propagation` |

#### `requirements.py` — 13 endpoint

| # | Kaynak Satır | Method + Route | Fonksiyon |
|---|-------------|----------------|-----------|
| 1 | L2311 | GET `/requirements` | `list_requirements` |
| 2 | L2399 | POST `/requirements` | `create_requirement_flat` |
| 3 | L2435 | GET `/requirements/<req_id>` | `get_requirement` |
| 4 | L2456 | PUT `/requirements/<req_id>` | `update_requirement` |
| 5 | L2478 | POST `/requirements/<req_id>/transition` | `transition_requirement_endpoint` |
| 6 | L2513 | POST `/requirements/<req_id>/link-open-item` | `link_open_item` |
| 7 | L2548 | POST `/requirements/<req_id>/add-dependency` | `add_requirement_dependency` |
| 8 | L2585 | POST `/requirements/bulk-sync-alm` | `bulk_sync_alm` |
| 9 | L2604 | GET `/requirements/stats` | `requirement_stats` |
| 10 | L2727 | GET `/requirements/coverage-matrix` | `requirement_coverage_matrix` |
| 11 | L2784 | POST `/requirements/batch-transition` | `batch_transition_endpoint` |
| 12 | L2808 | POST `/requirements/<req_id>/convert` | `convert_requirement_endpoint` |
| 13 | L2828 | POST `/requirements/batch-convert` | `batch_convert_endpoint` |

#### `open_items.py` — 8 endpoint

| # | Kaynak Satır | Method + Route | Fonksiyon |
|---|-------------|----------------|-----------|
| 1 | L2861 | GET `/open-items` | `list_open_items` |
| 2 | L2940 | POST `/open-items` | `create_open_item_flat` |
| 3 | L2988 | GET `/open-items/<oi_id>` | `get_open_item` |
| 4 | L2999 | PUT `/open-items/<oi_id>` | `update_open_item` |
| 5 | L3020 | POST `/open-items/<oi_id>/transition` | `transition_open_item_endpoint` |
| 6 | L3052 | POST `/open-items/<oi_id>/reassign` | `reassign_open_item_endpoint` |
| 7 | L3080 | POST `/open-items/<oi_id>/comments` | `add_comment` |
| 8 | L3107 | GET `/open-items/stats` | `open_item_stats` |

#### `supporting.py` — 34 endpoint

| Grup | Endpoint Sayısı |
|------|----------------|
| Health | 1 |
| Workshop Dependencies | 3 |
| Cross-Module Flags | 3 |
| Attachments | 4 |
| Scope Change Requests | 5 |
| Documents / Minutes | 4 |
| Attendees | 4 |
| Agenda Items | 4 |
| Decisions | 3 |
| Snapshots / Reports | 3 |

### Prompt Sıralaması

| Prompt | Kapsam | ~Satır |
|--------|--------|--------|
| **F1-1** | `__init__.py` + `workshops.py` (13 endpoint) | ~750 |
| **F1-2** | `process_levels.py` (20 endpoint) | ~870 |
| **F1-3** | `process_steps.py` + `requirements.py` (20 endpoint) | ~800 |
| **F1-4** | `open_items.py` + `supporting.py` (42 endpoint) + `app/__init__.py` güncelleme + eski dosya silme | ~1,180 |

Her prompt sonunda: `python -m pytest tests/test_workshop_integration_mapping.py` → 24 passed, 1 skipped beklenir.

---

## FAZ 2: Frontend Workshop Detail Yeniden Yazımı (~2 prompt)

`explore_workshop_detail.js` (768 satır) — sıfırdan yazılacak.

### Nedenler
- Over-fetching: tüm OI/Req çekip client-side filter
- `fitDecisions.update` → yanlış endpoint'e gidiyor
- `createDeltaWorkshop` yanlış field adı gönderiyor
- `sessions` verisi çekiliyor ama hiç render edilmiyor
- `flagStep` no-op

### Prompt Sıralaması

| Prompt | Kapsam |
|--------|--------|
| **F2-1** | Core: fetchAll, renderHeader, renderStepList, renderProcessStepCard, renderStepExpanded, inline forms, setFitDecision, transitionWorkshop |
| **F2-2** | Tabs: Agenda, Attendees, Sessions, Documents, L3 Summary + deltaWorkshop |

### Temel Değişiklikler
1. `openItems.list(pid)` → `openItems.list(pid, {workshop_id: wsId})` — backend zaten filter destekliyor
2. `requirements.list(pid)` → `requirements.list(pid, {workshop_id: wsId})` — backend zaten filter destekliyor
3. Tüm field referansları model-canonical yapılacak (`process_step_id`, `fit_decision`, `step_id`)
4. `fitDecisions.update` → `fitDecisions.create` (aynı endpoint upsert yapıyor)
5. `sessions` render'ı eklenmeli veya fetch kaldırılmalı
6. `flagStep` → `crossModuleFlags.create` entegrasyonu

---

## FAZ 3: Frontend API ve Diğer View Düzeltmeleri (~2 prompt)

| Prompt | Kapsam |
|--------|--------|
| **F3-1** | `explore-api.js` — sessions routing fix, fitDecisions.update fix, delete no-op'ları temizle |
| **F3-2** | `explore_requirements.js` — field adı tutarlılığı, assignee düzeltmesi + `explore_workshops.js` — create payload field fix |

`explore_hierarchy.js` ve `explore_dashboard.js` → **bu fazda dokunulmaz**. Scope hierarchy ve dashboard fonksiyonelliği mevcut haliyle çalışıyor.

---

## FAZ 4: Test & Stabilize (~1 prompt)

| Prompt | Kapsam |
|--------|--------|
| **F4-1** | Tüm endpoint'lerin curl testi, JS syntax check, mevcut 24 test'in korunması, smoke test |

---

## Risk Analizi

| Risk | Etki | Mitigasyon |
|------|------|-----------|
| Backend split sırasında import bozulması | Yüksek | Her prompt sonunda test + python import check |
| Frontend'in eski endpoint path'leri bozulması | Orta | URL prefix'ler birebir korunuyor |
| Circular import (explore/ paketi) | Düşük | Her module kendi import'larını yapar |
| Test'lerin kırılması | Yüksek | Her prompt sonunda 24 test doğrulaması |

---

## Toplam Tahmini Efor

| Faz | Prompt Sayısı | ~Süre |
|-----|---------------|-------|
| Faz 1: Backend Split | 4 | ~2-3 saat |
| Faz 2: Workshop Detail Rewrite | 2 | ~1-1.5 saat |
| Faz 3: API + View Fixes | 2 | ~1 saat |
| Faz 4: Test & Stabilize | 1 | ~30 dk |
| **TOPLAM** | **9 prompt** | **~5-6 saat** |

---

## SENARYO KAPSAMIYLA EŞLEŞTİRME

WORKSHOP_SCENARIO_v2 sahneleriyle mevcut model/kod karşılaştırması:

| Sahne | Durum | Bu rebuild'de ne oluyor |
|-------|-------|------------------------|
| S0: Governance | ⚠️ Tablo yok | Bu fazda kapsam dışı — doküman olarak yönetilir |
| S1: Workshop Oluştur | ✅ Model + endpoint var | Faz 1'de workshops.py'e taşınır |
| S2: Scope Atama + Step Üretimi | ✅ start_workshop + WorkshopScopeItem | Faz 1'de workshops.py'e taşınır |
| S3: Katılımcı + Gündem | ✅ Attendee + AgendaItem tam | Faz 1'de supporting.py'e taşınır |
| S4: Workshop Başlatma | ✅ start_workshop endpoint | Faz 1'de workshops.py'e taşınır |
| S5: Fit-to-Standard Döngüsü | ✅ ProcessStep + fit_decision | Faz 1: process_steps.py, Faz 2: workshop detail rewrite |
| S6: Decision/OI/Req Oluşturma | ✅ Inline form'lar + endpoint'ler | Faz 1: process_steps.py, Faz 2: inline form rewrite |
| S7: Gün Sonu Summary | ✅ workshop_docs + documents | Faz 1: supporting.py'e taşınır |
| S8: Complete + Quality Gate | ⚠️ Complete var, quality gate yok | Faz 1: workshops.py. Quality gate ileride eklenebilir |
| S9: OI + Req Lifecycle | ✅ Lifecycle services tam | Faz 1: requirements.py + open_items.py |
| S10: WRICEF/Config Conversion | ✅ convert_requirement service | Faz 1: requirements.py |
| S11: ALM Push | ✅ cloud_alm service | Faz 1: requirements.py (bulk-sync-alm) |
| S12: Reopen | ✅ reopen endpoint | Faz 1: workshops.py |
| S13: Delta Workshop | ✅ create-delta endpoint | Faz 1: workshops.py |
| S14: Dashboard | ✅ Mevcut | Bu fazda dokunulmaz |
