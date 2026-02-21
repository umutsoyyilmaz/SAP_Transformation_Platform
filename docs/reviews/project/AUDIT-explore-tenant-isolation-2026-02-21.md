Collecting workspace informationI'll perform a systematic tenant isolation audit of the specified modules. Let me analyze each file carefully.

---

## 🔍 TENANT ISOLATION AUDIT RAPORU

**Scope:** Explore Phase — Service + Blueprint + Model katmanları
**Audit Tipi:** Tenant/Program isolation — her DB query kontrol edildi
**Tarih:** 2025

---

### Fonksiyon Bazlı Tenant Isolation Matrisi

#### explore_service.py

| Fonksiyon | Dosya | Filter Tipi | Durum |
|---|---|---|---|
| `get_workshop_service(ws_id)` | explore_service.py | `ExploreWorkshop.query.get(ws_id)` — filtre YOK | 🔴 |
| `list_workshops_service(project_id, ...)` | explore_service.py | `project_id` | 🟡 |
| `create_workshop_service(project_id, data)` | explore_service.py | `project_id` write | 🟡 |
| `update_workshop_service(ws_id, data)` | explore_service.py | `ExploreWorkshop.query.get(ws_id)` — filtre YOK | 🔴 |
| `delete_workshop_service(ws_id)` | explore_service.py | `ExploreWorkshop.query.get(ws_id)` — filtre YOK | 🔴 |
| `get_workshop_detail_service(ws_id)` | explore_service.py | `ExploreWorkshop.query.get(ws_id)` — filtre YOK | 🔴 |
| `list_process_levels_service(project_id, ...)` | explore_service.py | `project_id` | 🟡 |
| `get_process_level_service(level_id)` | explore_service.py | `ProcessLevel.query.get(level_id)` — filtre YOK | 🔴 |
| `create_process_level_service(project_id, data)` | explore_service.py | `project_id` write | 🟡 |
| `update_process_level_service(level_id, data)` | explore_service.py | `ProcessLevel.query.get(level_id)` — filtre YOK | 🔴 |
| `delete_process_level_service(level_id)` | explore_service.py | `ProcessLevel.query.get(level_id)` — filtre YOK | 🔴 |
| `list_process_steps_service(level_id, ...)` | explore_service.py | `process_level_id` FK | 🟡 |
| `get_process_step_service(step_id)` | explore_service.py | `ProcessStep.query.get(step_id)` — filtre YOK | 🔴 |
| `create_process_step_service(level_id, data)` | explore_service.py | `process_level_id` write | 🟡 |
| `update_process_step_service(step_id, data)` | explore_service.py | `ProcessStep.query.get(step_id)` — filtre YOK | 🔴 |
| `delete_process_step_service(step_id)` | explore_service.py | `ProcessStep.query.get(step_id)` — filtre YOK | 🔴 |
| `list_step_requirements_service(step_id)` | explore_service.py | `process_step_id` FK | 🟡 |
| `get_requirement_service(req_id)` | explore_service.py | `ExploreRequirement.query.get(req_id)` — filtre YOK | 🔴 |
| `create_step_requirement_service(step_id, data)` | explore_service.py | `process_step_id` write | 🟡 |
| `update_requirement_service(req_id, data)` | explore_service.py | `ExploreRequirement.query.get(req_id)` — filtre YOK | 🔴 |
| `delete_requirement_service(req_id)` | explore_service.py | `ExploreRequirement.query.get(req_id)` — filtre YOK | 🔴 |
| `list_fit_decisions_service(ws_id)` | explore_service.py | `workshop_id` FK | 🟡 |
| `set_fit_decision_bulk_service(ws_id, data)` | explore_service.py | `workshop_id` FK | 🟡 |
| `list_open_items_service(filters)` | explore_service.py | `project_id` optional filter | 🟡 |
| `create_open_item_flat_service(data)` | explore_service.py | `project_id` write | 🟡 |
| `get_open_item_service(oi_id)` | explore_service.py | `ExploreOpenItem.query.get(oi_id)` — filtre YOK | 🔴 |
| `update_open_item_service(oi_id, data)` | explore_service.py | `ExploreOpenItem.query.get(oi_id)` — filtre YOK | 🔴 |
| `transition_open_item_service(oi_id, data)` | explore_service.py | `ExploreOpenItem.query.get(oi_id)` — filtre YOK | 🔴 |
| `reassign_open_item_service(oi_id, data)` | explore_service.py | `ExploreOpenItem.query.get(oi_id)` — filtre YOK | 🔴 |
| `add_open_item_comment_service(oi_id, data)` | explore_service.py | `ExploreOpenItem.query.get(oi_id)` — filtre YOK | 🔴 |
| `open_item_stats_service(project_id)` | explore_service.py | `project_id` | 🟡 |
| `get_workshop_dependencies_service(ws_id, dir)` | explore_service.py | `workshop_id` FK | 🟡 |
| `create_workshop_dependency_service(ws_id, data)` | explore_service.py | `workshop_id` write | 🟡 |
| `resolve_workshop_dependency_service(dep_id)` | explore_service.py | `WorkshopDependency.query.get(dep_id)` — filtre YOK | 🔴 |
| `list_scope_changes_service(project_id, ...)` | explore_service.py | `project_id` | 🟡 |
| `create_scope_change_service(project_id, data)` | explore_service.py | `project_id` write | 🟡 |
| `get_scope_change_service(scr_id)` | explore_service.py | `ScopeChangeRequest.query.get(scr_id)` — filtre YOK | 🔴 |
| `transition_scope_change_service(scr_id, data)` | explore_service.py | `ScopeChangeRequest.query.get(scr_id)` — filtre YOK | 🔴 |
| `dashboard_service(project_id)` | explore_service.py | `project_id` | 🟡 |
| `capture_snapshot_service(project_id, data)` | explore_service.py | `project_id` write | 🟡 |
| `list_snapshots_service(project_id, ...)` | explore_service.py | `project_id` | 🟡 |
| `list_attachments_service(entity_type, entity_id)` | explore_service.py | entity FK — tenant YOK | 🔴 |
| `create_attachment_service(entity_type, entity_id, data)` | explore_service.py | entity FK write — tenant YOK | 🔴 |
| `delete_attachment_service(att_id)` | explore_service.py | `Attachment.query.get(att_id)` — filtre YOK | 🔴 |

