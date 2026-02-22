# FDD-B03: Run / Hypercare Incident Management MVP

**Öncelik:** P2
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → B-03
**Effort:** L (2 sprint)
**Faz Etkisi:** Run — Go-live sonrası destek ve stabilizasyon
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Go-live sonrası platform neredeyse tamamen işlevsiz hale geliyor. `HypercareIncident` modeli (`app/models/cutover.py`) var ama:
- SLA tracking yok.
- Incident priority / severity sınıflandırması P1/P2/P3/P4 standardında değil.
- Escalation mekanizması yok.
- Post-go-live change request yönetimi yok.
- Müşteri "destekten memnun muyum?" sorusu platform üzerinden ölçülemiyor.

Bu durum müşteri platform bağını go-live'dan 2 hafta sonra kesiyor — SaaS retention'ı için kritik.

---

## 2. İş Değeri

- Müşteri go-live sonrası da platformu kullanmaya devam eder → retention.
- Hypercare süreci (genellikle 4–8 hafta) sistematik yönlenir.
- SAP projelerinin en kaotik dönemi olan hypercare'de traceability sağlanır.
- Level 1/2/3 support düzeni platform üzerinden dokümante edilir.

---

## 3. Mevcut Model Durumu

`app/models/cutover.py`:
- `HypercareIncident`: id, title, description, reported_by, status (open/in_progress/resolved/closed), priority, created_at, resolved_at — temel alanlar var.
- `HypercareSLA`: sla_type, response_minutes, resolution_minutes — SLA tanımı var ama enforcement yok.

Bu FDD mevcut modelleri genişletir ve eksik servisleri ekler.

---

## 4. Veri Modeli Değişiklikleri

### 4.1 `HypercareIncident` Modeli Genişletme
**Dosya:** `app/models/cutover.py`

```python
# Mevcut alanlara EKLENECEKler:
severity = db.Column(
    db.String(5),
    nullable=False,
    default="p3",
    comment="p1 | p2 | p3 | p4  (P1=sistem durdu, P2=kritik, P3=önemli, P4=düşük)"
)
incident_type = db.Column(
    db.String(30),
    nullable=True,
    comment="system_down | data_issue | performance | authorization | interface | other"
)
affected_module = db.Column(db.String(20), nullable=True, comment="FI,MM,SD vb.")
affected_users_count = db.Column(db.Integer, nullable=True)
assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

# SLA tracking
first_response_at = db.Column(db.DateTime, nullable=True)
sla_response_breached = db.Column(db.Boolean, nullable=False, default=False)
sla_resolution_breached = db.Column(db.Boolean, nullable=False, default=False)
sla_response_deadline = db.Column(db.DateTime, nullable=True, comment="Otomatik hesaplanır: created_at + SLA")
sla_resolution_deadline = db.Column(db.DateTime, nullable=True)

# Root cause
root_cause = db.Column(db.Text, nullable=True)
root_cause_category = db.Column(
    db.String(30),
    nullable=True,
    comment="config | data | training | process | development | external"
)
linked_backlog_item_id = db.Column(
    db.Integer,
    db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
    nullable=True,
    comment="Nedeni bir WRICEF ise bağlantı"
)

# Post-go-live change request
requires_change_request = db.Column(db.Boolean, nullable=False, default=False)
change_request_id = db.Column(
    db.Integer,
    db.ForeignKey("post_golive_change_requests.id", ondelete="SET NULL"),
    nullable=True
)
```

### 4.2 Yeni Model: `PostGoliveChangeRequest`

