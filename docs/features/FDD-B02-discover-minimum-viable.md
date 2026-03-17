# FDD-B02: Discover Fazı Minimum Viable (Project Charter)

**Öncelik:** P1
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → B-02
**Effort:** L (2–3 sprint)
**Faz Etkisi:** Discover — SAP Activate ilk faz
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Platform, SAP Activate metodolojisinin **Discover fazını hiç kapsamamaktadır.** Bir proje oluşturulduğunda direkt Explore fazına geçilmektedir. Bu durum:

1. Müşteri platformu kullandığında "proje neden yapılıyor?" sorusunun yanıtı kaybolmaktadır.
2. Proje tipi (Greenfield / Brownfield / Selective / Cloud) seçimi var ama bu seçime göre herhangi bir aksiyon tetiklenmiyor.
3. Business case, AS-IS tespiti, scope kararı — tüm bunlar platform dışında gerçekleşiyor.

### Discover Fazı Minimum Viable Scope
Bu FDD tam bir Discover modülü değil: **Project Charter** ve **Initial Assessment** formatında minimum viable Discover kapsamını tanımlar.

---

## 2. İş Değeri

- Müşteri proje yolculuğuna Discover'dan başlayabilir, platform tek kaynak olur.
- SAP projesinin "why" kısmı platform içinde belgelenmiş olur.
- Prepare fazına geçiş için formal bir gate check mümkün hale gelir.
- Satış sürecinde "uçtan uca SAP Activate uyumlu" iddiası doğrulanabilir hale gelir.

---

## 3. Hedef Kapsam (MVP)

| Capability | Model | Öncelik |
|------------|-------|---------|
| Project Charter | `ProjectCharter` (yeni) | ✅ Sprint 1 |
| AS-IS System Landscape | `SystemLandscape` (yeni) | ✅ Sprint 1 |
| SAP S/4HANA Deployment Model Selection | `Program.deployment_model` (mevcut genişletme) | ✅ Sprint 1 |
| Initial Scope Assessment | `ScopeAssessment` (yeni) | ✅ Sprint 2 |
| Business Case Builder (basit) | `BusinessCase` (yeni) | ⬜ Sprint 2 |
| Roadmap Builder (faz tahmini) | Program.Phase üzerinden | ⬜ Sprint 3 |

---

## 4. Veri Modeli

### 4.1 Yeni Model: `ProjectCharter`
**Dosya:** `app/models/program.py` içine ekle

```python
class ProjectCharter(db.Model):
    """
    SAP Activate Discover fazı çıktısı: proje gerekçesi ve temel kararlar.

    Her Program için bir charter oluşturulur. Discover Gate'i geçebilmek için
    charter'ın en az status='approved' olması gerekir.

    Lifecycle: draft → in_review → approved
    """
    __tablename__ = "project_charters"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="Her program için en fazla bir charter"
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # --- Proje Gerekçesi ---
    project_objective = db.Column(db.Text, nullable=True, comment="Projenin iş hedefi")
    business_drivers = db.Column(db.Text, nullable=True, comment="Neden şimdi? Tetikleyici faktörler")
    expected_benefits = db.Column(db.Text, nullable=True, comment="Beklenen iş faydaları")
    key_risks = db.Column(db.Text, nullable=True, comment="Bilinen başlangıç riskleri")

    # --- Kapsam Özeti ---
    in_scope_summary = db.Column(db.Text, nullable=True, comment="Kapsama dahil alanlar özeti")
    out_of_scope_summary = db.Column(db.Text, nullable=True, comment="Kapsam dışı alanlar")
    affected_countries = db.Column(db.String(500), nullable=True, comment="CSV ülke kodları: TR,DE,NL")
    affected_sap_modules = db.Column(db.String(500), nullable=True, comment="CSV modül kodları: FI,MM,SD")

    # --- Proje Tipi ---
    project_type = db.Column(
        db.String(30),
        nullable=False,
        default="greenfield",
        comment="greenfield | brownfield | selective_migration | cloud_move"
    )
    target_go_live_date = db.Column(db.Date, nullable=True)
    estimated_duration_months = db.Column(db.Integer, nullable=True)

    # --- Onay ---
    status = db.Column(
        db.String(20),
        nullable=False,
        default="draft",
        comment="draft | in_review | approved | rejected"
    )
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.2 Yeni Model: `SystemLandscape`
```python
class SystemLandscape(db.Model):
    """
    AS-IS sistem peyzajı. Hangi SAP/non-SAP sistemler mevcut?
    Go-live sonrası hangileri emekli olacak, hangileri entegre kalacak?
    """
    __tablename__ = "system_landscapes"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    system_name = db.Column(db.String(100), nullable=False)
    system_type = db.Column(
        db.String(30),
        nullable=False,
        comment="sap_erp | s4hana | non_sap | middleware | cloud | legacy"
    )
    role = db.Column(
        db.String(20),
        nullable=False,
        default="source",
        comment="source | target | interface | decommission | keep"
    )
    vendor = db.Column(db.String(100), nullable=True)
    version = db.Column(db.String(50), nullable=True)
    environment = db.Column(
        db.String(20),
        nullable=False,
        default="prod",
        comment="dev | test | q | prod"
    )
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.3 Yeni Model: `ScopeAssessment`
```python
class ScopeAssessment(db.Model):
    """
    SAP modül bazında ilk scope değerlendirmesi.
    Hangi modüller dahil, hangileri değil, kompleksite nedir?
    """
    __tablename__ = "scope_assessments"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    sap_module = db.Column(db.String(10), nullable=False, comment="FI, MM, SD, PP, CO, HR, etc.")
    is_in_scope = db.Column(db.Boolean, nullable=False, default=True)
    complexity = db.Column(
        db.String(10),
        nullable=True,
        comment="low | medium | high | very_high"
    )
    estimated_requirements = db.Column(db.Integer, nullable=True, comment="Tahmini requirement sayısı")
    estimated_gaps = db.Column(db.Integer, nullable=True, comment="Tahmini gap sayısı (WRICEF)")
    notes = db.Column(db.Text, nullable=True)
    assessment_basis = db.Column(
        db.String(30),
        nullable=True,
        comment="workshop | document_review | interview | expert_estimate"
    )
    assessed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assessed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.4 Migration
```
flask db migrate -m "add project_charters, system_landscapes, scope_assessments tables"
```

---

## 5. Servis Katmanı

### 5.1 Yeni Servis: `app/services/discover_service.py`

```python
"""
Discover fazı iş mantığı.

Discover → Prepare geçişi için gate check:
  - ProjectCharter.status == 'approved'
  - En az 1 SystemLandscape kaydı
  - En az 3 ScopeAssessment modülü tanımlanmış
"""

