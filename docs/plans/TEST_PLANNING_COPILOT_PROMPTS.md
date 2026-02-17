# 🤖 SAP Transformation Platform — Test Planning Enhancement Copilot Prompts

**Kullanım:** Her sprint için ilgili prompt'u kopyala → Copilot'a yapıştır → çalıştır.
**Sıra:** TP-Sprint 1 → 2 → 3 → 4 (sırayla, her biri öncekine bağımlı)
**Tarih:** 2026-02-17
**Toplam:** 33 task, ~60 saat, 14 gün

---

# ═══════════════════════════════════════════════════════════════════
# TP-SPRINT 1: SCHEMA FOUNDATION (~12h, 3 gün)
# 5 yeni model + 9 field addition + Alembic migration
# ═══════════════════════════════════════════════════════════════════

```
## BAĞLAM

SAP Transformation Platform — SAP S/4HANA transformation projelerini yöneten platform.
- Repo: umutsoyyilmaz/SAP_Transformation_Platform (main branch)
- Backend: Flask + PostgreSQL + SQLAlchemy + Alembic
- Blueprint Architecture: app/blueprints/ (testing_bp, backlog_bp, audit_bp, data_factory_bp, vb.)
- Models: app/models/ (testing.py, data_factory.py, backlog.py, explore.py, scenario.py, scope.py, vb.)
- Services: app/services/ (traceability.py, requirement_lifecycle.py, vb.)
- Frontend: static/js/views/ + static/js/components/ (Vanilla JS)
- DB: PostgreSQL (Supabase) — Alembic migrations
- Deploy: Railway (app.univer.com.tr)
- Test: 2191 test, zero regression

Mevcut Test Hub modelleri (app/models/testing.py):
- TestPlan, TestCycle, TestCase, TestExecution, TestRun, Defect, TestCycleSuite

Mevcut Data Factory modelleri (app/models/data_factory.py):
- DataObject, LoadCycle, CleansingTask

SAP Test Lifecycle:
SCOPE → PLAN → SCOPE DEFINITION → TC POOL → CYCLE → EXECUTION → DEFECT → RETEST

## GÖREV: TP-SPRINT 1 — Schema Foundation

### Adım 0: Backup + Branch
git checkout -b feature/test-planning-enhancement
git push -u origin feature/test-planning-enhancement

### Adım 1: TestPlan — plan_type field ekle

Dosya: app/models/testing.py
TestPlan modeline şu field'ı ekle:

plan_type = db.Column(db.String(30), nullable=False, default='sit',
    comment='sit|uat|regression|performance|security|cutover_rehearsal|e2e')

### Adım 2: TestCycle — 5 yeni field ekle

Dosya: app/models/testing.py
TestCycle modeline şu field'ları ekle:

environment = db.Column(db.String(50), nullable=True, default='',
    comment='QAS|PRD|Sandbox|PreProd')
build_tag = db.Column(db.String(100), nullable=True, default='',
    comment='Transport set / release identifier')
data_set_id = db.Column(db.Integer, db.ForeignKey('test_data_sets.id', ondelete='SET NULL'), nullable=True,
    comment='Active test data set for this cycle')
data_status = db.Column(db.String(20), nullable=True, default='not_checked',
    comment='not_checked|ready|stale|refresh_needed')
data_refreshed_at = db.Column(db.DateTime, nullable=True,
    comment='Last data refresh timestamp')

### Adım 3: TestCase — data_set_id FK ekle

Dosya: app/models/testing.py
TestCase modeline şu field'ı ekle:

data_set_id = db.Column(db.Integer, db.ForeignKey('test_data_sets.id', ondelete='SET NULL'), nullable=True,
    comment='Linked test data set')

### Adım 4: TestExecution — assigned_to fields ekle

Dosya: app/models/testing.py
TestExecution modeline şu field'ları ekle:

assigned_to = db.Column(db.String(100), nullable=True, default='',
    comment='Planned tester name')
assigned_to_id = db.Column(db.Integer, db.ForeignKey('team_members.id', ondelete='SET NULL'), nullable=True,
    comment='Planned tester FK reference')

### Adım 5: PlanScope modeli oluştur

Dosya: app/models/testing.py
TestPlan modelinin ALTINA şu yeni modeli ekle:

class PlanScope(db.Model):
    """Links TestPlan to source entities for scope definition.
    
    source_type values: process_l3, scenario, requirement, backlog_item, config_item
    SAP Activate: Plan → Scope Items → trace to TCs
    """
    __tablename__ = 'plan_scopes'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('test_plans.id', ondelete='CASCADE'), nullable=False)
    source_type = db.Column(db.String(30), nullable=False,
        comment='process_l3|scenario|requirement|backlog_item|config_item')
    source_id = db.Column(db.Integer, nullable=False,
        comment='ID of the source entity')
    source_code = db.Column(db.String(50), nullable=True,
        comment='Denormalized code for display (e.g. L3-MM-001)')
    source_title = db.Column(db.String(200), nullable=True,
        comment='Denormalized title for display')
    priority = db.Column(db.String(20), nullable=True, default='medium',
        comment='high|medium|low — scope item priority')
    risk_level = db.Column(db.String(20), nullable=True, default='medium',
        comment='high|medium|low — risk assessment')
    coverage_status = db.Column(db.String(20), nullable=True, default='not_calculated',
        comment='not_calculated|full|partial|none — cached coverage')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    plan = db.relationship('TestPlan', backref=db.backref('scopes', lazy='dynamic', cascade='all, delete-orphan'))
    
    # Unique constraint: same source can't be added to same plan twice
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'source_type', 'source_id', name='uq_plan_scope_source'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_code': self.source_code,
            'source_title': self.source_title,
            'priority': self.priority,
            'risk_level': self.risk_level,
            'coverage_status': self.coverage_status,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

### Adım 6: PlanTestCase modeli oluştur

Dosya: app/models/testing.py
PlanScope modelinin ALTINA şu modeli ekle:

class PlanTestCase(db.Model):
    """Links TestCase to TestPlan with plan-specific metadata.
    
    Suite = catalog (reusable across plans)
    PlanTestCase = planning decision (plan-specific: priority, tester, effort)
    Same TC can be in SIT Plan (high priority) and UAT Plan (medium priority).
    ADR-TP-01: PlanTestCase vs Suite separation.
    """
    __tablename__ = 'plan_test_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('test_plans.id', ondelete='CASCADE'), nullable=False)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_cases.id', ondelete='CASCADE'), nullable=False)
    added_method = db.Column(db.String(20), nullable=False, default='manual',
        comment='scope_auto|manual|suite_import|clone — ADR-TP-05 audit trail')
    priority = db.Column(db.String(20), nullable=True, default='medium',
        comment='high|medium|low — plan-level priority override')
    planned_tester = db.Column(db.String(100), nullable=True,
        comment='Planned tester name')
    planned_tester_id = db.Column(db.Integer, db.ForeignKey('team_members.id', ondelete='SET NULL'), nullable=True,
        comment='Planned tester FK')
    planned_cycle = db.Column(db.String(50), nullable=True,
        comment='Target cycle name (e.g. SIT Cycle 1)')
    estimated_effort = db.Column(db.Float, nullable=True,
        comment='Estimated minutes per execution')
    execution_order = db.Column(db.Integer, nullable=True,
        comment='Sequence for ordered execution (E2E, String tests)')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    plan = db.relationship('TestPlan', backref=db.backref('plan_test_cases', lazy='dynamic', cascade='all, delete-orphan'))
    test_case = db.relationship('TestCase', backref=db.backref('plan_entries', lazy='dynamic'))
    
    # Unique: same TC can't be in same plan twice
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'test_case_id', name='uq_plan_test_case'),
    )
    
    def to_dict(self):
        tc = self.test_case
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'test_case_id': self.test_case_id,
            'test_case_code': tc.code if tc else None,
            'test_case_title': tc.title if tc else None,
            'test_case_type': tc.test_type if tc else None,
            'added_method': self.added_method,
            'priority': self.priority,
            'planned_tester': self.planned_tester,
            'planned_tester_id': self.planned_tester_id,
            'planned_cycle': self.planned_cycle,
            'estimated_effort': self.estimated_effort,
            'execution_order': self.execution_order,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

### Adım 7: PlanDataSet bridge modeli oluştur

Dosya: app/models/testing.py
PlanTestCase modelinin ALTINA:

class PlanDataSet(db.Model):
    """Bridge: links TestPlan to TestDataSet.
    ADR-TP-02: Test data lives in Data Factory, consumed via bridge.
    """
    __tablename__ = 'plan_data_sets'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('test_plans.id', ondelete='CASCADE'), nullable=False)
    data_set_id = db.Column(db.Integer, db.ForeignKey('test_data_sets.id', ondelete='CASCADE'), nullable=False)
    is_mandatory = db.Column(db.Boolean, default=False,
        comment='If true, cycle cannot start without this data set being ready')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    plan = db.relationship('TestPlan', backref=db.backref('plan_data_sets', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'data_set_id', name='uq_plan_data_set'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'data_set_id': self.data_set_id,
            'is_mandatory': self.is_mandatory,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

### Adım 8: TestDataSet modeli oluştur

Dosya: app/models/data_factory.py
Mevcut modellerin ALTINA şu modeli ekle:

class TestDataSet(db.Model):
    """Named, versioned data package for test execution.
    
    Groups DataObjects into a test-consumable set.
    E.g. "SIT Cycle 1 Data" = {Customers: 50, Materials: 200, SOs: 100}
    ADR-TP-02: Lives in Data Factory module.
    """
    __tablename__ = 'test_data_sets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False,
        comment='Descriptive name, e.g. SIT Cycle 1 Data Package')
    version = db.Column(db.String(20), nullable=True, default='1.0',
        comment='Version identifier')
    description = db.Column(db.Text, nullable=True)
    environment = db.Column(db.String(50), nullable=False, default='QAS',
        comment='QAS|PRD|Sandbox|PreProd')
    status = db.Column(db.String(20), nullable=False, default='draft',
        comment='draft|loading|ready|stale|archived')
    refresh_strategy = db.Column(db.String(20), nullable=True, default='manual',
        comment='manual|per_cycle|per_run')
    last_loaded_at = db.Column(db.DateTime, nullable=True)
    last_verified_at = db.Column(db.DateTime, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    # Relationship to items
    items = db.relationship('TestDataSetItem', backref='data_set', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'environment': self.environment,
            'status': self.status,
            'refresh_strategy': self.refresh_strategy,
            'last_loaded_at': self.last_loaded_at.isoformat() if self.last_loaded_at else None,
            'last_verified_at': self.last_verified_at.isoformat() if self.last_verified_at else None,
            'project_id': self.project_id,
            'item_count': self.items.count() if self.items else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

### Adım 9: TestDataSetItem modeli oluştur

Dosya: app/models/data_factory.py
TestDataSet modelinin ALTINA:

class TestDataSetItem(db.Model):
    """Links TestDataSet to individual DataObjects with filtering.
    
    E.g. DataSet "SIT Cycle 1" has:
      - DataObject "Customer Master" → filter: "Country=DE", expected: 50 records
      - DataObject "Material Master" → filter: "Plant=1000", expected: 200 records
    """
    __tablename__ = 'test_data_set_items'
    
    id = db.Column(db.Integer, primary_key=True)
    data_set_id = db.Column(db.Integer, db.ForeignKey('test_data_sets.id', ondelete='CASCADE'), nullable=False)
    data_object_id = db.Column(db.Integer, db.ForeignKey('data_objects.id', ondelete='SET NULL'), nullable=True,
        comment='FK to DataObject — nullable if Data Factory not populated')
    data_object_name = db.Column(db.String(200), nullable=True,
        comment='Denormalized name for display')
    record_filter = db.Column(db.Text, nullable=True,
        comment='Filter criteria, e.g. Country=DE AND Plant=1000')
    expected_records = db.Column(db.Integer, nullable=True,
        comment='Expected record count after filter')
    actual_records = db.Column(db.Integer, nullable=True,
        comment='Actual loaded record count')
    status = db.Column(db.String(20), nullable=False, default='needed',
        comment='needed|loaded|verified|missing')
    load_cycle_id = db.Column(db.Integer, db.ForeignKey('load_cycles.id', ondelete='SET NULL'), nullable=True,
        comment='Which LoadCycle loaded this data')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_set_id': self.data_set_id,
            'data_object_id': self.data_object_id,
            'data_object_name': self.data_object_name,
            'record_filter': self.record_filter,
            'expected_records': self.expected_records,
            'actual_records': self.actual_records,
            'status': self.status,
            'load_cycle_id': self.load_cycle_id,
            'project_id': self.project_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

### Adım 10: Alembic Migration oluştur

bash komutları:

# Migration oluştur
cd /workspaces/SAP_Transformation_Platform
alembic revision --autogenerate -m "test_planning_enhancement: 5 new tables + 9 field additions"

# Migration dosyasını kontrol et — upgrade() fonksiyonunda şunlar olmalı:
# 1. plan_scopes tablosu CREATE
# 2. plan_test_cases tablosu CREATE
# 3. plan_data_sets tablosu CREATE
# 4. test_data_sets tablosu CREATE
# 5. test_data_set_items tablosu CREATE
# 6. test_plans.plan_type ADD COLUMN
# 7. test_cycles.environment ADD COLUMN
# 8. test_cycles.build_tag ADD COLUMN
# 9. test_cycles.data_set_id ADD COLUMN
# 10. test_cycles.data_status ADD COLUMN
# 11. test_cycles.data_refreshed_at ADD COLUMN
# 12. test_cases.data_set_id ADD COLUMN
# 13. test_executions.assigned_to ADD COLUMN
# 14. test_executions.assigned_to_id ADD COLUMN

# ÖNEMLİ: downgrade() fonksiyonunda ters işlemler olmalı

# Migration'ı çalıştır
alembic upgrade head

# Doğrula
python -c "
from app import create_app
from app.models import db
from app.models.testing import PlanScope, PlanTestCase, PlanDataSet
from app.models.data_factory import TestDataSet, TestDataSetItem
app = create_app()
with app.app_context():
    print('✅ PlanScope:', db.inspect(db.engine).has_table('plan_scopes'))
    print('✅ PlanTestCase:', db.inspect(db.engine).has_table('plan_test_cases'))
    print('✅ PlanDataSet:', db.inspect(db.engine).has_table('plan_data_sets'))
    print('✅ TestDataSet:', db.inspect(db.engine).has_table('test_data_sets'))
    print('✅ TestDataSetItem:', db.inspect(db.engine).has_table('test_data_set_items'))
"

### Adım 11: Mevcut testleri çalıştır

# Regression kontrolü
python -m pytest tests/ -x --tb=short 2>&1 | tail -20

# Hata varsa düzelt — mevcut testler KIRILMAMALI
# Tüm yeni field'lar nullable veya default'lu olduğu için sorun olmamalı

### Adım 12: Commit
git add -A
git commit -m "feat(testing): TP-Sprint 1 — Schema foundation

New models:
- PlanScope: plan-to-source entity mapping (process_l3, scenario, req, backlog, config)
- PlanTestCase: TC pool with plan-specific metadata (priority, tester, effort, order)
- PlanDataSet: bridge between TestPlan and TestDataSet
- TestDataSet: named, versioned data packages for test execution
- TestDataSetItem: data set to DataObject mapping with filters

Field additions:
- TestPlan.plan_type (sit/uat/regression/performance/security/cutover_rehearsal/e2e)
- TestCycle: environment, build_tag, data_set_id, data_status, data_refreshed_at
- TestCase.data_set_id
- TestExecution: assigned_to, assigned_to_id

ADRs: TP-01 (PlanTestCase vs Suite), TP-02 (DataSet in Data Factory),
TP-03 (denormalized source fields), TP-04 (cached coverage), TP-05 (added_method audit)"
git push

## KRİTİK KURALLAR
- ✅ Tüm yeni field'lar nullable veya default'lu — mevcut veri bozulmaz
- ✅ FK'lerde ondelete='SET NULL' veya 'CASCADE' kullan
- ✅ Unique constraint'ler ekle (duplicate koruma)
- ✅ Her model'de to_dict() metodu olmalı
- ✅ Migration sonrası mevcut testler geçmeli
- ❌ Mevcut model field'larını değiştirme/silme
- ❌ Mevcut tablo isimlerini değiştirme

## EXIT CRITERIA
- [ ] alembic upgrade head başarılı
- [ ] 5 yeni tablo var (plan_scopes, plan_test_cases, plan_data_sets, test_data_sets, test_data_set_items)
- [ ] 9 field addition uygulandı
- [ ] Mevcut testler hâlâ geçiyor (zero regression)
- [ ] git push başarılı
```

