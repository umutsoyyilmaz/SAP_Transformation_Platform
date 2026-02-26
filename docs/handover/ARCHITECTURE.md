# Architecture Handbook

## Katman Mimarisi

```
HTTP Request
  |
  v
[Middleware Chain]  JWT Auth -> Tenant Context -> Permission Guard -> Timing
  |
  v
[Blueprint]         HTTP routing, input validation, JSON response
  |                 Dosya: app/blueprints/*_bp.py
  |                 KURAL: ORM cagirisi YASAK, sadece service cagir
  v
[Service]           Is mantigi, transaction yonetimi, audit
  |                 Dosya: app/services/*_service.py
  |                 KURAL: db.session.commit() sadece burada
  v
[Model]             ORM tanimlari, to_dict() serialization
  |                 Dosya: app/models/*.py
  |                 KURAL: HTTP nesnesi (request, g, jsonify) YASAK
  v
[Database]          PostgreSQL (prod) / SQLite (test)
```

---

## Request Yasam Dongusu

Bir HTTP request geldiginde sirasiyla su middleware'ler calisir:

### 1. Content Validation (app/__init__.py before_request)
- Content-Length < 2MB kontrolu
- `/api/*` POST/PUT/PATCH icin `Content-Type: application/json` zorunlu
- Istisna: SCIM endpoint'leri, bulk import (multipart)

### 2. JWT Auth (app/middleware/jwt_auth.py)
- `Authorization: Bearer <token>` header'dan JWT extract
- Basarili ise: `g.jwt_user_id`, `g.jwt_tenant_id`, `g.jwt_roles`, `g.jwt_email` set edilir
- JWT yoksa: sessiz gecis (legacy auth destegi)

### 3. Tenant Context (app/middleware/tenant_context.py)
- `g.jwt_tenant_id` set edilmisse calisir
- DB'den `Tenant` modeli yukler -> `g.tenant` set eder
- Tenant bulunamazsa veya deaktif ise: 403 doner
- Platform admin'ler bypass eder
- Atlanan path'ler: `/auth`, `/health`, `/platform-admin`, `/static`

### 4. Blueprint Permission Guard (app/middleware/blueprint_permissions.py)
- Endpoint'in ait oldugu blueprint'i tespit eder
- Blueprint -> permission mapping'e bakar (ornek: `programs.view`)
- Yetki yoksa 403 doner

### 5. Route Handler (Blueprint)
- Input validation (uzunluk, enum, zorunlu alanlar)
- Service cagirisi: `service.create(tenant_id=g.jwt_tenant_id, data=data)`
- JSON response + HTTP status kodu

---

## Multi-Tenant Izolasyon (3 Katman)

### Katman 1: Model Kalitimi
```python
class MyModel(TenantModel):  # TenantModel otomatik tenant_id FK + index ekler
    __tablename__ = "my_models"
    # ...
```

### Katman 2: Scoped Query Helper
```python
# app/services/helpers/scoped_queries.py
from app.services.helpers.scoped_queries import get_scoped, get_scoped_or_none

# DOGRU — scope zorunlu
program = get_scoped(Program, program_id, tenant_id=tenant_id)

# YANLIS — scope'suz lookup, guvenlik acigi
program = Program.query.get(program_id)  # ASLA YAPMA
```

`get_scoped()` davranisi:
- Scope parametresi verilmezse `ValueError` firlatir
- Entity scope disindaysa `NotFoundError` firlatir (bilgi sizintisi engellenir)

### Katman 3: Blueprint Guard
- JWT'den `g.jwt_tenant_id` alinir
- Service'e `tenant_id` parametre olarak gonderilir
- Service tum sorgularda `query_for_tenant(tenant_id)` kullanir

---

## Yetkilendirme Sistemi (RBAC)

**Dosya:** `app/services/permission_service.py`

### Scope Hiyerarsisi
```
global (legacy) < tenant < program < project
```

### Veritabani Modeli
```
User -> UserRole -> Role -> RolePermission -> Permission
```

`UserRole` alanlari:
- `user_id`, `role_id`, `tenant_id`, `program_id`, `project_id`
- `starts_at`, `ends_at` (sureli roller icin)
- `is_active`

### Cache
- In-memory, 5 dakika TTL
- Key: `(user_id, tenant_id, program_id, project_id)`
- Value: `set[str]` permission codename'leri
- Thread-safe (`_cache_lock`)
- Invalidation: rol degisikliginde `invalidate_cache(user_id)`

### Superuser Roller
`platform_admin` ve `tenant_admin` tum kontrolleri bypass eder.

