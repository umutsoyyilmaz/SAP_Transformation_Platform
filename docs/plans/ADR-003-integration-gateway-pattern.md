# ADR-003: Integration Gateway Pattern

**Durum:** ✅ Onaylandı
**Tarih:** 2026-02-22
**Yazar:** Umut Soyyılmaz
**İlgili FDD:** `FDD-I05-integration-gateway.md`, `FDD-I03-cutover-clock-war-room.md`
**İlgili ADR:** `ADR-002-sap-auth-concept-extension.md`
**Kapsam:** Integration gateway sınıf yapısı, polling vs SSE/WebSocket kararı, `ALMGateway` referans implementasyonu

---

## 1. Karar Özeti

| # | Karar | Gerekçe |
|---|-------|---------|
| **D1** | Her integration alanı için **ayrı typed gateway sınıfı** — tek `IntegrationGateway` mega-class yerine | Tek class → 2000+ satır, test edilemez, tenant isolation hataları gizlenir |
| **D2** | `ProcessMiningGateway` — `ALMGateway`'den **ayrı**, bağımsız sınıf | SAP PM ve ALM farklı auth mekanizması, farklı rate-limit, farklı retry stratejisi |
| **D3** | Cutover War Room real-time için **30 saniye polling** — SSE/WebSocket değil | Platform Railway/Heroku üzerinde çalışıyor; sticky session yokluğu SSE bağlantılarını kesintiye uğratır |
| **D4** | Tüm dış HTTP çağrıları typed gateway üzerinden — servis katmanı doğrudan `requests.get()` çağıramaz | Retry, timeout, audit loglama, tenant isolation tek noktada uygulanır |
| **D5** | Tüm AI çağrıları `LLMGateway` üzerinden — `anthropic`, `openai`, `google.genai` servis dosyasında import edilemez | Maliyet takibi ve audit her AI çağrısında zorunlu |

**Seçilen Yol:** Option A — Domain-specific typed gateways, ALMGateway canonical pattern.

---

## 2. Bağlam

S4-02 sprint'inde `ALMGateway` (`app/ai/alm_gateway.py`) implement edildi. Bu gateway:
- Retry + exponential backoff
- Tenant-scoped API key lookup
- Request/response audit loglama
- Timeout yönetimi

Sprint 5'te iki yeni integration alanı ekleniyor:
1. **ProcessMiningGateway** (FDD-I05) — SAP Signavio / Celonis entegrasyonu
2. **Cutover War Room polling** (FDD-I03) — real-time dashboard

Her ikisi için gateway pattern'ı netleştirilmesi gerekiyordu.

---

## 3. Seçenek Analizi

### 3.1 Tek Unified IntegrationGateway

```python
class IntegrationGateway:
    def call_alm(self, tenant_id, ...): ...
    def call_process_mining(self, tenant_id, ...): ...
    def call_transport_api(self, tenant_id, ...): ...
```

**Neden Reddedildi:**
- Her integration'ın auth mekanizması farklı (OAuth2 vs API key vs certificate)
- Tek class spesifik testleri zorlaştırır — her test için tüm sistemin mock'unu kurmak gerekir
- Rate limit, timeout değerleri per-provider farklı olmalı

### 3.2 Domain-Specific Typed Gateways ✅ SEÇİLDİ

```python
# app/ai/alm_gateway.py       → ALM/ITSM entegrasyonu (S4-02, referans implementasyonu)
# app/ai/process_mining_gw.py → SAP Signavio / Celonis (S5-02, FDD-I05)
# app/services/transport_service.py içinde inline SAP CTS API client → küçük, ayrı file gerekmez
```

Her gateway'in sorumluluğu:

| Gateway | Auth | Rate Limit | Retry | Timeout |
|---------|------|-----------|-------|---------|
| `ALMGateway` | API key (per tenant) | 100 req/min | exp backoff 3x | 30s |
| `ProcessMiningGateway` | OAuth2 client credentials | 50 req/min | exp backoff 2x | 45s |
| LLMGateway | API key (env) | token budget | exp backoff 2x | 30s |

---

## 4. ALMGateway — Canonical Reference Pattern

S4-02'de implement edilen `ALMGateway` tüm yeni gateway'ler için referans alınır:

```python
class ALMGateway:
    """
    Canonical gateway implementation — use as template for new gateways.

    Enforces: retry + timeout + audit log + tenant isolation.
    All integration HTTP calls go through a subclass of this pattern.
    """

    def __init__(self, tenant_id: int):
        self._tenant_id = tenant_id
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Build session with per-tenant credentials and retry adapter."""
        session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 502, 503])
        )
        session.mount("https://", adapter)
        return session

    def _call(self, method: str, url: str, **kwargs) -> dict:
        """Execute HTTP call with timeout + audit log."""
        start = time.perf_counter()
        try:
            resp = self._session.request(method, url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            logger.error("ALMGateway timeout tenant=%s url=%s", self._tenant_id, url)
            raise IntegrationError("ALM API timeout")
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _log_integration_call(self._tenant_id, url, elapsed_ms)
```