---

# ═══════════════════════════════════════════════════════════════════
# TP-SPRINT 2: CRUD ENDPOINTS (~16h, 4 gün)
# 27 yeni REST endpoint + mevcut endpoint güncellemeleri
# ═══════════════════════════════════════════════════════════════════

```
## BAĞLAM

SAP Transformation Platform — Flask + PostgreSQL + Alembic
- TP-Sprint 1 TAMAMLANDI — 5 yeni tablo + 9 field addition
- Mevcut blueprint: app/blueprints/testing_bp.py (TestPlan, TestCycle, TestCase, TestExecution CRUD)
- Mevcut blueprint: app/blueprints/data_factory_bp.py (DataObject, LoadCycle CRUD)
- Models: app/models/testing.py (PlanScope, PlanTestCase, PlanDataSet — YENİ)
- Models: app/models/data_factory.py (TestDataSet, TestDataSetItem — YENİ)
- API prefix: /api/v1/
- Pattern: Her endpoint project_id filtresi kullanır
- Auth: @login_required veya permission_service pattern'ini takip et

Mevcut endpoint pattern'i (testing_bp.py'den):
- GET /api/v1/test-plans → list (project_id filter)
- POST /api/v1/test-plans → create
- GET /api/v1/test-plans/<id> → detail
- PUT /api/v1/test-plans/<id> → update
- DELETE /api/v1/test-plans/<id> → delete

## GÖREV: TP-SPRINT 2 — CRUD Endpoints

### TP-2.01: PlanScope CRUD (4 endpoint)

Dosya: app/blueprints/testing_bp.py
Mevcut test plan endpoint'lerinin ALTINA ekle:

# --- PLAN SCOPE ENDPOINTS ---

@testing_bp.route('/plans/<int:plan_id>/scopes', methods=['GET'])
def list_plan_scopes(plan_id):
    """List all scope items for a test plan."""
    plan = TestPlan.query.get_or_404(plan_id)
    scopes = PlanScope.query.filter_by(plan_id=plan_id).order_by(PlanScope.source_type, PlanScope.source_code).all()
    return jsonify([s.to_dict() for s in scopes])

@testing_bp.route('/plans/<int:plan_id>/scopes', methods=['POST'])
def create_plan_scope(plan_id):
    """Add a scope item to a plan.
    Body: {source_type, source_id, source_code?, source_title?, priority?, risk_level?}
    """
    plan = TestPlan.query.get_or_404(plan_id)
    data = request.get_json()
    
    # Validate required fields
    if not data.get('source_type') or not data.get('source_id'):
        return jsonify({'error': 'source_type and source_id are required'}), 400
    
    # Check duplicate
    existing = PlanScope.query.filter_by(
        plan_id=plan_id, source_type=data['source_type'], source_id=data['source_id']
    ).first()
    if existing:
        return jsonify({'error': 'This scope item is already in the plan'}), 409
    
    scope = PlanScope(
        plan_id=plan_id,
        project_id=plan.project_id,
        source_type=data['source_type'],
        source_id=data['source_id'],
        source_code=data.get('source_code', ''),
        source_title=data.get('source_title', ''),
        priority=data.get('priority', 'medium'),
        risk_level=data.get('risk_level', 'medium'),
    )
    db.session.add(scope)
    db.session.commit()
    return jsonify(scope.to_dict()), 201

@testing_bp.route('/plan-scopes/<int:scope_id>', methods=['PUT'])
def update_plan_scope(scope_id):
    """Update a plan scope item."""
    scope = PlanScope.query.get_or_404(scope_id)
    data = request.get_json()
    for field in ['priority', 'risk_level', 'coverage_status', 'source_code', 'source_title']:
        if field in data:
            setattr(scope, field, data[field])
    db.session.commit()
    return jsonify(scope.to_dict())

@testing_bp.route('/plan-scopes/<int:scope_id>', methods=['DELETE'])
def delete_plan_scope(scope_id):
    """Remove a scope item from plan."""
    scope = PlanScope.query.get_or_404(scope_id)
    db.session.delete(scope)
    db.session.commit()
    return jsonify({'message': 'Scope item removed'}), 200

### TP-2.02: PlanTestCase CRUD (4 endpoint)

@testing_bp.route('/plans/<int:plan_id>/test-cases', methods=['GET'])
def list_plan_test_cases(plan_id):
    """List all test cases in a plan's TC pool."""
    plan = TestPlan.query.get_or_404(plan_id)
    ptcs = PlanTestCase.query.filter_by(plan_id=plan_id)\
        .order_by(PlanTestCase.execution_order.nullslast(), PlanTestCase.priority)\
        .all()
    return jsonify([p.to_dict() for p in ptcs])

@testing_bp.route('/plans/<int:plan_id>/test-cases', methods=['POST'])
def add_test_case_to_plan(plan_id):
    """Add a test case to plan's TC pool.
    Body: {test_case_id, added_method?, priority?, planned_tester?, planned_tester_id?,
           planned_cycle?, estimated_effort?, execution_order?}
    """
    plan = TestPlan.query.get_or_404(plan_id)
    data = request.get_json()
    
    if not data.get('test_case_id'):
        return jsonify({'error': 'test_case_id is required'}), 400
    
    # Verify TC exists
    tc = TestCase.query.get(data['test_case_id'])
    if not tc:
        return jsonify({'error': f"TestCase {data['test_case_id']} not found"}), 404
    
    # Check duplicate
    existing = PlanTestCase.query.filter_by(plan_id=plan_id, test_case_id=data['test_case_id']).first()
    if existing:
        return jsonify({'error': 'This test case is already in the plan'}), 409
    
    ptc = PlanTestCase(
        plan_id=plan_id,
        project_id=plan.project_id,
        test_case_id=data['test_case_id'],
        added_method=data.get('added_method', 'manual'),
        priority=data.get('priority', 'medium'),
        planned_tester=data.get('planned_tester'),
        planned_tester_id=data.get('planned_tester_id'),
        planned_cycle=data.get('planned_cycle'),
        estimated_effort=data.get('estimated_effort'),
        execution_order=data.get('execution_order'),
    )
    db.session.add(ptc)
    db.session.commit()
    return jsonify(ptc.to_dict()), 201

@testing_bp.route('/plan-test-cases/<int:ptc_id>', methods=['PUT'])
def update_plan_test_case(ptc_id):
    """Update plan TC metadata (priority, tester, effort, order)."""
    ptc = PlanTestCase.query.get_or_404(ptc_id)
    data = request.get_json()
    for field in ['priority', 'planned_tester', 'planned_tester_id', 'planned_cycle',
                  'estimated_effort', 'execution_order', 'added_method']:
        if field in data:
            setattr(ptc, field, data[field])
    db.session.commit()
    return jsonify(ptc.to_dict())

@testing_bp.route('/plan-test-cases/<int:ptc_id>', methods=['DELETE'])
def remove_test_case_from_plan(ptc_id):
    """Remove a TC from plan."""
    ptc = PlanTestCase.query.get_or_404(ptc_id)
    db.session.delete(ptc)
    db.session.commit()
    return jsonify({'message': 'Test case removed from plan'}), 200

### TP-2.03: TestDataSet CRUD (5 endpoint)

Dosya: app/blueprints/data_factory_bp.py
Mevcut endpoint'lerin ALTINA ekle:

# --- TEST DATA SET ENDPOINTS ---

@data_factory_bp.route('/test-data-sets', methods=['GET'])
def list_test_data_sets():
    """List test data sets. Filter: ?project_id=X&status=ready&environment=QAS"""
    query = TestDataSet.query
    if request.args.get('project_id'):
        query = query.filter_by(project_id=request.args['project_id'])
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    if request.args.get('environment'):
        query = query.filter_by(environment=request.args['environment'])
    datasets = query.order_by(TestDataSet.updated_at.desc()).all()
    return jsonify([ds.to_dict() for ds in datasets])

@data_factory_bp.route('/test-data-sets', methods=['POST'])
def create_test_data_set():
    """Create a new test data set.
    Body: {name, project_id, version?, description?, environment?, refresh_strategy?}
    """
    data = request.get_json()
    if not data.get('name') or not data.get('project_id'):
        return jsonify({'error': 'name and project_id are required'}), 400
    
    ds = TestDataSet(
        name=data['name'],
        project_id=data['project_id'],
        version=data.get('version', '1.0'),
        description=data.get('description'),
        environment=data.get('environment', 'QAS'),
        status='draft',
        refresh_strategy=data.get('refresh_strategy', 'manual'),
    )
    db.session.add(ds)
    db.session.commit()
    return jsonify(ds.to_dict()), 201

@data_factory_bp.route('/test-data-sets/<int:ds_id>', methods=['GET'])
def get_test_data_set(ds_id):
    """Get data set detail with item count."""
    ds = TestDataSet.query.get_or_404(ds_id)
    result = ds.to_dict()
    result['items'] = [item.to_dict() for item in ds.items.all()]
    return jsonify(result)

@data_factory_bp.route('/test-data-sets/<int:ds_id>', methods=['PUT'])
def update_test_data_set(ds_id):
    """Update data set metadata or status."""
    ds = TestDataSet.query.get_or_404(ds_id)
    data = request.get_json()
    for field in ['name', 'version', 'description', 'environment', 'status',
                  'refresh_strategy', 'last_loaded_at', 'last_verified_at']:
        if field in data:
            setattr(ds, field, data[field])
    db.session.commit()
    return jsonify(ds.to_dict())

@data_factory_bp.route('/test-data-sets/<int:ds_id>', methods=['DELETE'])
def delete_test_data_set(ds_id):
    """Delete a data set (cascades to items)."""
    ds = TestDataSet.query.get_or_404(ds_id)
    db.session.delete(ds)
    db.session.commit()
    return jsonify({'message': 'Data set deleted'}), 200

### TP-2.04: TestDataSetItem CRUD (4 endpoint)

@data_factory_bp.route('/test-data-sets/<int:ds_id>/items', methods=['GET'])
def list_data_set_items(ds_id):
    """List items in a data set."""
    ds = TestDataSet.query.get_or_404(ds_id)
    items = TestDataSetItem.query.filter_by(data_set_id=ds_id).all()
    return jsonify([i.to_dict() for i in items])

@data_factory_bp.route('/test-data-sets/<int:ds_id>/items', methods=['POST'])
def add_data_set_item(ds_id):
    """Add a DataObject reference to data set.
    Body: {data_object_id?, data_object_name?, record_filter?, expected_records?}
    """
    ds = TestDataSet.query.get_or_404(ds_id)
    data = request.get_json()
    
    item = TestDataSetItem(
        data_set_id=ds_id,
        project_id=ds.project_id,
        data_object_id=data.get('data_object_id'),
        data_object_name=data.get('data_object_name', ''),
        record_filter=data.get('record_filter'),
        expected_records=data.get('expected_records'),
        status='needed',
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@data_factory_bp.route('/test-data-set-items/<int:item_id>', methods=['PUT'])
def update_data_set_item(item_id):
    """Update data set item (status, actual_records, etc.)."""
    item = TestDataSetItem.query.get_or_404(item_id)
    data = request.get_json()
    for field in ['data_object_id', 'data_object_name', 'record_filter',
                  'expected_records', 'actual_records', 'status', 'load_cycle_id']:
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify(item.to_dict())

@data_factory_bp.route('/test-data-set-items/<int:item_id>', methods=['DELETE'])
def delete_data_set_item(item_id):
    """Remove item from data set."""
    item = TestDataSetItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item removed'}), 200

### TP-2.05: PlanDataSet CRUD (3 endpoint)

Dosya: app/blueprints/testing_bp.py

@testing_bp.route('/plans/<int:plan_id>/data-sets', methods=['GET'])
def list_plan_data_sets(plan_id):
    """List data sets linked to a plan."""
    plan = TestPlan.query.get_or_404(plan_id)
    pds_list = PlanDataSet.query.filter_by(plan_id=plan_id).all()
    results = []
    for pds in pds_list:
        d = pds.to_dict()
        # Include data set details
        ds = TestDataSet.query.get(pds.data_set_id)
        if ds:
            d['data_set_name'] = ds.name
            d['data_set_status'] = ds.status
            d['data_set_environment'] = ds.environment
        results.append(d)
    return jsonify(results)

@testing_bp.route('/plans/<int:plan_id>/data-sets', methods=['POST'])
def link_data_set_to_plan(plan_id):
    """Link a data set to a plan.
    Body: {data_set_id, is_mandatory?}
    """
    plan = TestPlan.query.get_or_404(plan_id)
    data = request.get_json()
    
    if not data.get('data_set_id'):
        return jsonify({'error': 'data_set_id is required'}), 400
    
    existing = PlanDataSet.query.filter_by(plan_id=plan_id, data_set_id=data['data_set_id']).first()
    if existing:
        return jsonify({'error': 'Data set already linked to plan'}), 409
    
    pds = PlanDataSet(
        plan_id=plan_id,
        data_set_id=data['data_set_id'],
        is_mandatory=data.get('is_mandatory', False),
        project_id=plan.project_id,
    )
    db.session.add(pds)
    db.session.commit()
    return jsonify(pds.to_dict()), 201

@testing_bp.route('/plan-data-sets/<int:pds_id>', methods=['DELETE'])
def unlink_data_set_from_plan(pds_id):
    """Unlink data set from plan."""
    pds = PlanDataSet.query.get_or_404(pds_id)
    db.session.delete(pds)
    db.session.commit()
    return jsonify({'message': 'Data set unlinked from plan'}), 200

### TP-2.06–2.08: Mevcut endpoint güncellemeleri

TestPlan GET list endpoint'ine plan_type filtresi ekle:
- ?plan_type=sit → sadece SIT planlarını getir

TestCycle GET list/detail endpoint'lerine environment, build_tag dön:
- Response'a environment, build_tag, data_status field'larını ekle

TestExecution endpoint'lerine assigned_to dön:
- Response'a assigned_to, assigned_to_id field'larını ekle
- PUT'ta assigned_to güncellenebilir olsun

### TP-2.09: API Smoke Test

Şu curl komutlarını çalıştır (tüm 27 endpoint test):

BASE="http://localhost:5000/api/v1"

echo "=== PlanScope ==="
# POST plan scope
curl -s -X POST "$BASE/plans/1/scopes" -H "Content-Type: application/json" \
  -d '{"source_type":"process_l3","source_id":1,"source_code":"L3-MM-001","source_title":"Purchase Order Processing","priority":"high"}' | python3 -m json.tool

# GET plan scopes
curl -s "$BASE/plans/1/scopes" | python3 -m json.tool

# PUT plan scope
curl -s -X PUT "$BASE/plan-scopes/1" -H "Content-Type: application/json" \
  -d '{"risk_level":"high"}' | python3 -m json.tool

echo "=== PlanTestCase ==="
# POST plan TC
curl -s -X POST "$BASE/plans/1/test-cases" -H "Content-Type: application/json" \
  -d '{"test_case_id":1,"added_method":"manual","priority":"high","estimated_effort":30}' | python3 -m json.tool

# GET plan TCs
curl -s "$BASE/plans/1/test-cases" | python3 -m json.tool

echo "=== TestDataSet ==="
# POST data set
curl -s -X POST "$BASE/test-data-sets" -H "Content-Type: application/json" \
  -d '{"name":"SIT Cycle 1 Data","project_id":1,"environment":"QAS"}' | python3 -m json.tool

# GET data sets
curl -s "$BASE/test-data-sets?project_id=1" | python3 -m json.tool

echo "=== TestDataSetItem ==="
# POST item
curl -s -X POST "$BASE/test-data-sets/1/items" -H "Content-Type: application/json" \
  -d '{"data_object_name":"Customer Master","expected_records":50,"record_filter":"Country=DE"}' | python3 -m json.tool

echo "=== PlanDataSet ==="
# POST plan-data link
curl -s -X POST "$BASE/plans/1/data-sets" -H "Content-Type: application/json" \
  -d '{"data_set_id":1,"is_mandatory":true}' | python3 -m json.tool

echo "=== DONE ==="

### Commit
git add -A
git commit -m "feat(testing): TP-Sprint 2 — CRUD endpoints for test planning

PlanScope: 4 endpoints (GET/POST/PUT/DELETE)
PlanTestCase: 4 endpoints (GET/POST/PUT/DELETE)
TestDataSet: 5 endpoints (CRUD + list with filters)
TestDataSetItem: 4 endpoints (GET/POST/PUT/DELETE)
PlanDataSet: 3 endpoints (GET/POST/DELETE)
Updated: TestPlan (plan_type filter), TestCycle (environment), TestExecution (assigned_to)
Total: 27 new/updated endpoints"
git push

## EXIT CRITERIA
- [ ] 27 endpoint 200/201 dönüyor
- [ ] POST → duplicate 409 dönüyor
- [ ] GET → filter'lar çalışıyor (project_id, plan_type, status)
- [ ] DELETE → cascade çalışıyor
- [ ] Mevcut testler geçiyor
```

