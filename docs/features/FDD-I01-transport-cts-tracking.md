# FDD-I01: Transport / CTS Tracking

**Öncelik:** P3
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-01
**Effort:** L (2 sprint)
**Faz Etkisi:** Realize, Deploy — Geliştirme ve canlıya taşıma
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

SAP projelerinde transport/CTS (Change and Transport System) yönetimi kritik ve riskli bir aktivitedir. Platformda:
- Transport request tracking yok.
- Hangi WRICEF / config item'ın hangi transport'ta olduğu bilinmiyor.
- Deploy fazında transport wave planlama aracı yok.
- Import log / sonuç takibi yok.

---

## 2. İş Değeri

- Go-live kargaşasında "bu geliştirme hangi transport'ta?" sorusu anında yanıtlanır.
- Transport wave planlama ile import sırası (bağımlılıklar) dokümante edilir.
- Transport import hatalarının tracking'i: hangi transport X sisteminde başarısız oldu?
- "Transport missing" riski Realize fazında erkenden tespit edilir.

---

## 3. Veri Modeli

### 3.1 Yeni Model: `TransportRequest`
**Dosya:** `app/models/backlog.py` veya yeni `app/models/transport.py`

```python
class TransportRequest(db.Model):
    """
    SAP CTS Transport Request kaydı.

    Her geliştirme objesi (WRICEF, config) bir transport'a atanır.
    Transport, deploy aşamasında sistem sistemine aktarılır.

    Transport tipi:
        workbench: ABAP geliştirme nesneleri (WRICEF: W,R,I,E)
        customizing: Konfigürasyon (WRICEF: C, Config Items)

    Lifecycle: created → dev → test → q → prod
    """
    __tablename__ = "transport_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)

    transport_number = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        comment="SAP CTS numarası: DEVK900001 formatı"
    )
    transport_type = db.Column(
        db.String(20),
        nullable=False,
        comment="workbench | customizing | support_pkg | transport_of_copies"
    )
    description = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Transport sahibi (ABAP developer)"
    )
    sap_module = db.Column(db.String(10), nullable=True)
    wave_id = db.Column(
        db.Integer,
        db.ForeignKey("transport_waves.id", ondelete="SET NULL"),
        nullable=True
    )

    # Durum
    current_system = db.Column(
        db.String(5),
        nullable=False,
        default="DEV",
        comment="DEV | QAS | PRE | PRD"
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="created",
        comment="created | released | imported | failed | locked"
    )
    release_date = db.Column(db.DateTime, nullable=True)

    # Import log (JSON: sistem → durum, tarih)
    import_log = db.Column(
        db.JSON,
        nullable=True,
        comment="[{system: 'QAS', status: 'ok', imported_at: '...', return_code: 0}]"
    )

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    backlog_items = db.relationship("BacklogItem", secondary="transport_backlog_links", lazy="select")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TransportBacklogLink(db.Model):
    """N:M — TransportRequest ↔ BacklogItem (WRICEF)"""
    __tablename__ = "transport_backlog_links"
    transport_id = db.Column(db.Integer, db.ForeignKey("transport_requests.id", ondelete="CASCADE"), primary_key=True)
    backlog_item_id = db.Column(db.Integer, db.ForeignKey("backlog_items.id", ondelete="CASCADE"), primary_key=True)


class TransportWave(db.Model):
    """
    Transport wave = belirli bir import döngüsü için gruplanmış transport'lar.
    Örn: "Wave 2 — FI-MM Integration" → belirli transport'ları içerir.
    """
    __tablename__ = "transport_waves"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_system = db.Column(db.String(5), nullable=False, comment="QAS | PRE | PRD")
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="planned",
                       comment="planned | in_progress | completed | failed")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.2 Migration
```
flask db migrate -m "add transport_requests, transport_waves, transport_backlog_links tables"
```

---

## 4. Servis Katmanı

### 4.1 Yeni Servis: `app/services/transport_service.py`

```python
def create_transport(tenant_id: int, project_id: int, data: dict) -> dict:
def assign_backlog_to_transport(tenant_id: int, project_id: int,
                                 transport_id: int, backlog_item_id: int) -> dict:
def record_import_result(tenant_id: int, project_id: int, transport_id: int,
                          system: str, status: str, return_code: int) -> dict:
def get_transport_coverage(project_id: int, tenant_id: int) -> dict:
    """
    WRICEF → Transport coverage.
    Returns:
        {
          "total_backlog_items": 45,
          "with_transport": 30,
          "without_transport": 15,
          "by_type": {"W": {...}, "R": {...}, ...}
        }
    """
