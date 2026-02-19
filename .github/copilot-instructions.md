# GitHub Copilot — SAP Transformation Platform Coding Instructions

> This file is automatically loaded by GitHub Copilot for every session in this repository.
> Full standards: `docs/plans/CODING_STANDARDS.md`
> AI review rules: `docs/plans/CODING_STANDARDS.md` §17 and §21

---

## Stack Context

- **Language:** Python 3.11+
- **Framework:** Flask 3.1 (Application Factory pattern)
- **ORM:** SQLAlchemy 2.0 + Flask-Migrate (Alembic)
- **Auth:** JWT (PyJWT) + API Key (RBAC via `permission_service`)
- **DB:** PostgreSQL (prod) / SQLite in-memory (test)
- **Cache:** Redis via `app/services/cache_service.py`
- **AI:** Multi-provider LLM via `app/ai/gateway.py` ONLY
- **Linter/Formatter:** Ruff (`ruff.toml`) — no Black, no isort
- **Type checker:** mypy
- **Testing:** pytest with markers: `unit`, `integration`, `phase3`

---

## Architecture — ALWAYS Enforce

The project uses a strict 3-layer architecture. NEVER violate layer boundaries:

```
Blueprint (app/blueprints/*_bp.py)
    ↓ calls
Service  (app/services/*_service.py)
    ↓ calls
Model    (app/models/*.py)
```

**Layer rules — generate code that follows these exactly:**

1. Blueprint = HTTP parse + input validation + service call + JSON response. Nothing else.
2. Service = business logic + `db.session.commit()`. The ONLY place commits happen.
3. Model = ORM mapping + `to_dict()`. NEVER imports `request`, `g`, or `jsonify`.
4. Service NEVER accesses Flask `g` directly — tenant_id is passed as a parameter.
5. Blueprint NEVER calls another blueprint's functions.
6. Service MAY call another service.

---

## Multi-Tenant — ALWAYS Enforce

Every model that inherits `TenantModel` MUST be queried with `tenant_id` scoping:

```python
# ALWAYS — correct
items = Item.query_for_tenant(tenant_id).filter_by(status="active").all()

# NEVER — missing tenant scope
items = Item.query.filter_by(status="active").all()
```

- Blueprint passes `g.tenant_id` explicitly to every service call.
- Service receives `tenant_id` as a parameter — never reads `g` itself.

---

## Code Generation Rules

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Boolean variables: `is_`, `has_`, `can_` prefix
- Blueprint variable: `<domain>_bp` (e.g. `testing_bp`)
- Private helpers: `_snake_case`
- Flask context: only `g.current_user`, `g.tenant_id` — no other `g` fields

### Type Hints
Always add type hints on every new or modified public function:
```python
# ALWAYS
def create_requirement(tenant_id: int, data: dict) -> dict:

# NEVER
def create_requirement(tenant_id, data):
```

### Docstrings
Every module file, public class, and public function needs a Google-style docstring explaining **why**, not what.

### Imports
Order: stdlib → third-party → first-party (`app.*`) → relative. One blank line between groups.
NEVER: `from app.models import *`

### String quotes
Always double quotes. Never single quotes (enforced by `ruff.toml`).

### Formatting
Line length: 120. Use `ruff format` — never manually wrap.

---

## Security Rules — NEVER Violate

### Authentication & Authorization
```python
# ALWAYS protect routes
@bp.route("/items", methods=["POST"])
@require_permission("domain.create")
def create_item():
    ...

# NEVER inline role check
if g.role == "admin":  # FORBIDDEN
if g.current_user.role != "editor":  # FORBIDDEN

# ALWAYS use permission service
from app.services.permission_service import has_permission
if not has_permission(user_id, "domain.delete"):
    return jsonify({"error": "Forbidden"}), 403
```

### SQL — No Injection
```python
# ALWAYS parametrized
db.session.execute(sa.text("SELECT id FROM users WHERE email = :e"), {"e": email})

# NEVER f-string SQL
db.session.execute(f"SELECT * FROM users WHERE email = '{email}'")  # FORBIDDEN
```

### Secrets
```python
# ALWAYS from env
SECRET_KEY = os.getenv("SECRET_KEY")

# NEVER hard-coded
API_KEY = "sk-abc123"  # FORBIDDEN
PASSWORD = "admin123"  # FORBIDDEN
```

### Sensitive Fields in Responses
```python
# NEVER expose these fields in any API response or to_dict() output:
# password_hash, reset_token, mfa_secret, raw_api_key, jwt_token
SENSITIVE_FIELDS = {"password_hash", "reset_token", "mfa_secret", "raw_api_key"}

def to_dict(self) -> dict:
    return {c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in SENSITIVE_FIELDS}
```

### Logging
```python
# ALWAYS module-level logger
logger = logging.getLogger(__name__)

# NEVER print()
print("debug info")  # FORBIDDEN

# NEVER log sensitive data
logger.info("password=%s", password)  # FORBIDDEN
logger.debug("token=%s", token)       # FORBIDDEN

# ALWAYS truncate user input in logs
logger.info("Processing name=%s", str(name)[:200])
```

### Error Handling — Fail Closed
```python
# ALWAYS fail closed
try:
    result = some_service.get_data(tenant_id)
except Exception:
    logger.exception("Unexpected error in get_data")
    return jsonify({"error": "Internal server error"}), 500

# NEVER swallow exceptions
try:
    result = some_service.get_data(tenant_id)
except Exception:
    pass          # FORBIDDEN
except Exception:
    return []     # FORBIDDEN
```

---

## AI Module Rules