### Kullanim
```python
# Blueprint'te
@require_permission("tests.create")
def create_test():
    ...

# Service'te (manuel kontrol gerekirse)
from app.services.permission_service import has_permission
if not has_permission(user_id, "requirements.delete", tenant_id=tid):
    raise ForbiddenError()
```

### Permission Codename Yapisi
```
<kategori>.<fiil>

Kategoriler: programs, tests, requirements, backlog, raid, cutover, data, reports, admin
Fiiller:     view, create, edit, delete, approve, execute
```

---

## Veritabani Sema Yapisi

### Temel Modeller

| Domain | Ana Model | Alt Modeller | Dosya |
|--------|-----------|-------------|-------|
| Program | `Program` | `Phase`, `Gate`, `Workstream`, `TeamMember`, `Committee` | `models/program.py` |
| Project | `Project` | `ProjectMember` | `models/project.py` |
| Explore | `ExploreHierarchy` | `ProcessStep`, `ProcessObject`, `ExploreWorkshop`, `ExploreRequirement`, `ExploreDecision`, `ExploreOpenItem` | `models/explore/*.py` |
| Test | `TestSuite` | `TestCase`, `TestCaseStep`, `TestDataSet`, `TestExecution`, `TestResult` | `models/testing.py` |
| Cutover | `CutoverPlan` | `CutoverActivity`, `CutoverTask`, `CutoverRisk`, `WarRoomActivity` | `models/cutover.py` |
| Auth | `Tenant`, `User` | `Role`, `Permission`, `UserRole`, `RolePermission`, `Session` | `models/auth.py` |
| Audit | `AuditLog` | — | `models/audit.py` |
| AI | `AIUsageLog`, `AIAuditLog` | `AIResponseCache` | `models/ai.py` |

### FK Kurallari
- Tenant-scoped: `FK -> Tenant.id` ile `ondelete="CASCADE"`
- Child -> Parent: non-nullable FK (zorunlu iliski)
- Optional FK: `ondelete="SET NULL"` (nadir)

### Bilinen Gotcha
`ExploreDecision.project_id` FK'si aslinda `programs.id`'ye isaret eder (isimlendirme hatasi, legacy).

---

## Application Factory

**Dosya:** `app/__init__.py` — `create_app(config_name)`

Baslama sirasi (degistirmek tehlikeli):
1. Logging konfigurasyonu
2. SQLAlchemy + Migrate extension'lari
3. Auth middleware
4. Tenant context middleware
5. Model import'lari (Alembic icin)
6. `db.create_all()` + auto-schema-sync (PostgreSQL: `_auto_add_missing_columns()`)
7. Blueprint registration (50+ blueprint, sira onemli degil)
8. Permission guard'lar
9. CLI komutlari
10. Error handler'lar
11. Scheduler

### Auto-Add Columns
`_auto_add_missing_columns()` her startup'ta calisir (sadece PostgreSQL).
Eksik kolonlari `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` ile ekler.
Idempotent ve non-blocking.

---

## Entegrasyon Noktalari

### AI Gateway (`app/ai/gateway.py`)
- Provider-agnostic: Anthropic, OpenAI, Gemini, local stub
- `gw.chat(messages, model, purpose)` -> `{content, tokens, cost_usd, latency_ms}`
- 2 katli cache: memory + DB
- Retry: 3 deneme, exponential backoff (1s -> 2s -> 4s)
- Fallback chain: birincil basarisiz -> alternatif model dene
- Kullanim loglari: `AIUsageLog`, `AIAuditLog`

### SAP Cloud ALM Gateway (`app/integrations/alm_gateway.py`)
- OAuth2 client credentials (token cache + auto-refresh)
- Circuit breaker: 60 saniyede 5+ hata -> 30s pause
- `GatewayResult` donusu: `ok`, `status_code`, `data`, `error`, `duration_ms`
- Sync logu: `CloudALMSyncLog`

---

## Loglama & Gozlemlenebilirlik

### Logger Kurali
```python
logger = logging.getLogger(__name__)  # her dosyanin basinda
logger.info("Requirement created id=%s tenant=%s", req.id, tenant_id)
```

### Audit Trail
```python
from app.models.audit import write_audit
write_audit(entity_type="program", entity_id=program.id, action="create", ...)
```
- Immutable, append-only
- Her yazma islemi icin zorunlu

### Security Events
```python
from app.services.security_observability import record_security_event
record_security_event("cross_scope_access_attempt", severity="high", reason="...")
```