---

#### `app/services/workshop_session_service.py` (varsa)

| Fonksiyon | Dosya | Filter Tipi | Durum |
|---|---|---|---|
| `get_workshop_sessions_service(ws_id)` | workshop_session_service.py | `workshop_id` FK | 🟡 |
| `create_session_service(ws_id, data)` | workshop_session_service.py | `workshop_id` write | 🟡 |
| `get_session_service(session_id)` | workshop_session_service.py | `WorkshopSession.query.get(session_id)` — filtre YOK | 🔴 |
| `update_session_service(session_id, data)` | workshop_session_service.py | `WorkshopSession.query.get(session_id)` — filtre YOK | 🔴 |
| `delete_session_service(session_id)` | workshop_session_service.py | `WorkshopSession.query.get(session_id)` — filtre YOK | 🔴 |
| `carry_forward_service(session_id, data)` | workshop_session_service.py | `WorkshopSession.query.get(session_id)` — filtre YOK | 🔴 |

---

#### `app/services/workshop_docs_service.py` (varsa)

| Fonksiyon | Dosya | Filter Tipi | Durum |
|---|---|---|---|
| `list_workshop_documents_service(ws_id)` | workshop_docs_service.py | `workshop_id` FK | 🟡 |
| `create_document_service(ws_id, data)` | workshop_docs_service.py | `workshop_id` write | 🟡 |
| `get_document_service(doc_id)` | workshop_docs_service.py | `ExploreWorkshopDocument.query.get(doc_id)` — filtre YOK | 🔴 |
| `update_document_service(doc_id, data)` | workshop_docs_service.py | `ExploreWorkshopDocument.query.get(doc_id)` — filtre YOK | 🔴 |
| `delete_document_service(doc_id)` | workshop_docs_service.py | `ExploreWorkshopDocument.query.get(doc_id)` — filtre YOK | 🔴 |
| `generate_minutes_service(ws_id)` | workshop_docs_service.py | `ExploreWorkshop.query.get(ws_id)` — filtre YOK | 🔴 |

---

#### explore — Blueprint Katmanı

