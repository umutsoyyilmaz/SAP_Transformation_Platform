# FDD-I02: Authorization Concept Design Modülü

**Öncelik:** Backlog
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-02
**Effort:** XL (3 sprint)
**Faz Etkisi:** Explore, Realize — SAP yetkilendirme konsepti tasarımı
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

SAP S/4HANA projelerinde yetkilendirme konsepti (Authorization Concept) kritik bir çıktıdır:
- Hangi kullanıcı hangi transaction'lara erişebilir?
- Hangi authorization objects hangi değerlerle atanır?
- SOD (Segregation of Duties) çakışmaları var mı?
- SAP role tasarımı: single role vs composite role.

Platform'da SU24/SU25 tabanlı rol tasarımı araçları tamamen yoktur.

---

## 2. İş Değeri

- SI danışmanları authorization concept'i Excel'den çıkarır — platform bu çalışmayı zaten bulunan iş süreçleri (L4 process steps, WRICEF) ile ilişkilendirir.
- Otomatik SOD matrix: finance + procurement çakışması gibi riskler erken tespit edilir.
- Proje bitmeden müşteriyle authority concept'i revize edilebilir.
- SU10 bulk user assignment için çıktı üretilir.

---

## 3. SAP Teknik Bağlam

SAP Yetkilendirme Terminolojisi:
- **Authorization Object:** ABAP object, örn `F_BKPF_BUK` (FI belge, şirket kodu izni).
- **Authorization Field:** Her obje içinde field'lar: `ACTVT` (activity), `BUKRS` (şirket kodu).
- **Single Role:** Belirli bir iş fonksiyonu için gerekli tüm objeler. Örn `Z_FI_AR_CLERK`.
- **Composite Role:** Birden fazla single role'ün birleşimi. Örn `Z_FI_ACCOUNTANT`.
- **Org Level:** `BUKRS`, `WERKS`, `VKORG` — şirket/fabrika/satış org.
- **SOD:** Aynı kişinin ödemeyi hem create hem approve edememesi gibi kural.

---

## 4. Veri Modeli

### 4.1 Yeni Dosya: `app/models/authorization.py`

```python
class AuthRole(db.Model):
    """
    SAP Yetkilendirme Rolü tasarımı.
    Single role: belirli iş fonksiyonu.
    Composite role: single rollerin kümesi.
    """
    __tablename__ = "auth_roles"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    role_name = db.Column(db.String(30), nullable=False, comment="Z_FI_AR_CLERK formati")
    role_type = db.Column(db.String(20), nullable=False, default="single",
                          comment="single | composite")
    description = db.Column(db.String(500), nullable=True)
    sap_module = db.Column(db.String(10), nullable=True)

    # Org level değerleri (JSON dict: {BUKRS: "1000", WERKS: "*"})
    org_levels = db.Column(db.JSON, nullable=True)

    # Composite role için single role ID listesi
    child_role_ids = db.Column(db.JSON, nullable=True,
                                comment="[1, 2, 3] — composite için")

    # Business role eşlemesi
    business_role_description = db.Column(db.String(200), nullable=True,
                                           comment="Accounts Receivable Clerk")
    user_count_estimate = db.Column(db.Integer, nullable=True)
    linked_process_step_ids = db.Column(db.JSON, nullable=True,
                                         comment="[L4 ProcessStep ID listesi]")

    status = db.Column(db.String(20), nullable=False, default="draft",
                       comment="draft | in_review | approved | implemented")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    auth_objects = db.relationship("AuthRoleObject", back_populates="auth_role",
                                    cascade="all, delete-orphan", lazy="select")
    sod_assessments = db.relationship("SODRiskAssessment",
                                       foreign_keys="SODRiskAssessment.role_a_id",
                                       lazy="select")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AuthRoleObject(db.Model):
    """
    SAP Authorization Object atama: belirli role için obje + field değerleri.
    """
    __tablename__ = "auth_role_objects"

    id = db.Column(db.Integer, primary_key=True)
    auth_role_id = db.Column(db.Integer, db.ForeignKey("auth_roles.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"),
                           nullable=True, index=True)

    auth_object = db.Column(db.String(10), nullable=False,
                             comment="SAP auth object: F_BKPF_BUK")
    auth_object_description = db.Column(db.String(200), nullable=True)

    # Field→Value mapping olarak JSON
    # Örn: {"ACTVT": ["01","02","03"], "BUKRS": ["1000"], "KOART": ["*"]}
    field_values = db.Column(db.JSON, nullable=False)

    source = db.Column(db.String(20), nullable=True,
                       comment="su24 | manual | su25_template — nereden geldiği")

    auth_role = db.relationship("AuthRole", back_populates="auth_objects")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SODRiskAssessment(db.Model):
    """
    Segregation of Duties risk değerlendirmesi: iki role arasında çakışma.

    Örn: Z_FI_AR_CLERK (create invoice) + Z_FI_AP_PAYMENT (approve payment)
    aynı kullanıcıya atanırsa fraud riski oluşur.
    """
    __tablename__ = "sod_risk_assessments"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"),
                           nullable=True, index=True)

    role_a_id = db.Column(db.Integer, db.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False)
    role_b_id = db.Column(db.Integer, db.ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False)

    risk_level = db.Column(db.String(10), nullable=False,
                            comment="critical | high | medium | low")
    risk_description = db.Column(db.String(500), nullable=True)
    mitigating_control = db.Column(db.Text, nullable=True,
                                    comment="Compensating control tanımı")
    is_accepted = db.Column(db.Boolean, nullable=False, default=False,
                             comment="Risk kabul edildi mi (residual risk)")
    accepted_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.2 Migration
```
flask db migrate -m "add auth_roles, auth_role_objects, sod_risk_assessments tables"
```

---

## 5. Servis Katmanı

### 5.1 Yeni Servis: `app/services/authorization_service.py`

```python
def create_auth_role(tenant_id: int, project_id: int, data: dict) -> dict:
def add_auth_object(tenant_id: int, project_id: int,
                     role_id: int, data: dict) -> dict:
def generate_sod_matrix(tenant_id: int, project_id: int) -> list[dict]:
    """
    Projdeki tüm single role çiftlerini karşılaştırır.
    Çakışma = aynı auth object'te ACTVT 01 (create) ve 60 (approve) gibi kritik kombinasyonlar.

    SOD kural seti: built-in SOD_RULES dict (konfigüre edilebilir).
    """
def link_role_to_process_steps(tenant_id: int, project_id: int,
                                 role_id: int, process_step_ids: list[int]) -> dict:
def export_auth_concept_excel(tenant_id: int, project_id: int) -> bytes:
    """
    SAP Authorization Concept çıktısı:
    - Sheet 1: Role listesi
    - Sheet 2: Role → Auth Object matrix
    - Sheet 3: SOD Matrix
    - Sheet 4: User assignment plan
    """
def get_role_coverage(tenant_id: int, project_id: int) -> dict:
    """ProcessStep → role assignment coverage."""
```

---

## 6. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/authorization_bp.py`

```
GET    /api/v1/projects/<proj_id>/auth/roles
POST   /api/v1/projects/<proj_id>/auth/roles
GET    /api/v1/projects/<proj_id>/auth/roles/<id>
PUT    /api/v1/projects/<proj_id>/auth/roles/<id>
DELETE /api/v1/projects/<proj_id>/auth/roles/<id>

POST   /api/v1/projects/<proj_id>/auth/roles/<id>/objects
PUT    /api/v1/projects/<proj_id>/auth/roles/<id>/objects/<obj_id>
DELETE /api/v1/projects/<proj_id>/auth/roles/<id>/objects/<obj_id>

POST   /api/v1/projects/<proj_id>/auth/roles/<id>/link-process-steps
       Body: { "process_step_ids": [1, 2, 3] }

GET    /api/v1/projects/<proj_id>/auth/sod-matrix
       Response: SODRiskAssessment listesi (otomatik hesaplanmış)

POST   /api/v1/projects/<proj_id>/auth/sod-matrix/accept-risk
POST   /api/v1/projects/<proj_id>/auth/export
GET    /api/v1/projects/<proj_id>/auth/coverage

Permission: authorization.view / authorization.edit
```

---

## 7. Frontend Değişiklikleri

### 7.1 Yeni View: `static/js/views/authorization.js`