def create_or_update_charter(tenant_id: int, program_id: int, data: dict) -> dict:
def approve_charter(tenant_id: int, program_id: int, approver_id: int, notes: str | None) -> dict:
def get_charter(tenant_id: int, program_id: int) -> dict:

def add_system_landscape(tenant_id: int, program_id: int, data: dict) -> dict:
def list_system_landscapes(tenant_id: int, program_id: int) -> list[dict]:
def delete_system_landscape(tenant_id: int, program_id: int, landscape_id: int) -> None:

def save_scope_assessment(tenant_id: int, program_id: int, module: str, data: dict) -> dict:
def list_scope_assessments(tenant_id: int, program_id: int) -> list[dict]:

def get_discover_gate_status(tenant_id: int, program_id: int) -> dict:
"""
Returns:
    {
      "gate_passed": False,
      "criteria": [
        {"name": "charter_approved", "passed": True},
        {"name": "system_landscape_defined", "passed": True},
        {"name": "min_3_modules_assessed", "passed": False, "current": 1, "required": 3}
      ]
    }
"""
```

---

## 6. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/discover_bp.py`

```
# Project Charter
GET    /api/v1/programs/<prog_id>/discover/charter
POST   /api/v1/programs/<prog_id>/discover/charter
PUT    /api/v1/programs/<prog_id>/discover/charter
POST   /api/v1/programs/<prog_id>/discover/charter/approve

# System Landscape
GET    /api/v1/programs/<prog_id>/discover/landscape
POST   /api/v1/programs/<prog_id>/discover/landscape
PUT    /api/v1/programs/<prog_id>/discover/landscape/<id>
DELETE /api/v1/programs/<prog_id>/discover/landscape/<id>

# Scope Assessment
GET    /api/v1/programs/<prog_id>/discover/scope-assessment
POST   /api/v1/programs/<prog_id>/discover/scope-assessment
PUT    /api/v1/programs/<prog_id>/discover/scope-assessment/<id>

# Gate Check
GET    /api/v1/programs/<prog_id>/discover/gate-status

Permission: discover.view / discover.edit / discover.approve
```

---

## 7. Frontend Değişiklikleri

### 7.1 Yeni View: `static/js/views/discover.js`
Yeni Discover fazı sayfası:

**Tab 1: Project Charter**
- Form alanları: Proje hedefi, iş gerekçeleri, beklenen faydalar, riskler
- Kapsam özeti: in-scope SAP modülleri, ülkeler
- Proje tipi selection: Greenfield/Brownfield/Selective/Cloud (görsel kartlar)
- Target go-live date picker
- Approve butonu (permission: discover.approve)