def get_wave_status(project_id: int, tenant_id: int, wave_id: int) -> dict:
    """Wave'deki tüm transport'ların import durumunu döner."""
```

---

## 5. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/transport_bp.py`

```
GET    /api/v1/projects/<proj_id>/transports
POST   /api/v1/projects/<proj_id>/transports
GET    /api/v1/projects/<proj_id>/transports/<id>
PUT    /api/v1/projects/<proj_id>/transports/<id>

POST   /api/v1/projects/<proj_id>/transports/<id>/assign-backlog
DELETE /api/v1/projects/<proj_id>/transports/<id>/assign-backlog/<backlog_id>
POST   /api/v1/projects/<proj_id>/transports/<id>/import-result

GET    /api/v1/projects/<proj_id>/transports/waves
POST   /api/v1/projects/<proj_id>/transports/waves
GET    /api/v1/projects/<proj_id>/transports/waves/<wave_id>/status
GET    /api/v1/projects/<proj_id>/transports/coverage
```

---

## 6. Frontend Değişiklikleri

### 6.1 Yeni View: `static/js/views/transports.js`

**Transport Dashboard:**
```
Transport Manager
─────────────────────────────────────────────────────
WRICEF Coverage: 30/45 (67%) — 15 transport'suz ⚠️

Wave Plan:
  Wave 1 (QAS, 2026-05-01)  ████ 3/4 transport imported ✅
  Wave 2 (QAS, 2026-05-15)  ░░░░ 0/6 planned
  Wave 3 (PRD, 2026-10-15)  ░░░░ 0/12 planned — GO-LIVE WAVE

Transport Listesi:
  DEVK900001  Workbench  FI  Wave 1  ✅ QAS OK  ░ PRD pending
  DEVK900002  Customizing MM  Wave 1 ⚠️ QAS FAILED (RC 8)
```

### 6.2 `backlog.js` Entegrasyonu
BacklogItem detay modalında "Transport" sec bölümü:
- Mevcut transport assignment
- "Assign to Transport" dropdown
- Transport sistemindeki durumu (QAS: ✅, PRD: pending)

---

## 7. Test Gereksinimleri

```python
def test_create_transport_request_returns_201():
def test_assign_backlog_to_transport_creates_link():
def test_record_import_result_updates_import_log():
def test_transport_coverage_counts_items_with_and_without_transport():
def test_wave_status_returns_all_transports_with_latest_import():
def test_tenant_isolation_transport_cross_tenant_404():
```

---

## 8. Kabul Kriterleri

- [ ] Transport request CRUD çalışıyor.
- [ ] BacklogItem → Transport atanabiliyor.
- [ ] Import sonucu `import_log` JSON alanına kaydediliyor.
- [ ] Transport coverage endpoint'i WRICEF'siz transport'ları listeliyor.
- [ ] Wave status endpoint'i tüm transport'ların durumunu döndürüyor.
- [ ] `transports.js` view çalışıyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P3 — I-01 · Sprint 5-6 · Effort L
**Reviewer Kararı:** 🔵 KABUL EDİLİR — Sprint 5'e kadar bekleyebilir; ADR Sprint 3'te hazırlanmalı

### Tespit Edilen Bulgular

1. **SAP CTS API'si — müşteri pilot olmadan implement edilemez.**
   CTS API, SAP sistemine RFC/REST bağlantısı gerektirir. Bu erişim müşterinin Basis ekibine bağlıdır. İlk müşteri pilot projesi olmadan gerçek entegrasyon mümkün değil. Platform-side model ve UI Sprint 5'te yapılabilir, gerçek CTS bağlantısı pilot projeye bırakılmalı.

2. **`tenant_id nullable=True` — model şemasında düzeltilmeli.**
   FDD §3.1'deki `TransportRequest` modelinde `tenant_id nullable=True`. Platform standardına göre tüm tenant-scoped modellerde `nullable=False` zorunlu.

3. **Transport number format validasyonu — SAP CTS numaraları format'a uymalı.**
   `transport_number` için `DEVK900001` format örneği verilmiş. Bu format 3 karakter sistem ID + K + 6 rakam. Input validation'da bu format zorunlu tutulmalı (`re.match(r'^[A-Z]{3}K\d{6}$', transport_number)`), aksi halde geçersiz transport numaraları DB'ye girer.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | CTS API entegrasyonunu ilk müşteri pilot'una bırak, platform-side model Sprint 5'te | Architect | Sprint 3 (ADR) |
| A2 | `TransportRequest.tenant_id` → `nullable=False` | Coder | Sprint 5 |
| A3 | Transport number regex validation'ı servis katmanına ekle | Coder | Sprint 5 |
