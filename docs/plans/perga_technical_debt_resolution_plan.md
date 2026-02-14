# Perga — Teknik Borç Çözüm Planı

**Tarih:** 2026-02-14  
**Kaynak:** perga_technical_debt_analysis_v1.2.md  
**Yaklaşım:** 5 sprint, artan karmaşıklık sırasıyla, her sprint bağımsız olarak deploy edilebilir

---

## Mevcut Durum Özeti

| Metrik | Değer |
|--------|-------|
| Toplam teknik borç tahmini | 200-310 saat |
| Fat controller satır sayısı | 7.333 satır / 7 blueprint |
| Service katmanı satır sayısı | 9.752 satır / 31 modül |
| Eksik service modülleri | testing, backlog, integration, program, RAID, data_factory |
| Duplicate `_get_or_404` | 8 kopya (2 varyant) |
| Duplicate `_parse_date*` | 8 kopya (3 farklı davranış!) |
| Generic `except Exception` | 177 blok |
| RBAC korumalı route | 45/570 (%8) |
| Service seviyesi test | 0 |

---

## Sprint 0: Hızlı Kazanımlar (4-8 saat)

**Hedef:** Sıfır risk, anında fayda — mekanik refactor'lar

### 0.1 — Shared Helpers Modülü Oluştur

`app/utils/helpers.py` oluştur ve 16 duplicate tanımı tek kaynağa taşı.

**Oluşturulacak dosya:** `app/utils/helpers.py`

```python
"""Shared utility functions — replaces 16 duplicate definitions across blueprints."""
from datetime import date, datetime
from flask import jsonify
from app.models.explore import db


def get_or_404(model, pk, label=None):
    """Fetch a model instance by primary key or return a 404 error tuple.
    
    Mevcut codebase pattern'ini birebir korur:
    - Başarılı: (obj, None)
    - Başarısız: (None, (jsonify_response, 404))
    
    Tüm 8 kopyada bu pattern kullanılıyor:
        obj, err = get_or_404(Program, pid)
        if err:
            return err
    
    NOT: abort(404) kullanılmıyor — mevcut pattern tuple-return.
    Bu pattern'i değiştirmek 8 dosyada ~200+ çağrı noktasını etkiler.
    Dolayısıyla mevcut davranış aynen korunuyor.
    """
    label = label or model.__name__
    obj = db.session.get(model, pk)
    if not obj:
        return None, (jsonify({"error": f"{label} not found"}), 404)
    return obj, None


def parse_date(value):
    """Parse a date string (ISO or DD.MM.YYYY) to a date object.
    
    Returns None for empty/invalid input. Supports:
    - YYYY-MM-DD (ISO format)
    - DD.MM.YYYY (Turkish/European format)
    - datetime strings via fromisoformat
    """
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(str(value), "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None
```

**Güncelleme planı — 16 dosya:**

| # | Dosya | Silinecek fonksiyon | Import eklenecek |
|---|-------|-------------------|-----------------|
| 1 | `app/blueprints/testing_bp.py` | `_get_or_404()`, `_parse_date()` | `from app.utils.helpers import get_or_404, parse_date` |
| 2 | `app/blueprints/backlog_bp.py` | `_get_or_404()`, `_parse_date()` | `from app.utils.helpers import get_or_404, parse_date` |
| 3 | `app/blueprints/cutover_bp.py` | `_get_or_404()` | `from app.utils.helpers import get_or_404` |
| 4 | `app/blueprints/data_factory_bp.py` | `_get_or_404()` | `from app.utils.helpers import get_or_404` |
| 5 | `app/blueprints/integration_bp.py` | `_get_or_404()`, `_parse_date()` | `from app.utils.helpers import get_or_404, parse_date` |
| 6 | `app/blueprints/program_bp.py` | `_get_or_404()`, `_parse_date()` | `from app.utils.helpers import get_or_404, parse_date` |
| 7 | `app/blueprints/raid_bp.py` | `_parse_date()` | `from app.utils.helpers import parse_date` |
| 8 | `app/blueprints/explore/workshops.py` | `_parse_date_input()` | `from app.utils.helpers import parse_date` |
| 9 | `app/blueprints/explore/open_items.py` | `_parse_date_input()` | `from app.utils.helpers import parse_date` |
| 10-11 | `app/blueprints/archive/requirement_bp.py`, `scenario_bp.py` | `_get_or_404()` | `from app.utils.helpers import get_or_404` |
| 12 | `app/blueprints/archive/scope_bp.py` | `_parse_date()` | `from app.utils.helpers import parse_date` |

