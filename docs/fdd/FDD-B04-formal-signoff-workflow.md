# FDD-B04: Formal Sign-off Workflow

**Öncelik:** P0 — BLOCK (Compliance / Enterprise Satışı)
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → B-04
**Effort:** M (1 sprint)
**Faz Etkisi:** Explore, Realize, Deploy — tüm fazlarda sign-off gereklilikleri
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Platform'da workshoplarda teknik bir `signoff` flag'i var (`is_signed_off`, `signed_off_at`) ama:
- **Kimin** onayladığı kaydedilmiyor (`approver_id` yok).
- **Override** edildiğinde neden edildiği kaydedilmiyor.
- `FunctionalSpec`, `TechnicalSpec`, `TestCycle`, `UAT` için de benzer sign-off gerekli ama standartlaştırılmamış.
- SOX / ISAE 3402 audit'leri için gerekli olan immutable approval trail yok.

### Etkilenen Varlıklar

| Varlık | Model | Mevcut Durum |
|--------|-------|--------------|
| Workshop | `ExploreWorkshop` | `is_signed_off` flag var, audit trail yok |
| L3 ProcessLevel | `ProcessLevel` | `is_signed_off` flag var, kimin imzaladığı yok |
| FunctionalSpec | `FunctionalSpec` | `approval_status` alan var ama approver yok |
| TechnicalSpec | `TechnicalSpec` | `review_status` var ama approver yok |
| TestCycle | `TestCycle` | Signoff yok |
| UAT Sign-off | `UATSignOff` | Model var ama yeterince detaylı değil |

---

## 2. İş Değeri

- Enterprise müşterilerin "who approved what and when" sorusuna yanıt verilmesi.
- SAP projesinin kritik milestone'larında (Design Freeze, UAT completion) formal onay zinciri.
- SOX / GDPR / KVKK compliance için immutable audit trail.
- Proje yöneticisinin hangi artifact'ların kim tarafından onaylandığını görmesi.

---

## 3. Hedef Mimari

### 3.1 Generic `SignoffRecord` Modeli

**Dosya:** `app/models/audit.py` içine ekle (ya da yeni `app/models/signoff.py` oluştur)

```python
class SignoffRecord(db.Model):
    """
    Immutable sign-off kaydı. Bir kez oluşturulunca silinemez.

    Her artifact tipi için tek bir tablo — polymorphic foreign key pattern.
    entity_type + entity_id birlikte artifact'ı tanımlar.

    Business rule: Aynı entity için birden fazla SignoffRecord olabilir
    (revoke + re-approve senaryosu). En son kaydın action'ı geçerlidir.
    """
    __tablename__ = "signoff_records"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    entity_type = db.Column(
        db.String(50),
        nullable=False,
        comment="workshop | process_level | functional_spec | technical_spec | test_cycle | uat"
    )
    entity_id = db.Column(
        db.Integer,
        nullable=False,
        comment="Polymorphic: ilgili tablodaki PK"
    )
    action = db.Column(
        db.String(20),
        nullable=False,
        comment="approved | revoked | override_approved"
    )
    approver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Onayı gerçekleştiren kullanıcı"
    )
    approver_name_snapshot = db.Column(
        db.String(200),
        nullable=True,
        comment="Kullanıcı silinse bile isim korunur"
    )
    comment = db.Column(
        db.Text,
        nullable=True,
        comment="Override durumunda zorunlu; normal onayda opsiyonel"
    )
    override_reason = db.Column(
        db.Text,
        nullable=True,
        comment="is_override=True ise zorunlu"
    )
    is_override = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="Normal onay akışı dışında zorla onaylanmış"
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.Index("ix_signoff_entity", "entity_type", "entity_id"),
        db.Index("ix_signoff_project_type", "project_id", "entity_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name_snapshot,
            "comment": self.comment,
            "override_reason": self.override_reason,
            "is_override": self.is_override,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

### 3.2 Migration
```
flask db migrate -m "add signoff_records table"
```

---

## 4. Servis Katmanı

### 4.1 Yeni Servis: `app/services/signoff_service.py`

```python
"""
Formal sign-off workflow servisi.

Her artifact tipi için approve / revoke / override işlemlerini yönetir.
SignoffRecord immutable'dır — asla delete edilmez, yalnızca yeni action eklenir.

Business rules:
    - override_approved için `override_reason` zorunlu.
    - revoke sadece son action 'approved' ise mümkün.
    - Aynı kullanıcı kendi oluşturduğu artifact'ı onaylayabilir
      (Design Authority board önkoşulu değil — konfigürasyona bırakıldı).
"""

