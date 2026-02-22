# FDD-I05: Process Mining Integration

**Öncelik:** Backlog
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-05
**Effort:** XL (3 sprint — Phase A: 1 sprint, Phase B: 2 sprint)
**Faz Etkisi:** Discover, Explore — AS-IS süreç verisi entegrasyonu
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Platform şu an SAP projelerinin **TO-BE** tasarım tarafını destekliyor. Ancak Discover/Explore fazında ihtiyaç duyulan **AS-IS süreç keşfi** tamamen eksik.

Process Mining araçları (Celonis, SAP Signavio Process Intelligence, UiPath Process Mining):
- ERP log verilerinden gerçek süreç akışlarını çıkarır.
- Varyant analizi yapar: ideal süreç vs gerçek süreç.
- Bottleneck ve automation fırsatları gösterir.

Bu entegrasyon olduğunda: consultant platform üzerinden process mining platformundaki varyantları çekip direkt `ProcessLevel` hiyerarşisine aktarabilir.

---

## 2. İş Değeri

- Discover fazında "mevcut süreç nasıl çalışıyor?" sorusu hard data ile yanıtlanır.
- L4 process step oluşturma sürecini hızlandırır: mining varyantları → L4 adayları.
- Fit/Gap kararı için AS-IS veri sağlar.
- Celonis/Signavio yatırımı ek değer kazanır.
- SAP Cloud ALM ile üçgen bağlantı: Process Mining → Platform → Cloud ALM.

---

## 3. İki Fazlı Yaklaşım

### Phase A (Sprint 1): UI Placeholder + Bağlantı Kartı
- Settings sayfasında "Process Mining Integration" kartı görünür.
- Kullanıcı bağlantı kurmak isteyebilir ama henüz gerçek API yok.
- "Coming Soon" banner ile birlikte tanıtım metni.

### Phase B (Sprint 2-3): Gerçek Entegrasyon
- Provider bağlantısı: OAuth2 / API key.
- Process variant import flow.
- L4 seed önerileri.

---

## 4. Veri Modeli

### 4.1 Yeni Model: `ProcessMiningConnection`
**Dosya:** Yeni `app/models/integrations.py` veya `app/models/explore/infrastructure.py`'ya ekle

