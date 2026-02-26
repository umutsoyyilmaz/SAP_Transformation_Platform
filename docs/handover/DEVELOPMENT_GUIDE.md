# Development Guide

## Gelistirme Ortami Kurulumu

### Gereksinimler
- Python 3.11+
- PostgreSQL 14+ (prod) veya SQLite (dev/test)
- Node.js 18+ (sadece E2E testler icin)
- Git

### Hizli Baslangic
```bash
git clone <repo-url>
cd SAP_Transformation_Platform

# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Bagimliklar
pip install -r requirements.txt

# Ortam degiskenleri
cp .env.example .env
# .env dosyasini duzenle (DB URL, secret key, API key'ler)

# Veritabani
flask db upgrade

# Calistir
flask run
# veya
make run
```

### Makefile Komutlari
```bash
make setup       # Tam kurulum (venv + deps + db)
make run         # Flask development server
make test        # pytest calistir
make lint        # Ruff lint
make format      # Ruff format
make typecheck   # mypy
make seed        # Demo veri yukle
make e2e         # Playwright E2E testleri
```

---

## Yeni Feature Ekleme Kontrol Listesi

### 1. Model Katmani

```python
# app/models/<domain>.py
class NewEntity(TenantModel):
    __tablename__ = "new_entities"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"))
    name = db.Column(db.String(255), nullable=False)  # uzunluk ZORUNLU
    status = db.Column(db.String(32), nullable=False, default="draft")

    SENSITIVE_FIELDS = {"password_hash"}

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name)
                for c in self.__table__.columns
                if c.name not in self.SENSITIVE_FIELDS}
```

- [ ] `TenantModel` miras (tenant-scoped ise)
- [ ] `__tablename__` explicit
- [ ] String kolonlarda uzunluk belirtilmis
- [ ] `to_dict()` metodu var
- [ ] `SENSITIVE_FIELDS` tanimli (hassas alan varsa)

### 2. Alembic Migration

```bash
flask db migrate -m "Add new_entities table"
flask db upgrade
```

- [ ] Migration dosyasi olusturuldu
- [ ] `upgrade()` ve `downgrade()` dogru
- [ ] FK'ler `ondelete="CASCADE"` (tenant-scoped)

### 3. Service Katmani

```python
# app/services/<domain>_service.py
import logging
from app.models import db
from app.models.audit import write_audit

logger = logging.getLogger(__name__)

def create_entity(tenant_id: int, data: dict) -> dict:
    """
    Create a new entity scoped to tenant.

    Args:
        tenant_id: Owning tenant's primary key.
        data: Validated input dict.

    Returns:
        Serialized entity dict.

    Raises:
        ValidationError: If required fields missing.
    """
    # 1. Input validation
    name = (data.get("name") or "").strip()
    if not name or len(name) > 255:
        raise ValidationError("name is required (max 255 chars)")

    # 2. ORM olustur
    entity = NewEntity(tenant_id=tenant_id, name=name)
    db.session.add(entity)
    db.session.flush()  # ID olustur

    # 3. Commit (sadece service'te)
    db.session.commit()

    # 4. Audit
    write_audit(entity_type="new_entity", entity_id=entity.id,
                action="create", tenant_id=tenant_id)

    logger.info("Entity created id=%s tenant=%s", entity.id, tenant_id)
    return entity.to_dict()
```

