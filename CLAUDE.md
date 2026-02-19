# CLAUDE.md — SAP Transformation Platform

> Bu dosya Claude Code, Claude Sonnet/Opus, OpenAI Codex ve benzeri agent tabanlı
> AI araçları tarafından otomatik olarak okunur. Her kod üretme/düzenleme işleminde
> aşağıdaki kurallar geçerlidir.
>
> Tam standartlar: `docs/plans/CODING_STANDARDS.md`
> AI review kuralları: `docs/plans/CODING_STANDARDS.md` §17 ve §21

---

## Proje Özeti

SAP dönüşüm projelerini yönetmek için çok kiracılı (multi-tenant), Flask tabanlı bir SaaS platform.

- **Python 3.11+ / Flask 3.1** — Application Factory pattern
- **SQLAlchemy 2.0** — ORM; multi-tenant row-level isolation
- **PostgreSQL** (prod) / **SQLite in-memory** (test)
- **JWT + API Key** kimlik doğrulama; **DB-backed RBAC** (`permission_service.py`)
- **LLM Gateway** (`app/ai/gateway.py`) — tüm AI çağrıları buradan geçer
- **Ruff** lint/format, **mypy** type check, **pytest** test, **Playwright** E2E

---

## Mutlak Kurallar (ihlal edilemez)

### 1. Katman Mimarisi

```
Blueprint  →  Service  →  Model  →  DB
```

| Kural | Açıklama |
|---|---|
| Blueprint ≠ ORM | Blueprint dosyasında asla `.query.`, `.filter(`, `db.session.execute(` çağrısı yapılmaz |
| Service = commit sahibi | `db.session.commit()` yalnızca `app/services/` içinde |
| Model ≠ HTTP | Model dosyasında `request`, `g`, `jsonify` import/kullanımı yasak |
| Service ≠ g | Servis katmanı `g` nesnesine erişemez; `tenant_id` parametre olarak alır |
| Blueprint ≠ Blueprint | Bir blueprint başka bir blueprint fonksiyonu çağıramaz |

### 2. Multi-Tenant İzolasyon

`TenantModel` miras alan her model için tüm ORM sorgularında `tenant_id` filtresi zorunludur:

```python
# DOĞRU
items = Item.query_for_tenant(tenant_id).filter_by(status="active").all()

# YANLIŞ — tenant filtresi eksik — asla üretme
items = Item.query.all()
```

### 3. Güvenlik — Sıfır Tolerans

```python
# ASLA üretme:
API_KEY = "sk-abc123"               # hard-coded secret
db.session.execute(f"...{email}")   # f-string SQL
except Exception: pass              # hata yutma
if g.role == "admin":               # inline rol kontrolü
import anthropic                    # gateway dışında AI SDK
print("debug")                      # print() loglama
eval(user_input)                    # code injection
```

### 4. API Key / JWT / Servis Ayrımı

```python
# AI çağrısı — SADECE gateway üzerinden
from app.ai.gateway import LLMGateway
gw = LLMGateway()
result = gw.chat(prompt, model="claude-3-5-haiku-20241022")

# Yetkilendirme — SADECE permission_service üzerinden
from app.services.permission_service import has_permission
if not has_permission(user_id, "requirements.delete"):
    return jsonify({"error": "Forbidden"}), 403
```

---

## Kod Üretim Standartları

### İsimlendirme
- Dosya: `snake_case.py`
- Sınıf: `PascalCase`
- Fonksiyon/değişken: `snake_case`
- Sabit: `UPPER_SNAKE_CASE`
- Blueprint: `<domain>_bp`
- Boolean: `is_`, `has_`, `can_` prefix
- Flask g alanları: yalnızca `g.current_user`, `g.tenant_id`

### Her Yeni/Değiştirilen Public Fonksiyon

```python
def create_requirement(tenant_id: int, data: dict) -> dict:
    """
    Create a new requirement scoped to the given tenant.

    Args:
        tenant_id: Owning tenant's primary key.
        data: Validated input dict from blueprint.

    Returns:
        Serialized requirement dict.

    Raises:
        ValidationError: If required fields are missing.
    """
    ...
```