> **DİKKAT — Davranış farklılıkları:**
> - `_get_or_404()`: Tüm 8 kopya aynı tuple-return pattern'ini kullanıyor (`obj, err = ...`). Hiçbiri `abort()` çağırmıyor. `helpers.py` bu davranışı aynen koruyor — çağrı noktalarında değişiklik gerekmez, sadece import güncellemesi yeterli.
> - `_parse_date()` (5 dosya): kötü girdide `None` döndürür
> - `_parse_date()` (RAID): `datetime.fromisoformat` kullanır, sonra `.date()` çağırır
> - `_parse_date_input()` (explore): kötü girdide `ValueError` fırlatır + `DD.MM.YYYY` formatını destekler
> 
> Yeni `parse_date()` tüm formatları destekler ve `None` döndürür. Explore dosyalarında `_parse_date_input`'un `ValueError` fırlatma davranışı korunmalı mı karar verilmeli. **Öneri:** `None` döndüren versiyon kullanılsın, explore route handler'ları zaten kendi validation'larını yapıyor.

### 0.2 — Ölü Kod Temizliği

```bash
# Archive blueprint'leri ana branch'ten kaldır
git rm -r app/blueprints/archive/
git rm -r tests/archive/          # varsa

# Root'taki development artifact'ları
git rm unified_traceability_prompt.md
git rm static/js/views/prompt-g-backlog-redesign.md  # varsa
```