- [ ] Type hint + docstring (tum public fonksiyonlar)
- [ ] `tenant_id` parametre olarak alinir (`g`'den OKUNMAZ)
- [ ] Input validation (uzunluk + zorunlu alanlar)
- [ ] `db.session.commit()` var
- [ ] `write_audit()` cagiriliyor
- [ ] `logger` kullaniliyor (`print()` YASAK)

### 4. Blueprint Katmani

```python
# app/blueprints/<domain>_bp.py
from flask import Blueprint, request, jsonify, g
from app.services.permission_service import require_permission

bp = Blueprint("new_domain", __name__, url_prefix="/api/v1")

@bp.route("/programs/<int:program_id>/entities", methods=["POST"])
@require_permission("entities.create")
def create_entity(program_id):
    data = request.get_json(silent=True) or {}
    try:
        result = entity_service.create_entity(
            tenant_id=g.jwt_tenant_id,
            data=data
        )
        return jsonify(result), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError:
        return jsonify({"error": "Not found"}), 404
    except Exception:
        logger.exception("Unexpected error")
        return jsonify({"error": "Internal server error"}), 500
```

- [ ] `@require_permission` decorator var
- [ ] ORM cagirisi YOK (sadece service cagirilir)
- [ ] `tenant_id=g.jwt_tenant_id` service'e gonderiliyor
- [ ] Dogru HTTP kodlari (201, 400, 401, 403, 404, 422, 500)

### 5. Frontend

```javascript
// static/js/views/<feature>.js — IIFE modulu
const FeatureView = (() => {
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = PGEmptyState.html({
                icon: 'programs', title: 'Program Secin'
            });
            return;
        }
        main.innerHTML = `...`;
        // API.get(...), PGForm, PGButton, PGPanel kullan
    }
    return { render };
})();
```

- [ ] `app.js` views registry'sine eklendi
- [ ] `programRequiredViews`'e eklendi (program gerekliyse)
- [ ] `index.html`'de `<script>` tag'i eklendi (`app.js`'den ONCE)
- [ ] Sidebar'da `data-view` item eklendi
- [ ] `--pg-*` CSS token'lari kullanildi (hardcode renk YOK)

### 6. Testler

```python
# tests/test_<domain>_<feature>.py
def test_create_entity_returns_201(client):
    """Valid payload returns 201."""
    res = client.post("/api/v1/programs/1/entities", json={"name": "Test"})
    assert res.status_code == 201

def test_create_entity_returns_400_without_name(client):
    """Missing name returns 400."""
    res = client.post("/api/v1/programs/1/entities", json={})
    assert res.status_code == 400
```

- [ ] Her endpoint icin en az 1 pozitif test (200/201)
- [ ] Her endpoint icin en az 1 negatif test (400/401/403/404)
- [ ] Her test kendi verisini olusturur (baska teste bagimlilik YOK)
- [ ] `client` fixture ile HTTP cagirisi

---

## Test Altyapisi

### Fixture Hiyerarsisi (tests/conftest.py)

```
app (session scope)        # Flask app instance
  |
  +-- _setup_db            # Tablo olusturma/silme
        |
        +-- session (function scope, autouse)
        |     |-- App context ac
        |     |-- RBAC cache invalidate
        |     |-- Default tenant olustur
        |     |-- >>> TEST CALISIR <<<
        |     |-- RBAC cache invalidate
        |     +-- Tablolari drop + recreate (clean state)
        |
        +-- client          # Flask test client
        +-- default_tenant  # Test Tenant entity
        +-- program         # Kolaylik: test Program olusturur
```

### Test Calistirma
```bash
# Tum testler
pytest tests/ -q

# Tek dosya
pytest tests/test_api_program.py -v

# Tek test
pytest tests/test_api_program.py::test_create_program_returns_201 -v

# Paralel (hizli)
pytest tests/ -n auto

# Coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Alembic Migration Rehberi

### Yeni Migration Olusturma
```bash
# 1. Model'i degistir (app/models/*.py)
# 2. Migration dosyasi olustur
flask db migrate -m "Add status column to programs"
# 3. Olusturulan dosyayi kontrol et (migrations/versions/...)
# 4. Uygula
flask db upgrade
```

### Guvenli Pattern'ler
- Yeni kolon ekleme: `op.add_column('table', sa.Column(...))`
- Nullable kolon ekleme: Guvenli (veri kaybi yok)
- Non-nullable kolon ekleme: Once nullable olarak ekle, backfill yap, sonra nullable=False yap
- Tablo silme: Once ForeignKey'leri kaldir

### Dikkat
- Auto-add columns (`_auto_add_missing_columns`) sadece PostgreSQL'de calisir
- SQLite'da `db.create_all()` kullanilir (migration gereksiz)
- Migration dosyalari her zaman commit edilmeli

---

## Pre-commit Hook

**Dosya:** `.git/hooks/pre-commit`

Her commit'te calisir:
1. Staged dosya sayisi kontrolu (>15 uyari)
2. Degisen satir sayisi kontrolu (>500 uyari)
3. `pytest tests/` calistirma (basarisiz -> commit engellenir)

Atlamak icin: `git commit --no-verify` (sadece acil durumlarda)

---

## Sik Yapilan Hatalar

| Hata | Dogru Yaklasim |
|------|----------------|
| Blueprint'te `Model.query.all()` | Service katmaninda `query_for_tenant(tenant_id)` |
| Service'te `g.tenant_id` okuma | `tenant_id` parametre olarak al |
| Model'de `from flask import request` | Model'de HTTP nesnesi YASAK |
| `print("debug")` | `logger.debug("mesaj")` |
| `except Exception: pass` | `except Exception: logger.exception("hata")` |
| `API_KEY = "sk-..."` | `.env` dosyasindan `os.environ.get()` |
| Blueprint'ten blueprint cagirma | Ortak logic service'e tasir |
| `f"SELECT * FROM {table}"` | SQLAlchemy ORM veya parameterized query |