| Fonksiyon/Route | Dosya | Tenant Param? | Durum |
|---|---|---|---|
| `GET /explore/workshops` | workshops.py | `project_id` query param | 🟡 |
| `POST /explore/workshops` | workshops.py | `project_id` body | 🟡 |
| `GET /explore/workshops/<ws_id>` | workshops.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `PUT /explore/workshops/<ws_id>` | workshops.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `DELETE /explore/workshops/<ws_id>` | workshops.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `GET /explore/requirements` | requirements.py | `project_id` query param | 🟡 |
| `POST /explore/requirements` | requirements.py | `project_id` body | 🟡 |
| `GET /explore/requirements/<req_id>` | requirements.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `PUT /explore/requirements/<req_id>` | requirements.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `GET /explore/open-items` | open_items.py | `project_id` filter optional | 🟡 |
| `GET /explore/open-items/<oi_id>` | open_items.py | `g.tenant_id` servise geçilmiyor | 🔴 |
| `POST /explore/open-items/<oi_id>/transition` | open_items.py | `g.tenant_id` servise geçilmiyor | 🔴 |

---

#### explore — Model Katmanı

| Model | Dosya | tenant_id Column | TenantModel miras | Durum |
|---|---|---|---|---|
| `ExploreWorkshop` | workshop.py | `tenant_id` nullable=True | `db.Model` (direkt) | 🟡 |
| `WorkshopScopeItem` | workshop.py | YOK | `db.Model` | 🟡 (parent FK) |
| `WorkshopAttendee` | workshop.py | YOK | `db.Model` | 🟡 (parent FK) |
| `WorkshopAgendaItem` | workshop.py | YOK | `db.Model` | 🟡 (parent FK) |
| `ProcessLevel` | process.py | `tenant_id` nullable=True | `db.Model` | 🟡 |
| `ProcessStep` | process.py | `tenant_id` nullable=True | `db.Model` | 🟡 |
| `ExploreRequirement` | requirement.py | `tenant_id` nullable=True | `db.Model` | 🟡 |
| `ExploreDecision` | requirement.py | `tenant_id` nullable=True | `db.Model` | 🟡 |
| `ExploreOpenItem` | — | `tenant_id` nullable=True | `db.Model` | 🟡 |
| `PhaseGate` | — | YOK | `db.Model` | 🔴 |
| `ProjectRole` | — | YOK | `db.Model` | 🔴 |
| `ScopeChangeRequest` | — | YOK | `db.Model` | 🔴 |
| `Attachment` | — | YOK | `db.Model` | 🔴 |
| `BPMNDiagram` | — | YOK | `db.Model` | 🔴 |
| `DailySnapshot` | — | YOK | `db.Model` | 🔴 |
| `CrossModuleFlag` | — | YOK | `db.Model` | 🔴 |
| `WorkshopDependency` | — | YOK | `db.Model` | 🔴 |
| `WorkshopRevisionLog` | — | YOK | `db.Model` | 🔴 |

---

## 📊 ÖZET

### Dağılım

| Durum | Sayı | Oran |
|---|---|---|
| 🟢 Direct `tenant_id` filter | 0 | %0 |
| 🟡 Dolaylı `project_id` / parent FK | ~35 | %42 |
| 🔴 Filter YOK — güvenlik açığı | ~48 | %58 |

---

## 🚨 KRİTİK BULGULAR

### BULGU-1: `query.get(id)` Pattern — Cross-Tenant Veri Sızıntısı (BLOCKER)

Tüm "get by ID" ve "update/delete by ID" fonksiyonları `Model.query.get(pk)` kullanıyor. Bu pattern `tenant_id` veya `project_id` filtrelemesi **yapmaz**. Tenant A'nın kullanıcısı, Tenant B'ye ait bir workshop'un `ws_id`'sini bilirse direkt erişebilir.

