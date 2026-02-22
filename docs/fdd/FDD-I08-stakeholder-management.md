# FDD-I08: Stakeholder Management Modülü

**Öncelik:** P3
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-08
**Effort:** M (1 sprint)
**Faz Etkisi:** Prepare — Proje yönetişimi
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform'da proje ekibi `TeamMember` modeli üzerinden tanımlanıyor. Ancak:
- **Stakeholder register** yok: dışarıdan projekteyle ilgili kişiler (müşteri CXO'ları, key users, external vendors) kayıt altına alınamıyor.
- **Influence/Interest matrix** yok.
- **Communication plan** yok: kime ne sıklıkta ne iletilecek?
- **Stakeholder engagement tracking** yok: son iletişim ne zamandı?

Bu bilgiler SAP Activate Prepare fazının kritik çıktılarından biridir.

---

## 2. İş Değeri

- Proje yöneticisi tüm paydaşları tek ekranda görür.
- "Kime ne zaman ne anlatmam gerekiyor?" sorusu her hafta kolayca yanıtlanır.
- Steering committee listesi — committee moduli ile entegrasyon.
- Paydaş memnuniyet riski erken tespit edilir (engagement tracking).

---

## 3. Veri Modeli

### 3.1 Yeni Model: `Stakeholder`
**Dosya:** `app/models/program.py` içine ekle

```python
class Stakeholder(db.Model):
    """
    SAP proje paydaş kaydı.

    TeamMember ile fark: TeamMember proje ekibi içindeki kişidir.
    Stakeholder proje dışındaki (ama projeyi etkileyen/etkilenen) kişilerdir.
    Bir kişi hem TeamMember hem Stakeholder olabilir.

    Influence/Interest matrix:
        Yüksek Influence + Yüksek Interest = "Manage Closely" (Key Players)
        Yüksek Influence + Düşük Interest = "Keep Satisfied"
        Düşük Influence + Yüksek Interest = "Keep Informed"
        Düşük Influence + Düşük Interest = "Monitor"
    """
    __tablename__ = "stakeholders"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Kişi bilgileri
    name = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True, comment="CIO, CFO, Key User vb.")
    organization = db.Column(db.String(200), nullable=True, comment="Hangi firma/departman")
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    # Kategori
    stakeholder_type = db.Column(
        db.String(30),
        nullable=False,
        default="internal",
        comment="internal | external | vendor | sponsor | key_user | steering | regulator"
    )
    sap_module_interest = db.Column(
        db.String(200),
        nullable=True,
        comment="İlgili SAP modülleri: FI,SD,MM"
    )

    # Influence/Interest Matrix
    influence_level = db.Column(
        db.String(10),
        nullable=True,
        comment="high | medium | low"
    )
    interest_level = db.Column(
        db.String(10),
        nullable=True,
        comment="high | medium | low"
    )
    engagement_strategy = db.Column(
        db.String(30),
        nullable=True,
        comment="manage_closely | keep_satisfied | keep_informed | monitor"
        # Otomatik hesaplanabilir: influence + interest'ten
    )

    # Engagement tracking
    current_sentiment = db.Column(
        db.String(20),
        nullable=True,
        comment="champion | supporter | neutral | resistant | blocker"
    )
    last_contact_date = db.Column(db.Date, nullable=True)
    next_contact_date = db.Column(db.Date, nullable=True)
    contact_frequency = db.Column(
        db.String(20),
        nullable=True,
        comment="weekly | biweekly | monthly | as_needed"
    )

    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.2 Yeni Model: `CommunicationPlanEntry`

```python
class CommunicationPlanEntry(db.Model):
    """
    Communication plan kaydı: kiminle ne zaman ne iletişim kurulacak.

    Proje boyunca aktif iletişim takvimini tanımlar.
    """
    __tablename__ = "communication_plan_entries"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    # Kime
    stakeholder_id = db.Column(
        db.Integer,
        db.ForeignKey("stakeholders.id", ondelete="CASCADE"),
        nullable=True
    )
    audience_group = db.Column(
        db.String(100),
        nullable=True,
        comment="Bireysel değil grup (örn: 'Tüm Key Users', 'Steering Committee')"
    )

    # Ne iletişim
    communication_type = db.Column(
        db.String(30),
        nullable=False,
        comment="status_report | meeting | email | training | newsletter | workshop_invite"
    )
    subject = db.Column(db.String(255), nullable=False)
    channel = db.Column(
        db.String(30),
        nullable=True,
        comment="email | teams | in_person | presentation | sharepoint"
    )
    responsible_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Ne zaman
    frequency = db.Column(
        db.String(20),
        nullable=True,
        comment="weekly | biweekly | monthly | once | as_needed"
    )
    sap_activate_phase = db.Column(db.String(20), nullable=True)
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="planned",
        comment="planned | sent | completed | cancelled"
    )

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.3 Migration
```
flask db migrate -m "add stakeholders and communication_plan_entries tables"
```