---

# ═══════════════════════════════════════════════════════════════════
# TP-SPRINT 3: SMART SERVICES (~14h, 3 gün)
# Auto-suggest, Populate, Coverage, Data Check, Exit Criteria
# ═══════════════════════════════════════════════════════════════════

```
## BAĞLAM

SAP Transformation Platform — Flask + PostgreSQL + Alembic
- TP-Sprint 1 TAMAMLANDI — Schema foundation
- TP-Sprint 2 TAMAMLANDI — 27 CRUD endpoint
- Models: PlanScope, PlanTestCase, PlanDataSet, TestDataSet, TestDataSetItem (tümü çalışıyor)
- Services dizini: app/services/ (traceability.py, requirement_lifecycle.py mevcut pattern'ler)
- Blueprint: app/blueprints/testing_bp.py

## GÖREV: TP-SPRINT 3 — Smart Services

### TP-3.01: Suggest TCs from Scope (en karmaşık servis)

Dosya: app/services/test_planning_service.py (YENİ DOSYA)

"""
Test Planning Service — Smart operations for test plan management.

Key operations:
1. suggest_test_cases(plan_id) — PlanScope → trace → candidate TCs
2. import_from_suite(plan_id, suite_id) — bulk import
3. populate_cycle(cycle_id, source, filter) — create executions
4. calculate_coverage(plan_id) — scope × TC matrix
5. check_data_readiness(plan_id) — mandatory dataset check
6. evaluate_exit_criteria(plan_id) — automated gate check
"""
from app.models import db
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution,
    PlanScope, PlanTestCase, PlanDataSet, TestCycleSuite, Defect
)
from app.models.data_factory import TestDataSet, TestDataSetItem
from datetime import datetime


def suggest_test_cases(plan_id):
    """
    Auto-suggest test cases based on plan scope items.
    
    Traversal logic per source_type:
    - process_l3: Process(L3) → RequirementProcessMapping → Requirement → backlog_item/config_item → TestCase
    - scenario: Scenario → Workshop → ExploreRequirement → BacklogItem → TestCase
    - requirement: Requirement → backlog_item/config_item → TestCase
    - backlog_item: BacklogItem → TestCase (direct, via source_type='backlog_item')
    - config_item: ConfigItem → TestCase (direct, via source_type='config_item')
    
    Returns: list of {test_case_id, test_case_code, test_case_title, source_scope_id, reason}
    Already-in-plan TCs are excluded but flagged.
    """
    plan = TestPlan.query.get(plan_id)
    if not plan:
        return {'error': 'Plan not found'}, 404
    
    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    if not scopes:
        return {'suggestions': [], 'message': 'No scope items defined'}, 200
    
    # Get already-in-plan TC IDs
    existing_tc_ids = set(
        ptc.test_case_id for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    )
    
    suggestions = []
    seen_tc_ids = set()
    
    for scope in scopes:
        candidate_tcs = _trace_scope_to_test_cases(scope)
        for tc_info in candidate_tcs:
            tc_id = tc_info['test_case_id']
            if tc_id in seen_tc_ids:
                continue
            seen_tc_ids.add(tc_id)
            
            tc_info['scope_id'] = scope.id
            tc_info['scope_code'] = scope.source_code
            tc_info['already_in_plan'] = tc_id in existing_tc_ids
            suggestions.append(tc_info)
    
    return {
        'suggestions': suggestions,
        'total': len(suggestions),
        'new': sum(1 for s in suggestions if not s['already_in_plan']),
        'already_in_plan': sum(1 for s in suggestions if s['already_in_plan']),
    }, 200


def _trace_scope_to_test_cases(scope):
    """Trace a single scope item to its linked test cases."""
    results = []
    
    if scope.source_type == 'backlog_item':
        # Direct: BacklogItem → TestCase
        tcs = TestCase.query.filter_by(source_type='backlog_item', source_id=scope.source_id).all()
        for tc in tcs:
            results.append({
                'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                'test_type': tc.test_type, 'reason': f'Direct link from {scope.source_code}'
            })
    
    elif scope.source_type == 'config_item':
        tcs = TestCase.query.filter_by(source_type='config_item', source_id=scope.source_id).all()
        for tc in tcs:
            results.append({
                'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                'test_type': tc.test_type, 'reason': f'Direct link from {scope.source_code}'
            })
    
    elif scope.source_type == 'requirement':
        # Requirement → BacklogItem/ConfigItem → TestCase
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem
        
        req = db.session.get(Requirement, scope.source_id)
        if req:
            # Via backlog items
            bis = BacklogItem.query.filter_by(requirement_id=req.id).all()
            for bi in bis:
                tcs = TestCase.query.filter_by(source_type='backlog_item', source_id=bi.id).all()
                for tc in tcs:
                    results.append({
                        'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                        'test_type': tc.test_type,
                        'reason': f'Requirement {scope.source_code} → {bi.code} → TC'
                    })
            # Via config items
            cis = ConfigItem.query.filter_by(requirement_id=req.id).all()
            for ci in cis:
                tcs = TestCase.query.filter_by(source_type='config_item', source_id=ci.id).all()
                for tc in tcs:
                    results.append({
                        'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                        'test_type': tc.test_type,
                        'reason': f'Requirement {scope.source_code} → {ci.code} → TC'
                    })
    
    elif scope.source_type == 'process_l3':
        # Process(L3) → RequirementProcessMapping → Requirement → ...
        from app.models.scope import RequirementProcessMapping
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem
        
        mappings = RequirementProcessMapping.query.filter_by(process_id=scope.source_id).all()
        for mapping in mappings:
            req = db.session.get(Requirement, mapping.requirement_id)
            if not req:
                continue
            bis = BacklogItem.query.filter_by(requirement_id=req.id).all()
            for bi in bis:
                tcs = TestCase.query.filter_by(source_type='backlog_item', source_id=bi.id).all()
                for tc in tcs:
                    results.append({
                        'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                        'test_type': tc.test_type,
                        'reason': f'L3 {scope.source_code} → Req → {bi.code} → TC'
                    })
            cis = ConfigItem.query.filter_by(requirement_id=req.id).all()
            for ci in cis:
                tcs = TestCase.query.filter_by(source_type='config_item', source_id=ci.id).all()
                for tc in tcs:
                    results.append({
                        'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                        'test_type': tc.test_type,
                        'reason': f'L3 {scope.source_code} → Req → {ci.code} → TC'
                    })
    
    elif scope.source_type == 'scenario':
        # Scenario → Workshop → ExploreRequirement → BacklogItem → TestCase
        from app.models.scenario import Workshop
        from app.models.explore import ExploreRequirement
        from app.models.backlog import BacklogItem
        
        workshops = Workshop.query.filter_by(scenario_id=scope.source_id).all()
        for ws in workshops:
            reqs = ExploreRequirement.query.filter_by(workshop_id=ws.id).all()
            for req in reqs:
                if hasattr(req, 'backlog_item_id') and req.backlog_item_id:
                    tcs = TestCase.query.filter_by(source_type='backlog_item', source_id=req.backlog_item_id).all()
                    for tc in tcs:
                        results.append({
                            'test_case_id': tc.id, 'code': tc.code, 'title': tc.title,
                            'test_type': tc.test_type,
                            'reason': f'Scenario {scope.source_code} → WS → Req → TC'
                        })
    
    return results


### TP-3.02: Import from Suite

def import_from_suite(plan_id, suite_id):
    """Bulk import TCs from a TestCycleSuite into plan's TC pool."""
    plan = TestPlan.query.get(plan_id)
    if not plan:
        return {'error': 'Plan not found'}, 404
    
    suite = TestCycleSuite.query.get(suite_id)
    if not suite:
        return {'error': 'Suite not found'}, 404
    
    # Get TCs in suite (via suite.test_cases relationship or M:N table)
    suite_tcs = TestCase.query.filter_by(suite_id=suite_id).all()
    
    existing_tc_ids = set(
        ptc.test_case_id for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all()
    )
    
    added = 0
    skipped = 0
    for tc in suite_tcs:
        if tc.id in existing_tc_ids:
            skipped += 1
            continue
        ptc = PlanTestCase(
            plan_id=plan_id,
            project_id=plan.project_id,
            test_case_id=tc.id,
            added_method='suite_import',
            priority=tc.priority or 'medium',
        )
        db.session.add(ptc)
        added += 1
    
    db.session.commit()
    return {'added': added, 'skipped': skipped, 'suite_name': suite.name}, 200


### TP-3.03: Populate Cycle from Plan

def populate_cycle_from_plan(cycle_id):
    """Create TestExecution records from PlanTestCase pool."""
    cycle = TestCycle.query.get(cycle_id)
    if not cycle:
        return {'error': 'Cycle not found'}, 404
    
    plan = TestPlan.query.get(cycle.plan_id)
    if not plan:
        return {'error': 'Plan not found for this cycle'}, 404
    
    # Get plan TCs (optionally filtered by planned_cycle)
    ptcs = PlanTestCase.query.filter_by(plan_id=plan.id).all()
    
    existing_exec_tc_ids = set(
        ex.test_case_id for ex in TestExecution.query.filter_by(test_cycle_id=cycle_id).all()
    )
    
    created = 0
    for ptc in ptcs:
        if ptc.test_case_id in existing_exec_tc_ids:
            continue
        execution = TestExecution(
            test_cycle_id=cycle_id,
            test_case_id=ptc.test_case_id,
            project_id=cycle.project_id,
            result='not_run',
            assigned_to=ptc.planned_tester or '',
            assigned_to_id=ptc.planned_tester_id,
            executed_at=None,
        )
        db.session.add(execution)
        created += 1
    
    db.session.commit()
    return {'created': created, 'cycle_id': cycle_id, 'plan_id': plan.id}, 200


### TP-3.04: Populate from Previous Cycle

def populate_cycle_from_previous(cycle_id, prev_cycle_id, filter_status='failed'):
    """Carry forward failed/blocked executions from previous cycle.
    
    filter_status: 'failed' | 'blocked' | 'failed_blocked' | 'all'
    """
    cycle = TestCycle.query.get(cycle_id)
    prev_cycle = TestCycle.query.get(prev_cycle_id)
    if not cycle or not prev_cycle:
        return {'error': 'Cycle not found'}, 404
    
    status_filter = []
    if filter_status == 'failed':
        status_filter = ['fail']
    elif filter_status == 'blocked':
        status_filter = ['blocked']
    elif filter_status == 'failed_blocked':
        status_filter = ['fail', 'blocked']
    elif filter_status == 'all':
        status_filter = None  # No filter
    
    prev_execs = TestExecution.query.filter_by(test_cycle_id=prev_cycle_id)
    if status_filter:
        prev_execs = prev_execs.filter(TestExecution.result.in_(status_filter))
    prev_execs = prev_execs.all()
    
    existing_tc_ids = set(
        ex.test_case_id for ex in TestExecution.query.filter_by(test_cycle_id=cycle_id).all()
    )
    
    created = 0
    for prev_ex in prev_execs:
        if prev_ex.test_case_id in existing_tc_ids:
            continue
        execution = TestExecution(
            test_cycle_id=cycle_id,
            test_case_id=prev_ex.test_case_id,
            project_id=cycle.project_id,
            result='not_run',
            assigned_to=prev_ex.assigned_to or '',
            assigned_to_id=prev_ex.assigned_to_id,
        )
        db.session.add(execution)
        created += 1
    
    db.session.commit()
    return {
        'created': created,
        'source_cycle_id': prev_cycle_id,
        'filter': filter_status,
        'source_total': len(prev_execs),
    }, 200


### TP-3.05: Coverage Calculation

def calculate_scope_coverage(plan_id):
    """Calculate test coverage per scope item.
    
    For each PlanScope:
    1. Trace to linked TestCases (same logic as suggest)
    2. Check which are in PlanTestCase
    3. Check which have been executed (via TestExecution)
    4. Return: { scope_id, total_tcs, in_plan, executed, pass_rate, coverage_pct }
    """
    plan = TestPlan.query.get(plan_id)
    if not plan:
        return {'error': 'Plan not found'}, 404
    
    scopes = PlanScope.query.filter_by(plan_id=plan_id).all()
    plan_tc_ids = set(ptc.test_case_id for ptc in PlanTestCase.query.filter_by(plan_id=plan_id).all())
    
    # Get all executions for this plan's cycles
    cycles = TestCycle.query.filter_by(plan_id=plan_id).all()
    cycle_ids = [c.id for c in cycles]
    
    all_executions = []
    if cycle_ids:
        all_executions = TestExecution.query.filter(TestExecution.test_cycle_id.in_(cycle_ids)).all()
    
    exec_by_tc = {}
    for ex in all_executions:
        if ex.test_case_id not in exec_by_tc:
            exec_by_tc[ex.test_case_id] = []
        exec_by_tc[ex.test_case_id].append(ex)
    
    coverage_results = []
    for scope in scopes:
        traced_tcs = _trace_scope_to_test_cases(scope)
        traced_tc_ids = set(tc['test_case_id'] for tc in traced_tcs)
        
        in_plan_ids = traced_tc_ids & plan_tc_ids
        executed_ids = set(tc_id for tc_id in in_plan_ids if tc_id in exec_by_tc)
        passed_ids = set(
            tc_id for tc_id in executed_ids
            if any(ex.result == 'pass' for ex in exec_by_tc.get(tc_id, []))
        )
        
        total = len(traced_tc_ids)
        coverage_pct = round(len(in_plan_ids) / total * 100, 1) if total > 0 else 0
        exec_pct = round(len(executed_ids) / len(in_plan_ids) * 100, 1) if in_plan_ids else 0
        pass_rate = round(len(passed_ids) / len(executed_ids) * 100, 1) if executed_ids else 0
        
        # Update cached coverage_status
        if coverage_pct == 100:
            scope.coverage_status = 'full'
        elif coverage_pct > 0:
            scope.coverage_status = 'partial'
        else:
            scope.coverage_status = 'none'
        
        coverage_results.append({
            'scope_id': scope.id,
            'source_type': scope.source_type,
            'source_code': scope.source_code,
            'source_title': scope.source_title,
            'total_traceable_tcs': total,
            'in_plan': len(in_plan_ids),
            'executed': len(executed_ids),
            'passed': len(passed_ids),
            'coverage_pct': coverage_pct,
            'execution_pct': exec_pct,
            'pass_rate': pass_rate,
        })
    
    db.session.commit()  # Save coverage_status updates
    
    return {
        'plan_id': plan_id,
        'scopes': coverage_results,
        'summary': {
            'total_scopes': len(scopes),
            'full_coverage': sum(1 for r in coverage_results if r['coverage_pct'] == 100),
            'partial_coverage': sum(1 for r in coverage_results if 0 < r['coverage_pct'] < 100),
            'no_coverage': sum(1 for r in coverage_results if r['coverage_pct'] == 0),
        }
    }, 200


### TP-3.06: Data Readiness Check

def check_data_readiness(plan_id):
    """Check if all mandatory data sets for a plan are ready."""
    plan_datasets = PlanDataSet.query.filter_by(plan_id=plan_id).all()
    
    results = []
    all_ready = True
    for pds in plan_datasets:
        ds = TestDataSet.query.get(pds.data_set_id)
        if not ds:
            continue
        is_ready = ds.status == 'ready'
        if pds.is_mandatory and not is_ready:
            all_ready = False
        results.append({
            'data_set_id': ds.id,
            'name': ds.name,
            'status': ds.status,
            'environment': ds.environment,
            'is_mandatory': pds.is_mandatory,
            'is_ready': is_ready,
        })
    
    return {
        'plan_id': plan_id,
        'all_mandatory_ready': all_ready,
        'data_sets': results,
    }, 200


### TP-3.07: Exit Criteria Evaluation

def evaluate_exit_criteria(plan_id):
    """Automated evaluation of plan exit criteria.
    
    Checks:
    1. Pass rate threshold (default 95%)
    2. Open S1/S2 defects = 0
    3. All mandatory data sets verified
    4. Execution completion ≥ threshold
    """
    plan = TestPlan.query.get(plan_id)
    if not plan:
        return {'error': 'Plan not found'}, 404
    
    # Get all cycles and executions
    cycles = TestCycle.query.filter_by(plan_id=plan_id).all()
    cycle_ids = [c.id for c in cycles]
    
    executions = TestExecution.query.filter(TestExecution.test_cycle_id.in_(cycle_ids)).all() if cycle_ids else []
    
    total_execs = len(executions)
    passed = sum(1 for e in executions if e.result == 'pass')
    failed = sum(1 for e in executions if e.result == 'fail')
    not_run = sum(1 for e in executions if e.result == 'not_run')
    blocked = sum(1 for e in executions if e.result == 'blocked')
    
    pass_rate = round(passed / (passed + failed) * 100, 1) if (passed + failed) > 0 else 0
    completion_rate = round((total_execs - not_run) / total_execs * 100, 1) if total_execs > 0 else 0
    
    # Open critical/high defects
    open_s1 = Defect.query.filter(
        Defect.project_id == plan.project_id,
        Defect.severity == 'critical',
        Defect.status.notin_(['closed', 'cancelled', 'deferred'])
    ).count()
    
    open_s2 = Defect.query.filter(
        Defect.project_id == plan.project_id,
        Defect.severity == 'high',
        Defect.status.notin_(['closed', 'cancelled', 'deferred'])
    ).count()
    
    # Data readiness
    data_check, _ = check_data_readiness(plan_id)
    
    # Evaluate gates
    gates = [
        {'name': 'Pass Rate ≥ 95%', 'value': f'{pass_rate}%', 'passed': pass_rate >= 95},
        {'name': 'Zero S1 Defects', 'value': str(open_s1), 'passed': open_s1 == 0},
        {'name': 'Zero S2 Defects', 'value': str(open_s2), 'passed': open_s2 == 0},
        {'name': 'Completion ≥ 95%', 'value': f'{completion_rate}%', 'passed': completion_rate >= 95},
        {'name': 'Data Sets Ready', 'value': str(data_check['all_mandatory_ready']), 'passed': data_check['all_mandatory_ready']},
    ]
    
    all_passed = all(g['passed'] for g in gates)
    
    return {
        'plan_id': plan_id,
        'overall': 'PASS' if all_passed else 'FAIL',
        'gates': gates,
        'stats': {
            'total_executions': total_execs,
            'passed': passed, 'failed': failed, 'blocked': blocked, 'not_run': not_run,
            'pass_rate': pass_rate, 'completion_rate': completion_rate,
            'open_s1': open_s1, 'open_s2': open_s2,
        }
    }, 200


### Service Endpoint'leri Blueprint'e Ekle

Dosya: app/blueprints/testing_bp.py
Import ekle ve route'ları bağla:

from app.services.test_planning_service import (
    suggest_test_cases, import_from_suite,
    populate_cycle_from_plan, populate_cycle_from_previous,
    calculate_scope_coverage, check_data_readiness, evaluate_exit_criteria
)

@testing_bp.route('/plans/<int:plan_id>/suggest-test-cases', methods=['POST'])
def api_suggest_test_cases(plan_id):
    result, status = suggest_test_cases(plan_id)
    return jsonify(result), status

@testing_bp.route('/plans/<int:plan_id>/import-suite/<int:suite_id>', methods=['POST'])
def api_import_from_suite(plan_id, suite_id):
    result, status = import_from_suite(plan_id, suite_id)
    return jsonify(result), status

@testing_bp.route('/cycles/<int:cycle_id>/populate', methods=['POST'])
def api_populate_cycle(cycle_id):
    result, status = populate_cycle_from_plan(cycle_id)
    return jsonify(result), status

@testing_bp.route('/cycles/<int:cycle_id>/populate-from-cycle/<int:prev_id>', methods=['POST'])
def api_populate_from_previous(cycle_id, prev_id):
    filter_status = request.args.get('filter', 'failed_blocked')
    result, status = populate_cycle_from_previous(cycle_id, prev_id, filter_status)
    return jsonify(result), status

@testing_bp.route('/plans/<int:plan_id>/coverage', methods=['GET'])
def api_coverage(plan_id):
    result, status = calculate_scope_coverage(plan_id)
    return jsonify(result), status

@testing_bp.route('/cycles/<int:cycle_id>/data-check', methods=['GET'])
def api_data_check(cycle_id):
    cycle = TestCycle.query.get_or_404(cycle_id)
    result, status = check_data_readiness(cycle.plan_id)
    return jsonify(result), status

@testing_bp.route('/plans/<int:plan_id>/evaluate-exit', methods=['POST'])
def api_evaluate_exit(plan_id):
    result, status = evaluate_exit_criteria(plan_id)
    return jsonify(result), status


### Test
curl -s -X POST "$BASE/plans/1/suggest-test-cases" | python3 -m json.tool
curl -s -X POST "$BASE/cycles/1/populate" | python3 -m json.tool
curl -s "$BASE/plans/1/coverage" | python3 -m json.tool
curl -s -X POST "$BASE/plans/1/evaluate-exit" | python3 -m json.tool

### Commit
git add -A
git commit -m "feat(testing): TP-Sprint 3 — Smart services

- suggest_test_cases: Auto-trace PlanScope → TCs (5 source types)
- import_from_suite: Bulk import TCs from suite
- populate_cycle_from_plan: Create executions from PlanTestCase
- populate_cycle_from_previous: Carry forward failed/blocked
- calculate_scope_coverage: Scope × TC × Execution matrix
- check_data_readiness: Mandatory dataset validation
- evaluate_exit_criteria: Automated gate check (pass rate, defects, completion)"
git push

## EXIT CRITERIA
- [ ] suggest-test-cases endpoint JSON dönüyor
- [ ] populate endpoint execution kayıtları oluşturuyor
- [ ] coverage endpoint yüzde hesaplıyor
- [ ] evaluate-exit PASS/FAIL dönüyor
- [ ] Mevcut testler geçiyor
```