**Tab 2: System Landscape**
- Tablo: sistem adı, tip, rol (source/target/decommission), versiyon
- Görsel mimari diyagramı (basit — opsiyonel, Phase 2)

**Tab 3: Scope Assessment**
- SAP modül grid: her modül için in-scope toggle, complexity dropdown, tahmini req/gap sayıları
- Toplam tahmin: X requirement, Y WRICEF bekleniyor

**Discover Gate Status:**
Banner/card olarak sayfanın üstünde:
```
🔴 Discover Gate: OPEN | 2/3 kriter karşılandı
  ✅ Charter approved
  ✅ System landscape defined
  ❌ Min 3 modules assessed (1/3)
```

### 7.2 Navigation Güncellemesi
`program.js` veya sidebar'a "Discover" faz linkini ekle — proje setup'tan önce.

---

## 8. Test Gereksinimleri

```python
# tests/test_discover_service.py

def test_create_charter_returns_201():
def test_charter_approve_requires_discover_approve_permission():
def test_charter_approve_sets_approved_at_and_approver_id():
def test_discover_gate_fails_when_charter_not_approved():
def test_discover_gate_fails_when_no_system_landscape():
def test_discover_gate_passes_when_all_criteria_met():
def test_system_landscape_create_and_list():
def test_scope_assessment_create_upsert_by_module():
def test_tenant_isolation_charter_cross_tenant_404():
def test_tenant_isolation_landscape_cross_tenant_404():
```

---

## 9. Kabul Kriterleri

- [ ] Yeni `discover.js` view'ı tüm 3 tab ile çalışıyor.
- [ ] `ProjectCharter` oluşturulup onaylanabiliyor.
- [ ] `SystemLandscape` kayıtları eklenip listelenebiliyor.
- [ ] `ScopeAssessment` SAP modül bazında kaydediliyor.
- [ ] Discover Gate Status endpoint'i doğru `gate_passed` döndürüyor.
- [ ] Navigation'da Discover faz linki görünüyor.
- [ ] Tüm testler geçiyor, tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P1 — B-02 · Sprint 2-3 · Effort L
**Reviewer Kararı:** 🟡 ONAYLANIR — Sprint 2 başında aşağıdaki kararlar verilmeli

### Tespit Edilen Bulgular

1. **`ProjectCharter` lifecycle — PhaseGate entegrasyonu tanımlanmamış.**
   Charter `draft → in_review → approved` lifecycle'ına sahip. Ancak Discover Gate'i geçebilmek için charter'ın `approved` olması gerektiği belirtilmiş. Bu gate check'in `gate_service.py`'de nasıl implement edileceği FDD'de eksik. B-04 (sign-off) ile koordinasyon gerekiyor — charter approval da bir sign-off akışından geçebilir.

2. **`SystemLandscape` modeli — tenant izolasyonu belirsiz.**
   FDD'de `SystemLandscape` modeli tanımlanıyor ama `TenantModel`'den mı yoksa `db.Model`'den mı miras aldığı belirtilmemiş. Tenant bazlı sistem landscape verisi olduğu için `TenantModel` kullanılmalı ve tüm sorgular `tenant_id` ile scope'lanmalı.

3. **`ScopeAssessment` — SAP modül seçimi double-entry riski.**
   Kullanıcı hem `ScopeAssessment`'ta SAP modül seçiyor hem de ilerleyen fazda Explore Workshop'ta aynı modülleri tekrar tanımlıyor. Aralarında bağlantı olmazsa tutarsızlık çıkar. `ScopeAssessment.selected_modules` ile Explore scope arasında bir consistency check mekanizması zaman içinde eklenmeli.

4. **I-07 (1YG Seed Catalog) ve B-02 entegrasyonu.**
   Discover fazında scope assessment yapılırken seed catalog'dan standart SAP process scope'u önerilebilir. Bu entegrasyon Sprint 7'ye kadar bekleyebilir ama FDD'de entegrasyon noktası olarak not edilmeli.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Charter approval → Discover Gate bağlantısını FDD'ye ekle (B-04 ile koordine) | Architect | Sprint 2 |
| A2 | `SystemLandscape` modelini `TenantModel`'den türet | Coder | Sprint 2 |
| A3 | `ScopeAssessment` → Explore workshop consistency check'i backlog'a ekle | Architect | Sprint 3+ |
| A4 | I-07 entegrasyon noktasını FDD'ye not olarak ekle | Architect | Sprint 2 |
