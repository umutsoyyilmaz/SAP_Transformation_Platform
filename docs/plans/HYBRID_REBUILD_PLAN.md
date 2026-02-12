# Hibrit Cerrahi Rebuild Planı — Workshop Module

**Tarih:** 2026-02-12
**Yaklaşım:** Copilot Backend Split + Claude Frontend Rebuild + Enhancement Layer
**Toplam:** 11 prompt, ~6-7 saat

---

## Felsefe

| Katman | Strateji | Risk |
|--------|----------|------|
| **Backend Split** | Copilot'un cerrahi yaklaşımı — mevcut kodu birebir böl | 🟢 Düşük |
| **Backend Enhancement** | Claude'un yeni endpoint'leri ve business rule fix'leri | 🟡 Orta |
| **Frontend Rebuild** | Claude'un sıfırdan yazımı — critical bug fix'ler | 🟡 Orta |
| **Modeller** | DOKUNULMAZ | — |
| **Servisler** | DOKUNULMAZ | — |

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
| `app/blueprints/explore_bp.py` | FAZ 1 süresince KORUNUR — R-7'de silinir |
| `tests/test_workshop_integration_mapping.py` | 24 test — her prompt sonunda korunmalı |

---

## FAZ 1: Backend Split (4 prompt) — Copilot Cerrahi Yaklaşımı

> **Prensip:** Mevcut `explore_bp.py` (3,671 satır, 95 endpoint) → 7 dosyaya BİREBİR BÖLÜNÜR.
> Mantığa DOKUNULMAZ. Sadece dosya organizasyonu.

### Hedef Yapı

```
app/blueprints/explore/
├── __init__.py              # Blueprint registration, shared imports (~50 satır)
├── workshops.py             # 23 endpoint — CRUD + lifecycle + attendees + agenda + decisions + sessions
├── process_levels.py        # 20 endpoint — Scope hierarchy, signoff, readiness, BPMN
├── process_steps.py         # 7 endpoint  — Steps + fit decisions + propagation
├── requirements.py          # 13 endpoint — Req CRUD + transitions + conversion + ALM
├── open_items.py            # 8 endpoint  — OI CRUD + transitions + reassign
└── supporting.py            # 24 endpoint — Health, deps, flags, attachments, scope changes, docs, snapshots
```

### Kritik Kurallar (TÜM Faz 1 Prompt'ları İçin)

1. **Modellere DOKUNMA** — `app/models/explore.py` değişmeyecek
2. **Servislere DOKUNMA** — `app/services/` altındaki dosyalar değişmeyecek
3. **Her yeni dosya** `explore_bp` kullanacak (aynı blueprint, farklı dosya)
4. **URL prefix** aynı kalacak: `/api/v1/explore`
5. **Tüm endpoint fonksiyon isimleri** aynı kalacak (mevcut testler bozulmasın)
6. **Tüm endpoint route path'leri** aynı kalacak (frontend bozulmasın)
7. **`skip_permission=True`** tüm lifecycle transition çağrılarında kullanılacak
8. **Her prompt sonrası** doğrulama: `cd tests && python -m pytest --tb=short -q` → 24 passed, 1 skipped
9. **Eski dosya** (`explore_bp.py`) R-7'ye kadar SİLİNMEZ

### Blueprint Kaydı

Tüm sub-module'lar `explore_bp` isimli TEK blueprint'e endpoint ekler:

```python
# app/blueprints/explore/__init__.py
from flask import Blueprint
explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")

from app.blueprints.explore import workshops       # noqa
from app.blueprints.explore import process_levels   # noqa
from app.blueprints.explore import process_steps    # noqa
from app.blueprints.explore import requirements     # noqa
from app.blueprints.explore import open_items       # noqa
from app.blueprints.explore import supporting       # noqa
```

