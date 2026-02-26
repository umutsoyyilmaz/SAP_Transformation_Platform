# Architecture Handbook

## Muhendislik Felsefesi

Bu projedeki her kararin arkasindaki 6 temel ilke:

1. **Bir sonraki bug'i tahmin et.** Her fonksiyon beklemedigin sekilde cagirilacak. Defensive coding varsayilandir.
2. **Okuyucu icin optimize et.** Kod yazildigindan 10x fazla okunur. Netlik > zekalik.
3. **Sesli ve erken hatala.** Sessiz hatalar uretim kesintisidir. Yanlis olan bir sey varsa firsat, logla, yuzeyine cikar.
4. **Tenant izolasyonu bir guvenlik siniridir.** Tek bir cross-tenant veri sizintisi sirket-sonlandirici olaydır. `tenant_id` filtrelemeyi auth kadar ciddiye al.
5. **Her commit kodu buldugundan daha iyi biraksin.** Dosyaya dokunuyorsan kucuk seyleri duzelt — eksik type hint, belirsiz degisken adi.
6. **Talepleri sorgula.** Feature uygulamak mimari olarak yanlis hissettiriyorsa soyle. Daha iyi yaklasim oner.

---

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

## Cache Stratejisi

**Pattern:** Cache-Aside with Explicit Invalidation

```python
from app.services.cache_service import cache

def get_project(tenant_id: int, project_id: int) -> dict:
    cache_key = f"project:{tenant_id}:{project_id}"  # tenant_id ZORUNLU
    cached = cache.get(cache_key)
    if cached:
        return cached

    project = Project.query_for_tenant(tenant_id).get_or_404(project_id)
    result = project.to_dict()
    cache.set(cache_key, result, ttl=300)
    return result

def update_project(tenant_id: int, project_id: int, data: dict) -> dict:
    # ... update logic ...
    db.session.commit()

    # Invalidation ZORUNLU
    cache.delete(f"project:{tenant_id}:{project_id}")
    cache.delete_pattern(f"project_list:{tenant_id}:*")
    return project.to_dict()
```

### Cache Kurallari
1. Cache key MUTLAKA `tenant_id` icermeli (cross-tenant cache pollution onlenir)
2. Cache okumasi sadece service'te — blueprint veya model'de ASLA
3. Her yazma islemi etkilenen cache'leri invalidate etmeli
4. Liste/aggregate cache'ler icin `delete_pattern` kullan
5. TTL varsayilanlari: referans veri = 1 saat, islemsel veri = 5 dk, session = 30 dk
6. Supheye dusersen cache'leme — dogruluk > performans

---

## Tasarim Pattern'leri

### State Machine (status alanlari icin)
```python
# Gecisleri explicit tanimla — keyfi status degisikligine IZIN VERME
REQUIREMENT_TRANSITIONS: dict[str, set[str]] = {
    "draft":       {"in_review", "cancelled"},
    "in_review":   {"approved", "draft", "cancelled"},
    "approved":    {"implemented", "cancelled"},
    "implemented": {"verified", "approved"},
    "verified":    {"closed"},
    "closed":      set(),      # Terminal
    "cancelled":   set(),      # Terminal
}

def validate_transition(current: str, target: str) -> bool:
    return target in REQUIREMENT_TRANSITIONS.get(current, set())
```

### Repository Pattern (karmasik sorgular icin)
```python
class RequirementRepository:
    """Karmasik requirement sorgularini kapsullar.
    Service'leri is mantigi odakli tutar, sorgu yapimi ile ugrastirmaz."""

    @staticmethod
    def find_by_project(tenant_id: int, project_id: int,
                        status: str | None = None) -> list[Requirement]:
        stmt = select(Requirement).where(
            Requirement.tenant_id == tenant_id,
            Requirement.project_id == project_id
        )
        if status:
            stmt = stmt.where(Requirement.status == status)
        return db.session.execute(stmt).scalars().all()
```

