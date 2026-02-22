# FDD-F07: SAP Cloud ALM Entegrasyon MVP

**Öncelik:** P2
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-07
**Effort:** L (2 sprint — gerçek entegrasyon), S (UI placeholder — 1 gün)
**Faz Etkisi:** Explore, Realize — Requirement ve test senkronizasyonu
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

`app/models/explore/infrastructure.py` içinde `CloudALMSyncLog` modeli var. Bu model entegrasyonun varlığını ima ediyor ama gerçek SAP Cloud ALM API bağlantısı yok. Müşteriler SAP Cloud ALM kullanan SI firmalar olduğunda bu durum beklenti yönetimi sorunu yaratıyor.

**Bu FDD iki fazı kapsar:**
- **Faz A (S — 1 gün):** UI'da "Coming Soon" + mevcut log modelini görünür yapma
- **Faz B (L — 2 sprint):** Gerçek OAuth2 + SAP Cloud ALM API entegrasyonu

---

## 2. İş Değeri

- Faz A: Müşterilere yanlış beklenti verilmesini önler.
- Faz B: SAP Cloud ALM kullanan büyük SI firmalarına entegrasyon sağlar.
  - Requirement'lar iki platformda senkron tutulur.
  - Test results Cloud ALM'e push edilir.
  - Müşteri kendi SAP Cloud ALM portalından da durumu izleyebilir.

---

## 3. FAZ A: UI Placeholder (S)

### 3.1 Entegrasyon Ayarları Sayfası
**Dosya:** `static/js/views/integrations.js` veya yeni `integration_settings.js`

Mevcut `integrations.js` view'ına bir "SAP Cloud ALM" kartı ekle:

```
┌─────────────────────────────────────────────────┐
│  🔗 SAP Cloud ALM                               │
│  Requirement ve test sync                       │
│                                                 │
│  Status: 🔵 Coming Q2 2026                      │
│                                                 │
│  [Notify me when available]                     │
└─────────────────────────────────────────────────┘
```

### 3.2 Sync Log Görünürlüğü
`CloudALMSyncLog` modelinin datası admin panelinde görünür olmalı:
```
GET /api/v1/projects/<project_id>/integrations/cloud-alm/sync-log
```
Bu endpoint mevcut log'ları döndürür ama "no live connection" mesajı ekler.

---

## 4. FAZ B: Gerçek Entegrasyon (L)

### 4.1 SAP Cloud ALM API Bağlantısı

SAP Cloud ALM REST API dokümentasyonu: SAP BTP üzerinde OAuth2 Client Credentials flow.

#### Kimlik Bilgisi Yapılandırması
**Dosya:** Yeni `app/models/integrations.py` → mevcut dosyaya ekle veya yeni model

```python
class CloudALMConfig(db.Model):
    """
    SAP Cloud ALM bağlantı konfigürasyonu.
    Tenant başına bir konfigürasyon.
    client_secret şifreli saklanır (encrypted_secret alanı).
    """
    __tablename__ = "cloud_alm_configs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    alm_url = db.Column(
        db.String(500),
        nullable=False,
        comment="SAP Cloud ALM instance URL: https://<tenant>.alm.cloud.sap"
    )
    client_id = db.Column(db.String(200), nullable=False)
    encrypted_secret = db.Column(
        db.Text,
        nullable=False,
        comment="AES-256 şifreli client_secret — asla plaintext saklanmaz"
    )
    token_url = db.Column(
        db.String(500),
        nullable=False,
        comment="OAuth2 token endpoint URL"
    )
    sync_requirements = db.Column(db.Boolean, nullable=False, default=True)
    sync_test_results = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_test_at = db.Column(db.DateTime, nullable=True)
    last_test_status = db.Column(db.String(20), nullable=True, comment="ok | error | timeout")

    SENSITIVE_FIELDS = {"encrypted_secret"}

    def to_dict(self) -> dict:
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in self.SENSITIVE_FIELDS
        }
```

### 4.2 Yeni Servis: `app/services/cloud_alm_service.py`

```python
"""
SAP Cloud ALM entegrasyon servisi.

Tüm API çağrıları LLMGateway benzeri bir pattern ile:
  - OAuth2 token otomatik yenileme (cache'lenir)
  - Retry: max 2, exponential backoff
  - Timeout: 30s
  - Her istek CloudALMSyncLog'a yazılır (başarı/hata)
  - Tenant izolasyonu: per-tenant config

SAP Cloud ALM API endpoints kullanılır:
  https://help.sap.com/docs/cloud-alm/apis
"""

def test_connection(tenant_id: int) -> dict:
    """Bağlantı testi. Returns: {"ok": bool, "error": str | None}"""

def push_requirements(
    tenant_id: int,
    project_id: int,
    requirement_ids: list[int] | None = None,  # None = hepsini push et
) -> dict:
    """
    ExploreRequirement'ları SAP Cloud ALM'e gönderir.

    SAP Cloud ALM endpoint: POST /api/calm-ops/v1/requirements (varsayılan)
    Her requirement için external_id alanına Cloud ALM ID'si yazılır.

    Returns:
        {"pushed": 45, "updated": 12, "errors": 3, "error_details": [...]}
    """

def pull_requirements(tenant_id: int, project_id: int) -> dict:
    """
    SAP Cloud ALM'deki değişiklikleri platforma çeker.
    external_id üzerinden eşleştirilir.
    """

def push_test_results(
    tenant_id: int,
    project_id: int,
    test_cycle_id: int,
) -> dict:
    """TestCycle execution sonuçlarını Cloud ALM'e gönderir."""

def get_sync_log(tenant_id: int, project_id: int, limit: int = 50) -> list[dict]:
    """Son N sync işleminin logunu döner."""
```