**Tab 1: Role Matrix**
```
Authorization Concept
[+ New Role]  [Export Excel]  [Coverage: 18/45 ProcessSteps ⚠️]

Role Name       │ Type      │ Module │ Status    │ Objects │ SOD Risks │ Users
────────────────┼───────────┼────────┼───────────┼─────────┼───────────┼───────
Z_FI_AR_CLERK   │ Single    │ FI     │ approved  │ 8       │ 🔴 1 crit │ ~5
Z_FI_AP_PAYMENT │ Single    │ FI     │ in_review │ 12      │ 🔴 1 crit │ ~3
Z_FI_ACCOUNTANT │ Composite │ FI     │ draft     │ —       │ 🟡 2 high │ ~2
```

**Tab 2: SOD Matrix**
```
SOD Risk Matrix  [Run SOD Analysis]

┌────────────────────┬──────────────────────────┬──────────────────────────┐
│ Role A             │ Role B                   │ Risk    │ Status         │
├────────────────────┼──────────────────────────┼─────────┼────────────────┤
│ Z_FI_AR_CLERK      │ Z_FI_AP_PAYMENT          │ 🔴 CRIT │ Not accepted  │
│ Z_MM_PO_CREATE     │ Z_MM_GR_POST             │ 🟡 HIGH │ Accepted ✅    │
└────────────────────┴──────────────────────────┴─────────┴────────────────┘
```

---

## 8. Test Gereksinimleri

```python
def test_create_auth_role_returns_201():
def test_add_auth_object_links_to_role():
def test_sod_matrix_detects_create_approve_conflict():
def test_sod_matrix_no_conflict_when_no_overlap():
def test_export_auth_concept_returns_excel_bytes():
def test_role_coverage_counts_linked_process_steps():
def test_tenant_isolation_auth_role_cross_tenant_404():
```

---

## 9. Kabul Kriterleri

- [ ] AuthRole ve AuthRoleObject CRUD çalışıyor.
- [ ] `generate_sod_matrix()` create+approve aynı role kombinasyonunu tespit ediyor.
- [ ] SOD risk accept endpoint'i çalışıyor.
- [ ] ProcessStep → Role linki çalışıyor.
- [ ] Export Excel: 4 sheet dolu dönüyor.
- [ ] `authorization.js` view role matrix + SOD matrix tabları çalışıyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** Backlog — I-02 · Sprint 7+ · Effort XL
**Reviewer Kararı:** 🔵 ERTELEME ONAYLI — Sprint 5'te ADR hazırlanmalı, Sprint 7'den önce başlanmamalı

### Tespit Edilen Bulgular

1. **SAP güvenlik danışmanı input'u zorunlu.**
   Authorization concept modülü SU24/SU25/PFCG mantığı gerektirir. Platform ekibinin SAP security uzmanlığı olmadan bu modülü implement etmesi yanlış model oluşturma riskini taşır. Backlog ertelemesi doğru karar.

2. **Mevcut platform RBAC ile SAP auth concept karışmamalı.**
   `app/services/permission_service.py` platform RBAC'ını yönetiyor. `AuthRole` modeli SAP role'lerini temsil ediyor — bu ikisi farklı konsept. FDD'de bu ayrım iyi belirtilmiş. Ancak `AuthRole` adlandırması platform `Role` modeli ile karışıklık yaratabilir. `SapAuthRole` veya `SapRole` adı daha açık.

3. **SOD matrix — PostgreSQL specific partial index.**
   `generate_sod_matrix()` için partial constraint önerisi var. SQLite test ortamında çalışmayacak. Test mock'ları hazırlanmalı.

4. **Sprint 9 geçilirse retrofit riski.**
   API contract `AuthRole` endpoint'leri içeriyorsa Sprint 7+ gecikirse mevcut API'lara breaking change girmek zorunda kalınabilir. Bu riski en geç Sprint 5'te ADR belgeleyin.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Sprint 5'te ADR yaz: extension points, API contract placeholder | Architect | Sprint 5 |
| A2 | `AuthRole` → `SapAuthRole` adlandırma kararını belgele | Architect | Sprint 7 |
| A3 | SOD matrix için SQLite test mock stratejisini ADR'a ekle | QA | Sprint 7 |