Yeni gateway'ler `_call()`, `_build_session()`, `_log_integration_call()` pattern'ını aynen uygular. Sadece auth ve rate limit parametreleri override edilir.

---

## 5. Polling vs SSE/WebSocket Kararı (FDD-I03 için)

### 5.1 Seçenekler

| Teknoloji | Avantaj | Dezavantaj |
|-----------|---------|-----------|
| **30s Polling** | Stateless, her ortamda çalışır | N req/dakika → DB yükü artar |
| Server-Sent Events (SSE) | Tek yönlü push, HTTP/1.1 uyumlu | Railway sticky session yok → bağlantı düşer |
| WebSocket | Full duplex, en düşük gecikme | Infrastructure değişikliği + sticky session zorunlu |

### 5.2 Karar — 30 Saniye Polling ✅

**Gerekçe:**
1. **Railway/Heroku platformu** HTTP request'leri farklı instance'lara dağıtabilir. SSE bağlantısı açılan instance ile sonraki request'i işleyen instance farklı olabilir → bağlantı kopar.
2. **Veri güncellenme hızı** cut-over sırasında makul: görev durumu günde 50-200 kez değişir → 30 saniyelik gecikme operasyonel olarak kabul edilebilir.
3. **Implementasyon karmaşıklığı** düşük: tek GET endpoint + `setInterval(30000)`.

**Implementasyon:**
```javascript
// static/js/views/cutover.js
let warRoomTimer = null;

function startWarRoomPolling(planId) {
    refreshLiveStatus(planId);  // immediate first load
    warRoomTimer = setInterval(() => refreshLiveStatus(planId), 30_000);
}

function stopWarRoomPolling() {
    if (warRoomTimer) {
        clearInterval(warRoomTimer);
        warRoomTimer = null;
    }
}
```

**İleride WebSocket geçişi için:** `GET .../live-status` endpoint'i değişmeden kalır. Frontend'de sadece `setInterval` → WebSocket event listener değiştirilir. Backend logic aynı kalır.

---

## 6. Tüm Integration HTTP Çağrıları — Kural

```python
# ✅ DOĞRU — gateway üzerinden
from app.ai.alm_gateway import ALMGateway
gw = ALMGateway(tenant_id)
result = gw.get_incidents(project_key=key)

# ✅ DOĞRU — AI çağrısı
from app.ai.gateway import LLMGateway
gw = LLMGateway()
result = gw.chat(prompt, model="claude-3-5-haiku-20241022")

# 🚫 YASAK — servis / blueprint içinde doğrudan HTTP
import requests
resp = requests.get("https://api.external.com/...")  # FORBIDDEN

# 🚫 YASAK — AI SDK doğrudan import
import anthropic   # FORBIDDEN outside app/ai/gateway.py
import openai      # FORBIDDEN outside app/ai/gateway.py
```

**Zorlama mekanizması:** Code review checklist'e eklendi (§14 Forbidden Patterns).

---

## 7. ProcessMiningGateway — Taslak (S5-02 kapsamı)

```python
# app/ai/process_mining_gw.py

class ProcessMiningGateway:
    """
    Gateway for SAP Signavio / Celonis Process Mining API.

    Auth: OAuth2 client credentials (per-tenant, stored in tenant config).
    Rate limit: 50 req/min — exponential backoff on 429.
    Timeout: 45s (process graph queries can be slow).

    NOT a subclass of ALMGateway — separate instantiation per tenant call.
    Reference pattern: ALMGateway (app/ai/alm_gateway.py).
    """

    def get_process_variants(self, tenant_id: int, process_id: str) -> dict:
        """Return variant analysis for a process model."""
        ...

    def get_conformance_metrics(self, tenant_id: int, process_id: str) -> dict:
        """Return conformance checking metrics against SAP reference model."""
        ...
```

> **Not:** ProcessMiningGateway tam implementasyonu FDD-I05 kapsamında yapılacak.
> Bu ADR sadece class naming ve isolation kararını belgeliyor.

---

## 8. Etkilenen Dosyalar

| Dosya | Değişiklik | Sprint |
|-------|-----------|--------|
| `docs/plans/ADR-003-integration-gateway-pattern.md` | **YENİ** — bu dosya | S5-02 |
| `app/ai/process_mining_gw.py` | **YENİ** — ProcessMiningGateway stub | FDD-I05 |
| `static/js/views/cutover.js` | 30s polling warroom | S5-03 |
| `app/blueprints/cutover_bp.py` | `/live-status` endpoint | S5-03 |

---

## 9. Onay Kontrolleri

- [x] ADR oluşturuldu
- [x] ALMGateway canonical pattern belgelendi
- [x] Polling kararı belgelendi (FDD-I03 referans)
- [ ] ProcessMiningGateway implementasyonu — FDD-I05
- [ ] Gateway audit loglama testi — S7-01