```python
class ProcessMiningConnection(db.Model):
    """
    Process Mining platform bağlantı konfigürasyonu.

    Her tenant kendi bağlantısını tanımlar.
    Desteklenen providerlar: celonis, signavio, uipath, sap_lama.
    Secret field encrypted (Fernet) — asla plaintext saklanmaz.

    Connection lifecycle:
        configured → testing → active | failed
    """
    __tablename__ = "process_mining_connections"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"),
                           nullable=False, index=True, unique=True,
                           comment="Tenant başına bir bağlantı")

    provider = db.Column(
        db.String(30),
        nullable=False,
        comment="celonis | signavio | uipath | sap_lama | custom"
    )
    connection_url = db.Column(db.String(500), nullable=True,
                                comment="Platform base URL")
    client_id = db.Column(db.String(200), nullable=True)
    encrypted_secret = db.Column(db.Text, nullable=True,
                                  comment="Fernet encrypted client_secret — NEVER log")
    api_key_encrypted = db.Column(db.Text, nullable=True,
                                   comment="API key alternatifi — encrypted")

    status = db.Column(
        db.String(20),
        nullable=False,
        default="configured",
        comment="configured | testing | active | failed | disabled"
    )
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)

    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    SENSITIVE_FIELDS = {"encrypted_secret", "api_key_encrypted"}

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name)
                for c in self.__table__.columns
                if c.name not in self.SENSITIVE_FIELDS}


class ProcessVariantImport(db.Model):
    """
    Process Mining platformundan import edilen süreç varyantı.

    Her varyant daha sonra L4 ProcessStep önerisine dönüştürülebilir.
    """
    __tablename__ = "process_variant_imports"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"),
                            nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"),
                           nullable=True, index=True)
    connection_id = db.Column(db.Integer, db.ForeignKey("process_mining_connections.id",
                                                          ondelete="SET NULL"), nullable=True)

    variant_id = db.Column(db.String(100), nullable=False,
                            comment="Provider'dan gelen unique variant ID")
    process_name = db.Column(db.String(255), nullable=False)
    sap_module_hint = db.Column(db.String(10), nullable=True)
    variant_count = db.Column(db.Integer, nullable=True,
                               comment="Bu varyantın gerçekte kaç kez yaşandığı")
    conformance_rate = db.Column(db.Numeric(5, 2), nullable=True,
                                  comment="Happy path'e uyum oranı: 0-100")
    steps_raw = db.Column(db.JSON, nullable=True,
                           comment="Provider'dan gelen ham adımlar")

    # İşlenme durumu
    status = db.Column(
        db.String(20),
        nullable=False,
        default="imported",
        comment="imported | reviewed | promoted | rejected"
    )
    promoted_to_process_step_id = db.Column(
        db.Integer,
        db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True
    )

    imported_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.2 Migration
```
flask db migrate -m "add process_mining_connections and process_variant_imports tables"
```

---

## 5. Servis Katmanı

### 5.1 Gateway Katmanı: `app/services/integrations/process_mining_gateway.py`

```python
class ProcessMiningGateway:
    """
    Process Mining provider abstraction layer.
    Strategy pattern: her provider ayrı adapter.
    """

    def __init__(self, connection: ProcessMiningConnection):
        self._connection = connection
        self._adapter = self._build_adapter()

    def _build_adapter(self) -> "BaseProcessMiningAdapter":
        match self._connection.provider:
            case "celonis":
                return CelonisAdapter(self._connection)
            case "signavio":
                return SignavioAdapter(self._connection)
            case _:
                raise ValidationError(f"Unsupported provider: {self._connection.provider}")

    def test_connection(self) -> bool:
        return self._adapter.ping()

    def list_processes(self) -> list[dict]:
        return self._adapter.fetch_processes()

    def fetch_variants(self, process_id: str) -> list[dict]:
        return self._adapter.fetch_variants(process_id)
```

### 5.2 Servis: `app/services/process_mining_service.py`

```python
def save_connection(tenant_id: int, data: dict) -> dict:
    """
    Bağlantı konfigürasyonunu kaydeder.
    Client secret Fernet ile encrypt edilir — plaintext DB'ye yazılmaz.
    """

def test_connection(tenant_id: int) -> dict:
    """Bağlantıyı test eder, status günceller."""

def import_variants(tenant_id: int, project_id: int, process_id: str) -> dict:
    """Provider'dan varyantları çeker, ProcessVariantImport table'ına kaydeder."""

def promote_variant_to_process_step(
    tenant_id: int, project_id: int, variant_import_id: int,
    parent_process_level_id: int
) -> dict:
    """
    Seçilen varyantı L4 ProcessStep'e dönüştürür.
    steps_raw → ProcessStep entities.
    """
```

---

## 6. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/integrations/process_mining_bp.py`

```
# Connection Management
GET    /api/v1/integrations/process-mining
POST   /api/v1/integrations/process-mining
PUT    /api/v1/integrations/process-mining
DELETE /api/v1/integrations/process-mining
POST   /api/v1/integrations/process-mining/test

# Process & Variant Import
GET    /api/v1/integrations/process-mining/processes
GET    /api/v1/integrations/process-mining/processes/<process_id>/variants
POST   /api/v1/projects/<proj_id>/process-mining/import
       Body: { "process_id": "...", "variant_ids": ["v1", "v2"] }

GET    /api/v1/projects/<proj_id>/process-mining/imports
POST   /api/v1/projects/<proj_id>/process-mining/imports/<id>/promote
       Body: { "parent_process_level_id": 42 }

Permission: integrations.admin (bağlantı) / explore.edit (import+promote)
```

---

## 7. Frontend Değişiklikleri

### 7.1 Settings Sayfası — Integration Kartları