**Test:** `python -m pytest tests/ --tb=line -q` — tüm testler geçmeli (archive blueprint'leri zaten register değil)

### 0.3 — Sprint 0 Doğrulama

- [ ] `helpers.py` yüklendi, tüm testler geçiyor
- [ ] 16 duplicate tanım kaldırıldı, import'lar eklendi
- [ ] Ölü kod temizlendi
- [ ] `git diff --stat` ile değişiklik boyutu kontrol edildi

---

## Sprint 1: testing_service.py Çıkarımı (20-30 saat)

**Hedef:** En büyük fat controller'ı (2.755 satır) thin controller + service katmanına dönüştür

### Neden Önce Testing?

- En büyük dosya (2.755 satır, 76 route, 172 db.session)
- En sık değişen modüllerden biri
- AI asistanların test senaryosu üretmesi için service katmanı şart
- Mevcut `app/services/` altında testing ile ilgili HİÇBİR service yok

### 1.0 — Transaction Boundary Politikası

> **KRİTİK KARAR — Tüm service extraction'lar bu kurala uymalıdır.**

Mevcut codebase'deki 31 service modülü incelendi. Baskın pattern:

| Service | `commit()` çağırıyor mu? | `flush()` çağırıyor mu? | Pattern |
|---------|:---:|:---:|---|
| `cutover_service.py` (432 satır) | **Hayır** | Evet | Caller commits |
| `requirement_lifecycle.py` (589 satır) | **Hayır** | Evet | Caller commits |
| `bulk_import_service.py` (291 satır) | **Evet** (1 kez) | Evet | Kendi yönetir (batch semantik) |

**Kural: Service method'ları `db.session.commit()` çağırmaz.**

```python
# ✅ DOĞRU — Service: flush ile ID al, commit'i caller'a bırak
class TestingService:
    @staticmethod
    def create_cycle(project_id: int, data: dict) -> TestCycle:
        cycle = TestCycle(project_id=project_id, **data)
        db.session.add(cycle)
        db.session.flush()  # ID oluşsun, constraint'ler kontrol edilsin
        return cycle  # commit caller'ın sorumluluğunda

# ✅ DOĞRU — Route handler: service çağır, commit yap
@bp.route('/test-cycles', methods=['POST'])
def create_cycle():
    data = request.get_json()
    cycle = TestingService.create_cycle(project_id, data)
    db.session.commit()
    return jsonify(cycle.to_dict()), 201

# ❌ YANLIŞ — Service içinde commit
class TestingService:
    @staticmethod
    def create_cycle(project_id, data):
        cycle = TestCycle(...)
        db.session.add(cycle)
        db.session.commit()  # ← YAPMA — caller birden fazla service çağırabilir
        return cycle
```

**Neden bu pattern?**
- Route handler birden fazla service method'unu tek transaction'da çağırabilir
- Exception durumunda tüm değişiklikler otomatik rollback olur
- Mevcut 31 service modülünün 30'u zaten bu pattern'i kullanıyor
- `bulk_import_service.py` tek istisna — batch partial-success semantiği için kendi commit/rollback'ini yönetiyor

**İstisna kuralı:** Batch/bulk işlemlerde (örn. 1000 satır import) service kendi transaction'ını yönetebilir. Bu durumda method docstring'inde açıkça belirtilmeli:

```python
def bulk_import(project_id, items: list) -> dict:
    """Bulk import — manages its own transaction (partial-success semantics).
    
    WARNING: Caller must NOT call db.session.commit() after this method.
    """
```

### 1.1 — Service Modülü Yapısı

**Oluşturulacak:** `app/services/testing_service.py`

```python
"""Testing service layer — business logic extracted from testing_bp.py.

Extracted operations:
- Test cycle CRUD + state management
- Test case CRUD + cloning
- Test run execution + defect tracking
- Test coverage analysis
- UAT/SIT/GoGo-NoGo workflows
"""
from app.models.testing import (
    TestCycle, TestCase, TestRun, TestDefect,
    TestSuite, TestStep, SLAConfig, GoGoAssessment, db
)


class TestingService:
    """Encapsulates testing business logic independent of Flask request context."""
    
    @staticmethod
    def create_cycle(project_id: int, data: dict) -> TestCycle:
        """Create a new test cycle with auto-generated code."""
        ...
    
    @staticmethod
    def clone_test_case(source_id: int, target_cycle_id: int) -> TestCase:
        """Clone a test case into a different cycle."""
        ...
    
    @staticmethod
    def execute_run(run_id: int, result: str, evidence: dict) -> TestRun:
        """Record a test run execution result."""
        ...
    
    @staticmethod
    def calculate_coverage(cycle_id: int) -> dict:
        """Calculate test coverage metrics for a cycle."""
        ...
    
    @staticmethod
    def evaluate_go_nogo(cycle_id: int) -> dict:
        """Evaluate Go/No-Go criteria for a test cycle."""
        ...
```

### 1.2 — Refactor Stratejisi

**Kural:** Her seferinde 1 route handler refactor et, test geçene kadar devam et.

```
Adım 1: En basit CRUD'dan başla (GET /test-cycles → list_cycles)
         Route handler → validation + TestingService.list_cycles() + response
         
Adım 2: Create/Update operasyonları (POST /test-cycles)
         Inline db.session → TestingService.create_cycle()
         
Adım 3: Karmaşık iş mantığı (clone, coverage calc, go-nogo)
         Bu operasyonlar birden fazla model etkileşimi içeriyor
         
Adım 4: Toplu işlemler (bulk update, bulk delete)
```

### 1.3 — Test Stratejisi

**Oluşturulacak:** `tests/test_testing_service.py`

```python
"""Unit tests for TestingService — independent of Flask routes."""
import pytest
from app.services.testing_service import TestingService


class TestCycleCreation:
    def test_create_cycle_generates_auto_code(self, db_session):
        ...
    
    def test_create_cycle_validates_required_fields(self, db_session):
        ...
    
    def test_create_cycle_with_duplicate_code_raises(self, db_session):
        ...


class TestCaseCloning:
    def test_clone_preserves_steps(self, db_session):
        ...
    
    def test_clone_resets_execution_status(self, db_session):
        ...
    
    def test_clone_sets_cloned_from_id(self, db_session):
        ...
```

### 1.4 — Başarı Kriterleri

- [ ] `testing_bp.py` < 1.500 satır (şu an 2.755)
- [ ] `testing_service.py` > 500 satır iş mantığı
- [ ] db.session çağrıları testing_bp.py'de %50 azalmış
- [ ] `test_testing_service.py` ile en az 20 birim test
- [ ] Mevcut `test_api_testing.py` testleri hâlâ geçiyor

---

## Sprint 2: İkinci Dalga Service Extraction (30-40 saat)

**Hedef:** Kalan 5 fat controller için service modülleri oluştur

### Sıralama (db.session sayısına göre)

| # | Blueprint | Satır | db.session | Oluşturulacak Service |
|---|-----------|------:|:---:|----------------------|
| 1 | `backlog_bp.py` | 889 | ~80 | `backlog_service.py` |
| 2 | `raid_bp.py` | 822 | ~60 | `raid_service.py` |
| 3 | `integration_bp.py` | 731 | ~55 | `integration_service.py` |
| 4 | `program_bp.py` | 717 | ~50 | `program_service.py` |
| 5 | `data_factory_bp.py` | 544 | ~40 | `data_factory_service.py` |

### Her Service İçin Aynı Şablon

```
1. Blueprint'teki en sık tekrarlanan iş mantığını tespit et
2. Service class oluştur (static methods)
3. Route handler'ı thin wrapper'a dönüştür:
   - Request validation (Flask katmanında kalır)
   - Service method çağrısı
   - Response serialization (Flask katmanında kalır)
4. Birim testi yaz
5. Mevcut API testlerini çalıştır → hepsi geçmeli
```

### 2.1 — backlog_service.py Odak Noktaları

```python
class BacklogService:
    @staticmethod
    def create_backlog_item(project_id, data) -> BacklogItem:
        """Validate, auto-code, create backlog item + traceability link."""
    
    @staticmethod
    def convert_to_requirement(backlog_id) -> ExploreRequirement:
        """Convert backlog item to explore requirement — critical business flow."""
    
    @staticmethod
    def bulk_import(project_id, items: list) -> dict:
        """Bulk import backlog items from Excel/CSV."""
```

### 2.2 — raid_service.py Odak Noktaları

```python
class RAIDService:
    @staticmethod
    def create_risk(project_id, data) -> Risk:
        """Create risk with auto-notification to project manager."""
    
    @staticmethod
    def escalate_item(item_id, reason) -> None:
        """Escalate RAID item — trigger notification chain."""
    
    @staticmethod
    def calculate_risk_score(risk_id) -> dict:
        """Monte Carlo risk scoring."""
```

### 2.3 — Başarı Kriterleri

- [ ] 5 yeni service modülü oluşturulmuş
- [ ] Her biri için en az 10 birim test
- [ ] Fat controller'larda toplam db.session çağrısı %40 azalmış (915 → ~550)
- [ ] Tüm mevcut API testleri hâlâ geçiyor

---

## Sprint 3: Model Birleştirme & explore.py Split (30-40 saat)

**Hedef:** Paralel model hiyerarşilerini birleştir, God Module'ü parçala

### 3.1 — explore.py Split (12-16 saat)

**Mevcut:** 1 dosya, 2.158 satır, 25 model, 70 FK  
**Hedef:** 5 dosya, domain-cohesive modüller

```
app/models/explore/
├── __init__.py          # Re-export tüm modeller (geriye dönük uyumluluk)
├── workshop.py          # ExploreWorkshop, WorkshopScopeItem, WorkshopAttendee,
│                        # WorkshopAgendaItem, WorkshopDependency, 
│                        # WorkshopRevisionLog, ExploreWorkshopDocument
├── requirement.py       # ExploreRequirement, RequirementOpenItemLink,
│                        # RequirementDependency, ExploreOpenItem,
│                        # OpenItemComment, ExploreDecision
├── process.py           # ProcessStep, ProcessLevel, L4SeedCatalog, BPMNDiagram
├── governance.py        # ProjectRole, PhaseGate, CrossModuleFlag,
│                        # ScopeChangeRequest, ScopeChangeLog, PERMISSION_MATRIX
└── infrastructure.py    # CloudALMSyncLog, Attachment, DailySnapshot
```

**Kritik:** `__init__.py` dosyasında tüm modelleri re-export et, böylece `from app.models.explore import ExploreWorkshop` hâlâ çalışır:

```python
# app/models/explore/__init__.py
"""Re-export all explore models for backward compatibility.

Her alt modül __all__ tanımlamalıdır — wildcard import
ancak __all__'da listelenen isimleri çeker.
"""
from app.models.explore.workshop import *      # noqa: F401,F403
from app.models.explore.requirement import *    # noqa: F401,F403
from app.models.explore.process import *        # noqa: F401,F403
from app.models.explore.governance import *     # noqa: F401,F403
from app.models.explore.infrastructure import * # noqa: F401,F403
```

**Her alt modülde `__all__` zorunlu** — `import *` sırasında isim çakışmasını önler:

```python
# app/models/explore/workshop.py
__all__ = [
    'ExploreWorkshop', 'WorkshopScopeItem', 'WorkshopAttendee',
    'WorkshopAgendaItem', 'WorkshopDependency', 'WorkshopRevisionLog',
    'ExploreWorkshopDocument',
]

# app/models/explore/requirement.py  
__all__ = [
    'ExploreRequirement', 'RequirementOpenItemLink', 'RequirementDependency',
    'ExploreOpenItem', 'OpenItemComment', 'ExploreDecision',
]

# app/models/explore/process.py
__all__ = ['ProcessStep', 'ProcessLevel', 'L4SeedCatalog', 'BPMNDiagram']

# app/models/explore/governance.py
__all__ = [
    'ProjectRole', 'PhaseGate', 'CrossModuleFlag',
    'ScopeChangeRequest', 'ScopeChangeLog', 'PERMISSION_MATRIX',
]

# app/models/explore/infrastructure.py
__all__ = ['CloudALMSyncLog', 'Attachment', 'DailySnapshot']
```

> **Neden `__all__` zorunlu?** `from module import *` sadece `__all__` listesindeki isimleri çeker. Eğer iki alt modülde aynı isimde bir helper, constant veya import varsa (örn. `db`, `datetime`), `__all__` olmadan sessizce override olur. Bu, debug edilmesi çok zor hatalara yol açar.

### 3.2 — Model Deprecation Stratejisi (20-24 saat)

3 paralel model çifti var:

| Canonical (kalacak) | Deprecated (kaldırılacak) | Aksiyon |
|---------------------|--------------------------|---------|
| `ExploreWorkshop` (27 col) | `Workshop` (22 col) | Workshop kullanımlarını ExploreWorkshop'a yönlendir |
| `ExploreRequirement` (40 col) | `Requirement` (19 col) | Requirement kullanımlarını ExploreRequirement'a yönlendir |
| `ExploreOpenItem` (23 col) | `OpenItem` (14 col) | OpenItem kullanımlarını ExploreOpenItem'a yönlendir |

**Adım 1:** Deprecated modellere docstring uyarısı ekle:

```python
class Requirement(db.Model):
    """DEPRECATED — Use ExploreRequirement instead.
    
    This model is retained for backward compatibility during migration.
    All new code should use ExploreRequirement from app.models.explore.
    Migration target: Sprint 3 (2026-Q1)
    """
```

**Adım 2:** `grep -rn "from app.models.requirement import Requirement"` ile tüm kullanımları listele

**Adım 3:** Her kullanımı teker teker ExploreRequirement'a taşı, testlerle doğrula

**Adım 4:** Traceability service birleştirme:
- `traceability.py` → `get_chain()` (satır 43) ve `trace_explore_requirement()` (satır 590) tek fonksiyona birleştirilecek
- Canonical model üzerinden tek bir izlenebilirlik zinciri

### 3.3 — Migration

```python
# migrations/versions/xxx_deprecate_program_domain_models.py
"""Mark program-domain models as deprecated, add view/synonym for backward compat."""

def upgrade():
    # Mevcut verileri Explore tablolarına kopyala (varsa)
    # Foreign key'leri güncelle
    pass

def downgrade():
    pass
```

### 3.4 — Başarı Kriterleri

- [ ] `explore.py` (2.158 satır) → 5 dosyaya bölünmüş
- [ ] `from app.models.explore import ...` hâlâ çalışıyor (geriye uyumluluk)
- [ ] Deprecated modellere uyarı docstring'leri eklenmiş
- [ ] Traceability service'te tek kod yolu
- [ ] Tüm testler geçiyor

---

## Sprint 4: RBAC Rollout & Error Handling (25-35 saat)

**Hedef:** Yetkilendirmeyi kritik endpoint'lere yay, generic catch blokları temizle

### 4.0 — RBAC Middleware Analizi ve Hazırlık

> **KRİTİK BULGU:** Mevcut `permission_required.py` middleware'i incelendi. Üç önemli davranış tespit edildi:

**1. Basic Auth kullanıcıları RBAC'ı tamamen bypass ediyor:**

```python
# app/middleware/permission_required.py — mevcut davranış
def require_permission(codename):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(g, 'jwt_user_id', None)
            if user_id is None:
                return f(*args, **kwargs)  # ← JWT yoksa → RBAC ATLANIR
            ...
```

Bu, mevcut production'da tüm route'ların Basic Auth ile erişilebilir olduğu anlamına gelir — `@require_permission` decorator'ı eklense bile Basic Auth kullanıcıları için hiçbir şey değişmez.

**2. "Allow by default" mekanizması zaten var — ama kasıtsız:**

Basic Auth bypass sayesinde, `@require_permission` eklemek mevcut kullanıcıları **kilitlemez**. RBAC sadece JWT-tabanlı auth kullandığında devreye girer.

**3. Superuser bypass mevcut:**

`permission_service.py` içinde `platform_admin` ve `tenant_admin` rolleri tüm permission kontrollerini otomatik geçer.

### 4.0.1 — RBAC Rollout Stratejisi

Bu bulgular ışığında, RBAC rollout'u 3 aşamalıdır:

```
Aşama A (Sprint 4): Decorator'ları ekle — Basic Auth bypass aktif
    → Sıfır risk, mevcut kullanıcılar etkilenmez
    → JWT kullanıcıları için RBAC devreye girer
    → Production'da test edilebilir

Aşama B (Multi-tenant ile): Basic Auth bypass'ı kaldır
    → permission_required.py'de bypass satırını değiştir:
    
    # ÖNCEKİ:
    if user_id is None:
        return f(*args, **kwargs)  # bypass
    
    # YENİ:
    if user_id is None:
        return jsonify({"error": "Authentication required"}), 401
    
    → Tüm kullanıcılar JWT auth'a geçmeli
    → Tenant isolation bu noktada zorunlu hale gelir

Aşama C (Production hardening): Grace period kaldır
    → Eksik permission'lar 403 döndürür
    → Audit log ile permission denied olayları izlenir
```

> **Neden bu strateji güvenli?** Sprint 4'te `@require_permission` decorator'larını eklemek, Basic Auth bypass sayesinde mevcut kullanıcıları **hiç etkilemez**. Bu, RBAC altyapısını production'da test etme fırsatı verir. Asıl "swich" multi-tenant geçişinde bypass kaldırıldığında olur.

### 4.1 — RBAC Phase 2: Kritik Mutation Endpoint'leri (15-20 saat)

Mevcut durum: 45/570 route korumalı. Hedef: 120+ route korumalı.

**Öncelik 1 — Veri değiştiren endpoint'ler (POST/PUT/DELETE):**

| Blueprint | Korunacak Route Sayısı | Permission Tipi |
|-----------|:---:|---|
| `testing_bp` | 25+ | `testing.create`, `testing.update`, `testing.delete` |
| `backlog_bp` | 15+ | `backlog.create`, `backlog.update`, `backlog.convert` |
| `explore/*` | 20+ | `explore.workshop.create`, `explore.requirement.update` |
| `cutover_bp` | 10+ | `cutover.create`, `cutover.execute` |
| `integration_bp` | 10+ | `integration.create` |
| `raid_bp` | 10+ | `raid.create`, `raid.escalate` |

**Uygulama deseni:**

```python
# Mevcut (korumasız):
@bp.route('/test-cycles', methods=['POST'])
@auth_required
def create_cycle():
    ...

# Hedef (RBAC korumalı):
@bp.route('/test-cycles', methods=['POST'])
@auth_required
@require_permission('testing.create')
def create_cycle():
    ...
```

**Strateji:** GET endpoint'leri şimdilik korumasız bırakılabilir (read-only, risk düşük). Öncelik: POST, PUT, DELETE, PATCH.

### 4.2 — Error Handling Temizliği (10-15 saat)

177 generic `except Exception` bloğunu 3 kategoride ele al:

**Kategori A — Kaldır (tahminen 60-70 blok):**
Basit CRUD işlemlerinde generic catch gereksiz — merkezi handler zaten var.

```python
# Önce (gereksiz catch):
@bp.route('/items/<int:id>')
def get_item(id):
    try:
        item = db.session.get(Item, id)
        return jsonify(item.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sonra (merkezi handler devreye girer):
@bp.route('/items/<int:id>')
def get_item(id):
    item, err = get_or_404(Item, id)
    if err:
        return err
    return jsonify(item.to_dict())
```

**Kategori B — Spesifik hata tipine dönüştür (~70 blok):**

```python
# Önce:
try:
    data = request.get_json()
    cycle = TestingService.create_cycle(project_id, data)
    return jsonify(cycle.to_dict()), 201
except Exception as e:
    return jsonify({"error": str(e)}), 500

# Sonra:
try:
    data = request.get_json()
    cycle = TestingService.create_cycle(project_id, data)
    return jsonify(cycle.to_dict()), 201
except ValueError as e:
    return jsonify({"error": str(e)}), 400
except IntegrityError:
    db.session.rollback()
    return jsonify({"error": "Duplicate or constraint violation"}), 409
```

**Kategori C — Koru ama logla (~40 blok):**
Harici API çağrıları (CloudALM, Gemini) gibi gerçekten beklenmeyen hata olabilecek yerler.

```python
except Exception as e:
    current_app.logger.exception(f"Unexpected error in {request.path}")
    return jsonify({"error": "Internal server error"}), 500  # str(e) değil!
```

### 4.3 — Başarı Kriterleri

- [ ] RBAC korumalı route sayısı: 45 → 120+
- [ ] Generic `except Exception` sayısı: 177 → <60
- [ ] Hiçbir endpoint `str(e)` ile iç hata detayı sızdırmıyor
- [ ] Tüm testler geçiyor

---

## Sprint 5: Konsolidasyon & Metrik Doğrulama (8-12 saat)

**Hedef:** Tüm sprint'lerin etkisini ölç, dokümantasyonu güncelle

### 5.1 — Metrik Karşılaştırma Tablosu

| Metrik | Sprint 0 Öncesi | Hedef |
|--------|:-:|:-:|
| Duplicate utility fonksiyonları | 16 | 0 |
| db.session çağrısı (blueprint'lerde) | 915 | <400 |
| Service modül sayısı | 31 | 37 (+6 yeni) |
| Service birim test sayısı | 0 | 100+ |
| RBAC korumalı route | 45 (%8) | 120+ (%21+) |
| Generic `except Exception` | 177 | <60 |
| `explore.py` satır sayısı | 2.158 | ~0 (5 dosyaya bölünmüş) |
| Deprecated model kullanımı | 3 çift aktif | Deprecated uyarılarla işaretli |
| Ölü kod (archive/) | 2.068 satır | 0 |
| Traceability kod yolu | 2 ayrı | 1 birleşik |

### 5.2 — Dokümantasyon Güncellemesi

- [ ] `perga_technical_debt_analysis_v1.2.md` → v2.0 olarak güncelle (kapanmış maddeler işaretle)
- [ ] `docs/archive/` altındaki eskimiş dokümanları arşiv branch'ine taşı
- [ ] README.md'ye mimari güncelleme ekle (service katmanı, model yapısı)

### 5.3 — CI/CD İyileştirme

```yaml
# Önerilen: Makefile'a eklenecek
lint-architecture:
    @echo "Checking fat controllers..."
    @find app/blueprints -name "*.py" -exec sh -c 'lines=$$(wc -l < "$$1"); if [ $$lines -gt 1000 ]; then echo "WARNING: $$1 has $$lines lines"; fi' _ {} \;
    @echo "Checking for duplicate utilities..."
    @grep -rn "def _get_or_404\|def _parse_date" app/blueprints/ && echo "ERROR: Duplicate utilities found!" && exit 1 || echo "OK"
```

---

## Zaman Çizelgesi

```
Sprint 0 ─────  4-8 saat   │ helpers.py + ölü kod temizliği
Sprint 1 ───── 20-30 saat  │ testing_service.py extraction
Sprint 2 ───── 30-40 saat  │ 5 service modülü
Sprint 3 ───── 30-40 saat  │ Model birleştirme + explore.py split
Sprint 4 ───── 25-35 saat  │ RBAC rollout + error handling
Sprint 5 ─────  8-12 saat  │ Konsolidasyon
                ──────────
Toplam:       117-165 saat
```

> **Not:** Bu tahmin, v1.2 analizindeki 200-310 saat tahminine göre daha düşük çünkü:
> 1. Service katmanı (31 modül) zaten var — sıfırdan yazmak yerine bağlantı kurmak yeterli
> 2. Explore blueprint (7 dosya) referans mimari olarak kullanılacak — her blueprint için yeniden tasarım gereksiz
> 3. Merkezi error handler zaten kayıtlı — sadece bypass eden catch blokları kaldırmak yeterli
> 4. Sprint'ler arası bağımlılık minimize edilmiş — paralel çalışma mümkün

---

## Risk ve Mitigasyon

| Risk | Olasılık | Etki | Mitigasyon |
|------|:---:|:---:|-----------|
| Service extraction sırasında regresyon | Orta | Yüksek | Her adımda `pytest` çalıştır, API testleri koruma ağı |
| Transaction boundary tutarsızlığı | Orta | Yüksek | **Kural: Service'ler commit çağırmaz** (bkz. §1.0). Code review'da zorunlu kontrol |
| Model birleştirme sırasında veri kaybı | Düşük | Kritik | Migration'ı önce staging'de test et, backup al |
| RBAC rollout mevcut kullanıcıları kilitler | **Çok Düşük** | Yüksek | Basic Auth bypass mevcut — decorator eklemek kullanıcıları etkilemez (bkz. §4.0) |
| explore.py split circular import | Orta | Orta | `__init__.py` re-export + **`__all__` zorunlu** (bkz. §3.1) |
| `import *` isim çakışması | Orta | Orta | Her alt modülde `__all__` tanımlanacak — sadece model class'ları export edilecek |
| `_parse_date` davranış farklılıkları | Düşük | Düşük | Birleşik versiyon tüm formatları destekler |

---

## Hemen Başlanabilecek İşler (Sprint 0)

Herhangi bir karar beklemeden **bugün başlanabilecek** 3 iş:

1. **`app/utils/helpers.py` oluştur** — 16 duplicate tanımı tek dosyaya taşı
2. **`app/blueprints/archive/` sil** — git history'de zaten korunuyor
3. **Deprecated docstring'ler ekle** — `Workshop`, `Requirement`, `OpenItem` modellerine

Bu 3 iş toplam 4-6 saat sürer, sıfır risk taşır ve anında fayda sağlar.