def approve_entity(
    tenant_id: int,
    project_id: int,
    entity_type: str,
    entity_id: int,
    approver_id: int,
    comment: str | None = None,
    is_override: bool = False,
    override_reason: str | None = None,
) -> dict:
    """Bir artifact'ı onaylar ve SignoffRecord oluşturur."""
    ...

def revoke_approval(
    tenant_id: int,
    project_id: int,
    entity_type: str,
    entity_id: int,
    revoker_id: int,
    reason: str,
) -> dict:
    """Son onayı geri alır."""
    ...

def get_signoff_history(
    tenant_id: int,
    project_id: int,
    entity_type: str,
    entity_id: int,
) -> list[dict]:
    """Bir artifact'ın tüm onay geçmişini döner (immutable log)."""
    ...

def get_pending_signoffs(
    tenant_id: int,
    project_id: int,
    entity_type: str | None = None,
) -> list[dict]:
    """Henüz onaylanmamış artifact listesini döner."""
    ...

def get_signoff_summary(
    tenant_id: int,
    project_id: int,
) -> dict:
    """
    Proje genelinde sign-off durumunu özetler.
    Returns: {entity_type: {total, approved, pending, revoked}}
    """
    ...
```

---

## 5. API Endpoint'leri

### 5.1 Yeni Blueprint: `app/blueprints/signoff_bp.py`

```
POST   /api/v1/projects/<project_id>/signoff/<entity_type>/<entity_id>
       Body: { "action": "approved|revoked|override_approved", "comment": "...", "override_reason": "..." }
       Permission: signoff.approve

GET    /api/v1/projects/<project_id>/signoff/<entity_type>/<entity_id>/history
       Permission: signoff.view

GET    /api/v1/projects/<project_id>/signoff/pending
       Query params: entity_type (opsiyonel)
       Permission: signoff.view

GET    /api/v1/projects/<project_id>/signoff/summary
       Permission: signoff.view
```

### 5.2 Mevcut Endpoint'lere Sign-off Status Ekleme

`explore/workshops.py` — `GET /workshops/<id>` response'una ekle:
```json
{
  "signoff_status": "approved",
  "last_signoff": {
    "approver_name": "Mehmet Yılmaz",
    "action": "approved",
    "created_at": "2026-02-22T14:30:00Z"
  }
}
```

---

## 6. Frontend Değişiklikleri

### 6.1 Sign-off Button Component (`static/js/components/signoff_button.js`)
Yeni reusable component:
- Onaylanmamış durum: 🔲 "Sign Off" butonu (yeşil)
- Onaylanmış durum: ✅ "Signed off by [name] on [date]" badge + "Revoke" linki
- Override: ⚠️ turuncu badge

### 6.2 Etkilenen View'lar
- `explore_workshop_detail.js` — Workshop sign-off bölümü: approver ismi + tarih + revoke butonu
- `backlog.js` — FS/TS sign-off status badge
- `test_plan_detail.js` — TestCycle sign-off

### 6.3 Sign-off Dashboard Widget
`executive_cockpit.js` içindeki summary card'lara ekle:
"15 artifact onay bekliyor" tıklanabilir badge.

---

## 7. Test Gereksinimleri

```python
# tests/test_signoff_workflow.py