**Phase A UI:**
```
┌──────────────────────────────────────────────────────────┐
│ 🔄 Process Mining Integration                             │
│                                                           │
│ AS-IS süreçlerinizi Celonis veya SAP Signavio'dan         │
│ otomatik olarak içe aktarın.                              │
│                                                           │
│ Desteklenen: Celonis • SAP Signavio • UiPath              │
│                                                           │
│ [Configure Connection]         Status: ⚪ Not Configured  │
└──────────────────────────────────────────────────────────┘
```

### 7.2 **Phase B**: `static/js/views/process_mining.js`

**Tab 1: Connection**
```
Connection Status: ✅ Active (Celonis)
Last sync: 2026-02-20 09:15
[Test Connection]  [Re-configure]
```

**Tab 2: Import Wizard**
```
Available Processes (from Celonis):
  ✅ Order-to-Cash (FI) — 45 variants
  ☐  Procure-to-Pay (MM) — 32 variants

[Import Selected]
```

**Tab 3: Imported Variants**
```
FI - Invoice to Payment  │ Conformance: 72%  │ Count: 1,240  │ [Promote to L4] [Reject]
FI - Invoice with Hold   │ Conformance: 45%  │ Count: 318    │ [Promote to L4] [Reject]
```

---

## 8. Test Gereksinimleri

```python
def test_save_connection_encrypts_secret():
def test_secret_not_in_to_dict_output():
def test_import_variants_creates_process_variant_import_records():
def test_promote_variant_creates_process_step():
def test_test_connection_updates_status_on_success():
def test_test_connection_updates_status_and_error_message_on_failure():
def test_tenant_isolation_connection_cross_tenant_404():
```

---

## 9. Güvenlik Notları

- `encrypted_secret` ve `api_key_encrypted` alanları `to_dict()` çıktısında ASLA görünmez.
- Bağlantı bilgileri loglanmaz.
- Provider'a giden HTTP istekleri gateway üzerinden geçer — timeout=10s, retry=2.
- Provider OAuth2 token cache: Redis, TTL=3600, cache key includes tenant_id.

---

## 10. Kabul Kriterleri

- [ ] Phase A: Settings kartı görünüyor, configure butonu bağlantı formunu açıyor.
- [ ] Phase B: Bağlantı konfigürasyonu kaydediliyor.
- [ ] Test connection endpoint durum güncelliyor.
- [ ] Encrypted secret `to_dict()` çıktısında yok.
- [ ] Import endpoint variant'ları `ProcessVariantImport` tablosuna kaydediyor.
- [ ] Promote endpoint L4 ProcessStep oluşturuyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** Backlog — I-05 · Sprint 8+ · Effort XL
**Reviewer Kararı:** 🔵 ERTELEME ONAYLI — Faz A (placeholder) Sprint 3'te yapılabilir

### Tespit Edilen Bulgular

1. **Celonis lisansı — ayrı müzakere gerektirir.**
   Celonis API erişimi müşteri lisansına bağlıdır. Platform birden fazla process mining provider destekleyecekse provider-agnostic adapter pattern kullanılmalı. F-07 (Cloud ALM) için benzer `ALMGateway` yaklaşımı burada da geçerli: `ProcessMiningGateway` (`app/integrations/process_mining_gateway.py`).

2. **Faz A UI placeholder — `integrations.js` ile tutarlı olmalı.**
   F-07 için de benzer bir "Coming Soon" kartı öneriliyor. İki kart aynı `integrations.js` dosyasına eklenecekse UI consistency şablonu (card component) Sprint 3'te standartlaştırılmalı.

3. **L4 seed öneresi — AI feature gerektirir.**
   Process mining varyantlarından L4 adaylarını önermek LLM veya rule-based mapping gerektirir. Eğer LLM kullanılacaksa `LLMGateway` üzerinden geçmeli ve audit log'a yazılmalı.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Faz A UI kartını F-07 ile aynı Sprint'te (Sprint 3) implement et, card şablonunu standartlaştır | Frontend | Sprint 3 |
| A2 | `ProcessMiningGateway` pattern kararını ADR'a yaz | Architect | Sprint 5 |
| A3 | L4 öneri motoru — LLM vs rule-based kararını Faz B scope'una ekle | Architect | Sprint 8 |