### 4.3 `CloudALMSyncLog` Modeli Güncellemesi
**Dosya:** `app/models/explore/infrastructure.py`

Mevcut modele eklenecek alanlar:
```python
http_status_code = db.Column(db.Integer, nullable=True)
error_message = db.Column(db.Text, nullable=True)
records_pushed = db.Column(db.Integer, nullable=True)
records_pulled = db.Column(db.Integer, nullable=True)
duration_ms = db.Column(db.Integer, nullable=True)
triggered_by = db.Column(db.String(20), nullable=True, comment="manual | scheduled | webhook")
```

---

## 5. API Endpoint'leri

**Dosya:** `app/blueprints/integrations_bp.py`

```
# Faz A
GET  /api/v1/projects/<project_id>/integrations/cloud-alm/sync-log
     Response: {"connection_active": false, "message": "Coming Q2 2026", "logs": [...]}

# Faz B
POST /api/v1/tenants/<tenant_id>/integrations/cloud-alm/config
PUT  /api/v1/tenants/<tenant_id>/integrations/cloud-alm/config
POST /api/v1/tenants/<tenant_id>/integrations/cloud-alm/test-connection

POST /api/v1/projects/<project_id>/integrations/cloud-alm/push-requirements
POST /api/v1/projects/<project_id>/integrations/cloud-alm/pull-requirements
POST /api/v1/projects/<project_id>/integrations/cloud-alm/push-test-results/<cycle_id>
GET  /api/v1/projects/<project_id>/integrations/cloud-alm/sync-log
```

---

## 6. Güvenlik Notları

- `client_secret` asla plaintext saklanmaz — AES-256 ile şifrelenmiş olarak `encrypted_secret`'ta tutulur.
- Şifreleme anahtarı `os.getenv("ENCRYPTION_KEY")` üzerinden alınır.
- `to_dict()` metodunda `encrypted_secret` SENSITIVE_FIELDS'da — API response'a asla girmez.
- Token cache: Redis'te `cloud_alm_token:{tenant_id}` key'i, TTL = token expiry - 60s.

---

## 7. Test Gereksinimleri (Faz B)

```python
# tests/test_cloud_alm_service.py

def test_test_connection_returns_ok_with_valid_mock_oauth():
def test_push_requirements_calls_correct_alm_endpoint():
def test_push_requirements_writes_sync_log_on_success():
def test_push_requirements_writes_sync_log_on_error():
def test_push_requirements_updates_external_id_on_each_requirement():
def test_config_endpoint_does_not_return_encrypted_secret():
def test_tenant_isolation_push_blocks_cross_tenant():
```

---

## 8. Kabul Kriterleri

**Faz A:**
- [ ] `integrations.js` içinde SAP Cloud ALM kartı "Coming Q2 2026" etiketi ile görünüyor.
- [ ] `GET /integrations/cloud-alm/sync-log` çalışıyor, `connection_active: false` döndürüyor.

**Faz B:**
- [ ] `CloudALMConfig` oluşturulabiliyor, secret şifreli saklanıyor.
- [ ] Test connection endpoint'i OAuth2 token alıyor ve OK döndürüyor.
- [ ] Push requirements sonrası `external_id` alanları doluyor.
- [ ] Her push/pull işlemi `CloudALMSyncLog`'a yazılıyor.
- [ ] `encrypted_secret` hiçbir API response'da görünmüyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P2 — F-07 · Sprint 3 · Effort S/L
**Reviewer Kararı:** ⛔ FAZ B — GATEWAY PATTERN ZORUNLU (LLMGateway eşdeğeri)

### Tespit Edilen Bulgular

1. **KRİTİK: `encrypted_secret` — şifreleme mekanizması FDD'de belirtilmemiş.**
   `CloudALMConfig.encrypted_secret` alanı var ama nasıl şifreleneceği yazılmamış. `os.getenv("SECRET_KEY")` ile symmetric encryption (Fernet/AES) mı, yoksa KMS mi? Hard-coded key kesinlikle yasak. `app/utils/crypto.py` veya benzeri bir utility kullanılmalı.

2. **ALM API çağrıları `LLMGateway` benzeri bir `ALMGateway` üzerinden geçmeli.**
   Platform standardına göre tüm dış servis çağrıları gateway pattern ile audit log'a yazılmalı. Her ALM push/pull işlemi `tenant_id`, `user_id`, `payload_hash`, `response_code`, `latency_ms` ile loglanmalı. Doğrudan `requests.post()` çağrısı yapılması yasak.

3. **Circuit breaker — Faz B'de zorunlu.**
   SAP Cloud ALM dış bağımlılık. 5 hata / 1 dakikada circuit breaker devreye girmeli, 30 saniye SAP ALM'e çağrı yapılmamalı. Bu olmadan ALM down olduğunda platform cascade fail eder.

4. **OAuth2 token refresh — token expiry yönetimi eksik.**
   OAuth2 client credentials token genellikle 1 saat geçerli. Token önbelleğe alınmalı, süre dolmadan yenilenmeli. Her API çağrısında yeni token almak performans ve rate-limit sorununa yol açar.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `encrypted_secret` için `app/utils/crypto.py` Fernet şifreleme utility'si tanımla | Coder | Sprint 3 |
| A2 | `app/integrations/alm_gateway.py` gateway sınıfı oluştur — doğrudan `requests` yasak | Architect | Sprint 3 |
| A3 | Circuit breaker implementasyonunu Faz B scope'una ekle | Architect | Sprint 3 |
| A4 | OAuth2 token cache ve refresh mekanizmasını gateway içinde implement et | Coder | Sprint 3 |