def test_approve_workshop_creates_signoff_record():
def test_approve_returns_400_if_entity_not_found():
def test_override_requires_override_reason():
def test_revoke_removes_approved_status():
def test_double_approve_creates_second_record_not_error():
def test_signoff_history_is_immutable_ordered_list():
def test_pending_signoffs_excludes_approved_entities():
def test_signoff_summary_returns_correct_counts_per_type():
def test_tenant_isolation_signoff_record_not_visible_cross_tenant():
def test_approver_name_snapshot_preserved_after_user_delete():
```

---

## 8. Kabul Kriterleri

- [ ] `signoff_records` tablosu oluşturuldu, kayıtlar silinemez.
- [ ] Workshop sign-off'da approver ismi ve tarihi `SignoffRecord`'da görünüyor.
- [ ] Override onayı `override_reason` olmadan 400 döndürüyor.
- [ ] `/signoff/history` endpoint'i tüm action geçmişini sıralı döndürüyor.
- [ ] `/signoff/pending` endpoint'i onaylanmamış tüm artifact'ları döndürüyor.
- [ ] Eski `is_signed_off` flag'leri hâlâ çalışıyor (backward compatibility).
- [ ] Tüm sign-off testleri geçiyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P0 — B-04 · Sprint 1 · Effort M
**Reviewer Kararı:** ⛔ TENANT İZOLASYON AÇIĞI — DÜZELTİLMEDEN IMPLEMENT EDİLEMEZ

### Tespit Edilen Bulgular

1. **KRİTİK: `SignoffRecord.tenant_id` — `nullable=True` olamaz.**
   FDD §3.1 model şemasında `tenant_id nullable=True` tanımlanmış. Bu P0 tenant isolation standardına aykırı. `SignoffRecord` compliance audit trail kaydıdır — hangi tenant'ın kaydı olduğu zorunlu bilgidir. `nullable=False` ve `ondelete='CASCADE'` olmalı.

2. **`approver_name_snapshot` alanı modelde yok ama test'te var.**
   `test_approver_name_snapshot_preserved_after_user_delete` isimli test, modelde olmayan bir alanı test ediyor. Approver sistemi terk ederse `approver_id` orphan kalır, SOX audit'inde "kim onayladı" sorusu yanıtsız kalır. `approver_name_snapshot = db.Column(db.String(255), nullable=True)` modele eklenmeli, sign-off anında kullanıcı adı kopyalanmalı.

3. **Self-approval guard servis katmanında implement edilmeli.**
   Kabul kriterlerinde self-approval 422 döndürme şartı var. Bu kontrol `signoff_service.py`'de olmalı — blueprint'te `if g.current_user.id == approver_id` kontrolü yapılırsa katman ihlali ve RBAC bypass riski doğar.

4. **PhaseGate entegrasyonu FDD'de eksik.**
   Sign-off, gate geçişine blok olmalı. `gate_service.py` içinde `signoff_service.is_entity_approved(entity_type, entity_id)` çağrısı yoksa feature fonksiyonel değil. Entegrasyon noktası FDD'ye eklenmeli.

5. **IP adresi load balancer arkasında yanlış alınabilir.**
   `request.remote_addr` load balancer IP'sini döner. `X-Forwarded-For` header'ı kullanılmalı ya da `app/utils/request_helpers.py` varsa oradan gerçek client IP alınmalı.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `SignoffRecord.tenant_id` → `nullable=False, ondelete='CASCADE'` | Coder | Sprint 1 |
| A2 | `approver_name_snapshot` alanını modele ekle, sign-off anında doldur | Coder | Sprint 1 |
| A3 | Self-approval guard'ı `signoff_service.py`'de implement et | Coder | Sprint 1 |
| A4 | `gate_service.py` → `signoff_service` entegrasyon noktasını FDD'ye ekle | Architect | Sprint 1 |
| A5 | IP adresi için `X-Forwarded-For` handling kullanımını doğrula | Coder | Sprint 1 |
