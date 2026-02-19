# SAP Transformation Platform — Proje Özgü Kodlama Standartları

> **Durum:** Zorunlu — tüm katkılar bu standarda uymak zorundadır.  
> **Kapsam:** `app/`, `tests/`, `e2e/`, `scripts/`, `migrations/`  
> **Yürürlük:** 2026-02-19  
> **Sorumlu:** Platform Mimarı  
> **Revizyon:** Mimari kararlar ADR süreciyle, bu döküman PR + Mimar onayıyla güncellenir.

---

## Uygulama Kademeleri

Bu dökümandaki her kural aşağıdaki üç kademeden birine aittir. Kademe belirtilmeyen kural **Tier 1**'dir.

| Kademe | Tanım | Uygulama yöntemi |
|---|---|---|
| **Tier 1 — Anında (Yeni Kod)** | Bugünden itibaren her yeni/değiştirilen kod bu kurala uymak zorundadır. CI gate blocker'dır. | `ruff`, `mypy`, `gitleaks`, `pytest`, test coverage |
| **Tier 2 — Sprint Hedefi** | Mevcut ihlaller teknik borç olarak kayıtlıdır; her sprint en az %10 azaltılır. Yeni ihlal **yasaktır**. | Sprint review checklist, PR review blocker |
| **Tier 3 — ADR Kapsamlı** | Büyük mimari/yapısal değişiklik gerektirir; ADR ve Mimar onayı ile planlanır. | ADR + Mimar onayı |

> Mevcut ihlaller için teknik borç sicili: `docs/plans/TECH_DEBT_REGISTER.md`

---

## İçindekiler