### Service Composition (kalitim degil, bilesim)
```python
# Service'ler baska service'leri compose eder — kalitim zinciri YOK
class TestExecutionService:
    def __init__(self):
        self.requirement_service = RequirementService()
        self.notification_service = NotificationService()

    def execute_test_run(self, tenant_id: int, run_id: int) -> dict:
        run = self._get_run(tenant_id, run_id)
        results = self._execute_steps(run)
        self.requirement_service.update_coverage(tenant_id, run.requirement_id)
        if any(r.status == "failed" for r in results):
            self.notification_service.notify_test_failure(tenant_id, run)
        return run.to_dict()
```

**Kural:** 3+ service cagirisi derinligi = tasarim kokusu. Coordinator service veya event dusun.

---

## SAP Domain Konteksti

### Veri Modeli Hiyerarsisi
```
Program
  +-- Project
        +-- Scenario (orn: "Order-to-Cash", "Procure-to-Pay")
              +-- Requirement (classification: fit | partial_fit | gap)
                    |-- fit         -> ConfigItem (standart SAP yapilandirmasi)
                    |-- gap         -> WricefItem (ozel gelistirme)
                    |-- partial_fit -> WricefItem
                    +-- TestCase
                          +-- TestStep
```

### Domain Terimleri

| SAP Terimi | Kod Karsiligi | Aciklama |
|------------|--------------|----------|
| SAP Modulu | `sap_module` alani ("FI", "MM", "SD") | Standart SAP modul kodlari |
| Fit/Gap | `classification` enum | Config vs WRICEF yonlendirmesini belirler |
| WRICEF | `WricefItem` modeli | 6 tip: Workflow, Report, Interface, Conversion, Enhancement, Form |
| Go-Live | Project status gecisi | Cutover kontrolleri gerektirir |
| Transport | `TransportRequest` modeli | SAP degisiklik yonetimi |
| Yetki Konsepti | RBAC mapping | SAP rolu = Platform permission seti |
| Activate | `methodology` alani | SAP Activate metodolojisi (Discover-Explore-Realize-Deploy-Run) |

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
```

### Structured Logging (extra dict pattern)
```python
# Temel format yerine structured log kullan
logger.info(
    "Requirement status transitioned",
    extra={
        "tenant_id": tenant_id,
        "requirement_id": req_id,
        "from_status": old_status,
        "to_status": new_status,
        "user_id": user_id,
        "duration_ms": elapsed_ms
    }
)

# Kullanici verisi kisaltilmali
logger.info("Processing name=%s", str(name)[:200])
```

### Log Seviyeleri
| Seviye | Ne Zaman | Ornek |
|--------|----------|-------|
| `DEBUG` | Dahili state, degisken degerleri (prod'da KAPALI) | Sorgu parametreleri |
| `INFO` | Is olaylari (olusturma, guncelleme, gecis) | `Requirement created id=42` |
| `WARNING` | Kurtarilabilir sorunlar (retry, fallback, deprecation) | `Slow query detected 1200ms` |
| `ERROR` | Mevcut istegi etkileyen hatalar | `Service call failed` |
| `CRITICAL` | Sistem seviyesi arizalar (DB kapali, cache erisemez) | `Database connection lost` |

### Performans Loglama
```python
import time

def expensive_operation(tenant_id: int) -> dict:
    start = time.perf_counter()
    result = do_work()
    elapsed_ms = (time.perf_counter() - start) * 1000

    if elapsed_ms > 1000:  # Esik: 1 saniye
        logger.warning(
            "Slow operation detected",
            extra={"operation": "expensive_operation",
                   "duration_ms": elapsed_ms, "tenant_id": tenant_id}
        )
    return result
```

### Hassas Veri YASAK
```python
# YANLIS — hassas veri loglama
logger.info("password=%s", password)
logger.debug("token=%s", token)
logger.info("API key used: %s", api_key)
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