```python
class PostGoliveChangeRequest(db.Model):
    """
    Go-live sonrası değişiklik talepleri.

    Incident veya kullanıcı talebinden doğabilir.
    Normal backlog/WRICEF'den farklı: production sistemde yapılacak değişiklik.
    Önce Change Board onayı gerekli.

    Lifecycle: draft → pending_approval → approved → in_progress → implemented → closed
    """
    __tablename__ = "post_golive_change_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    cr_number = db.Column(db.String(20), nullable=False, unique=True, index=True, comment="CR-001, CR-002...")
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    change_type = db.Column(
        db.String(20),
        nullable=False,
        comment="config | development | data | authorization | emergency"
    )
    priority = db.Column(db.String(5), nullable=False, default="p3", comment="p1|p2|p3|p4")
    status = db.Column(
        db.String(30),
        nullable=False,
        default="draft",
        comment="draft | pending_approval | approved | rejected | in_progress | implemented | closed"
    )
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    planned_implementation_date = db.Column(db.Date, nullable=True)
    actual_implementation_date = db.Column(db.Date, nullable=True)
    impact_assessment = db.Column(db.Text, nullable=True)
    test_required = db.Column(db.Boolean, nullable=False, default=True)
    rollback_plan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.3 Yeni Model: `IncidentComment`
```python
class IncidentComment(db.Model):
    """Hypercare incident güncelleme logu."""
    __tablename__ = "incident_comments"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("hypercare_incidents.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, nullable=False, default=False, comment="Internal note vs müşteri görür")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
```

### 4.4 Migration
```
flask db migrate -m "extend hypercare_incidents, add post_golive_change_requests, incident_comments"
```

---

## 5. Servis Katmanı

### 5.1 Yeni Servis: `app/services/hypercare_service.py`

```python
"""
Run/Hypercare fazı incident yönetimi.

SLA Enforcement:
    - Incident oluşturulduğunda priority'ye göre SLA deadline'ları otomatik hesaplanır.
    - Bir background job (veya her API çağrısında lazy check) SLA breach'leri işaretler.
    - SLA breach olduğunda Notification servisi tetiklenir.

SLA Defaults (HypercareSLA tablosundan veya hardcoded):
    P1: Response 1h, Resolution 4h
    P2: Response 4h, Resolution 8h
    P3: Response 8h, Resolution 24h
    P4: Response 24h, Resolution 72h
"""

def create_incident(tenant_id: int, project_id: int, data: dict) -> dict:
    """Incident oluşturur ve SLA deadline'larını otomatik hesaplar."""

def update_incident(tenant_id: int, project_id: int, incident_id: int, data: dict) -> dict:

def add_first_response(tenant_id: int, project_id: int, incident_id: int, user_id: int) -> dict:
    """first_response_at'ı set eder, SLA breach kontrolü yapar."""

def resolve_incident(tenant_id: int, project_id: int, incident_id: int,
                     root_cause: str, resolution_notes: str) -> dict:

def check_sla_breaches(project_id: int, tenant_id: int) -> list[dict]:
    """SLA'sı geçmiş açık incident'ları döner ve breach flag'lerini günceller."""

def get_incident_metrics(project_id: int, tenant_id: int) -> dict:
    """
    Returns:
        {
          "open_by_priority": {"p1": 0, "p2": 1, "p3": 3, "p4": 2},
          "sla_breached": 2,
          "avg_resolution_hours": 6.5,
          "resolved_this_week": 8
        }
    """

def create_change_request(tenant_id: int, project_id: int, data: dict) -> dict:
def approve_change_request(tenant_id: int, project_id: int, cr_id: int, approver_id: int) -> dict:
def list_change_requests(tenant_id: int, project_id: int, status: str | None = None) -> list[dict]:
```

---

## 6. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/run_sustain_bp.py` veya mevcut genişletme

```
# Incident Management
GET    /api/v1/projects/<proj_id>/hypercare/incidents
POST   /api/v1/projects/<proj_id>/hypercare/incidents
GET    /api/v1/projects/<proj_id>/hypercare/incidents/<id>
PUT    /api/v1/projects/<proj_id>/hypercare/incidents/<id>
POST   /api/v1/projects/<proj_id>/hypercare/incidents/<id>/first-response
POST   /api/v1/projects/<proj_id>/hypercare/incidents/<id>/resolve
POST   /api/v1/projects/<proj_id>/hypercare/incidents/<id>/comments
GET    /api/v1/projects/<proj_id>/hypercare/incidents/<id>/comments

# SLA
GET    /api/v1/projects/<proj_id>/hypercare/sla-breaches
GET    /api/v1/projects/<proj_id>/hypercare/metrics

# Change Requests
GET    /api/v1/projects/<proj_id>/hypercare/change-requests
POST   /api/v1/projects/<proj_id>/hypercare/change-requests
GET    /api/v1/projects/<proj_id>/hypercare/change-requests/<id>
POST   /api/v1/projects/<proj_id>/hypercare/change-requests/<id>/approve
POST   /api/v1/projects/<proj_id>/hypercare/change-requests/<id>/reject
```

---

## 7. Frontend Değişiklikleri

### 7.1 Yeni View: `static/js/views/hypercare.js`

**Hypercare War Room Dashboard:**
```
Hypercare Dashboard — Go-live +12 days 🟢

SLA Status:
  P1: 0 açık  ✅    P2: 1 açık  ⚠️    P3: 3 açık     P4: 2 açık
  SLA İhlali: 2 ⚠️

Incident Listesi: [+ New Incident]
┌────┬───────────────────────────┬──────┬───────────┬────────────┬──────────┐
│ ID │ Başlık                    │ P    │ Modül     │ Atanan     │ SLA      │
├────┼───────────────────────────┼──────┼───────────┼────────────┼──────────┤
│ #5 │ GR posting blocked        │ 🔴P2 │ MM        │ A.Koç      │ ⚠️ BREACH│
│ #4 │ Invoice approval slow     │ 🟡P3 │ FI        │ M.Yılmaz   │ ✅ 18h   │
└────┴───────────────────────────┴──────┴───────────┴────────────┴──────────┘

Change Requests: [+ New CR]
CR-001  Config fix - FI posting  P2  pending_approval  [Approve] [Reject]
```

### 7.2 `cutover.js` Entegrasyonu
Cutover view altına "Go-Live + Hypercare" tab'ı ekle.

---

## 8. Test Gereksinimleri

```python
# tests/test_hypercare_service.py

def test_create_incident_sets_sla_deadlines_based_on_priority():
def test_p1_incident_sla_deadline_is_4_hours_from_creation():
def test_add_first_response_sets_first_response_at():
def test_first_response_after_sla_sets_breach_flag_true():
def test_check_sla_breaches_returns_overdue_incidents():
def test_resolve_incident_sets_resolved_at():
def test_create_cr_generates_cr_number_sequence():
def test_approve_cr_sets_approved_by_and_approved_at():
def test_incident_metrics_returns_correct_p1_p2_counts():
def test_tenant_isolation_incident_cross_tenant_404():
def test_tenant_isolation_cr_cross_tenant_404():
```

---

## 9. Kabul Kriterleri

- [ ] Incident oluşturulduğunda priority'ye göre SLA deadline'ları otomatik hesaplanıyor.
- [ ] SLA ihlalinde incident'a `sla_response_breached = True` yazılıyor.
- [ ] `GET /hypercare/sla-breaches` SLA ihlali olan incident'ları listeli yor.
- [ ] Post-go-live change request oluşturulup onaylanabiliyor.
- [ ] `hypercare.js` war room dashboard çalışıyor.
- [ ] `GET /hypercare/metrics` P1/P2/P3/P4 bazında açık incident sayılarını döndürüyor.
- [ ] Tüm testler geçiyor, tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P2 — B-03 · Sprint 4 · Effort L
**Reviewer Kararı:** ⛔ BLOKER — FDD-P0-tenant-isolation-fix tamamlanmadan implement edilemez

### Tespit Edilen Bulgular

1. **SERT BLOKER: `run_sustain_service.py` ve `cutover.py` tenant isolation açığı taşıyor.**
   Platform audit raporu (2026-02-21) `run_sustain_service.py` içinde `Model.query.get(pk)` pattern'i ile tenant filtresiz sorgular tespit etti. `HypercareIncident` ve `HypercareSLA` modelleri de bu servis üzerinden yönetiliyor. `FDD-P0-tenant-isolation-fix` tamamlanmadan bu FDD implement edilirse yeni feature'lar da aynı açığı taşır.

2. **`HypercareIncident.tenant_id` — nullable kontrolü yapılmalı.**
   `cutover.py` modelindeki mevcut `HypercareIncident` modelinde `tenant_id` nullable mı, zorunlu mu? Yeni alanlar eklenmeden önce mevcut model tenant isolation standardına uygun hale getirilmeli.

3. **SLA breach notification — notification service entegrasyonu eksik.**
   FDD SLA ihlal detection mekanizmasını tanımlıyor ancak ihlal tespit edildiğinde `notification_service.py`'e nasıl bağlanacağı belirtilmemiş. Scheduled task mı (celery/APScheduler), webhook mı, yoksa her sorguda kontrol mü? Bu karar performans ve altyapı açısından kritik.

4. **Severity enumeration — Defect modeli ile tutarsızlık riski.**
   FDD `p1/p2/p3/p4` severity kullanıyor. `Defect` modeli muhtemelen farklı bir severity seti kullanıyor (P2-O06 bulgusu). Incident ve Defect severity'leri aynı terminolojiyi kullanmalı, aksi halde raporlama ve önceliklendirme karışır.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `FDD-P0-tenant-isolation-fix` Sprint 1'de tamamlanmadan B-03 Sprint planına alınmasın | Tech Lead | Sprint 1 |
| A2 | Mevcut `HypercareIncident.tenant_id` nullable durumunu kontrol et, zorunlu yap | Coder | Sprint 4 |
| A3 | SLA breach notification — scheduler vs webhook kararını FDD'ye ekle | Architect | Sprint 4 |
| A4 | `Defect` severity ile `HypercareIncident` severity terminolojisini hizala | Architect | Sprint 4 |