---

# ═══════════════════════════════════════════════════════════════════
# TP-SPRINT 4: FRONTEND INTEGRATION (~18h, 4 gün)
# Plan detail view, Scope tab, TC Pool tab, Data tab, Coverage dashboard
# ═══════════════════════════════════════════════════════════════════

```
## BAĞLAM

SAP Transformation Platform — Flask + PostgreSQL
- TP-Sprint 1–3 TAMAMLANDI — Schema + CRUD + Services
- Frontend: static/js/views/ (Vanilla JS, modular view pattern)
- Mevcut test views: test_plans.js, test_execution.js, test_suites.js
- API client: static/js/explore-api.js (API.get, API.post, API.put, API.delete)
- UI components: static/js/components/ (ExpUI helper)
- Design: Perga brand (navy #0B1623, gold #C08B5C, marble #F7F5F0)
- Entity colors: blue=Scenario, gold=WRICEF, green=Fit, red=Gap

## GÖREV: TP-SPRINT 4 — Frontend Integration

### TP-4.01: Plan Detail View — 4 Tab Yapısı

Dosya: static/js/views/test_planning.js (MEVCUT dosyayı genişlet veya YENİ oluştur)

Plan detail view açıldığında 4 tab göster:
1. **Scope** — PlanScope items (kaynak entity'ler)
2. **Test Cases** — PlanTestCase pool (TC listesi + suggest/import butonları)
3. **Data** — PlanDataSet + linked TestDataSet'ler
4. **Cycles** — Mevcut TestCycle listesi + populate butonu

Tab yapısı mevcut test_execution.js'teki tab pattern'ini takip et:

async function renderPlanDetail(planId) {
    const plan = await API.get(`/test-plans/${planId}`);
    
    const container = document.getElementById('content-area');
    container.innerHTML = `
        <div class="page-header">
            <h2>${plan.name}</h2>
            <span class="badge badge-${plan.plan_type}">${plan.plan_type.toUpperCase()}</span>
            <span class="badge badge-${plan.status}">${plan.status}</span>
        </div>
        
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchPlanTab('scope', ${planId})">
                📋 Scope
            </button>
            <button class="tab-btn" onclick="switchPlanTab('test-cases', ${planId})">
                🧪 Test Cases
            </button>
            <button class="tab-btn" onclick="switchPlanTab('data', ${planId})">
                💾 Data Sets
            </button>
            <button class="tab-btn" onclick="switchPlanTab('cycles', ${planId})">
                🔄 Cycles
            </button>
        </div>
        
        <div id="plan-tab-content"></div>
    `;
    
    // Default: Scope tab
    await renderScopeTab(planId);
}

### TP-4.02: Scope Tab

async function renderScopeTab(planId) {
    const scopes = await API.get(`/plans/${planId}/scopes`);
    const container = document.getElementById('plan-tab-content');
    
    container.innerHTML = `
        <div class="tab-actions">
            <button class="btn btn-primary" onclick="openAddScopeModal(${planId})">
                + Add Scope Item
            </button>
            <button class="btn btn-secondary" onclick="refreshCoverage(${planId})">
                📊 Refresh Coverage
            </button>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Code</th>
                    <th>Title</th>
                    <th>Priority</th>
                    <th>Risk</th>
                    <th>Coverage</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${scopes.map(s => `
                    <tr>
                        <td><span class="badge badge-scope-${s.source_type}">${s.source_type}</span></td>
                        <td>${s.source_code || '—'}</td>
                        <td>${s.source_title || '—'}</td>
                        <td><span class="badge badge-${s.priority}">${s.priority}</span></td>
                        <td><span class="badge badge-risk-${s.risk_level}">${s.risk_level}</span></td>
                        <td>${renderCoverageBadge(s.coverage_status)}</td>
                        <td>
                            <button class="btn-icon" onclick="deletePlanScope(${s.id}, ${planId})">🗑️</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function renderCoverageBadge(status) {
    const colors = { full: '#10B981', partial: '#F59E0B', none: '#EF4444', not_calculated: '#6B7280' };
    const labels = { full: '✅ Full', partial: '⚠️ Partial', none: '❌ None', not_calculated: '— N/A' };
    return `<span style="color:${colors[status]}">${labels[status] || status}</span>`;
}

### TP-4.03: TC Pool Tab

async function renderTestCasesTab(planId) {
    const ptcs = await API.get(`/plans/${planId}/test-cases`);
    const container = document.getElementById('plan-tab-content');
    
    container.innerHTML = `
        <div class="tab-actions">
            <button class="btn btn-primary" onclick="openAddTCModal(${planId})">
                + Add Manual
            </button>
            <button class="btn btn-gold" onclick="suggestTestCases(${planId})">
                🤖 Suggest from Scope
            </button>
            <button class="btn btn-secondary" onclick="openImportSuiteModal(${planId})">
                📥 Import Suite
            </button>
        </div>
        
        <div class="stats-bar">
            <span>Total: ${ptcs.length}</span>
            <span>Effort: ${ptcs.reduce((sum, p) => sum + (p.estimated_effort || 0), 0)} min</span>
        </div>
        
        <table class="data-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>TC Code</th>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Method</th>
                    <th>Priority</th>
                    <th>Tester</th>
                    <th>Effort</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${ptcs.map((p, i) => `
                    <tr>
                        <td>${p.execution_order || i + 1}</td>
                        <td>${p.test_case_code || '—'}</td>
                        <td>${p.test_case_title || '—'}</td>
                        <td>${p.test_case_type || '—'}</td>
                        <td><span class="badge badge-method-${p.added_method}">${p.added_method}</span></td>
                        <td><span class="badge badge-${p.priority}">${p.priority}</span></td>
                        <td>${p.planned_tester || '—'}</td>
                        <td>${p.estimated_effort ? p.estimated_effort + ' min' : '—'}</td>
                        <td>
                            <button class="btn-icon" onclick="editPlanTC(${p.id})">✏️</button>
                            <button class="btn-icon" onclick="removePlanTC(${p.id}, ${planId})">🗑️</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function suggestTestCases(planId) {
    const result = await API.post(`/plans/${planId}/suggest-test-cases`);
    // Modal ile önerileri göster — kullanıcı seçip ekleyebilsin
    openSuggestionsModal(result.suggestions, planId);
}

### TP-4.04: Data Sets Tab (Data Factory UI)

async function renderDataTab(planId) {
    const planDataSets = await API.get(`/plans/${planId}/data-sets`);
    const container = document.getElementById('plan-tab-content');
    
    container.innerHTML = `
        <div class="tab-actions">
            <button class="btn btn-primary" onclick="openLinkDataSetModal(${planId})">
                🔗 Link Data Set
            </button>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Environment</th>
                    <th>Status</th>
                    <th>Mandatory</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${planDataSets.map(pds => `
                    <tr>
                        <td>${pds.data_set_name || '—'}</td>
                        <td>${pds.data_set_environment || '—'}</td>
                        <td>${renderDataSetStatus(pds.data_set_status)}</td>
                        <td>${pds.is_mandatory ? '⚠️ Yes' : 'No'}</td>
                        <td>
                            <button class="btn-icon" onclick="unlinkDataSet(${pds.id}, ${planId})">🔗❌</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

### TP-4.05: Cycle Populate Flow

Mevcut test_execution.js'e "Populate" butonu ekle:

// Cycle detail'de buton:
<button class="btn btn-gold" onclick="populateCycleFromPlan(${cycleId})">
    📥 Populate from Plan
</button>
<button class="btn btn-secondary" onclick="openPopulateFromCycleModal(${cycleId})">
    🔄 Carry Forward
</button>

async function populateCycleFromPlan(cycleId) {
    if (!confirm('Populate this cycle from the test plan? This will create execution records for all planned test cases.')) return;
    const result = await API.post(`/cycles/${cycleId}/populate`);
    showToast(`✅ ${result.created} executions created`);
    await refreshCycleDetail(cycleId);
}

### TP-4.06: Coverage Dashboard

async function renderCoverageDashboard(planId) {
    const coverage = await API.get(`/plans/${planId}/coverage`);
    const exitResult = await API.post(`/plans/${planId}/evaluate-exit`);
    
    // Coverage matrix: scope × TC table
    // Exit criteria gates: pass/fail indicators
    // Progress bars per scope item
    // Summary cards: total scopes, full/partial/none coverage counts
}

### Commit
git add -A
git commit -m "feat(testing): TP-Sprint 4 — Frontend integration

- Plan detail view with 4 tabs (Scope, Test Cases, Data, Cycles)
- Scope management: add/remove/coverage indicators
- TC Pool: manual add, suggest from scope, import from suite
- Data Sets: link/unlink, readiness status
- Cycle populate: from plan, carry forward from previous
- Coverage dashboard: scope × TC matrix with % bars
- Exit criteria evaluation display"
git push

## EXIT CRITERIA
- [ ] Plan detail 4 tab gösteriyor
- [ ] Scope tab'da item ekle/sil/coverage çalışıyor
- [ ] TC Pool tab'da suggest/import/manual ekleme çalışıyor
- [ ] Data tab'da link/unlink çalışıyor
- [ ] Cycle populate butonu execution oluşturuyor
- [ ] Coverage dashboard yüzde gösteriyor
- [ ] F12 Console'da JS error yok
```

---

# ═══════════════════════════════════════════════════════════════════
# HIZLI REFERANS
# ═══════════════════════════════════════════════════════════════════

## Sprint Sırası ve Bağımlılıklar

```
TP-Sprint 1 (Schema) ──► TP-Sprint 2 (CRUD) ──► TP-Sprint 3 (Services) ──► TP-Sprint 4 (Frontend)
```

Her sprint öncekine bağımlı. Sırayla yap.

## Model Özeti

| Model | Tablo | Modül | Key Fields |
|-------|-------|-------|------------|
| PlanScope | plan_scopes | testing.py | plan_id, source_type, source_id, coverage_status |
| PlanTestCase | plan_test_cases | testing.py | plan_id, test_case_id, added_method, estimated_effort |
| PlanDataSet | plan_data_sets | testing.py | plan_id, data_set_id, is_mandatory |
| TestDataSet | test_data_sets | data_factory.py | name, environment, status, refresh_strategy |
| TestDataSetItem | test_data_set_items | data_factory.py | data_set_id, data_object_id, status |

## Endpoint Özeti (27 yeni)

| # | Method | Endpoint | Sprint |
|---|--------|----------|--------|
| 1-4 | CRUD | /plans/{id}/scopes, /plan-scopes/{id} | S2 |
| 5-8 | CRUD | /plans/{id}/test-cases, /plan-test-cases/{id} | S2 |
| 9-13 | CRUD | /test-data-sets, /test-data-sets/{id} | S2 |
| 14-17 | CRUD | /test-data-sets/{id}/items, /test-data-set-items/{id} | S2 |
| 18-20 | CRUD | /plans/{id}/data-sets, /plan-data-sets/{id} | S2 |
| 21 | POST | /plans/{id}/suggest-test-cases | S3 |
| 22 | POST | /plans/{id}/import-suite/{suite_id} | S3 |
| 23 | POST | /cycles/{id}/populate | S3 |
| 24 | POST | /cycles/{id}/populate-from-cycle/{prev_id} | S3 |
| 25 | GET | /plans/{id}/coverage | S3 |
| 26 | GET | /cycles/{id}/data-check | S3 |
| 27 | POST | /plans/{id}/evaluate-exit | S3 |

## Her Sprint Sonrası Checklist

- [ ] Alembic migration başarılı (Sprint 1)
- [ ] curl test'ler geçti
- [ ] Mevcut testler kırılmadı (zero regression)
- [ ] git commit + push başarılı
- [ ] Browser'da hata yok (Sprint 4)

## Acil Kurtarma

git checkout main -- app/models/testing.py app/models/data_factory.py
alembic downgrade -1

---

*Test Planning Enhancement Copilot Prompts — 2026-02-17*
*33 tasks, 4 sprints, ~60 saat, 14 gün*