```python
# ALWAYS use the gateway
from app.ai.gateway import LLMGateway
gw = LLMGateway()
result = gw.chat(prompt, model="claude-3-5-haiku-20241022")

# NEVER call provider SDK directly outside gateway.py
import anthropic             # FORBIDDEN (outside app/ai/gateway.py)
import openai                # FORBIDDEN (outside app/ai/gateway.py)
from google import genai     # FORBIDDEN (outside app/ai/gateway.py)
```

Prompts go in `ai_knowledge/prompts/` as YAML/MD files — not hardcoded strings.
Every LLM call MUST be logged to `AIAuditLog` with `tenant_id`, `user_id`, `model`, token counts, cost, latency.

---

## Database Rules

### Models
```python
# ALWAYS inherit TenantModel for tenant-scoped data
class Requirement(TenantModel):
    __tablename__ = "requirements"  # always explicit
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(32), nullable=False, default="draft")  # always specify length
    tenant_id is inherited from TenantModel

# NEVER
status = db.Column(db.String)  # missing length — FORBIDDEN
```

### N+1 — Never Loop Query
```python
# NEVER query inside loop
for run in runs:
    steps = TestStep.query.filter_by(run_id=run.id).all()  # FORBIDDEN (N+1)

# ALWAYS eager load
runs = db.session.execute(
    select(TestRun).options(selectinload(TestRun.steps))
    .where(TestRun.cycle_id == cycle_id)
).scalars().all()
```

### Transactions
```python
# db.session.commit() ONLY in services — NEVER in blueprints or models
```

---

## API & Response Rules

### URL Pattern
```
/api/v1/<domain>/<resource>/<id>/<sub-resource>
```

### HTTP Status Codes
| Scenario | Code |
|---|---|
| Created | 201 |
| Success read/update | 200 |
| Invalid input | 400 |
| Unauthenticated | 401 |
| Forbidden | 403 |
| Not found | 404 |
| Business rule violation | 422 |
| Server error | 500 |

### Response Envelope
```python
# Single resource
return jsonify({"id": 1, "status": "draft", ...}), 200

# List
return jsonify({"items": [...], "total": 42, "page": 1, "per_page": 20}), 200

# Error
return jsonify({"error": "Validation failed", "details": {"field": "reason"}}), 400
```

### Input Parsing
```python
# ALWAYS silent=True
data = request.get_json(silent=True) or {}

# ALWAYS validate length on strings
name = data.get("name", "")
if not name or len(name) > 255:
    return jsonify({"error": "name is required and must be ≤ 255 chars"}), 400
```

---

## Test Generation Rules

When asked to write tests:

1. File name: `test_<domain>_<topic>.py`
2. Function name: `test_<scenario>_<expected_result>`
3. ALWAYS write at least one negative test (400/401/403/404/422) for every endpoint.
4. NEVER rely on data created by another test — each test creates its own data.
5. Use `client` fixture for HTTP calls, `session` fixture is autouse (auto-rollback).

```python
def test_create_requirement_returns_201_with_valid_data(client):
    """Valid payload should return 201 and the created resource."""
    res = client.post("/api/v1/requirements", json={"title": "Test", "tenant_id": 1})
    assert res.status_code == 201
    assert res.get_json()["title"] == "Test"

def test_create_requirement_returns_400_without_title(client):
    """Missing title should return 400."""
    res = client.post("/api/v1/requirements", json={})
    assert res.status_code == 400
```

---

## Forbidden Patterns — Never Generate

| Pattern | Why |
|---|---|
| `Model.query.all()` without `tenant_id` filter | Cross-tenant data leak |
| `db.session.commit()` in a blueprint | Transaction ownership violation |
| Any hard-coded secret/password/token string | Secret leakage |
| `except Exception: pass` or `return []` | Fail-open, hidden errors |
| AI provider SDK outside `app/ai/gateway.py` | Audit/budget bypass |
| `print()` for logging | Unstructured log |
| `eval()`, `exec()` | Code injection |
| f-string SQL construction | SQL injection |
| `g.role ==` inline check | Central RBAC bypass |
| ORM query inside a loop | N+1 performance issue |
| `from module import *` | Name collision |
| `g` access inside `app/services/` | Layer violation |
| `API_AUTH_ENABLED=false` in production config | Auth bypass |

---

## Quick Reference: New Blueprint Checklist

When generating a new blueprint endpoint, verify:
- [ ] `@require_permission("<domain>.<action>")` on every route
- [ ] `request.get_json(silent=True) or {}`
- [ ] Input length validation for all strings
- [ ] Service call (no ORM in blueprint)
- [ ] `g.tenant_id` passed explicitly to service
- [ ] Correct HTTP status code returned
- [ ] Test file with happy path + at least one error path

## Quick Reference: New Service Function Checklist

When generating a new service function:
- [ ] Type hints on all parameters and return value
- [ ] Google-style docstring
- [ ] `db.session.commit()` only here, not in blueprint
- [ ] `tenant_id` as explicit parameter
- [ ] Exception raises typed error (`ValidationError`, `NotFoundError`, etc.)
- [ ] Cache invalidation if modifying cached data

## Quick Reference: New Model Checklist

When generating a new model:
- [ ] Inherits `TenantModel` (if tenant-scoped) or `db.Model` (if global)
- [ ] `__tablename__` explicitly set
- [ ] All strings have length: `db.String(N)`
- [ ] `nullable` explicitly set on every column
- [ ] `to_dict()` excludes sensitive fields
- [ ] Composite index with `tenant_id` for frequently queried columns
