# FDD-F06: RACI Matrix UI

**Öncelik:** P2
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-06
**Effort:** M (1 sprint)
**Faz Etkisi:** Prepare — Proje yönetişimi
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

`app/services/governance_rules.py` içinde RACI template tanımları mevcut. Ancak platformda interaktif bir RACI matrix ekranı yok. Proje ekibi kimin hangi aktivitede Responsible / Accountable / Consulted / Informed olduğunu platform üzerinden göremez veya güncelleyemez.

---

## 2. İş Değeri

- Proje governance'ının somut bir aracı olur.
- SAP projelerinde sık yaşanan "kim kararı verecek?" belirsizliği ortadan kalkar.
- Prepare fazı gate kontrolünde RACI matrix tamamlanmış mı? kontrol edilebilir.
- Workstream liderlerinin sorumluluk alanlarını net görmeleri sağlanır.

---

## 3. Teknik Tasarım

### 3.1 Yeni Model: `RaciEntry`
**Dosya:** `app/models/program.py` içine ekle

```python
class RaciEntry(db.Model):
    """
    RACI matrix kaydı: bir kişi/rol, bir aktivite için R/A/C/I rolü.

    RACI Tanımları:
        R (Responsible): İşi yapan — Her aktivite için en az 1 R gerekli.
        A (Accountable): Karar veren ve hesap veren — Kesinlikle 1 kişi.
        C (Consulted): Görüş alınan — Çift yönlü iletişim.
        I (Informed): Bilgilendirilen — Tek yönlü iletişim.

    Validation kuralı:
        Her activity_id için A rolü en fazla 1 kişide olabilir.
    """
    __tablename__ = "raci_entries"

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

    # Aktivite
    workstream_id = db.Column(
        db.Integer,
        db.ForeignKey("workstreams.id", ondelete="CASCADE"),
        nullable=True,
        comment="Hangi workstream içinde"
    )
    activity_name = db.Column(
        db.String(200),
        nullable=False,
        comment="RACI aktivitesinin adı"
    )
    activity_category = db.Column(
        db.String(50),
        nullable=True,
        comment="governance | technical | testing | data | training | cutover"
    )
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | prepare | explore | realize | deploy | run"
    )

    # Kişi / Rol
    team_member_id = db.Column(
        db.Integer,
        db.ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=True,
        comment="Bireysel kişi ataması"
    )
    role_name = db.Column(
        db.String(100),
        nullable=True,
        comment="Bireysel değil rol bazlı atama (team_member_id yoksa)"
    )

    # RACI rolü
    raci_role = db.Column(
        db.String(1),
        nullable=False,
        comment="R | A | C | I"
    )

    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_raci_program_activity", "program_id", "activity_name"),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.2 Yeni Model: `RaciActivity`
RACI etkinliklerini yönetilebilir hale getirmek için ayrı tablo:

```python
class RaciActivity(db.Model):
    """
    RACI aktivite tanımı. RaciEntry'ler bu aktivitelere referans verir.
    Proje başlarken SAP template aktiviteleri bulk-import edilebilir.
    """
    __tablename__ = "raci_activities"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    sap_activate_phase = db.Column(db.String(20), nullable=True)
    workstream_id = db.Column(db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True)
    is_template = db.Column(db.Boolean, nullable=False, default=False, comment="SAP Activate'den gelen hazır aktivite")
    sort_order = db.Column(db.Integer, nullable=True)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.3 Migration
```
flask db migrate -m "add raci_entries and raci_activities tables"
```

---

## 4. Servis Katmanı

### 4.1 Yeni Servis: `app/services/raci_service.py`

```python
def get_raci_matrix(
    tenant_id: int,
    program_id: int,
    workstream_id: int | None = None,
    sap_phase: str | None = None,
) -> dict:
    """
    RACI matrisini pivot formatında döner.
    Satır: Aktivite, Sütun: Kişi/Rol, Hücre: R|A|C|I|None

    Returns:
        {
          "activities": [{"id": 1, "name": "...", "category": "..."}],
          "team_members": [{"id": 1, "name": "...", "role": "..."}],
          "matrix": {
            "1": {"1": "R", "2": "A", "3": "C"},  # activity_id: {member_id: raci_role}
            "2": {"1": "I", "2": "R"}
          },
          "validation": {
            "activities_without_accountable": ["Activity X"],
            "activities_without_responsible": ["Activity Y"]
          }
        }
    """
    ...

def upsert_raci_entry(
    tenant_id: int, program_id: int,
    activity_id: int, team_member_id: int,
    raci_role: str | None,  # None = hücreyi temizle
) -> dict | None:
    """
    Matris hücresini günceller. raci_role=None ise kaydı siler.
    Validation: 'A' rolü aynı aktivitede birden fazla kişiye atanamaz.
    """
    ...

def bulk_import_sap_template_activities(
    tenant_id: int, program_id: int,
) -> int:
    """SAP Activate standart RACI aktivitelerini programa ekler. Returns count."""
    ...
```

### 4.2 SAP Template Aktiviteleri
`app/services/raci_service.py` içine SAP Activate standart aktivite listesi (30–50 adet):

```python
SAP_ACTIVATE_RACI_ACTIVITIES = [
    {"name": "Project Charter Onayı", "phase": "discover", "category": "governance"},
    {"name": "Steering Committee Toplantıları", "phase": "prepare", "category": "governance"},
    {"name": "Workshop Yönetimi", "phase": "explore", "category": "technical"},
    {"name": "Fit-Gap Analizi", "phase": "explore", "category": "technical"},
    {"name": "WRICEF Onayı", "phase": "realize", "category": "technical"},
    {"name": "SIT Koordinasyonu", "phase": "deploy", "category": "testing"},
    {"name": "UAT Koordinasyonu", "phase": "deploy", "category": "testing"},
    {"name": "Data Migration Onayı", "phase": "deploy", "category": "data"},
    {"name": "Go-Live Kararı", "phase": "deploy", "category": "governance"},
    # ... 40 aktivite daha
]
```