---

## 4. Servis Katmanı

### 4.1 Yeni Servis: `app/services/stakeholder_service.py`

```python
def create_stakeholder(tenant_id: int, program_id: int, data: dict) -> dict:
def list_stakeholders(tenant_id: int, program_id: int, stakeholder_type: str | None = None) -> list[dict]:
def update_stakeholder(tenant_id: int, program_id: int, stakeholder_id: int, data: dict) -> dict:
def calculate_engagement_strategy(influence: str, interest: str) -> str:
    """
    Influence/Interest matrisinden engagement_strategy otomatik hesapla.
    high/high → manage_closely | high/low → keep_satisfied
    low/high → keep_informed | low/low → monitor
    """
def get_stakeholder_matrix(tenant_id: int, program_id: int) -> dict:
    """
    2x2 matris: influence (x) vs interest (y) — her stratejide stakeholder listesi.
    """
def get_overdue_contacts(tenant_id: int, program_id: int) -> list[dict]:
    """next_contact_date < today olan stakeholder'lar."""

def create_comm_plan_entry(tenant_id: int, program_id: int, data: dict) -> dict:
def list_comm_plan(tenant_id: int, program_id: int, phase: str | None = None) -> list[dict]:
def mark_comm_completed(tenant_id: int, program_id: int, entry_id: int, actual_date: date) -> dict:
```

---

## 5. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/stakeholder_bp.py`

```
# Stakeholder Register
GET    /api/v1/programs/<prog_id>/stakeholders
POST   /api/v1/programs/<prog_id>/stakeholders
GET    /api/v1/programs/<prog_id>/stakeholders/<id>
PUT    /api/v1/programs/<prog_id>/stakeholders/<id>
DELETE /api/v1/programs/<prog_id>/stakeholders/<id>

GET    /api/v1/programs/<prog_id>/stakeholders/matrix
       Response: 2x2 influence/interest pivot

GET    /api/v1/programs/<prog_id>/stakeholders/overdue-contacts
       Response: İletişim tarihi geçmiş stakeholder'lar

# Communication Plan
GET    /api/v1/programs/<prog_id>/communication-plan
GET    /api/v1/programs/<prog_id>/communication-plan?phase=explore
POST   /api/v1/programs/<prog_id>/communication-plan
PUT    /api/v1/programs/<prog_id>/communication-plan/<id>
POST   /api/v1/programs/<prog_id>/communication-plan/<id>/complete

Permission: stakeholder.view / stakeholder.edit
```

---

## 6. Frontend Değişiklikleri

### 6.1 Yeni View: `static/js/views/stakeholders.js`

**Tab 1: Stakeholder Register (Tablo)**
```
Stakeholders
[+ Add Stakeholder]

Filter: [Type ▾] [Sentiment ▾]

Name             │ Title           │ Organization │ Type    │ Influence│ Interest│ Strategy     │ Last Contact
─────────────────┼────────────────┼──────────────┼─────────┼──────────┼─────────┼──────────────┼─────────────
S. Yıldız        │ CFO             │ ACME Corp    │ Sponsor │ High     │ High    │Manage Closely│ 2026-02-10 ⚠️
A. Kurt          │ IT Director     │ ACME Corp    │Internal │ High     │ Medium  │Keep Satisfied│ 2026-02-18 ✅
M. Demir         │ FI Key User     │ ACME Corp    │Key User │ Low      │ High    │Keep Informed │ 2026-02-01 ⚠️
```