1. [Teknoloji Yığını ve Kesin Sürümler](#1-teknoloji-yığını-ve-kesin-sürümler)
2. [Genel Python Kuralları](#2-genel-python-kuralları)
3. [Proje Mimarisi ve Katman Kuralları](#3-proje-mimarisi-ve-katman-kuralları)
20. [Tehdit Modelleme ve Zafiyet Yönetimi](#20-tehdit-modelleme-ve-zafiyet-yönetimi)
4. [Model Katmanı Standartları](#4-model-katmanı-standartları)
5. [Blueprint (Controller) Katmanı Standartları](#5-blueprint-controller-katmanı-standartları)
6. [Service Katmanı Standartları](#6-service-katmanı-standartları)
7. [Kimlik Doğrulama ve Yetkilendirme (AuthN/AuthZ)](#7-kimlik-doğrulama-ve-yetkilendirme-authnauthorz)
8. [Çok Kiracılı (Multi-Tenant) Mimari Kuralları](#8-çok-kiracılı-multi-tenant-mimari-kuralları)
9. [AI Modülü Standartları](#9-ai-modülü-standartları)
10. [Veritabanı ve Migration Kuralları](#10-veritabanı-ve-migration-kuralları)
11. [Hata Yönetimi](#11-hata-yönetimi)
12. [Loglama Standartları](#12-loglama-standartları)
13. [Güvenlik Kontrolleri](#13-güvenlik-kontrolleri)
14. [Test Standartları](#14-test-standartları)
15. [API Sözleşme Kuralları](#15-api-sözleşme-kuralları)
16. [CI/CD Kapıları ve Kalite Metrikleri](#16-cicd-kapıları-ve-kalite-metrikleri)
17. [Kod İnceleme (Code Review) Standartları](#17-kod-i̇nceleme-code-review-standartları)
18. [PR Şablonu ve Zorunlu Alanlar](#18-pr-şablonu-ve-zorunlu-alanlar)
19. [Yasak Desenler ve Kırmızı Çizgiler](#19-yasak-desenler-ve-kırmızı-çizgiler)

---

## 1. Teknoloji Yığını ve Kesin Sürümler

Aşağıdaki sürümler sabittir; yükseltme teklifi için ADR gereklidir.

| Bileşen | Versiyon | Notlar |
|---|---|---|
| Python | **3.11+** | `pyproject.toml` ile zorunlu kılınır |
| Flask | **3.1.0** | Application Factory zorunlu |
| SQLAlchemy | **2.0.x** | Legacy Query API (`Model.query`) kabul edilir; yeni kod `db.session.execute()` tercih eder |
| Flask-Migrate / Alembic | **4.0.x** | Her tablo değişikliği migration ile |
| PostgreSQL | **15+** | Production; dev/test için SQLite in-memory |
| Redis | **5.x** | Cache ve rate limiting |
| PyJWT | **2.9.x** | — |
| bcrypt | **4.x** | Parola hash; Argon2 geçişi ADR bekliyor |
| Ruff | **≥ 0.8.0** | Lint + format; Black, isort kullanılmaz |
| pytest | **8.3.x** | — |
| Playwright | **E2E** | `e2e/` dizininde TypeScript |
| Gunicorn | **23.x** | Production WSGI |

---

## 2. Genel Python Kuralları

### 2.1 Formatter ve Linter

- **Tek formatter:** `ruff format` — başka formatter kullanılmaz.
- **Kurallar `ruff.toml` içinde tanımlıdır ve CI'da zorunludur:**
  - `line-length = 120`
  - `quote-style = "double"` (tek tırnak **yasak**)
  - `indent-style = "space"` (tab **yasak**)
  - Seçili kurallar: `E, W, F, I, B, UP, C` — `C901` (cyclomatic complexity) **zorunludur**

> **ruff.toml'a eklenmesi gereken satır:**
> ```toml
> [lint]
> select = ["E", "W", "F", "I", "B", "UP", "C"]
>
> [lint.mccabe]
> max-complexity = 10
> ```

```bash
# CI'da çalışan komutlar — lokal çalıştırmadan önce mutlaka yapılmalı
ruff check .
ruff format --check .
mypy app/ --ignore-missing-imports --strict-optional
```

- **Commit öncesi zorunlu:** `make lint && make format` temiz çıkmalıdır.

### 2.0 Pre-commit Hooks (Tier 1)

Repo kökünde `.pre-commit-config.yaml` tanımlıdır. Tüm geliştiriciler `pre-commit install` komutunu çalıştırmak **zorundadır**:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports, --strict-optional]
        files: ^app/
```

Pre-commit hook kurulmadan yapılan commit CI'da **otomatik reddedilir**.

### 2.2 İsimlendirme Kuralları

| Kapsam | Kural | Örnek |
|---|---|---|
| Modül dosyası | `snake_case` | `permission_service.py` |
| Sınıf | `PascalCase` | `TenantModel`, `LLMGateway` |
| Fonksiyon / metod | `snake_case` | `get_user_permissions()` |
| Sabit | `UPPER_SNAKE_CASE` | `CACHE_TTL = 300` |
| Blueprint değişkeni | `<domain>_bp` | `testing_bp`, `backlog_bp` |
| Private fonksiyon/metod | `_snake_case` | `_parse_api_keys()` |
| Boolean değişken | `is_`, `has_`, `can_` prefix | `is_active`, `has_permission` |
| Flask `g` context değişkenleri | `g.current_user`, `g.tenant_id` | Başka alan adı **yasak** |

### 2.3 Tip Açıklamaları (Type Hints)

> **Tier:** Yeni ve değiştirilen kod için Tier 1; legacy kod için Tier 2 (mevcut cohort'ta ihlal sayısı sprint başına ≥10 azaltılır).

- **Yeni yazılan veya değiştirilen** her `public` fonksiyonun parametreleri ve dönüş tipi açıklanmak **zorundadır**.
- `Optional[X]` yerine `X | None` kullanılabilir (Python 3.11+).
- `dict`, `list`, `tuple` koleksiyon tipleri küçük harfle yazılır (`dict[str, int]`, `list[str]`).
- Private/iç yardımcı fonksiyonlarda tip açıklaması isteğe bağlıdır, ancak teşvik edilir.
- **Tip doğruluğu `mypy` ile CI'da doğrulanır** — sadece tip hint varlığı değil, tutarlılığı da kontrol edilir.

```python
# DOĞRU
def get_user_permissions(user_id: int) -> set[str]:
    ...

# YANLIŞ
def get_user_permissions(user_id, role=None):
    ...
```

### 2.4 Docstring Kuralları

- Her **modül** dosyası, üst kısımda `"""..."""` modül docstring içermelidir.
- Her **public sınıf ve fonksiyon** docstring içermelidir.
- Format: Google-style docstring.
- Docstring gövdesi **"ne"** değil **"neden"** yi açıklar; kullanım örneği (Usage) içermelidir.

```python
# DOĞRU
def query_for_tenant(cls, tenant_id: int):
    """
    Return a base query scoped to the given tenant.

    Args:
        tenant_id: The tenant's primary key.

    Returns:
        SQLAlchemy query filtered by tenant_id.

    Note:
        All callers MUST scope queries through this method to prevent
        cross-tenant data leakage.
    """
    return cls.query.filter_by(tenant_id=tenant_id)
```

### 2.5 Import Sırası

Ruff `I` kuralı zorlar. Manuel kural:

1. Standard library
2. Third-party (`flask`, `sqlalchemy`, `jwt`)
3. First-party (`app.*`)
4. Relative (`.models`, `..services`)

Her grup arasında bir boş satır.

---

## 3. Proje Mimarisi ve Katman Kuralları

### 3.1 Katman Hiyerarşisi

```
HTTP İsteği
    │
    ▼
[Blueprint] (app/blueprints/<domain>_bp.py)   → HTTP parse, validate, respond
    │
    ▼
[Service] (app/services/<domain>_service.py)   → İş mantığı, transaction yönetimi
    │
    ▼
[Model] (app/models/<domain>.py)               → ORM mapping, tenant kapsam
    │
    ▼
[DB / Redis / AI Gateway]                      → Altyapı
```

**Kural 1:** Blueprint → Service → Model yönünde bağımlılık tek yönlüdür.  
**Kural 2:** Model katmanı hiçbir zaman HTTP objesine (`request`, `g`, `jsonify`) dokunmaz.  
**Kural 3:** Blueprint hiçbir zaman doğrudan ORM sorgusunu çalıştırmaz; servis fonksiyonu çağırır.  
**Kural 4:** Servis → Servis çağrısı izin verilir; Blueprint → Blueprint çağrısı **yasaktır**.

### 3.2 Dosya Boyutu Limitleri

| Dosya türü | Maksimum satır | Kademe | Aşınca yapılacak |
|---|---|---|---|
| Blueprint (`*_bp.py`) | **600 satır** | Tier 1 (yeni), Tier 2 (mevcut) | Domain alt-blueprint'e bölün |
| Service | **400 satır** | Tier 1 (yeni), Tier 2 (mevcut) | Sorumluluk ayrıştırın |
| Model | **250 satır** | Tier 1 | Mixin kullanın |
| Test dosyası | **500 satır** | Tier 1 | Konuya göre bölün |

> **Mevcut teknik borç:** `testing_bp.py` (3324 satır) — Tier 3 (ADR-0001 kapsamında). Hedef: Q3 2026'ya kadar `testing_bp_runs.py`, `testing_bp_signoff.py`, `testing_bp_snapshots.py` olarak 3 dosyaya bölünmesi.

### 3.3 Cyclomatic Complexity

- Cyclomatic complexity fonksiyon başına **≤ 10** — `ruff` `C901` kuralı ile CI'da **otomatik** kontrol edilir. **ruff.toml'da `C` kural seti ve `max-complexity = 10` tanımlı olmalıdır.**
- Cognitive complexity fonksiyon başına **≤ 15** — review aşamasında kontrol edilir (otomatik araç: `flake8-cognitive-complexity`, opsiyonel CI eklentisi).
- Tek bir `if/elif` zinciri **≤ 5 dal** içermeli; aşıyorsa lookup dict veya strategy pattern kullanın.
- Nested `for/while` maksimum **2 seviye**; daha derin döngü extract-function ile ayrılır.

---

## 4. Model Katmanı Standartları

### 4.1 Tablo Tanımlama Kuralları

- Tenant kapsamlı her model `TenantModel` abstract base'inden miras alır:

```python
from app.models.base import TenantModel

class Requirement(TenantModel):
    __tablename__ = "requirements"
    ...
```

- Tenant'a ait olmayan global tablolar doğrudan `db.Model`den miras alır.
- `__tablename__` her zaman **açıkça** belirtilir; otomatik isim kullanılmaz.
- Her tablo; `id`, `created_at`, `updated_at` kolonlarını içerir.

### 4.2 Kolon Standartları

```python
# DOĞRU — açık null constraint + default
status = db.Column(db.String(32), nullable=False, default="draft")

# YANLIŞ — belirsiz nullable
status = db.Column(db.String)
```

- String kolonu `length` parametresi olmadan tanımlanamaz; minimum `String(64)`.
- Enum değerler doğrudan `db.String` + Python `Enum` ile; `db.Enum` yerine string tutulur (migration esnekliği).
- Foreign key'ler `ondelete` açıkça belirtilir (`CASCADE` veya `SET NULL`).

### 4.3 İndeks Kuralları

- `tenant_id` + sık sorgulanan kolon kombinasyonları için composite index zorunlusu:

```python
__table_args__ = (
    db.Index("ix_requirements_tenant_status", "tenant_id", "status"),
)
```

- `tenant_id` tek başına otomatik indexlenir (`TenantModel` baz sınıf).

### 4.4 Soft Delete

`SoftDeleteMixin` kullanan modellerde:
- `deleted_at` kontrolü servis katmanında yapılır, blueprint'te değil.
- Hard delete yalnızca admin servisi aracılığıyla gerçekleşir.

---

## 5. Blueprint (Controller) Katmanı Standartları

### 5.1 Blueprint Kaydı

```python
# Blueprint tanımı — her dosyanın en üstünde
blueprint_name_bp = Blueprint("blueprint_name", __name__)
```

- Blueprint URL prefix'i `app/__init__.py` içinde `register_blueprint` çağrısında belirtilir; blueprint dosyasında değil.

### 5.2 Route Fonksiyon Kuralları

```python
@testing_bp.route("/api/v1/testing/cycles", methods=["POST"])
@require_permission("testing.create")
def create_test_cycle():
    """Create a new test cycle within a program."""
    data = request.get_json(silent=True) or {}
    # 1. Input validation
    # 2. Service call
    # 3. Response
```

- Her route fonksiyonu **≤ 50 satır** (Tier 1: yeni kod); mevcut route'lar için Tier 2 hedef. İş mantığı satıra dahil edilmez — servis çağrısı, input parse ve response üç ayrı blok olmalıdır.
- `request.get_json(silent=True) or {}` — `silent=True` zorunludur (geçersiz JSON 400 döner).
- Tüm state-changing route'lar (`POST`, `PUT`, `PATCH`, `DELETE`) `@require_permission` ile korunur.
- `GET` endpoint'leri de minimum `@require_permission("domain.read")` gerektirir.

### 5.3 HTTP Durum Kodları

| Senaryo | Kod |
|---|---|
| Kaynak oluşturuldu | 201 |
| Başarılı okuma/güncelleme | 200 |
| Başarılı silme (içerik döner) | 200 |
| Geçersiz input | 400 |
| Kimlik doğrulama hatası | 401 |
| Yetki yok | 403 |
| Kaynak bulunamadı | 404 |
| İş kuralı ihlali | 422 |
| Sunucu hatası | 500 |

- `404` dönerken her zaman `{"error": "...", "resource": "...", "id": ...}` formatı kullanılır.

### 5.4 Yanıt Formatı

**Tüm API yanıtları JSON olmalıdır.** Standart zarflar:

```json
// Başarılı tekil kaynak
{ "id": 1, "status": "draft", ... }

// Başarılı liste
{ "items": [...], "total": 42, "page": 1, "per_page": 20 }

// Hata
{ "error": "Validation failed", "details": { "field": "reason" } }
```

---

## 6. Service Katmanı Standartları

### 6.0 Serializasyon Güvenlik Kuralı (Tier 1)

Her modelde `to_dict()` veya eşdeğer serializasyon metodu **hassas alan dışlama** listesi içermek **zorundadır**.

```python
# DOĞRU
SENSITIVE_FIELDS = {"password_hash", "reset_token", "mfa_secret", "raw_api_key"}

def to_dict(self, include_sensitive: bool = False) -> dict:
    """
    Serialize model to dict.

    Args:
        include_sensitive: Must be False in all API response paths.
            Only True for internal audit/migration scripts.
    """
    data = {
        c.name: getattr(self, c.name)
        for c in self.__table__.columns
        if include_sensitive or c.name not in SENSITIVE_FIELDS
    }
    return data

# YANLIŞ — tüm kolonları dökmek
def to_dict(self):
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

- `password_hash`, `reset_token`, `mfa_secret`, `raw_api_key`, `jwt_token` alanları **hiçbir API yanıtında** bulunamaz.
- Bu alanların response'a girip girmediği Semgrep kuralıyla CI'da taranır.

### 6.1 Transaction Yönetimi

```python
# DOĞRU — servis transaction sahibidir
def create_requirement(tenant_id: int, data: dict) -> dict:
    req = Requirement(tenant_id=tenant_id, **data)
    db.session.add(req)
    db.session.commit()           # başarı yolu
    return req.to_dict()
    # Hata yolunda servis exception fırlatır; blueprint rollback yapar
```

- `db.session.commit()` yalnızca **servis** katmanında çağrılır.
- Blueprint `db.session.commit()` çağrısı **yasaktır**.
- Her servis fonksiyonu ya commit eder ya da exception fırlatır; yarı yazma durumu bırakılmaz.

### 6.2 Cache Kullanımı

```python
from app.services.cache_service import cache_get, cache_set, cache_invalidate

# TTL açıkça belirtilmeli
cache_set(f"perms:{user_id}", permissions, ttl=CACHE_TTL)
```

- Cache key'leri şablon: `<varlık>:<id>` veya `<varlık>:<tanımlayıcı>`.
- Cache invalidasyon, ilgili entity değiştiğinde aynı servis fonksiyonunda yapılır.
- Redis bağlantısı olmadığında fallback **memory cache** aktiftir; bu durum log'a yazılır ama hata fırlatılmaz.

---

## 7. Kimlik Doğrulama ve Yetkilendirme (AuthN/AuthZ)

### 7.1 API Key Auth

- `API_KEYS` env var formatı: `key1:admin,key2:editor,key3:viewer`
- `API_AUTH_ENABLED=false` **yalnızca** geliştirme ortamında kullanılır; `production` config'de bu değer her zaman `true`dur.
- API key'ler env var dışında hiçbir yerde (kod, veritabanı, log) saklanamaz.

### 7.2 JWT Auth

- Access token süresi: **900 saniye (15 dk)** — `JWT_ACCESS_EXPIRES` env var ile.
- Refresh token süresi: **604800 saniye (7 gün)** — `JWT_REFRESH_EXPIRES` env var ile.
- Token payload'ında `tenant_id` bulunmak **zorundadır**; yoksa 401 döner.
- Her token rotasyon endpoint'i rate-limit altındadır.

### 7.3 RBAC Kuralları

- İzin kodu formatı: `<domain>.<action>` (örn. `requirements.create`, `testing.read`)
- Yeni bir domain eklenirken **önce** `Permission` seed verisi oluşturulur; sonra blueprint yazılır.
- `SUPERUSER_ROLES = {"platform_admin", "tenant_admin"}` — bu roller permission kontrolünü bypass eder.
- `has_permission()` servisi dışında inline permission kontrolü **yasaktır**.

```python
# DOĞRU
from app.services.permission_service import has_permission

if not has_permission(user_id, "requirements.delete"):
    return jsonify({"error": "Forbidden"}), 403

# YANLIŞ
if g.role != "admin":   # direktif rol kontrolü yasak
    ...
```

### 7.4 Parola Güvenliği

- Parola hash algoritması: **bcrypt** (cost factor ≥ 12).
- Plain text parola hiçbir zaman loglanamaz, döndürülemez, veritabanına yazılamaz.
- Parola validasyonu: minimum 12 karakter, en az 1 büyük harf, 1 rakam, 1 özel karakter.

---

## 8. Çok Kiracılı (Multi-Tenant) Mimari Kuralları

### 8.1 Tenant İzolasyon Kuralı

**Her** ORM sorgusunda `tenant_id` filtresi zorunludur. İstisna yoktur.

```python
# DOĞRU
requirements = Requirement.query_for_tenant(tenant_id).filter_by(status="active").all()

# YANLIŞ — tenant filtresi eksik; cross-tenant sızıntı riski
requirements = Requirement.query.filter_by(status="active").all()
```

### 8.2 `g.tenant_id` Kullanımı

- `g.tenant_id` değişkeni `init_tenant_context` middleware tarafından set edilir.
- Blueprint, service çağrısına `g.tenant_id`'yi **açık parametre** olarak geçirir.
- Servis katmanı `g`'ye doğrudan erişmez; tenant_id parametre olarak alır.

### 8.3 Platform Admin İşlemleri

- Platform admin endpoint'leri `/api/v1/admin/` prefix altında ayrı blueprint'tedir.
- Bu endpoint'ler `@require_permission("platform_admin.*")` ile korunur.
- Cross-tenant veri erişimi yalnızca platform admin servislerinin explicit metotlarıyla gerçekleşir.

---

## 9. AI Modülü Standartları

### 9.1 LLM Gateway Kullanımı

```python
# DOĞRU — gateway üzerinden çağrı
from app.ai.gateway import LLMGateway

gw = LLMGateway()
result = gw.chat(prompt, model="claude-3-5-haiku-20241022")

# YANLIŞ — provider SDK'sını direkt çağırmak
import anthropic
client = anthropic.Anthropic(api_key=...)  # yasak
```

- AI provider SDK'ları **yalnızca** `app/ai/gateway.py` içinden çağrılır.
- Token bütçesi `AIBudget` servisiyle kontrol altına alınmadan AI çağrısı yapılamaz.

### 9.2 Prompt Yönetimi

- Promtlar `ai_knowledge/prompts/` dizininde YAML/MD dosyaları olarak tutulur; kod içine gömülmez.
- Prompt içinde kullanıcı verisi interpolation yapılırken `{user_input}` gibi değişken yer tutucuları kullanılır; f-string ile doğrudan birleştirme **yasaktır** (injection riski).

### 9.3 AI Audit Logging

- Her LLM çağrısı `AIAuditLog` modeline yazılmak **zorundadır**:
  - `tenant_id`, `user_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`
- Audit log yazımı başarısız olursa AI çağrısı rollback edilmez; ancak `CRITICAL` seviyesinde log atılır.

---

## 10. Veritabanı ve Migration Kuralları

### 10.1 Migration Zorunluluğu

- Tablo/kolon/indeks değişikliği **her zaman** Alembic migration dosyası üretir.
- Manuel `db.create_all()` çağrısı yalnızca `testing` config'de, test fixture'ında izin verilir.
- Migration dosyaları commit edilirken review'da şu kontroller yapılır:
  - Down migration (`downgrade`) yazılmış mı?
  - `nullable=False` kolon ekleniyorsa `server_default` var mı?
  - Index ekleniyorsa `CONCURRENTLY` kullanılmış mı? (production'da lock'u önler)

### 10.2 Ham SQL Kuralı

- Ham SQL yalnızca `db.session.execute(sa.text(...))` ile ve **pozisyonel parametre** (`:param`) aracılığıyla çalıştırılır.
- String birleştirme ile üretilen SQL **yasaktır** (SQL Injection).

```python
# DOĞRU
result = db.session.execute(
    sa.text("SELECT id FROM users WHERE email = :email"),
    {"email": email}
).fetchone()

# YANLIŞ
result = db.session.execute(f"SELECT id FROM users WHERE email = '{email}'")
```

### 10.3 N+1 Sorgu Yasağı

- İlişkisel veri yüklenirken `lazy="select"` ile N+1 oluşturan pattern tespit edildiğinde `joinedload` / `selectinload` zorunludur.
- Servis fonksiyonu içinde döngüde ORM query çağrısı yapılıyorsa bu bir review blocker'dır.

---

## 11. Hata Yönetimi

### 11.1 Fail-Closed İlkesi

- Her exception yakalandığında varsayılan davranış **erişimi reddetmek** ve 500 döndürmektir; hiçbir zaman "fail open" (boş liste, boş erişim) davranışı sergilenmez.

```python
# DOĞRU
try:
    result = some_service.get_data(tenant_id)
except Exception:
    logger.exception("Unexpected error in get_data")
    return jsonify({"error": "Internal server error"}), 500

# YANLIŞ — sessizce boş sonuç döndürme
try:
    result = some_service.get_data(tenant_id)
except Exception:
    result = []   # hata gizlendi; izlenemiyor
```

### 11.2 Exception Hiyerarşisi

```
BaseAppError
├── ValidationError          → 400
├── AuthenticationError      → 401
├── PermissionDeniedError    → 403
├── NotFoundError            → 404
├── ConflictError            → 409
├── BusinessRuleError        → 422
└── ExternalServiceError     → 502
```

- Yeni exception tipi eklendiğinde bu hiyerarşiye dahil edilmeli ve `app/utils/exceptions.py` içinde tanımlanmalıdır.
- Blueprint'teki global error handler bu tipleri otomatik olarak doğru HTTP koduna eşler.

### 11.3 Hata Mesajı Kuralları

- Kullanıcıya dönen hata mesajları **stack trace, query, internal path** içeremez.
- İnternal detay sadece log'a yazılır, response'a koyulmaz.
- Hata mesajları İngilizce yazılır (frontend lokalizasyon yapar).

---

## 12. Loglama Standartları

### 12.1 Logger Edinme

```python
import logging
logger = logging.getLogger(__name__)   # her modülde bu satır; başka yöntem yasak
```

### 12.2 Log Seviyeleri

| Seviye | Kullanım |
|---|---|
| `DEBUG` | Geliştirme izleme; production'da kapalı |
| `INFO` | Normal iş akışı dönüm noktaları (kullanıcı girişi, kaynak oluşturma) |
| `WARNING` | Beklenmeyen ama kurtarılabilir durum (cache miss, retry) |
| `ERROR` | İş fonksiyonunun başarısız olduğu durumlar |
| `CRITICAL` | Audit log yazma başarısızlığı, güvenlik ihlali, veri bütünlüğü sorunu |

### 12.3 Yapılandırılmış Log Formatı

- Tüm log mesajları `%(correlation_id)s` içerir (middleware tarafından set edilir).
- Log içine **asla** `password`, `token`, `api_key`, `secret` değerleri yazılmaz.
- Güvenlik olayları (başarısız auth, yetki ihlali, rate-limit) `SECURITY` logger'ına ayrıca yazılır:

```python
security_logger = logging.getLogger("security")
security_logger.warning(
    "AUTH_FAILURE user_id=%s ip=%s path=%s",
    user_id, request.remote_addr, request.path
)
```

### 12.4 Log Injection Koruması

- Log mesajına interpolate edilen kullanıcı verisi `str()` ile cast edilir ve maksimum 200 karaktere kısılır:

```python
logger.info("Processing requirement title=%s", str(title)[:200])
```

---

## 13. Güvenlik Kontrolleri

### 13.1 Input Validation Kuralları

- Tüm kullanıcı girdisi (URL param, query string, JSON body, header) **sunucu tarafında** allow-list ile doğrulanır.
- String alanların maksimum uzunluğu açıkça kontrol edilir; uzunluk kontrolü olmayan string kabul **yasaktır**.
- Sayısal alanlar tip kontrolü + aralık kontrolü geçirmeden kullanılamaz.

```python
# DOĞRU
name = data.get("name", "")
if not name or len(name) > 255:
    return jsonify({"error": "name is required and must be ≤ 255 chars"}), 400
```

### 13.2 SQL Injection Önleme

- ORM parametreli sorgular default güvenlidir.
- Ham SQL için bkz. [10.2 Ham SQL Kuralı](#102-ham-sql-kuralı).
- SAST: `ruff` B kuralı string-concat SQL ifadelerini işaretler.

### 13.3 SSRF Önleme

- Kullanıcı tarafından kontrol edilen URL'lere `requests.get(user_url)` **yasaktır**.
- Dış HTTP çağrısı gerekiyorsa: allow-list doğrulama + internal IP/metadata bloklama + `httpx` ile.

### 13.4 Secret Yönetimi

- Tüm secret'lar **ortam değişkeni** ile alınır; `os.getenv("SECRET_KEY")`.
- Hard-coded secret (kod içinde string olarak parola, API key, JWT secret) CI'da `gitleaks` ile taranır ve **sıfır tolerans** uygulanır.
- `.env` dosyası repo'ya commit edilmez; `.env.example` (gerçek değer yok) kullanılır.

### 13.5 Güvenlik Header'ları

`init_security_headers` middleware aşağıdakileri zorunlu kılar:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (HSTS, production)

Header middleware'i devre dışı bırakmak için ADR + Mimar onayı gereklidir.

### 13.6 Rate Limiting

- Auth endpoint'leri: **10 req/dk** per IP.
- AI endpoint'leri: **20 req/dk** per user.
- Varsayılan API: **100 req/dk** per IP.
- Rate limit değerleri `app/middleware/rate_limiter.py` içinde merkezi olarak tanımlanır; blueprint içinde farklı değer kullanılmaz.

### 13.7 SBOM (Software Bill of Materials) — Tier 1

- Her production release için [CycloneDX](https://cyclonedx.org/) formatında SBOM artifact üretilir:

```bash
# CI pipeline'ına eklenmeli
pip install cyclonedx-bom
cyclonedx-py requirements requirements.txt --outfile sbom.cyclonedx.json
```

- SBOM, release tag ile birlikte repo artifact olarak saklanır.
- Bu gereksinim OWASP A03 (Software Supply Chain Failures) ve A08 (Software/Data Integrity Failures) kapsamındadır.

### 13.8 Bağımlılık CVE Yaması SLA'sı — Tier 1

CI'da tespit edilen CVE'ler aşağıdaki süre içinde yamalanmak **zorundadır**:

| Seviye | Tanım | Max yamalama süresi |
|---|---|---|
| CRITICAL (9.0–10.0) | Uzaktan sömürülebilir, kimlik doğrulama gerektirmeyen | **48 saat** |
| HIGH (7.0–8.9) | Önemli etki, kısıtlı erişim gerektiriyor | **7 gün** |
| MEDIUM (4.0–6.9) | Sınırlı etki | **30 gün** (sprint planına girer) |
| LOW (0.1–3.9) | Minimal etki | **Bir sonraki major release** |

- Süre aşılırsa platform mimarı ve güvenlik sorumlusuna otomatik bildirim gönderilir.
- `requirements.txt` güncellemesi ayrı bir PR ile yapılır; fonksiyonel değişiklikle birleştirilemez.

---

## 14. Test Standartları

### 14.1 Test Kategorileri ve Yürütme

| Marker | Amaç | CI'da koşul |
|---|---|---|
| `unit` | İzole birim testi (mock bağımlılık) | Her PR'da zorunlu |
| `integration` | Gerçek DB (SQLite in-memory) ile çapraz modül | Her PR'da zorunlu |
| `phase3` | Yönetişim/governance senaryoları | Her PR'da zorunlu |
| `performance` | Benchmark (≥ 5 sn) | Nightly/on-demand |
| `ai_accuracy` | AI doğruluk testleri (API key gerektirir) | Nightly/on-demand |
| `slow` | Zaman aşan testler | Nightly/on-demand |

### 14.2 Test Yazım Kuralları

```python
# Dosya adı: test_<domain>_<konu>.py
# Fonksiyon adı: test_<senaryo>_<beklenen_sonuç>

def test_create_requirement_returns_201_with_valid_data(client):
    """Geçerli veri ile requirement oluşturma 201 döndürmeli."""
    ...

def test_create_requirement_returns_400_without_title(client):
    """Title eksik olduğunda 400 dönmeli."""
    ...
```

### 14.3 Fixture Kuralları

- Her test **kendi verisini oluşturur**; başka test'in verisine bağımlı olamaz.
- `conftest.py` `session` fixture'ı her test sonrası `rollback + drop_all + create_all` yapar; bu davranış değiştirilemez.
- Tenant ID `1` test fixture'larında sabittir; `g.tenant_id = 1` mock etmek yerine auth bypass environ kullanılır.

### 14.4 Coverage Hedefleri

| Kapsam | Hedef | Uygulama |
|---|---|---|
| Yeni kod (PR bazlı) | **≥ %80** | CI gate blocker |
| `app/services/` | **≥ %75** | Sprint sonrası review |
| `app/ai/` | **≥ %60** | Sprint sonrası review |
| `scripts/` | İzleme yok | — |

- Coverage raporu PR comment'i olarak eklenir.
- Test olmadan servis fonksiyonu merge edilemez.

### 14.5 Test Piramidi

```
           ┌──────────┐
           │    E2E   │  ← az, sadece kritik akışlar (Playwright)
          ┌┴──────────┴┐
          │ Integration │ ← DB + API katmanı
         ┌┴────────────┴┐
         │     Unit      │ ← çoğunluk; service + model logic
         └──────────────┘
```

- E2E testler CI'da `staging` ortamına karşı çalışır, `production`'a karşı **çalıştırılamaz**.
- Flaky test (intermittent failure) tespit edildiğinde **merge blocker** olarak işaretlenir ve öncelikli fix edilir.

---

## 15. API Sözleşme Kuralları

### 15.1 URL Yapısı

```
/api/v1/<domain>/<resource>/<id>/<sub-resource>
```

Örnekler:
- `GET /api/v1/testing/cycles` — Liste
- `POST /api/v1/testing/cycles` — Oluştur
- `GET /api/v1/testing/cycles/42` — Tekil
- `PUT /api/v1/testing/cycles/42` — Tam güncelleme
- `PATCH /api/v1/testing/cycles/42` — Kısmi güncelleme
- `DELETE /api/v1/testing/cycles/42` — Sil
- `GET /api/v1/testing/cycles/42/runs` — Alt kaynak listesi

API versiyonu `/api/v1/` prefix'i ile sabit olarak korunur. Yeni major versiyon için ADR gereklidir.

### 15.2 Sayfalama

Tüm liste endpoint'leri standart sayfalama parametrelerini destekler:

```
GET /api/v1/testing/cases?page=1&per_page=20&sort=created_at&order=desc
```

Yanıt:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "pages": 8
}
```

`per_page` maksimum **200**'e kısıtlanır; aşan değer 400 döner.

### 15.3 Tarih/Zaman Formatı

- Tüm tarih/zaman değerleri **ISO 8601 UTC** formatında döner: `"2026-02-19T10:30:00Z"`.
- Client'tan gelen değerler parse edilirken `datetime.fromisoformat()` kullanılır; başarısız parse 400 döner.

---

## 16. CI/CD Kapıları ve Kalite Metrikleri

### 16.1 PR Merge Blocker'ları (Sıfır Tolerans)

Aşağıdakilerden herhangi biri başarısız olursa merge **otomatik engellenir**:

| Kontrol | Araç | Beklenen Sonuç |
|---|---|---|
| Format check | `ruff format --check .` | 0 fark |
| Lint (+ C901 complexity) | `ruff check .` | 0 hata |
| Type check | `mypy app/ --ignore-missing-imports --strict-optional` | 0 hata |
| Unit + Integration testler | `pytest -m "not performance and not ai_accuracy"` | 0 başarısız |
| Yeni kod coverage | `pytest --cov` | ≥ %80 |
| Secret taraması | `gitleaks detect` | 0 bulgu |
| SAST (Critical/High) | Semgrep | 0 Critical, 0 High |
| Bağımlılık CVE | OWASP Dependency-Check | 0 Critical CVE |
| SBOM üretimi | `cyclonedx-py requirements` | Artifact upload başarılı |
| Serializasyon hassas alan | Semgrep kuralı | 0 `password_hash` API response'ta |

### 16.2 CI Pipeline Akışı

```
PR / Commit
    │
    ▼
[Checkout + venv]
    │
    ▼
[ruff format --check && ruff check]  ──── FAIL → Engelle
    │
    ▼
[pytest unit + integration + coverage]  ── FAIL → Engelle
    │
    ▼
[gitleaks secret scan]  ──────────────── FAIL → Engelle
    │
    ▼
[Semgrep SAST]  ──────────────────────── Critical/High → Engelle
    │
    ▼
[OWASP Dependency-Check]  ────────────── Critical CVE → Engelle
    │
    ▼
[Quality Gate: coverage + duplication]  ─ Fail → Engelle
    │
    ▼
[Build / Docker image]
    │
    ▼
[Deploy → Staging]
    │
    ▼
[E2E Smoke Tests (Playwright)]  ──────── FAIL → Release engelle
    │
    ▼
[Release Approval]  ──────────────────── Manuel onay
    │
    ▼
[Deploy → Production]
    │
    ▼
[Post-deploy health check]  ──────────── FAIL → Otomatik rollback
```

### 16.3 Kalite Metrikleri

| Metrik | Hedef | Ölçüm | Araç |
|---|---|---|---|
| Yeni kod test coverage | ≥ %80 | PR bazlı | pytest-cov |
| Yeni kod duplikasyon | ≤ %3 | PR bazlı | ruff |
| Cyclomatic complexity (fonksiyon) | ≤ 10 | Her commit | ruff C901 |
| Cognitive complexity (fonksiyon) | ≤ 15 | Review | flake8-cognitive-complexity |
| Type error sayısı | 0 (yeni kod) | Her commit | mypy |
| Secret bulgusu | 0 | Her commit | gitleaks |
| Critical/High SAST bulgusu | 0 | Her PR | Semgrep |
| Critical CVE (bağımlılık) | 0 | Nightly + PR | OWASP DC |
| Flaky test sayısı | 0 | Her run | pytest |
| Hassas alan API response'ta | 0 | Her PR | Semgrep custom rule |
| SBOM artifact | Mevcut | Her release | cyclonedx-bom |

---

## 17. Kod İnceleme (Code Review) Standartları

> Bu bölüm hem **insan reviewer** hem de **AI review aracı** (GitHub Copilot, Claude, Gemini vb.) tarafından doğrudan uygulanabilecek şekilde yazılmıştır. Her kontrol; aranacak kod deseni, PASS/FAIL kriteri ve severity içerir.

### 17.1 Reviewer Gereksinimleri

| Değişiklik tipi | Min. onay sayısı | Özel gereksinim |
|---|---|---|
| Rutin özellik / bug fix | 1 | — |
| Auth, RBAC, tenant izolasyon değişikliği | 2 | En az 1'i Platform Mimarı |
| AI modülü (gateway, prompt, audit) değişikliği | 2 | En az 1'i Platform Mimarı |
| Migration + DB şema değişikliği | 2 | — |
| Dependency güncelleme | 1 | CI CVE scan temiz olmalı |

- Reviewer kendi yazdığı kodu approve edemez.
- Reviewer 48 saat içinde yanıt vermeli; vermediyse author escalate edebilir.

---

### 17.2 Mimari Review — Kontrol Seti (AI + İnsan)

Aşağıdaki her kontrol; AI'ın kod üzerinde arayacağı **kesin deseni**, **PASS koşulunu** ve **FAIL örneğini** içerir.

#### ARCH-01 — Katman İhlali (BLOCKER)

**Kural:** Blueprint doğrudan ORM sorgusu çalıştıramaz; Model HTTP nesnesine dokunamaz.

| Arama hedefi | FAIL deseni | PASS deseni |
|---|---|---|
| Blueprint dosyasında ORM query | `*_bp.py` içinde `.query.`, `.filter(`, `.filter_by(`, `db.session.execute(` çağrısı | Sadece servis fonksiyon çağrısı |
| Model dosyasında HTTP nesnesi | `models/*.py` içinde `from flask import request`, `jsonify`, `g.` kullanımı | Yok |

```python
# FAIL — blueprint içinde ORM (ARCH-01 ihlali)
@bp.route("/items", methods=["GET"])
def list_items():
    return jsonify([i.to_dict() for i in Item.query.all()])  # BLOCKER

# PASS
@bp.route("/items", methods=["GET"])
def list_items():
    return jsonify(item_service.get_all(g.tenant_id))
```

#### ARCH-02 — Tenant İzolasyon Eksikliği (BLOCKER)

**Kural:** `TenantModel` alt sınıfı olan her modelde tüm sorgular `tenant_id` filtresi içermek zorundadır.

| Arama hedefi | FAIL deseni | PASS deseni |
|---|---|---|
| Tenant filtresi olmayan sorgu | `TenantModel` miras alan sınıf adı + `.query.all()`, `.query.get(`, `.query.filter(` — `tenant_id` içermeyen | `.query_for_tenant(tenant_id)` veya `.filter_by(tenant_id=...)` ile başlayan |

```python
# FAIL — tenant filtresi eksik (ARCH-02 ihlali)
reqs = Requirement.query.filter_by(status="active").all()  # BLOCKER

# PASS
reqs = Requirement.query_for_tenant(tenant_id).filter_by(status="active").all()
```

#### ARCH-03 — DB Commit Katman İhlali (BLOCKER)

**Kural:** `db.session.commit()` yalnızca `app/services/` içinde çağrılabilir.

| Arama hedefi | FAIL deseni |
|---|---|
| Blueprint'te commit | `app/blueprints/*.py` içinde `db.session.commit()` |
| Model metodunda commit | `app/models/*.py` içinde `db.session.commit()` |

#### ARCH-04 — Servis Katmanı `g` Nesnesi Erişimi (BLOCKER)

**Kural:** `app/services/` dizinindeki hiçbir dosya Flask `g` nesnesine erişemez.

| Arama hedefi | FAIL deseni |
|---|---|
| Servis içinde `g` kullanımı | `app/services/*.py` içinde `from flask import g` veya `g.` erişimi |

#### ARCH-05 — AI Gateway Bypass (BLOCKER)

**Kural:** AI provider SDK'ları yalnızca `app/ai/gateway.py` içinden çağrılabilir.

| Arama hedefi | FAIL deseni |
|---|---|
| Gateway dışında provider import | `app/` içinde, `app/ai/gateway.py` dışında: `import anthropic`, `import openai`, `from google import genai`, `google.generativeai` |

---

### 17.3 Güvenlik Review — Kontrol Seti (AI + İnsan)

#### SEC-01 — Hard-coded Secret (BLOCKER)

**Kural:** API key, parola, JWT secret, token — hiçbiri string literal olarak kodda bulunamaz.

| Arama hedefi | FAIL deseni |
|---|---|
| String içinde secret kalıpları | `password = "`, `api_key = "`, `SECRET_KEY = "`, `token = "eyJ`, `Bearer ` (string literal içinde) |

#### SEC-02 — String Birleştirme ile SQL (BLOCKER)

**Kural:** Kullanıcı verisini SQL string'e katmak SQL Injection'dır.

```python
# FAIL — f-string ile SQL (SEC-02 ihlali)
db.session.execute(f"SELECT * FROM users WHERE email = '{email}'")

# PASS
db.session.execute(sa.text("SELECT * FROM users WHERE email = :e"), {"e": email})
```

| Arama hedefi | FAIL deseni |
|---|---|
| SQL string birleştirme | `execute(f"`, `execute("..." +`, `execute("..." %` |

#### SEC-03 — Log'a Hassas Veri (BLOCKER)

**Kural:** `password`, `token`, `api_key`, `secret`, `credential` içeren değişkenler log fonksiyonlarına geçilemez.

```python
# FAIL
logger.info("User login password=%s", password)  # BLOCKER

# PASS
logger.info("User login user_id=%s", user_id)
```

| Arama hedefi | FAIL deseni |
|---|---|
| Log'a hassas parametre | `logger.*(.*password`, `logger.*(.*token`, `logger.*(.*secret`, `logger.*(.*api_key` |

#### SEC-04 — Inline Rol Kontrolü (BLOCKER)

**Kural:** `g.role`, `g.user.role`, `current_user.role` ile yapılan doğrudan rol karşılaştırması merkezi RBAC'ı bypass eder.

```python
# FAIL
if g.role == "admin":  # BLOCKER — merkezi kontrol bypass

# PASS
if not has_permission(g.current_user.id, "requirements.delete"):
```

| Arama hedefi | FAIL deseni |
|---|---|
| Inline rol karşılaştırması | `g.role ==`, `g.role !=`, `.role == "admin"`, `.role in [` |

#### SEC-05 — Hassas Alan API Yanıtında (BLOCKER)

**Kural:** `password_hash`, `reset_token`, `mfa_secret`, `raw_api_key` alanları hiçbir `jsonify()` veya `to_dict()` çağrısının çıktısında bulunamaz.

| Arama hedefi | FAIL deseni |
|---|---|
| Hassas alan explicit return | `"password_hash"`, `"reset_token"`, `"mfa_secret"` literal string bir response dict/list içinde |

#### SEC-06 — `eval` / `exec` Kullanımı (BLOCKER)

| Arama hedefi | FAIL deseni |
|---|---|
| Dinamik kod çalıştırma | `eval(`, `exec(`, `__import__(` — `tests/` ve `scripts/` dışında |

#### SEC-07 — Input Uzunluk Kontrolü Eksikliği (WARNING)

**Kural:** `request.get_json()` veya `request.args` ile alınan her string değişken için uzunluk kontrolü yapılmalıdır.

```python
# FAIL — uzunluk kontrolü yok (SEC-07 uyarı)
name = data.get("name", "")
if not name: ...
# uzunluk kontrolü eksik

# PASS
name = data.get("name", "")
if not name or len(name) > 255: ...
```

---

### 17.4 Kod Kalitesi Review — Kontrol Seti (AI + İnsan)

#### QUAL-01 — `print()` ile Loglama (BLOCKER)

| Arama hedefi | FAIL deseni |
|---|---|
| print kullanımı | `app/` içinde `print(` — `scripts/` hariç |

#### QUAL-02 — `import *` Kullanımı (BLOCKER)

| Arama hedefi | FAIL deseni |
|---|---|
| Wildcard import | `from * import *`, `from app.models import *` |

#### QUAL-03 — `except Exception: pass` (BLOCKER)

**Kural:** Exception yakalanıp sessizce yutulması fail-open davranışı yaratır.

```python
# FAIL
except Exception:
    pass          # BLOCKER

except Exception:
    return []     # BLOCKER

# PASS
except Exception:
    logger.exception("...")
    return jsonify({"error": "Internal server error"}), 500
```

| Arama hedefi | FAIL deseni |
|---|---|
| Hata yutma | `except.*:\s*\n\s*pass`, `except.*:\s*\n\s*return \[\]`, `except.*:\s*\n\s*return {}` (regex) |

#### QUAL-04 — Magic Number / Hard-coded String (WARNING)

```python
# FAIL
if status_code == 422: ...      # 422 nereden geliyor?
time.sleep(300)                 # 300 saniye neden?

# PASS
HTTP_UNPROCESSABLE = 422
CACHE_TTL = 300
```

#### QUAL-05 — Public Fonksiyon Type Hint Eksikliği (WARNING — yeni kod)

**Kural:** Yeni yazılan veya değiştirilen `public` fonksiyonlar için parametre ve dönüş tipi zorunludur.

```python
# FAIL — yeni fonksiyon, type hint yok
def get_requirements(tenant_id, status=None):  # WARNING

# PASS
def get_requirements(tenant_id: int, status: str | None = None) -> list[dict]:
```

#### QUAL-06 — Döngü İçinde ORM Query / N+1 (BLOCKER)

```python
# FAIL — N+1 pattern (QUAL-06 ihlali)
for run in runs:
    steps = TestStep.query.filter_by(run_id=run.id).all()  # BLOCKER

# PASS
runs_with_steps = db.session.execute(
    select(TestRun).options(selectinload(TestRun.steps))
    .where(TestRun.cycle_id == cycle_id)
).scalars().all()
```

| Arama hedefi | FAIL deseni |
|---|---|
| Döngü içi ORM sorgu | `for .* in .*:` bloğu içinde `.query.`, `.filter(`, `.filter_by(` |

#### QUAL-07 — `g` Nesnesine Servis Katmanından Erişim (BLOCKER)

| Arama hedefi | FAIL deseni |
|---|---|
| Servis dosyasında `g` import | `app/services/*.py` içinde `from flask import.*g` veya `flask.g` |

---

### 17.5 Test Review — Kontrol Seti (AI + İnsan)

#### TEST-01 — Test Olmayan Servis Fonksiyonu (BLOCKER)

**Kural:** `app/services/` içinde yeni eklenen veya değiştirilen `public` fonksiyon için `tests/` içinde en az bir test fonksiyonu bulunmalıdır.

AI kontrolü: Değişen fonksiyon adını `tests/` dizininde `grep` ile ara. Bulunmuyorsa BLOCKER.

#### TEST-02 — Test Bağımlılığı (WARNING)

**Kural:** Test fonksiyonu `conftest.py` dışındaki başka bir test fonksiyonunun ürettiği veriye bağımlı olmamalıdır.

```python
# FAIL — başka testin global state'ine bağımlı
def test_update_requirement(client):
    # test_create_requirement'ın yarattığı id=1'i varsayıyor
    res = client.put("/api/v1/requirements/1", json={...})  # WARNING

# PASS
def test_update_requirement(client):
    created = client.post("/api/v1/requirements", json={...}).get_json()
    res = client.put(f"/api/v1/requirements/{created['id']}", json={...})
```

#### TEST-03 — Mutlu Yol Testi Yalnız Yazılamaz (WARNING)

**Kural:** Her yeni endpoint veya servis fonksiyonu için en az bir negatif senaryo testi zorunludur (eksik alan, yanlış tip, yetki hatası).

AI kontrolü: Yeni eklenen test dosyasında `400`, `401`, `403`, `404`, `422` durum kodlarından en az birine `assert` var mı? Yoksa WARNING.

---

### 17.6 Veritabanı Review — Kontrol Seti (AI + İnsan)

#### DB-01 — Migration Down Eksikliği (BLOCKER)

**Kural:** Her Alembic migration dosyasında `downgrade()` fonksiyonu içi dolu olmalıdır.

```python
# FAIL
def downgrade() -> None:
    pass  # BLOCKER

# PASS
def downgrade() -> None:
    op.drop_column("requirements", "new_field")
```

#### DB-02 — NOT NULL Kolon + server_default Eksikliği (BLOCKER)

**Kural:** `nullable=False` yeni kolon eklenirken mevcut satırlar için `server_default` zorunludur.

```python
# FAIL
op.add_column("requirements", sa.Column("priority", sa.String(32), nullable=False))
# BLOCKER — mevcut satırlarda NULL olur

# PASS
op.add_column("requirements", sa.Column("priority", sa.String(32),
    nullable=False, server_default="medium"))
```

#### DB-03 — String Kolon Length Eksikliği (WARNING)

| Arama hedefi | FAIL deseni |
|---|---|
| Uzunluksuz string | `db.Column(db.String)` veya `sa.Column(sa.String)` — parantez içi boş |

---

### 17.7 Feedback Kuralları

Review yapan (insan veya AI) her bulguyu aşağıdaki formatta raporlar:

```
[SEVERİTE] KURAL-KODU — Dosya:satır
Bulgu: <tek cümle>
Neden: <risk açıklaması>
Düzeltme: <önerilen kod veya adım>
```

Severite seviyeleri:
- **BLOCKER** — merge engeli; PR reddedilir.
- **WARNING** — iyileştirme gerekli; 1 sprint içinde kapatılmalı.
- **NITPICK** — tercih meselesi; merge engellemez.

Review yorumları kod yazarını değil, kodu eleştirir. `nit:` prefix nitpick için kullanılır.

---

## 18. PR Şablonu ve Zorunlu Alanlar

Her PR açıklamasında aşağıdaki bölümler **zorunludur**. Eksik PR review'a alınmaz.

```markdown
## Özet
<!-- Ne değişti? 2-3 cümle. -->

## Değişiklik Tipi
- [ ] Bug fix
- [ ] Yeni özellik
- [ ] Refactor
- [ ] Güvenlik düzeltmesi
- [ ] Migration / DB değişikliği
- [ ] Bağımlılık güncellemesi

## Test Kanıtı
<!-- Hangi testler eklendi/güncellendi? Coverage rakamı. -->

## Güvenlik Etkisi
<!-- Auth, RBAC, tenant izolasyon veya secret etkilendi mi? Evet/Hayır + açıklama. -->

## Migration Notu
<!-- DB değişikliği varsa: up/down yazıldı mı? Production'da risk var mı? -->

## Rollback Planı
<!-- Bu PR hızlı geri alınabilir mi? Feature flag kullanıldı mı? -->

## Bağlantılı Issue
<!-- Closes #<issue_no> veya References #<issue_no> -->
```

---

## 19. Yasak Desenler ve Kırmızı Çizgiler

Aşağıdaki desenler **herhangi bir koşulda** kabul edilemez; tespit edildiğinde PR reddedilir ve teknik borç olarak kayıt altına alınır.

| # | Yasak Desen | Neden |
|---|---|---|
| 1 | `Requirement.query.all()` — tenant filtresi olmadan | Cross-tenant veri sızıntısı |
| 2 | `db.session.commit()` blueprint fonksiyonunda | Transaction sahipliği ihlali |
| 3 | Hard-coded API key, secret veya parola | Secret sızıntısı |
| 4 | `except Exception: pass` veya `except Exception: return []` | Hata gizleme, fail-open |
| 5 | AI provider SDK'sı gateway dışından çağırma | Audit/budget bypass |
| 6 | `print()` ile loglama | Yapılandırılmamış log |
| 7 | `eval()`, `exec()` veya `__import__()` dinamik kullanımı | Code injection |
| 8 | String birleştirme ile SQL yapımı | SQL Injection |
| 9 | `g.role` veya `g.user.role` ile inline yetki kontrolü | Merkezi RBAC bypass |
| 10 | Blueprint içinde döngüsel ORM sorgulama (N+1) | Performans felaketi |
| 11 | `import *` kullanımı | İsim çakışması, ruff F tarafından yakalanır |
| 12 | Tenant scope olmadan AI audit log atlamak | Compliance ihlali |
| 13 | User password'un herhangi bir log veya response'a girmesi | Güvenlik ihlali |
| 14 | `API_AUTH_ENABLED=false` production config'de | Kimlik doğrulama bypass |
| 15 | `g` nesnesine servis katmanından erişim | Katman ihlali |

---

---

## 20. Tehdit Modelleme ve Zafiyet Yönetimi

### 20.1 Tehdit Modelleme (OWASP A06 — Insecure Design)

Aşağıdaki koşullardan biri karşılandığında **PR açılmadan önce** lightweight threat modeling yapılır ve PR açıklamasına eklenir:

- Yeni bir authentication/authorization mekanizması ekleniyor.
- Yeni bir dış sistem entegrasyonu (SSO, ödeme, SMS) ekleniyor.
- Yeni bir multi-tenant veri akışı tasarlanıyor.
- AI modülüne kullanıcı girdisini etkileyen yeni bir prompt veya tool ekleniyor.
- Kritik iş verisi (SAP verisi, requirement, test result) için yeni bir export akışı ekleniyor.

**Minimum threat modeling çıktısı (PR description'a eklenir):**
```
## Tehdit Analizi
- Varlıklar: [Hangi veri/işlem etkileniyor?]
- Saldırı yüzeyi: [Giriş noktaları neler?]
- En yüksek risk senaryosu: [Örn. tenant izolasyon bypass]
- Mitigasyon: [Uygulanan kontrol]
- Kalan risk: [Kabul edilen risk + gerekçe]
```

### 20.2 Zafiyet Bildirim Kanalı (ISO 29147 / ISO 30111)

- **Bildirim kanalı:** `security@<platform-domain>` — bu adres README ve `SECURITY.md` dosyasında yayınlanır.
- `SECURITY.md` dosyası repo kökünde bulunmak **zorundadır** ve şu bilgileri içerir:
  - Desteklenen sürümler tablosu
  - Bildirim kanalı
  - Beklenen yanıt SLA'sı (bkz. §13.8)
  - PGP key (opsiyonel ama tavsiye edilir)

- **Triage akışı:**
  1. Bildirim alındı → **48 saat içinde** bildiren tarafa alındı onayı
  2. Teknik doğrulama → CVE severity belirleme
  3. Fix geliştirme → §13.8 SLA'sına göre
  4. Koordineli ifşa → Fix release'den sonra advisory yayını
  5. Postmortem → `docs/reviews/` altında kayıt

---

## 21. AI Review Protokolü

> Bu bölüm, bir AI aracına (GitHub Copilot, Claude Sonnet/Opus, Gemini vb.) bu dökümana göre kod review yaptırmak için **kopyala-yapıştır** hazır prompt şablonları ve beklenen çıktı formatı içerir.

### 21.1 Temel AI Review Prompt'u

```
Sen bu projenin kıdemli kod review uzmanısın.
Aşağıdaki değiştirilmiş kodu (diff veya dosya içeriği) docs/plans/CODING_STANDARDS.md
belgesindeki kurallara göre review et.

─── İNCELENECEK KOD ───
<buraya diff veya dosya içeriği yapıştır>
────────────────────────

Sadece §17'deki kural setini uygula. Her bulgu için şu formatı kullan:

[BLOCKER|WARNING|NITPICK] KURAL-KODU — Dosya:satır
Bulgu: <tek cümle>
Neden: <risk>
Düzeltme: <önerilen kod>

Kontrol et:
- ARCH-01: Blueprint'te doğrudan ORM query var mı?
- ARCH-02: Tüm TenantModel sorgularında tenant_id filtresi var mı?
- ARCH-03: Blueprint veya model dosyasında db.session.commit() var mı?
- ARCH-04: app/services/ içinde Flask g nesnesine erişim var mı?
- ARCH-05: app/ai/gateway.py dışında provider SDK import'u var mı?
- SEC-01: String literal olarak API key, password, token var mı?
- SEC-02: f-string veya string birleştirme ile SQL üretimi var mı?
- SEC-03: logger çağrısında password, token, secret parametresi var mı?
- SEC-04: g.role veya .role == "admin" ile inline rol kontrolü var mı?
- SEC-05: password_hash, reset_token, mfa_secret API yanıtında var mı?
- SEC-06: eval(), exec(), __import__() çağrısı var mı?
- SEC-07: request'ten alınan string değişkende uzunluk kontrolü var mı?
- QUAL-01: app/ içinde (scripts/ hariç) print() kullanımı var mı?
- QUAL-02: from * import * kullanımı var mı?
- QUAL-03: except bloğu pass veya return [] ile bitmiş mi?
- QUAL-04: Açıklamasız magic number veya hard-coded string var mı?
- QUAL-05: Yeni/değiştirilen public fonksiyonda type hint eksik mi?
- QUAL-06: for döngüsü içinde ORM query var mı (N+1)?
- QUAL-07: app/services/ içinde Flask g import'u var mı?
- TEST-01: Değiştirilen servis fonksiyonunun testi tests/ içinde var mı?
- TEST-02: Yeni test conftest.py dışında başka teste bağımlı mı?
- TEST-03: Yeni endpoint testlerinde en az 1 hata senaryosu (400/401/403/404/422) var mı?
- DB-01: Migration'da downgrade() fonksiyonu dolu mu (pass değil)?
- DB-02: nullable=False yeni kolon için server_default var mı?
- DB-03: db.Column(db.String) — uzunluk parametresi eksik mi?

Son olarak şunu ekle:
ÖZET: <N blocker, M warning, K nitpick tespit edildi.>
MERGE: <BLOCKER VAR — merge yapılmamalı | TEMİZ — merge onaylanabilir>
```

---

### 21.2 Mimari Odaklı Review Prompt'u

```
Sen bu projenin mimarısın. Aşağıdaki kodu, mevcut projenin
Blueprint → Service → Model katman mimarisine ve multi-tenant tasarımına
göre değerlendir.

─── İNCELENECEK KOD ───
<buraya kod yapıştır>
────────────────────────

Şu sorulara yanıt ver:

1. KATMAN UYUMU
   - Bu kod hangi katmanda duruyor? (blueprint / service / model / yardımcı)
   - Katman sınırları ihlal ediliyor mu? (ARCH-01 – ARCH-04)
   - Servis → Servis bağımlılığı döngüsel mi?

2. TENANT İZOLASYONU
   - TenantModel miras alan tüm modeller için tenant_id filtresi var mı? (ARCH-02)
   - g.tenant_id, servis parametresi olarak mı geçiliyor, yoksa servisten g'ye mi erişiliyor?

3. YETKİLENDİRME
   - Tüm route'lar @require_permission decorator'ı ile korunmuş mu?
   - Yeni domain için Permission seed verisi tanımlandı mı?
   - İzin kodu formatı <domain>.<action> standardına uyuyor mu?

4. YENİ BAĞIMLILIK
   - Yeni import eklendi mi? Bu bağımlılık gereksiz mi veya katman ihlali yaratıyor mu?

5. MİMARİ BORÇ
   - Bu değişiklik mevcut teknik borcu artırıyor mu, azaltıyor mu?

Her bulgu için:
[BLOCKER|WARNING|NITPICK] — kısa açıklama + önerilen düzeltme
```

---

### 21.3 Güvenlik Odaklı Review Prompt'u (OWASP hizalı)

```
Sen bir uygulama güvenlik uzmanısın. Aşağıdaki Flask/Python kodunu
OWASP Top 10:2025 ve projenin CODING_STANDARDS.md §13 kurallarına göre
güvenlik review'u yap.

─── İNCELENECEK KOD ───
<buraya kod yapıştır>
────────────────────────

Aşağıdaki güvenlik kontrol setini uygula ve bulguları sırala:

OWASP A01 — Broken Access Control
[ ] Her route @require_permission ile korumalı mı?
[ ] Obje düzeyinde authorization (IDOR) kontrolü var mı?
[ ] TenantModel sorgularında tenant_id zorunlu mu? (ARCH-02)

OWASP A02 — Security Misconfiguration  
[ ] API_AUTH_ENABLED=false production config'de var mı?
[ ] Default credential hard-coded var mı?
[ ] Gereksiz debug flag var mı?

OWASP A03 — Injection
[ ] f-string ile SQL var mı? (SEC-02)
[ ] Kullanıcı girdisi OS command'a geçiyor mu?
[ ] Template injection riski var mı?

OWASP A04 — Cryptographic Failures
[ ] Deprecated hash (md5, sha1) kullanımı var mı?
[ ] Plain text parola log veya response'ta var mı? (SEC-03, SEC-05)

OWASP A05 — Security Misconfiguration (daha geniş)
[ ] Security header middleware bypass var mı?

OWASP A07 — Authentication Failures
[ ] Token süreleri config'den mi okunuyor, hard-coded mi?
[ ] bcrypt cost factor < 12 mi?

OWASP A09 — Security Logging Failures
[ ] Güvenlik olayları (auth fail, yetki ihlali) security logger'a yazılıyor mu?
[ ] Log injection koruması (kullanıcı verisi str()[:200]) var mı?

OWASP A10 — Exceptional Conditions
[ ] except bloğunda fail-open davranış var mı? (QUAL-03)
[ ] Kullanıcıya stack trace dönüyor mu?

Her bulgu için:
[OWASP-AXX | SEVER\u0130TE] Dosya:satır
Bulgu: <açıklama>
Exploit senaryosu: <kısa saldırı yolu>
Düzeltme: <önerilen kod veya adım>
```

---

### 21.4 Beklenen AI Review Çıktı Formatı

AI'ın dönmesi gereken çıktı şu yapıya uymalıdır. Bu format PR comment'e yapıştırılabilir:

```markdown
## AI Code Review — CODING_STANDARDS.md §17

### Bulgular

---

**[BLOCKER] ARCH-02 — app/blueprints/requirement_bp.py:84**
Bulgu: tenant_id filtresi olmayan Requirement sorgusu.
Neden: Cross-tenant veri sızıntısı; başka tenant'ın gereksinimleri görülebilir.
Düzeltme:
```python
# Mevcut (FAIL)
reqs = Requirement.query.filter_by(status="active").all()

# Düzeltilmiş (PASS)
reqs = Requirement.query_for_tenant(g.tenant_id).filter_by(status="active").all()
```

---

**[WARNING] QUAL-05 — app/services/new_service.py:12**
Bulgu: create_item() fonksiyonunda dönüş tipi belirtilmemiş.
Neden: mypy kontrolü geçemez; API sözleşmesi belirsiz kalır.
Düzeltme: `def create_item(tenant_id: int, data: dict) -> dict:`

---

### Özet

| Seviye | Sayı |
|---|---|
| BLOCKER | 1 |
| WARNING | 1 |
| NITPICK | 0 |

**MERGE: BLOCKER VAR — merge yapılmamalı.**
```

---

### 21.5 AI Review İçin Kural Hızlı Referans Tablosu

AI'a dökümandan bağımsız, tek tablo olarak verilebilecek kural özeti:

| Kural | Kontrol | Seviye | Ne aranır |
|---|---|---|---|
| ARCH-01 | Katman ihlali | BLOCKER | `*_bp.py` dosyasında ORM query |
| ARCH-02 | Tenant izolasyon | BLOCKER | TenantModel sorgusu + `tenant_id` yok |
| ARCH-03 | DB commit katmanı | BLOCKER | Blueprint/model'de `db.session.commit()` |
| ARCH-04 | Servis `g` erişimi | BLOCKER | `services/*.py` içinde Flask `g` |
| ARCH-05 | AI gateway bypass | BLOCKER | `gateway.py` dışında provider SDK import |
| SEC-01 | Hard-coded secret | BLOCKER | `api_key = "`, `password = "`, `token = "eyJ` |
| SEC-02 | SQL injection | BLOCKER | `execute(f"` veya string `+` ile SQL |
| SEC-03 | Log'a hassas veri | BLOCKER | `logger.*(.*password\|.*token\|.*secret` |
| SEC-04 | Inline rol kontrolü | BLOCKER | `g.role ==`, `.role == "admin"` |
| SEC-05 | Hassas alan response | BLOCKER | `"password_hash"` response dict içinde |
| SEC-06 | eval/exec | BLOCKER | `eval(`, `exec(` app/ içinde |
| SEC-07 | Uzunluk kontrolü | WARNING | `data.get("name")` + `len()` yok |
| QUAL-01 | print() loglama | BLOCKER | `print(` app/ içinde |
| QUAL-02 | import * | BLOCKER | `from * import *` |
| QUAL-03 | Hata yutma | BLOCKER | `except:` + `pass` veya `return []` |
| QUAL-04 | Magic number | WARNING | Açıklamasız sayısal literal |
| QUAL-05 | Type hint eksik | WARNING | Yeni public fonksiyon: parametre/return tipi yok |
| QUAL-06 | N+1 sorgu | BLOCKER | `for` döngüsü içinde ORM query |
| QUAL-07 | Servis `g` erişimi | BLOCKER | `services/*.py` içinde `from flask import g` |
| TEST-01 | Test yok | BLOCKER | Yeni servis fonksiyonu → `tests/` içinde arama |
| TEST-02 | Test bağımlılığı | WARNING | Test hard-coded id ile başka teste bağımlı |
| TEST-03 | Sadece happy path | WARNING | Yeni endpoint testi: 4xx assert yok |
| DB-01 | downgrade() boş | BLOCKER | Alembic migration'da `downgrade(): pass` |
| DB-02 | server_default eksik | BLOCKER | `nullable=False` + `server_default` yok |
| DB-03 | String length yok | WARNING | `db.Column(db.String)` uzunluksuz |

---

## EK A: Hızlı Referans Komutları

```bash
# Linting ve format kontrolü
make lint
make format

# Testleri çalıştır
make test                              # unit + integration
pytest tests/ -m unit -v               # sadece unit
pytest tests/ -m integration -v        # sadece integration
pytest tests/ --cov=app --cov-report=term-missing  # coverage

# E2E testler
cd e2e && npx playwright test

# Migration
make db-migrate                        # yeni migration oluştur
make db-upgrade                        # migration uygula

# Secret taraması (gitleaks kurulu ise)
gitleaks detect --source=. --no-git

# Type checking
.venv/bin/mypy app/ --ignore-missing-imports --strict-optional

# SBOM üretimi
.venv/bin/pip install cyclonedx-bom
.venv/bin/cyclonedx-py requirements requirements.txt --outfile sbom.cyclonedx.json

# Pre-commit kurulumu (bir kere yapılır)
.venv/bin/pre-commit install

# Tenant yönetimi
make tenant-list
make tenant-create ID=demo NAME="Demo Tenant"
```

---

## EK B: Mimari Karar Kaydı (ADR) Gerektiren Değişiklikler

Aşağıdaki değişiklikler için ADR oluşturulması ve Mimar onayı zorunludur. ADR dosyaları `docs/plans/adr/` altında tutulur.

- Python sürüm yükseltmesi
- Flask major sürüm değişikliği
- ORM (SQLAlchemy) major versiyon değişikliği
- Authentication mekanizması değişikliği (bcrypt → Argon2 vb.)
- AI provider değişikliği (LLMGateway provider ekleme dışında)
- Multi-tenant strateji değişikliği (row-level → schema-level vb.)
- Yeni dış servis entegrasyonu (ödeme, SMTP, SSO provider)
- Veritabanı motoru değişikliği (SQLite dev → başka motor)
- Lisans değişikliği olan bağımlılık eklenmesi
- Security header politikası değişikliği
- SBOM format değişikliği (CycloneDX → SPDX veya tersi)
- Zafiyet bildirim kanalı değişikliği
- Tehdit modelleme sürecinin kapsam genişletmesi

---

---

## EK C: Global Standart Uyum Matrisi

Bu dökümanın hangi global standarda hizalandığını gösteren referans tablosu:

| Bu dökümandaki bölüm | Global standart referansı |
|---|---|
| §2 Python kuralları, §3 mimari | PEP 8, PEP 484, Google Style Guide |
| §7 AuthN/AuthZ, §13.1–13.5 | OWASP ASVS v5.0 Lvl2, NIST SP 800-63-4 |
| §8 Multi-tenant | OWASP A01 Broken Access Control |
| §9 AI modülü | OWASP LLM Top 10 (2025-v2) |
| §10 DB/migration, §13.2 SQL | OWASP A05 Injection, CERT SEI |
| §11 Hata yönetimi | OWASP A10, NIST SSDF PW.5 |
| §12 Loglama | OWASP A09, NIST SP 800-92 |
| §13.7 SBOM | ISO/IEC 5962:2021 (SPDX), CycloneDX (ECMA-424) |
| §13.8 CVE SLA | ISO/IEC 30111:2019, NIST NVD |
| §14 Test standartları | ISO/IEC/IEEE 29119, test pyramid |
| §15 API sözleşme | RFC 7807 (Problem Details), REST best practices |
| §16 CI/CD kapıları | NIST SP 800-204C DevSecOps, NIST SSDF |
| §20.1 Tehdit modelleme | OWASP A06 Insecure Design, STRIDE |
| §20.2 Zafiyet bildirimi | ISO/IEC 29147:2018, ISO/IEC 30111:2019 |

---

*Bu döküman, projenin teknik mimarisi ve öngörülen büyüme yolu doğrultusunda düzenli olarak güncellenir. Sorular ve öneriler için mimari review sürecini kullanın.*