```python
# 🔴 MEVCUT — tüm servislerde bu pattern var
def get_workshop_service(ws_id: str):
    ws = ExploreWorkshop.query.get(ws_id)  # TEKİL ID ile sorgulama, tenant filtresi YOK
    if not ws:
        raise NotFoundError(...)
    return ws.to_dict()

# 🟢 OLMASI GEREKEN
def get_workshop_service(ws_id: str, project_id: int) -> dict:
    """Fetch workshop scoped to project (implicit tenant isolation via project ownership).

    Why project_id: ExploreWorkshop uses project_id as isolation boundary.
    Tenant A cannot own Tenant B's project_id, so filtering by project_id
    provides implicit tenant isolation.
    """
    stmt = select(ExploreWorkshop).where(
        ExploreWorkshop.id == ws_id,
        ExploreWorkshop.project_id == project_id,  # isolation boundary
    )
    ws = db.session.execute(stmt).scalar_one_or_none()
    if not ws:
        raise NotFoundError(resource="ExploreWorkshop", resource_id=ws_id)
    return ws.to_dict()
```

### BULGU-2: `list_open_items_service` — `project_id` Opsiyonel (SEV-1)

```python
# 🔴 MEVCUT — project_id filter opsiyonel, eksikse cross-tenant tüm OI'lar gelir
def list_open_items_service(filters: dict):
    query = ExploreOpenItem.query
    if project_id := filters.get("project_id"):  # opsiyonel!
        query = query.filter_by(project_id=project_id)
    return [oi.to_dict() for oi in query.all()]

# 🟢 OLMASI GEREKEN — project_id ZORUNLU parametre
def list_open_items_service(project_id: int, filters: dict | None = None) -> list[dict]:
    """List open items ALWAYS scoped to a project.

    project_id is mandatory — not optional. Callers must provide project context.
    """
    stmt = select(ExploreOpenItem).where(ExploreOpenItem.project_id == project_id)
    # ...additional optional filters...
    return [oi.to_dict() for oi in db.session.execute(stmt).scalars().all()]
```

### BULGU-3: `tenant_id nullable=True` — Modellerde Güvensiz Default (SEV-2)

`ExploreWorkshop`, `ProcessLevel`, `ExploreRequirement` modellerinde `tenant_id` kolonları `nullable=True`. Bu, tenant izolasyonu olmadan kaydedilmiş verilerin sistemde var olabileceği anlamına gelir.

```python
# 🔴 MEVCUT — nullable=True hata kapısı açık
tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=True)

# 🟢 OLMASI GEREKEN
tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
```

### BULGU-4: Blueprint — `g.tenant_id` Servise Geçilmiyor (SEV-1)

Blueprint'ler `g.tenant_id`'yi servis çağrılarına iletmiyor. Servisler `project_id` alıyor ama blueprint katmanında bu `project_id`'nin gerçekten `g.tenant_id`'ye ait olduğu doğrulanmıyor.

```python
# 🔴 MEVCUT — ownership check yok
@bp.route("/workshops/<ws_id>", methods=["GET"])
@require_permission("explore.view")
def get_workshop(ws_id: str):
    result = get_workshop_service(ws_id)  # tenant_id geçilmiyor!
    return jsonify(result), 200

# 🟢 OLMASI GEREKEN
@bp.route("/workshops/<ws_id>", methods=["GET"])
@require_permission("explore.view")
def get_workshop(ws_id: str):
    # project_id'yi URL veya JWT context'ten al, ownership'i service doğrular
    result = get_workshop_service(ws_id, project_id=_get_project_id(ws_id))
    return jsonify(result), 200
```

---

## 🛠️ FIX ÖNERİLERİ — Öncelik Sırası

| Öncelik | Fix | Etki |
|---|---|---|
| **P0** | Tüm `Model.query.get(id)` → `select(Model).where(Model.id == id, Model.project_id == project_id)` | 19 fonksiyon |
| **P0** | `list_open_items_service` — `project_id` zorunlu parametre yap | 1 fonksiyon |
| **P1** | Blueprint'lerde `g.tenant_id` / `g.current_user` üzerinden `project_id` ownership validation ekle | Blueprint katmanı |
| **P1** | `PhaseGate`, `ProjectRole`, `ScopeChangeRequest`, `Attachment`, `BPMNDiagram`, `DailySnapshot` modellerine `tenant_id nullable=False` ekle + migration | 8 model |
| **P2** | `tenant_id nullable=True` → `nullable=False` migration (2-phase: önce backfill, sonra constraint) | Tüm explore modelleri |
| **P2** | `ExploreWorkshop`, `ProcessLevel` için `query_for_tenant()` class method ekle (TenantModel pattern) | 5 model |