`app/__init__.py` değişikliği (R-7'de):
```python
# ESKİ: from app.blueprints.explore_bp import explore_bp
# YENİ: from app.blueprints.explore import explore_bp
```

---

### Prompt F1-1: `__init__.py` + `workshops.py` (23 endpoint)

**Amaç:** Paket oluştur, blueprint tanımla, workshop endpoint'lerini taşı.

**Kopyalanacak fonksiyonlar (kaynak: `explore_bp.py`):**

| # | Fonksiyon | Satır | Route |
|---|-----------|-------|-------|
| 1 | `list_workshops()` | L1593 | GET `/workshops` |
| 2 | `get_workshop(ws_id)` | L1671 | GET `/workshops/<ws_id>` |
| 3 | `get_workshop_full(ws_id)` | L1695 | GET `/workshops/<ws_id>/full` |
| 4 | `create_workshop()` | L1788 | POST `/workshops` |
| 5 | `update_workshop(ws_id)` | L1844 | PUT `/workshops/<ws_id>` |
| 6 | `list_workshop_steps(ws_id)` | L1876 | GET `/workshops/<ws_id>/steps` |
| 7 | `start_workshop(ws_id)` | L1914 | POST `/workshops/<ws_id>/start` |
| 8 | `complete_workshop(ws_id)` | L1980 | POST `/workshops/<ws_id>/complete` |
| 9 | `workshop_capacity()` | L2049 | GET `/workshops/capacity` |
| 10 | `workshop_stats()` | L2091 | GET `/workshops/stats` |
| 11 | `reopen_workshop(id)` | L347 | POST `/workshops/<id>/reopen` |
| 12 | `create_delta_workshop(id)` | L392 | POST `/workshops/<id>/create-delta` |
| 13 | `list_workshop_sessions(ws_id)` | L3512 | GET `/workshops/<ws_id>/sessions` |
| 14 | `list_attendees(ws_id)` | L3289 | GET `/workshops/<ws_id>/attendees` |
| 15 | `create_attendee(ws_id)` | L3296 | POST `/workshops/<ws_id>/attendees` |
| 16 | `update_attendee(att_id)` | L3318 | PUT `/attendees/<att_id>` |
| 17 | `delete_attendee(att_id)` | L3332 | DELETE `/attendees/<att_id>` |
| 18 | `list_agenda_items(ws_id)` | L3347 | GET `/workshops/<ws_id>/agenda-items` |
| 19 | `create_agenda_item(ws_id)` | L3359 | POST `/workshops/<ws_id>/agenda-items` |
| 20 | `update_agenda_item(item_id)` | L3389 | PUT `/agenda-items/<item_id>` |
| 21 | `delete_agenda_item(item_id)` | L3410 | DELETE `/agenda-items/<item_id>` |
| 22 | `list_workshop_decisions(ws_id)` | L3425 | GET `/workshops/<ws_id>/decisions` |
| 23 | `update_decision(dec_id)` | L3438 | PUT `/decisions/<dec_id>` |

**Ayrıca kopyala:** `_parse_date_input()` helper (satır 139-155)

**Tek değişiklik:** `start_workshop()` ve `complete_workshop()` içinde `transition_open_item` veya `transition_requirement` çağrısı varsa → `skip_permission=True` ekle.

**Import bloğu:**
```python
"""Explore — Workshop endpoints: CRUD, lifecycle, attendees, agenda, sessions."""
from datetime import datetime, timezone
from flask import jsonify, request
from sqlalchemy import func, or_
from app.models import db
from app.models.explore import (
    ExploreDecision, ExploreOpenItem, ExploreRequirement,
    ExploreWorkshop, ProcessLevel, ProcessStep,
    WorkshopAttendee, WorkshopAgendaItem, WorkshopRevisionLog,
    WorkshopScopeItem, _uuid, _utcnow,
)
from app.services.code_generator import generate_workshop_code
from app.services.fit_propagation import (
    get_fit_summary, recalculate_project_hierarchy,
    workshop_completion_propagation,
)
from app.services.permission import PermissionDenied
from app.blueprints.explore import explore_bp
```

**Doğrulama:**
```bash
python -c "from app.blueprints.explore.workshops import *; print('OK')"
# Not: Henüz olmayan modüllerin __init__.py import satırlarını geçici yorum yap
```

---

### Prompt F1-2: `process_levels.py` (20 endpoint)

**Amaç:** Scope hierarchy endpoint'lerini taşı.

**Kopyalanacak fonksiyonlar:**

| # | Fonksiyon | Satır | Route |
|---|-----------|-------|-------|
| 1 | `list_process_levels()` | L799 | GET `/process-levels` |
| 2 | `import_process_template()` | L873 | POST `/process-levels/import-template` |
| 3 | `bulk_create_process_levels()` | L953 | POST `/process-levels/bulk` |
| 4 | `create_process_level()` | L1081 | POST `/process-levels` |
| 5 | `delete_process_level(pl_id)` | L1157 | DELETE `/process-levels/<pl_id>` |
| 6 | `get_process_level(pl_id)` | L1194 | GET `/process-levels/<pl_id>` |
| 7 | `update_process_level(pl_id)` | L1213 | PUT `/process-levels/<pl_id>` |
| 8 | `get_scope_matrix()` | L1250 | GET `/scope-matrix` |
| 9 | `seed_from_catalog(l3_id)` | L1286 | POST `/process-levels/<l3_id>/seed-from-catalog` |
| 10 | `add_l4_child(l3_id)` | L1346 | POST `/process-levels/<l3_id>/children` |
| 11 | `consolidate_fit(l3_id)` | L1391 | POST `/process-levels/<l3_id>/consolidate-fit` |
| 12 | `get_consolidated_view_endpoint(l3_id)` | L1417 | GET `/process-levels/<l3_id>/consolidated-view` |
| 13 | `override_fit_endpoint(l3_id)` | L1429 | POST `/process-levels/<l3_id>/override-fit-status` |
| 14 | `signoff_endpoint(l3_id)` | L1450 | POST `/process-levels/<l3_id>/signoff` |
| 15 | `l2_readiness()` | L1472 | GET `/process-levels/l2-readiness` |
| 16 | `confirm_l2(l2_id)` | L1512 | POST `/process-levels/<l2_id>/confirm` |
| 17 | `area_milestones()` | L1547 | GET `/area-milestones` |
| 18 | `get_process_level_change_history(pl_id)` | L772 | GET `/process-levels/<pl_id>/change-history` |
| 19 | `get_bpmn(level_id)` | L3175 | GET `/process-levels/<level_id>/bpmn` |
| 20 | `create_bpmn(level_id)` | L3189 | POST `/process-levels/<level_id>/bpmn` |

**Ayrıca kopyala:** `_get_l3_consolidated_view(l3)` helper ve kullandığı diğer helper fonksiyonlar.

**Import bloğu:**
```python
"""Explore — Process Level endpoints: hierarchy, scope, signoff, readiness, BPMN."""
from flask import jsonify, request
from sqlalchemy import func, and_
from app.models import db
from app.models.explore import (
    ProcessLevel, ProcessStep, WorkshopScopeItem, ExploreWorkshop,
    ExploreDecision, ExploreOpenItem, ExploreRequirement,
    ScopeChangeLog, _uuid, _utcnow,
)
from app.services.signoff import signoff_l3
from app.services.permission import PermissionDenied
from app.blueprints.explore import explore_bp
```

**Doğrulama:** `python -c "from app.blueprints.explore.process_levels import *; print('OK')"`

---

### Prompt F1-3: `process_steps.py` + `requirements.py` (20 endpoint)

**Amaç:** ProcessStep ve Requirement endpoint'lerini taşı.

**process_steps.py — 7 endpoint:**

| # | Fonksiyon | Satır | Route |
|---|-----------|-------|-------|
| 1 | `update_process_step(step_id)` | L2132 | PUT `/process-steps/<step_id>` |
| 2 | `create_decision(step_id)` | L2184 | POST `/process-steps/<step_id>/decisions` |
| 3 | `create_open_item(step_id)` | L2217 | POST `/process-steps/<step_id>/open-items` |
| 4 | `create_requirement(step_id)` | L2257 | POST `/process-steps/<step_id>/requirements` |
| 5 | `list_fit_decisions(ws_id)` | L3553 | GET `/workshops/<ws_id>/fit-decisions` |
| 6 | `set_fit_decision_bulk(ws_id)` | L3575 | POST `/workshops/<ws_id>/fit-decisions` |
| 7 | `run_fit_propagation()` | L3608 | POST `/fit-propagation/propagate` |

**requirements.py — 13 endpoint:**

| # | Fonksiyon | Satır | Route |
|---|-----------|-------|-------|
| 1 | `list_requirements()` | L2311 | GET `/requirements` |
| 2 | `create_requirement_flat()` | L2399 | POST `/requirements` |
| 3 | `get_requirement(req_id)` | L2435 | GET `/requirements/<req_id>` |
| 4 | `update_requirement(req_id)` | L2456 | PUT `/requirements/<req_id>` |
| 5 | `transition_requirement_endpoint(req_id)` | L2478 | POST `/requirements/<req_id>/transition` |
| 6 | `link_open_item(req_id)` | L2513 | POST `/requirements/<req_id>/link-open-item` |
| 7 | `add_requirement_dependency(req_id)` | L2548 | POST `/requirements/<req_id>/add-dependency` |
| 8 | `bulk_sync_alm()` | L2585 | POST `/requirements/bulk-sync-alm` |
| 9 | `requirement_stats()` | L2604 | GET `/requirements/stats` |
| 10 | `requirement_coverage_matrix()` | L2727 | GET `/requirements/coverage-matrix` |
| 11 | `batch_transition_endpoint()` | L2784 | POST `/requirements/batch-transition` |
| 12 | `convert_requirement_endpoint(req_id)` | L2808 | POST `/requirements/<req_id>/convert` |
| 13 | `batch_convert_endpoint()` | L2828 | POST `/requirements/batch-convert` |

**İmport'lar (her dosya için ayrı blok).**

**Doğrulama:**
```bash
python -c "from app.blueprints.explore.process_steps import *; print('OK')"
python -c "from app.blueprints.explore.requirements import *; print('OK')"
```

---

### Prompt F1-4: `open_items.py` + `supporting.py` + Switch & Cleanup

**Amaç:** Kalan endpoint'leri taşı, `app/__init__.py`'yi güncelle, eski dosyayı sil.

**open_items.py — 8 endpoint:**

| # | Fonksiyon | Satır | Route |
|---|-----------|-------|-------|
| 1 | `list_open_items()` | L2861 | GET `/open-items` |
| 2 | `create_open_item_flat()` | L2940 | POST `/open-items` |
| 3 | `get_open_item(oi_id)` | L2988 | GET `/open-items/<oi_id>` |
| 4 | `update_open_item(oi_id)` | L2999 | PUT `/open-items/<oi_id>` |
| 5 | `transition_open_item_endpoint(oi_id)` | L3020 | POST `/open-items/<oi_id>/transition` |
| 6 | `reassign_open_item_endpoint(oi_id)` | L3052 | POST `/open-items/<oi_id>/reassign` |
| 7 | `add_comment(oi_id)` | L3080 | POST `/open-items/<oi_id>/comments` |
| 8 | `open_item_stats()` | L3107 | GET `/open-items/stats` |

**supporting.py — 24 endpoint:**

| Grup | Endpoint'ler |
|------|-------------|
| Health | `health_check()` — GET `/health` |
| Dependencies | 3 endpoint — CRUD |
| Cross-Module Flags | 3 endpoint — CRUD |
| Attachments | 4 endpoint — upload, list, download, delete |
| Scope Change Requests | 5 endpoint — request, list, approve, reject, history |
| Documents / Minutes | 4 endpoint — generate, list, get, ai-summary |
| Snapshots | 3 endpoint — capture, list, compare |

**Switch (bu prompt'un son adımı):**

1. `app/__init__.py`'de import değiştir:
```python
# ESKİ:
from app.blueprints.explore_bp import explore_bp
# YENİ:
from app.blueprints.explore import explore_bp
```

2. `__init__.py`'deki tüm import yorum satırlarını kaldır (R-1'de geçici yorum yapılmışsa).

3. Eski dosyayı sil:
```bash
rm app/blueprints/explore_bp.py
```

**Final Doğrulama:**
```bash
# Import check
python -c "from app.blueprints.explore import explore_bp; print('Endpoints:', len(explore_bp.deferred_functions))"

# Tüm testler
cd tests && python -m pytest --tb=short -q
# Beklenen: 24 passed, 1 skipped
```

---

## FAZ 2: Backend Enhancement (2 prompt) — Claude Business Rule Fix'leri

> **Prensip:** Faz 1'de birebir taşınan endpoint'lere YENİ fonksiyonellik ve bug fix'ler eklenir.
> Mevcut endpoint'ler bozulmaz, sadece zenginleştirilir veya yeni endpoint'ler eklenir.

### Prompt F2-1: Workshop Lifecycle Enhancement

**Dosya:** `app/blueprints/explore/workshops.py`

**Değişiklikler:**

1. **`start_workshop()` enhancement — ProcessStep auto-creation:**
   - Mevcut davranış: WorkshopScopeItem'lardan step oluşturuyor ✅
   - Eklenecek: Scope item yoksa 400 hatası + açıklayıcı mesaj
   - Eklenecek: WorkshopRevisionLog kaydı (action="started")

2. **`complete_workshop()` enhancement — Quality Gate Warnings:**
   - Mevcut davranış: status → completed ✅
   - Eklenecek: Response'a `warnings` array ekle:
     ```json
     {
       "workshop": { ... },
       "warnings": [
         "3 process steps henüz değerlendirilmedi (pending)",
         "2 open item hala açık",
         "1 gap decision escalate edilmemiş"
       ]
     }
     ```
   - Uyarılar BLOKLAMAYACak — sadece bilgi amaçlı
   - Eklenecek: `fit_propagation` çağrısı sadece `session_number == total_sessions` ise (final session)

3. **`reopen_workshop()` enhancement:**
   - Eklenecek: `reopen_reason` zorunlu kontrolü (400 if missing)
   - Eklenecek: `reopen_count` increment
   - Eklenecek: WorkshopRevisionLog kaydı

4. **`create_delta_workshop()` enhancement:**
   - Eklenecek: Delta code generation: `WS-SD-01` → `WS-SD-01A` (letter suffix)
   - Eklenecek: `original_workshop_id` link

5. **YENİ endpoint — `list_workshop_steps(ws_id)`:**
   - GET `/workshops/<ws_id>/steps` zaten var, ama processStep'lerin L3 parent bilgisiyle döndüğünden emin ol
   - Response'a `process_level_name`, `process_level_code` ekle

**Doğrulama:** Mevcut 24 test + yeni endpoint'lerin curl testi.

---

### Prompt F2-2: Items & Links Enhancement

**Dosyalar:** `process_steps.py`, `requirements.py`, `open_items.py`

**Değişiklikler:**

1. **`create_decision(step_id)` — process_steps.py:**
   - Mevcut: step_id'den decision oluşturuyor ✅
   - Eklenecek: Auto code generation → `DEC-{seq:03d}`
   - Eklenecek: Supersede logic — aynı step'te yeni decision → eski → "superseded"

2. **`create_open_item(step_id)` — process_steps.py:**
   - Mevcut: step_id'den OI oluşturuyor ✅
   - Eklenecek: Auto code generation → `OI-{seq:03d}`
   - Eklenecek: `is_overdue` ve `aging_days` computed field'lar response'da

3. **`create_requirement(step_id)` — process_steps.py:**
   - Mevcut: step_id'den requirement oluşturuyor ✅
   - Eklenecek: Auto code generation → `REQ-{seq:03d}`

4. **`transition_requirement_endpoint()` — requirements.py:**
   - Mevcut: lifecycle transition var ✅
   - Eklenecek: **`approve` guard** — blocking OI varsa approve engellenir:
     ```python
     if action == "approve":
         blocking_ois = RequirementOpenItemLink.query.filter_by(
             requirement_id=req_id, link_type="blocks"
         ).join(ExploreOpenItem).filter(
             ExploreOpenItem.status.in_(["open", "in_progress"])
         ).count()
         if blocking_ois > 0:
             return jsonify({"error": f"{blocking_ois} blocking OI(s) still open"}), 409
     ```

5. **`convert_requirement_endpoint()` — requirements.py:**
   - Mevcut: convert service çağrısı var ✅
   - Eklenecek: WRICEF type mapping doğrulaması:
     - gap + type=integration → BacklogItem(wricef_type="I")
     - gap + type=reporting → BacklogItem(wricef_type="R")
     - gap + type=form → BacklogItem(wricef_type="F")
     - gap + type=workflow → BacklogItem(wricef_type="W")
     - gap + type=conversion → BacklogItem(wricef_type="C")
     - gap + type=enhancement → BacklogItem(wricef_type="E")
     - fit/partial + type=configuration → ConfigItem

6. **Requirement↔OI Link endpoint'inde `link_type` validasyonu:**
   - Sadece `"blocks"` ve `"related"` kabul et

**Doğrulama:** 24 test + conversion curl testi.

---

## FAZ 3: Frontend Workshop Detail Yeniden Yazımı (2 prompt)

> **Prensip:** `explore_workshop_detail.js` (768 satır) SIFIRDAN yazılır.
> Mevcut dosya yedeklenir, yeni dosya clean implementation.

### Mevcut Bug'lar (Neden Yeniden Yazım Gerekli)

| # | Bug | Etki |
|---|-----|------|
| 1 | `fitDecisions.update(pid, stepId, data)` → yanlış endpoint | Fit kararları kaydedilmiyor |
| 2 | Decision/OI/Req oluşturmada `process_step_id` context kaybı | Orphan item'lar |
| 3 | `openItems.list(pid)` → tüm proje OI'larını çekip client filter | Performans |
| 4 | `sessions` verisi çekilip render edilmiyor | Gereksiz API çağrısı |
| 5 | `flagStep` fonksiyonu no-op | Flag özelliği çalışmıyor |
| 6 | `createDeltaWorkshop` yanlış field adı | Delta oluşturma bozuk |
| 7 | Reopen endpoint mapping yok | Reopen çalışmıyor |

### Prompt F3-1: Workshop Detail — Core

**Dosya:** `static/js/explore_workshop_detail.js` (yeniden yazılacak)

**Sayfa Yapısı:**
```
┌─────────────────────────────────────────────────────────┐
│ ← Back  │  WS-SD-01  │  Status Badge  │ [▶ Start] [⋮] │  HEADER
├─────────────────────────────────────────────────────────┤
│ 12/18 assessed │ 7 fit │ 3 gap │ 8 dec │ 3 OI │ 2 req │  KPI STRIP
├─────────────────────────────────────────────────────────┤
│ [Steps] [Decisions] [Open Items] [Requirements] [+more] │  TABS
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ L3: Order to Cash ─────────────────────────────┐   │
│  │  Step 1: Create Sales Order    [Fit] [P] [Gap]  │   │
│  │  Step 2: Pricing               [Fit] [P] [Gap]  │   │
│  │  ► Expand → notes, demo, decisions, OIs, reqs   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ L3: Procure to Pay ────────────────────────────┐   │
│  │  Step 3: Purchase Requisition  [Fit] [P] [Gap]  │   │
│  │  ...                                             │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Data Loading — TEK API çağrısı:**
```javascript
const _ws = await ExploreAPI.workshops.getFull(pid, wsId);
// İçerik: workshop, steps, decisions, open_items, requirements, attendees, agenda, documents
```

**Implementasyon detayları:**

1. **`fetchAll()`** — `ExploreAPI.workshops.getFull()` çağırır, `_ws` objesine atar
2. **`renderHeader()`** — code, name, status badge, action buttons (Start/Complete/Reopen/Delta)
3. **`renderKPIStrip()`** — assessed/fit/partial/gap/dec/oi/req sayıları (computed from _ws.steps)
4. **`renderStepList()`** — L3'e göre grouped step cards
5. **`renderProcessStepCard(step)`** — inline fit decision buttons (sadece in_progress'te)
6. **`renderStepExpanded(step)`** — notes, checkboxes (demo_shown, bpmn_reviewed), inline items
7. **Inline forms:** Decision, OI, Requirement (expandable panel inside step)
8. **`setFitDecision(stepId, decision)`**:
   - `ExploreAPI.fitDecisions.create(pid, wsId, [{step_id: stepId, fit_decision: decision}])`
   - Local state update + KPI strip recalc (partial re-render, not full refresh)
   - Gap/Partial → "Create requirement?" dialog
9. **Lifecycle transitions:**
   - `startWorkshop()` → scope items check, confirm, `ExploreAPI.workshops.start(pid, wsId)`
   - `completeWorkshop()` → `ExploreAPI.workshops.complete(pid, wsId)`, show warnings
   - `reopenWorkshop()` → prompt for reopen_reason, `ExploreAPI.workshops.reopen(pid, wsId, {reopen_reason})`
   - `createDelta()` → `ExploreAPI.workshops.createDelta(pid, wsId)`

**Critical field mappings:**
```javascript
// DOĞRU field adları (model canonical):
step.fit_decision       // "fit" | "partial_fit" | "gap" | "pending"
step.process_level_id   // FK → ProcessLevel (L4)
step.id                 // ProcessStep UUID
decision.process_step_id // FK → ProcessStep
oi.process_step_id      // FK → ProcessStep (nullable)
req.process_step_id     // FK → ProcessStep (nullable)
```

---

### Prompt F3-2: Workshop Detail — Tabs + Delta

**Dosya:** `static/js/explore_workshop_detail.js` (devamı)

**Tab implementasyonları:**

1. **Decisions Tab:**
   - Tablo: code, text, category, decided_by, status, step_name
   - Filter: `_ws.decisions` array'i (zaten yüklü)

2. **Open Items Tab:**
   - Tablo: code, title, priority badge, status badge, assignee, due_date, is_overdue
   - Filter: `_ws.open_items` array'i
   - Inline transition buttons: open → in_progress → close

3. **Requirements Tab:**
   - Tablo: code, title, type badge, priority badge, complexity, status
   - Filter: `_ws.requirements` array'i
   - Inline transition + convert button

4. **Agenda Tab:**
   - List: time, title, duration_minutes, type badge
   - CRUD: add/edit/delete agenda items

5. **Attendees Tab:**
   - List: name, role, organization, attendance_status toggle
   - CRUD: add/edit/delete attendees

6. **Sessions Tab:**
   - List: session cards (session_number, date, status)
   - Navigate to session workshop on click

7. **L3 Summary:**
   - L3'lere göre aggregate: toplam step, fit/partial/gap, completion %

8. **Delta Workshop:**
   - `createDeltaWorkshop()` → navigate to new workshop detail

---

## FAZ 4: Frontend API + Diğer View Düzeltmeleri (2 prompt)

### Prompt F4-1: `explore-api.js` Düzeltmeleri

**Dosya:** `static/js/explore-api.js`

**Değişiklikler:**

| # | Bug | Mevcut | Düzeltme |
|---|-----|--------|----------|
| 1 | sessions routing | `workshops.sessions()` route yanlış/eksik | Doğru route: GET `/workshops/${wsId}/sessions` |
| 2 | fitDecisions.update | `PUT /fit-decisions/${stepId}` | `POST /workshops/${wsId}/fit-decisions` (bulk upsert) |
| 3 | delete no-op'lar | Bazı delete fonksiyonları tanımlı ama çağrılmıyor | Temizle veya bağla |
| 4 | processSteps namespace | Yok | **YENİ** — `ExploreAPI.processSteps.list(pid, wsId)` ekle |
| 5 | workshops.reopen | Yok/eksik | `ExploreAPI.workshops.reopen(pid, wsId, data)` ekle |
| 6 | workshops.createDelta | Yanlış field | `ExploreAPI.workshops.createDelta(pid, wsId)` düzelt |

**Yeni API namespace yapısı:**
```javascript
ExploreAPI = {
  workshops: {
    list, get, getFull, create, update, delete,
    start, complete, reopen, createDelta,
    stats, capacity, sessions
  },
  scopeItems: { list, assign, remove },
  processSteps: { list, update },           // YENİ
  fitDecisions: { list, create },            // create = bulk upsert
  decisions: { list, update, delete },
  openItems: { list, get, create, update, transition, reassign, addComment, stats },
  requirements: { list, get, create, update, transition, convert, batchConvert, linkOI, stats },
  attendees: { list, create, update, delete },
  agenda: { list, create, update, delete },
  documents: { list, get, generate, aiSummary },
}
```

---

### Prompt F4-2: View Dosyası Düzeltmeleri

**Dosyalar:**

1. **`explore_requirements.js`:**
   - Field adı tutarlılığı: `assignee` → `assignee_id` veya model canonical
   - Status badge renk mapping'i düzelt

2. **`explore_workshops.js` (hub/list):**
   - Create payload field fix: `process_area` → doğru field adı
   - Workshop card'larda progress bar hesaplaması düzelt

**Dokunulmayacak:**
- `explore_hierarchy.js` — scope hierarchy çalışıyor
- `explore_dashboard.js` — dashboard çalışıyor

---

## FAZ 5: Test & Stabilize (1 prompt)

### Prompt F5-1: Smoke Test & Doğrulama

1. **Backend doğrulama:**
   ```bash
   # Tüm modüller import edilebilir mi?
   python -c "from app.blueprints.explore import explore_bp; print('Total endpoints:', len(explore_bp.deferred_functions))"

   # Mevcut testler
   cd tests && python -m pytest --tb=short -q
   # Beklenen: 24 passed, 1 skipped
   ```

2. **Endpoint smoke test (curl):**
   - Workshop CRUD cycle: create → start → fit decision → complete
   - OI lifecycle: create → transition → close
   - Requirement lifecycle: create → approve → convert
   - Delta workshop creation
   - Reopen with reason

3. **Frontend syntax check:**
   ```bash
   # JS syntax validation
   node --check static/js/explore_workshop_detail.js
   node --check static/js/explore-api.js
   node --check static/js/explore_workshops.js
   node --check static/js/explore_requirements.js
   ```

4. **Cross-check: Tüm frontend API çağrıları → backend endpoint eşleşmesi**

---

## SENARYO KAPSAMIYLA EŞLEŞTİRME

WORKSHOP_SCENARIO_v2 sahneleriyle mevcut model/kod karşılaştırması:

| Sahne | Faz 1 (Split) | Faz 2 (Enhance) | Faz 3-4 (Frontend) |
|-------|---------------|------------------|---------------------|
| S0: Governance | — | — | — (kapsam dışı, doküman) |
| S1: Workshop Oluştur | workshops.py | — | F3-1 create UI |
| S2: Scope + Step Üretimi | workshops.py | F2-1 start enhancement | F3-1 start flow |
| S3: Katılımcı + Gündem | workshops.py | — | F3-2 tabs |
| S4: Workshop Başlatma | workshops.py | F2-1 start enhancement | F3-1 transition |
| S5: Fit-to-Standard | process_steps.py | — | F3-1 fit buttons |
| S6: Decision/OI/Req | process_steps.py | F2-2 code gen + guards | F3-1 inline forms |
| S7: Gün Sonu Summary | supporting.py | — | F3-2 documents tab |
| S8: Complete + QGate | workshops.py | F2-1 quality gate warnings | F3-1 complete flow |
| S9: OI + Req Lifecycle | open_items.py + requirements.py | F2-2 approve guard | F3-2 transition buttons |
| S10: WRICEF Conversion | requirements.py | F2-2 type mapping | F3-2 convert button |
| S11: ALM Push | requirements.py | — | — |
| S12: Reopen | workshops.py | F2-1 reopen enhancement | F3-1 reopen flow |
| S13: Delta Workshop | workshops.py | F2-1 delta code gen | F3-2 delta creation |
| S14: Dashboard | — | — | — (dokunulmaz) |

---

## Risk Analizi

| Risk | Etki | Mitigasyon |
|------|------|-----------|
| Backend split sırasında import bozulması | Yüksek | Her prompt sonunda test + python import check |
| Frontend'in eski endpoint path'leri bozulması | Düşük | URL prefix'ler birebir korunuyor (Faz 1) |
| Circular import (explore/ paketi) | Düşük | Her module kendi import'larını yapar |
| Test'lerin kırılması | Yüksek | Her prompt sonunda 24 test doğrulaması |
| Enhancement'lar mevcut davranışı bozar | Orta | Faz 2 sadece additive — mevcut response'lara field ekler, kaldırmaz |
| Frontend rebuild'de field mapping hatası | Orta | Faz 3 prompt'larında canonical field listesi verildi |

---

## Toplam Tahmini Efor

| Faz | Prompt | ~Süre | Risk |
|-----|--------|-------|------|
| Faz 1: Backend Split | F1-1, F1-2, F1-3, F1-4 | ~2-3 saat | 🟢 Düşük |
| Faz 2: Backend Enhancement | F2-1, F2-2 | ~1-1.5 saat | 🟡 Orta |
| Faz 3: Frontend Workshop Detail | F3-1, F3-2 | ~1.5-2 saat | 🟡 Orta |
| Faz 4: Frontend API + Views | F4-1, F4-2 | ~1 saat | 🟢 Düşük |
| Faz 5: Test & Stabilize | F5-1 | ~30 dk | 🟢 Düşük |
| **TOPLAM** | **11 prompt** | **~6-7 saat** | — |

---

## Uygulama Sırası Özet

```
FAZ 1 — Backend Split (Copilot Güvenli Yaklaşım)
  F1-1: __init__.py + workshops.py (23 endpoint)        → test
  F1-2: process_levels.py (20 endpoint)                  → test
  F1-3: process_steps.py + requirements.py (20 endpoint) → test
  F1-4: open_items.py + supporting.py + switch (32 endpoint) → test ✅ Eski dosya silinir

FAZ 2 — Backend Enhancement (Claude Business Rules)
  F2-1: Workshop lifecycle (quality gate, reopen, delta)  → test
  F2-2: Items (code gen, approve guard, WRICEF mapping)   → test

FAZ 3 — Frontend Workshop Detail (Claude Sıfırdan Yazım)
  F3-1: Core (fetchAll, steps, fit, transitions)
  F3-2: Tabs (decisions, OI, req, agenda, attendees, delta)

FAZ 4 — Frontend Fixes
  F4-1: explore-api.js düzeltmeleri
  F4-2: explore_requirements.js + explore_workshops.js fixes

FAZ 5 — Stabilize
  F5-1: Smoke test + cross-check ✅ COMPLETED
```

---

## ✅ ALL PHASES COMPLETED — Final Status

**Completion Date:** 2025-02-12

### Faz 5 Results

| Check | Result |
|-------|--------|
| Backend import check | 95 endpoints, 6 sub-modules OK |
| Backend pytest | 871 passed, 3 failed (pre-existing), 2 skipped |
| JS syntax check | 7/7 files pass |
| Smoke test | **66 passed, 0 failed** (11 categories) |
| Frontend ↔ Backend cross-check | **93 matched**, 1 fixed (workshops.delete), 2 stubs, 11 backend-only |

### Pre-existing Bugs (not introduced by rebuild)
1. `test_matrix_with_coverage` / `test_matrix_uncovered_requirements` — pre-existing test failures
2. `test_full_requirement_lifecycle` — `BacklogItem.project_id` missing (uses `process_id`)
3. Steering committee report — `ProcessStep` model has no `project_id` (crash in `snapshot.py`)

### Fix Applied During Faz 5
- Added `DELETE /workshops/<ws_id>` endpoint (was missing — frontend `workshops.delete` would 405)

---

**Her prompt BAĞIMSIZ uygulanabilir. Önceki prompt'un çıktısına bağımlılık varsa açıkça belirtilmiştir.**