---

## 5. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/raci_bp.py`

```
GET    /api/v1/programs/<prog_id>/raci
       Query params: workstream_id, phase
       Permission: raci.view
       Response: get_raci_matrix() pivot format

POST   /api/v1/programs/<prog_id>/raci/activities
       Body: {name, category, phase, workstream_id}
       Permission: raci.edit

PUT    /api/v1/programs/<prog_id>/raci/entries
       Body: {activity_id, team_member_id, raci_role}  (raci_role=null → delete)
       Permission: raci.edit

POST   /api/v1/programs/<prog_id>/raci/import-template
       Permission: raci.edit
       Response: {imported_count: 45}

GET    /api/v1/programs/<prog_id>/raci/validate
       Permission: raci.view
       Response: {activities_without_accountable: [...], activities_without_responsible: [...]}
```

---

## 6. Frontend Değişiklikleri

### 6.1 Yeni View: `static/js/views/raci.js`

**RACI Matrix Görünümü** (spreadsheet benzeri):

```
RACI Matrix — S/4HANA Migration
Phase: [All ▾]  Workstream: [All ▾]  [Import SAP Template]

                        │ A.Koç  │ M.Yılmaz │ S.Demir │ Z.Arslan │
                        │ PM     │ Sr.Cons. │ Jr.Dev  │ Sponsor  │
────────────────────────┼────────┼──────────┼─────────┼──────────┤
⬛ DISCOVER             │        │          │         │          │
  Project Charter Onayı │  R     │    C     │         │    A     │
  System Landscape      │  R     │    R     │    C    │    I     │
⬛ PREPARE              │        │          │         │          │
  Steering Committee    │  R     │    C     │         │    A     │
  ...

Hücre tıklama: R → A → C → I → (boş) döngüsü
```

**Renk kodu:**
- R: mavi
- A: kırmızı (tek olmalı)
- C: yeşil
- I: gri
- Boş: beyaz

**Validation uyarıları:**
- Sarı uyarı: "3 aktivitenin Accountable'ı yok"
- Kırmızı uyarı: "2 aktivitenin Responsible'ı yok"

---

## 7. Test Gereksinimleri

```python
# tests/test_raci.py

def test_get_raci_matrix_returns_pivot_format():
def test_upsert_raci_entry_creates_new_record():
def test_upsert_raci_entry_with_null_role_deletes_record():
def test_raci_validation_flags_activity_without_accountable():
def test_raci_validation_flags_activity_without_responsible():
def test_accountable_role_cannot_be_assigned_twice_same_activity():
def test_bulk_import_template_creates_sap_activities():
def test_tenant_isolation_raci_cross_tenant_404():
```

---

## 8. Kabul Kriterleri

- [ ] `GET /raci` endpoint pivot formatında matrix döndürüyor.
- [ ] Hücre click → R/A/C/I toggle çalışıyor (inline edit).
- [ ] Aynı aktiviteye 2 kişi "A" atanamıyor (400 dönüyor).
- [ ] "Import SAP Template" 30+ standart aktiviteyi ekliyor.
- [ ] Validation endpoint aktivitesiz Accountable'ları listeliyor.
- [ ] Phase ve workstream filtresi çalışıyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P2 — F-06 · Sprint 3 · Effort M
**Reviewer Kararı:** ⛔ TENANT İZOLASYON AÇIĞI — `RaciEntry.tenant_id nullable=True` DÜZELTİLMELİ

### Tespit Edilen Bulgular

1. **KRİTİK: `RaciEntry.tenant_id nullable=True` — platform standardına aykırı.**
   FDD §3.1 model şemasında `tenant_id nullable=True` tanımlanmış. `RaciEntry` tenant-scoped bir kayıt — hangi tenant'a ait olduğu her sorguda zorunlu. `nullable=False` olmalı. `nullable=True` olursa tenant filtresiz query ile cross-tenant RACI verisi okunabilir.

2. **"A" rolü uniqueness constraint — DB seviyesinde olmalı.**
   Bir aktivite için aynı anda yalnızca 1 kişi Accountable (A) olabilir. Bu kural servis katmanında kontrol ediliyor (kabul kriteri: 400 döner) ama DB-level unique constraint yoksa concurrent requestlerde race condition ile ikinci A atanabilir. `db.UniqueConstraint('activity_id', 'raci_role', name='uq_raci_single_accountable')` eklenebilir, ancak bu `raci_role='A'` için partial index gerektirir — PostgreSQL destekler, SQLite desteklemez. Test ortamı farkı belgelenmeli.

3. **"Import SAP Template" özelliği — SAP IP riski.**
   30+ standart SAP aktivitesi içeren template SAP içeriği içeriyorsa F-03'teki gibi lisans riski var. Template içeriği özgün yazılmalı (SAP terminolojisi kullanılabilir ama SAP IP kopyalanamaz).

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `RaciEntry.tenant_id` → `nullable=False` olarak güncelle | Coder | Sprint 3 |
| A2 | Accountable uniqueness için DB constraint araştır, PostgreSQL partial index dokümante et | Coder | Sprint 3 |
| A3 | SAP aktivite template içeriğinin orijinal yazılmasını sağla | PM | Sprint 3 |