- Type hint zorunlu (parametre + dönüş)
- Google-style docstring zorunlu
- Import sırası: stdlib → third-party → `app.*` → relative

### Her Blueprint Route

```python
@bp.route("/api/v1/<domain>/<resource>", methods=["POST"])
@require_permission("<domain>.create")
def create_resource():
    data = request.get_json(silent=True) or {}
    # 1. input validation (uzunluk kontrolü dahil)
    # 2. service çağrısı (tenant_id = g.tenant_id)
    # 3. JSON response + doğru HTTP kodu
```

### Her Model

```python
class MyModel(TenantModel):                     # tenant-scoped ise TenantModel
    __tablename__ = "my_models"                 # explicit zorunlu
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # uzunluk zorunlu
    status = db.Column(db.String(32), nullable=False, default="draft")

    SENSITIVE_FIELDS = {"password_hash", "reset_token"}

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name)
                for c in self.__table__.columns
                if c.name not in self.SENSITIVE_FIELDS}
```

### Hata Yönetimi

```python
# DOĞRU — fail closed
try:
    result = service.get_data(tenant_id)
except ValidationError as e:
    return jsonify({"error": str(e)}), 400
except NotFoundError:
    return jsonify({"error": "Resource not found"}), 404
except Exception:
    logger.exception("Unexpected error")
    return jsonify({"error": "Internal server error"}), 500
```

### Loglama

```python
logger = logging.getLogger(__name__)  # her dosyanın en üstünde

# DOĞRU
logger.info("Requirement created id=%s tenant=%s", req.id, tenant_id)
logger.info("Processing title=%s", str(title)[:200])  # kullanıcı verisi kısalt

# YANLIŞ
logger.info("password=%s token=%s", password, token)  # hassas veri
print("debug")  # print yasak
```

---

## Test Üretim Kuralları

```python
# Dosya adı: test_<domain>_<konu>.py
# Fonksiyon adı: test_<senaryo>_<beklenen_sonuç>

def test_create_requirement_returns_201_with_valid_data(client):
    """Valid payload returns 201."""
    res = client.post("/api/v1/requirements", json={"title": "T1"})
    assert res.status_code == 201

def test_create_requirement_returns_400_without_title(client):
    """Missing title returns 400."""
    res = client.post("/api/v1/requirements", json={})
    assert res.status_code == 400
```

- Her endpoint için en az 1 negatif test (400/401/403/404/422)
- Her test kendi verisini oluşturur (başka teste bağımlılık yasak)
- `client` fixture ile HTTP çağrısı, `session` fixture autouse (rollback)

---

## HTTP Kodu Referansı

| Durum | Kod |
|---|---|
| Oluşturuldu | 201 |
| Başarılı okuma/güncelleme | 200 |
| Geçersiz input | 400 |
| Kimlik doğrulama hatası | 401 |
| Yetki yok | 403 |
| Bulunamadı | 404 |
| İş kuralı ihlali | 422 |
| Sunucu hatası | 500 |

---

## Dosya Düzenleme Öncesi Kontrol

Bir dosyayı değiştirmeden önce şu soruları yanıtla:

1. Bu değişiklik hangi katmanda? (blueprint / service / model)
2. Tenant izolasyonu etkileniyor mu?
3. Auth/permission mantığı değişiyor mu? → 2 reviewer + mimar onayı
4. DB şeması değişiyor mu? → Alembic migration gerekli
5. AI gateway kullanılıyor mu? → AIAuditLog yazılıyor mu?

---

## Hızlı Kontrol Listesi (kod üretmeden önce)

- [ ] Blueprint → ORM çağrısı yok
- [ ] Service → `db.session.commit()` var
- [ ] Model → HTTP nesnesi yok
- [ ] Tüm TenantModel sorguları → `query_for_tenant(tenant_id)`
- [ ] Tüm route'lar → `@require_permission` var
- [ ] Tüm string inputlar → uzunluk kontrolü var
- [ ] Hard-coded secret/password yok
- [ ] `print()` yok — `logger.` kullanılıyor
- [ ] `except Exception: pass` yok
- [ ] AI çağrısı `LLMGateway` üzerinden
- [ ] Yeni fonksiyon → type hint + docstring var
- [ ] Yeni endpoint → test dosyasında negatif senaryo var