**Tab 2: Influence/Interest Matrix (Görsel 2x2)**
```
High Influence │  Keep Satisfied   │  Manage Closely  │
               │  [A. Kurt]        │  [S. Yıldız]     │
               │───────────────────┼──────────────────│
Low Influence  │  Monitor          │  Keep Informed   │
               │  [...]            │  [M. Demir]      │
               └───────────────────┴──────────────────┘
                    Low Interest          High Interest
```

**Tab 3: Communication Plan**
```
Communication Plan [+ Add Entry]

Filter: [Phase ▾]  [Channel ▾]  [Responsible ▾]

Upcoming (next 7 days):
  📧 Weekly Status Report → Steering Committee  (Mon, A.Koç) [Mark Complete]
  📊 Explore Phase Review → CFO  (Thu, PM) [Mark Complete]

All Entries:
  [Planned] Monthly Newsletter            Key Users    Email   Monthly   ─
  [Planned] Steering Comm. Presentation   Committee    Pres.   Biweekly  ─
  [Done ✅] Kick-off Workshop             All          InPers  Once      ─
```

---

## 7. Test Gereksinimleri

```python
def test_create_stakeholder_returns_201():
def test_engagement_strategy_calculated_correctly_for_high_high():
def test_engagement_strategy_calculated_correctly_for_low_high():
def test_stakeholder_matrix_returns_four_quadrants():
def test_overdue_contacts_returns_stakeholders_past_next_contact():
def test_create_comm_plan_entry_returns_201():
def test_mark_comm_completed_sets_actual_date_and_status():
def test_tenant_isolation_stakeholder_cross_tenant_404():
def test_comm_plan_filter_by_phase_returns_correct_entries():
```

---

## 8. Kabul Kriterleri

- [ ] Stakeholder oluşturulabiliyor ve listseleniyor.
- [ ] `calculate_engagement_strategy()` doğru quadrant hesaplıyor.
- [ ] `GET /stakeholders/matrix` 4 quadrant dolu dönüyor.
- [ ] `GET /stakeholders/overdue-contacts` geçen next_contact_date olanları listeliyor.
- [ ] Communication plan CRUD çalışıyor.
- [ ] Mark complete endpoint'i durum ve tarihi güncelliyor.
- [ ] `stakeholders.js` view 3 tab ile çalışıyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P3 — I-08 · Sprint 5 · Effort M
**Reviewer Kararı:** 🔵 KABUL EDİLİR — `tenant_id nullable` düzeltilmeli

### Tespit Edilen Bulgular

1. **`Stakeholder.tenant_id nullable=True` — platform standardına aykırı.**
   FDD §3.1 model şemasında `tenant_id nullable=True` görünüyor. Stakeholder verisi tenant-scoped'dur. `nullable=False` olmalı. Tenant bazlı izolasyon zorunlu: bir tenant'ın stakeholder'ları başka tenant'a görünmemeli.

2. **Influence/Interest matrix — DB seviyesinde enum.**
   `influence_level` ve `interest_level` `high/low` enum değerleri alıyor. Bu alanlar `db.String` yerine `db.Enum` veya check constraint ile kısıtlanmalı, aksi halde `"medium"` gibi geçersiz değer girilmesi önlenemez.

3. **Communication plan — GDPR veri saklama.**
   Stakeholder iletişim geçmişi (e-posta adresleri, kişisel bilgiler) GDPR kapsamındadır. Proje silindiğinde stakeholder kişisel verilerinin de silindiği (ya da anonymize edildiği) açıkça belirtilmeli. `on_project_delete` cascade veya anonymization hook gerekiyor.

4. **`TeamMember` ile overlap — "hem ekip üyesi hem stakeholder" senarayosu.**
   FDD bu senaryoyu doğru tanımlıyor. Ancak bir kullanıcı hem `TeamMember` hem `Stakeholder` tablosunda varsa engagement tracking'de duplicate gösterim riski var. UI'da birleşik view veya servis katmanında merge mantığı düşünülmeli.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `Stakeholder.tenant_id` → `nullable=False` | Coder | Sprint 5 |
| A2 | `influence_level`, `interest_level` için check constraint ekle | Coder | Sprint 5 |
| A3 | Proje silme cascade'ı veya anonymization hook'unu FDD'ye ekle | Architect | Sprint 5 |
| A4 | TeamMember + Stakeholder overlap senaryosu için UI/servis kararını not et | Architect | Sprint 5 |
