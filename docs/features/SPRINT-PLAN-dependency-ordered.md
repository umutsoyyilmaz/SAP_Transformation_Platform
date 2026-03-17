# Sprint Planı — Bağımlılık Sıralı Master Liste

**Hazırlayan:** Reviewer Agent
**Tarih:** 2026-02-22
**Kaynak:** FDD Audit (AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md) + Reviewer Audit Notları
**Pipeline:** Tüm item'lar FDD belgelerine referans verir

---

## Bağımlılık Grafiği (Özet)

```
S1-01 (get_scoped helper)
  ├── S1-02 (78 servis fix)
  │     └── S4-01 (B-03 Hypercare)  ← SERT BLOKER
  ├── S1-04 (B-04 Signoff)
  │     └── S3-01 (B-02 Discover)
  ├── S3-03 (F-06 RACI)
  └── S5-04 (I-01 Transport)

S1-03 (B-01 karar — ADR)
  └── S1-05 (B-01 migration)
        ├── S2-01 (F-01 ConfigItem trace)
        │     ├── S2-02 (F-02 Upstream trace)
        │     └── S2-03 (F-05 Coverage)
        │           └── S2-04 (F-03 Export)
        └── S5-04 (I-01 Transport)

S3-04 (F-07 Faz A)
  └── S4-02 (F-07 Faz B)
        └── S5-02 (ADR-003 gateway)
              └── S8-01 (I-05 Faz B)

S4-01 (B-03 Hypercare)
  ├── S5-03 (I-03 Cutover clock)
  └── S6-01 (I-04 KB)

S5-01 (ADR-002 auth)
  └── S7-02 (I-02 Auth Concept)
```

---

## 🔴 SPRINT 1 — Temel Altyapı

> Tüm sonraki sprintlerin zemini. Bu sprint tamamlanmadan hiçbir P1/P2 feature başlayamaz.

---

### S1-01 · `FDD-P0` · P0-BLOKER · Effort: S (1 gün)

**`get_scoped()` Tenant-Scoped Query Helper**

| Alan | Değer |
|---|---|
| Dosya | `app/services/helpers/scoped_queries.py` (yeni) |
| Bağımlılıklar | **Yok — ilk iş bu** |
| Bloke ettiği | S1-02, S1-04, S3-03, S4-01, S5-04 |

**Yapılacaklar:**
- [x] `get_scoped(model, pk, *, project_id=None, program_id=None, tenant_id=None)` utility yazılacak
- [x] En az bir scope parametresi zorunlu — yoksa `ValueError` fırlat
- [x] `NotFoundError` scope mismatch'de raise edilecek
- [x] Unit test: `tests/unit/test_scoped_queries.py`

---

### S1-02 · `FDD-P0` · P0-BLOKER · Effort: M (2-3 gün)

**78 Servis Fonksiyonunda `Model.query.get(pk)` → `get_scoped()` Migrasyonu**

| Alan | Değer |
|---|---|
| Dosya | `run_sustain_service.py`, `cutover_service.py`, `explore_service.py` öncelikli |
| Bağımlılıklar | S1-01 |
| Bloke ettiği | S4-01 (B-03 — SERT BLOKER) |

**Yapılacaklar:**
- [x] `grep -rn "\. query\.get(" app/services/` ile tüm instance'ları listele
- [x] `run_sustain_service.py` örüntüleri düzelt (önce)
- [x] `cutover_service.py` örüntüleri düzelt (önce)
- [x] `explore_service.py` örüntüleri düzelt (önce)
- [x] Kalan tüm servisler düzelt (data_factory_service, scope_resolution, spec_template, traceability)
- [x] Integration test suite geçiyor

---

### S1-03 · `FDD-B01` · P0 · Effort: XS (yarım gün — karar toplantısı)

**Mimari Karar: `ExploreRequirement` Canonical Kaynak Onayı**

| Alan | Değer |
|---|---|
| Çıktı | `docs/plans/ADR-001-requirement-consolidation.md` |
| Bağımlılıklar | **Yok — kod değil, karar** |
| Bloke ettiği | S1-05, S2-01, S2-02, S2-03, S2-04, S5-04 |

**Yapılacaklar:**
- [x] Tech lead oturumu: Option A (ExploreRequirement canonical) vs Option B (bridge pattern)
- [x] ADR belgesi imzalanacak — `docs/plans/ADR-001-requirement-consolidation.md`
- [x] Karar S1-05'e başlamadan önce alınacak

---

### S1-04 · `FDD-B04` · P0 · Effort: M (3-4 gün)

**Formal Sign-off Workflow — `SignoffRecord` + `signoff_service.py`**

| Alan | Değer |
|---|---|
| Dosya | `app/models/signoff.py` (yeni), `app/services/signoff_service.py` (yeni), `app/blueprints/signoff_bp.py` (yeni) |
| Bağımlılıklar | S1-01 (`get_scoped` kullanılacak) |
| Bloke ettiği | S3-01 (B-02 — charter approval sign-off'a bağlı) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `tenant_id → nullable=False, ondelete='CASCADE'` (kritik açık)
- [x] `approver_name_snapshot = db.Column(db.String(255), nullable=True)` modele eklenmeli
- [x] Self-approval guard `signoff_service.py`'de — blueprint'te değil
- [x] `gate_service.py` → `signoff_service.is_entity_approved(entity_type, entity_id)` entegrasyonu (governance_rules.py RULE-SO-04)
- [x] IP: `X-Forwarded-For` header kullanımı (`request.remote_addr` yetersiz)
- [x] Approved record immutable — update/delete girişimi 422 döndürmeli
- [ ] `flask db migrate -m "add signoff_records table"` ← run after merge

**Kabul Kriterleri:**
- [x] Workshop sign-off'da approver ismi ve tarihi `SignoffRecord`'da görünüyor
- [x] Self-approval 422 döndürüyor
- [x] Approved record değiştirilemiyor
- [x] Tenant isolation: cross-tenant 404

---

### S1-05 · `FDD-B01` · P0 · Effort: XL (5-7 gün)

**`ExploreRequirement` Model Genişletme + Migration + Legacy Deprecation**

| Alan | Değer |
|---|---|
| Dosya | `app/models/explore/requirement.py`, `scripts/migrate_requirements_to_explore.py` (yeni) |
| Bağımlılıklar | S1-03 (ADR kararı), S1-01 (`get_scoped`) |
| Bloke ettiği | S2-01, S2-02, S2-03, S2-04, S5-04 |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Tüm yeni alanlar `nullable=True` ile başla: `requirement_type`, `moscow_priority`, `source`, `parent_id`, `external_id`
- [x] Migration script: `backlog_items.requirement_id`, `test_cases.requirement_id` FK'larını da güncelle
- [x] Script idempotent olmalı (birden fazla çalıştırmaya dayanıklı)
- [x] `requirements` tablosuna write-block: yeni kayıt oluşturulamaz (`TESTING` bypass ile test-güvenli)
- [x] `static/js/views/requirement.js` → zaten kaldırılmıştı (önceki sprint'te)
- [x] `grep -r "from app.models.requirement import" tests/` — impacted testleri refactor et (test file oluşturuldu + TESTING bypass)
- [ ] `flask db migrate -m "add fields to explore_requirements"` — prod deploy öncesi çalıştırılacak

**Kabul Kriterleri:**
- [x] `requirements` tablosunda yeni kayıt oluşturulamıyor (ORM write-block, TESTING=False ortamında çalışır)
- [ ] Tüm `requirements` kayıtları `explore_requirements`'a migrate edildi (production task — script hazır)
- [x] `traceability.py` yalnızca `ExploreRequirement` üzerinden çalışıyor (→ S2-02 kapsamında)
- [x] Tüm mevcut testler geçiyor (83 test: 82 passed, 1 xfailed)

---

## 🟡 SPRINT 2 — P1 Feature'lar

> **Önkoşul:** S1-03 ve S1-05 tamamlanmış olmalı (B-01 canonical)

---

### S2-01 · `FDD-F01` · P1 · Effort: S (3-4 gün)

**`ConfigItem → TestCase` Traceability Zinciri**

| Alan | Değer |
|---|---|
| Dosya | `app/models/backlog.py`, `app/services/traceability.py` |
| Bağımlılıklar | S1-05 (B-01 canonical requirement), S1-01 (`get_scoped`) |
| Bloke ettiği | S2-02 (F-02), S2-03 (F-05) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `ConfigItem.requirement_id` FK hedefi B-01 sonrası `ExploreRequirement` olarak kesinleşti
- [x] `trace_config_item()` içinde `tenant_id` scope manuel eklenmeli
- [x] `overlaps` SQLAlchemy uyarısı — relationship yeniden tasarla veya justify et

**Kabul Kriterleri:**
- [x] `trace_config_item(config_item_id)` çalışıyor
- [x] `GET /trace/config-items/<id>` 200 döndürüyor
- [x] Tenant isolation korunuyor

---

### S2-02 · `FDD-F02` · P1 · Effort: S (3-4 gün)

**Upstream Defect Trace — `Defect → L3 ProcessLevel`**

| Alan | Değer |
|---|---|
| Dosya | `app/services/traceability.py` |
| Bağımlılıklar | S1-05 (B-01), S2-01 (F-01 relationship'leri tamamlanmış) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Kırık zincir senaryosu: partial trace response (500 değil, null dönmeli)
- [x] N+1 uyarısı docstring'e ekle: "bulk trace için ayrı endpoint"
- [x] B-01 tam stable olana kadar feature flag arkasında tut

**Kabul Kriterleri:**
- [x] `trace_upstream_from_defect(defect_id, project_id, tenant_id)` L1-L4 döndürüyor
- [x] Kırık zincirde partial response — 500 değil
- [x] `GET /trace/defects/<id>/upstream` çalışıyor

---

### S2-03 · `FDD-F05` · P1 · Effort: S (3-4 gün)

**Requirement Coverage Raporlama**

| Alan | Değer |
|---|---|
| Dosya | `app/services/metrics.py`, `app/blueprints/metrics_bp.py` |
| Bağımlılıklar | S1-05 (B-01), S2-01 (F-01 — ConfigItem coverage dahil edilecek) |
| Bloke ettiği | S2-04 (F-03 — Excel'e coverage metriği dahil edilecek) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Hangi tablodan sorgu yapıldığı (`ExploreRequirement`) docstring'e yaz
- [x] Cache invalidation: `ExploreRequirement` write'larına da bağla
- [x] `status='cancelled'` requirement'ları coverage hesabından çıkar

**Kabul Kriterleri:**
- [x] `GET /metrics/requirement-coverage` classification + priority breakdown döndürüyor
- [x] `uncovered_only=true` yalnızca test'siz requirement'ları döndürüyor
- [x] `critical_uncovered` quality gate çalışıyor

---

### S2-04 · `FDD-F03` · P1 · Effort: M (4-5 gün)

**Fit-Gap Raporu Excel/CSV Export**

| Alan | Değer |
|---|---|
| Dosya | `app/services/export_service.py` (genişlet) |
| Bağımlılıklar | S1-05 (B-01 — veri kaynağı), S2-03 (F-05 — coverage metriği Excel'e dahil) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] İlk fazda PDF çıkar — sadece Excel + CSV (`weasyprint` production riski var)
- [x] Async export eşiği: 200+ requirement → task queue'ya al
- [x] Export temp dosyalarında `tenant_id` path izolasyonu
- [x] "SAP standart template" ibaresi için **hukuki onay önce alınmalı**

**Kabul Kriterleri:**
- [x] Excel dosyası 5 tab içeriyor: Executive Summary, L3 Özet, Req Detay, WRICEF, Config
- [x] `format=csv` requirements CSV olarak indiriliyor
- [x] Tenant isolation korunuyor

---

## 🟢 SPRINT 3 — P1 Tamamlama + P2 Başlangıcı

> **Önkoşul:** S1-04 (B-04 sign-off) tamamlanmış olmalı

---

### S3-01 · `FDD-B02` · P1 · Effort: L (6-8 gün)

**Discover Fazı MVP — ProjectCharter + SystemLandscape + ScopeAssessment**

| Alan | Değer |
|---|---|
| Dosya | `app/models/program.py` (yeni modeller), `app/blueprints/discover_bp.py` (yeni) |
| Bağımlılıklar | S1-04 (B-04 — charter approval sign-off akışından geçecek) |
| Bloke ettiği | S5-05 (I-08 — Stakeholder, Prepare fazı çıktısı) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Charter approval → Discover Gate bağlantısı `gate_service.py`'e ekle
- [x] `SystemLandscape` → `TenantModel`'den türet (şu an belirsiz)
- [x] SAP modül double-entry riski için consistency check notu backlog'a
- [x] I-07 (1YG seed) entegrasyon noktasını FDD'ye not et

**Kabul Kriterleri:**
- [x] `ProjectCharter` oluşturulup onaylanabiliyor
- [x] Charter onaylanmadan Discover Gate geçilemiyor
- [x] `SystemLandscape` kayıtları tenant-scoped
- [x] Navigation'da Discover faz linki görünüyor

---

### S3-02 · `FDD-F04` · P2 · Effort: M (3-4 gün)

**Proje Timeline Görselleştirme — Gantt/Faz Barları**

| Alan | Değer |
|---|---|
| Dosya | `app/blueprints/program_bp.py` (yeni endpoint), `static/js/views/program.js` |
| Bağımlılıklar | **Yok** (model değişikliği yok) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `frappe-gantt` (MIT lisans) seçilmeli — `dhtmlx` ticari lisanslı, kullanılamaz
- [x] Null `start_date`/`end_date` olan fazlar için fallback görünüm tanımla
- [x] Drag-to-reschedule disabled; cursor pointer kaldırılacak

**Kabul Kriterleri:**
- [x] `GET /api/v1/programs/<id>/timeline` phases + gates + sprints döndürüyor
- [x] Geciken fazlar kırmızı renkte
- [x] Bugün çizgisi (today marker) görünüyor

---

### S3-03 · `FDD-F06` · P2 · Effort: M (3-4 gün)

**RACI Matrix UI**

| Alan | Değer |
|---|---|
| Dosya | `app/models/program.py` (RaciEntry), `app/services/governance_service.py`, `app/blueprints/raci_bp.py` |
| Bağımlılıklar | S1-01 (`get_scoped` — `RaciEntry` sorgularında) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `RaciEntry.tenant_id → nullable=False` (kritik açık)
- [x] Accountable uniqueness DB constraint — PostgreSQL partial index araştır, test ortamı farkı belgele
- [x] SAP aktivite template içeriği özgün yazılmalı (SAP IP kopyalanamaz)

**Kabul Kriterleri:**
- [x] Hücre click → R/A/C/I toggle çalışıyor
- [x] Aynı aktiviteye 2 kişi "A" atanamıyor (400 dönüyor)
- [x] Tenant isolation korunuyor

---

### S3-04 · `FDD-F07 Faz A` + `FDD-I05 Faz A` · P2 · Effort: S (1 gün)

**Cloud ALM + Process Mining UI Placeholder — `integrations.js`**

| Alan | Değer |
|---|---|
| Dosya | `static/js/views/integrations.js` |
| Bağımlılıklar | **Yok** (Faz A sadece UI) |
| Bloke ettiği | S4-02 (F-07 Faz B) |

**Yapılacaklar:**
- [x] `integrations.js`'e "SAP Cloud ALM" kartı ekle — "Coming Q2 2026"
- [x] `integrations.js`'e "Process Mining" kartı ekle — aynı card şablonuyla
- [x] `GET /integrations/cloud-alm/sync-log` aktif, `connection_active: false` döndürüyor
- [x] Card şablonu standardize edildi (iki kart aynı component)

---

## 🟠 SPRINT 4 — P2 Tamamlama

> **Önkoşul:** S1-01 + S1-02 (P0 fix) kesinlikle tamamlanmış olmalı

---

### S4-01 · `FDD-B03` · P2 · Effort: L (6-8 gün)

**Run / Hypercare Incident Management MVP**

| Alan | Değer |
|---|---|
| Dosya | `app/models/cutover.py` (genişlet), `app/services/run_sustain_service.py` (genişlet), `app/blueprints/hypercare_bp.py` |
| Bağımlılıklar | S1-01 + S1-02 (P0 tenant fix — **SERT BLOKER**), S3-02 (F-04 timeline — hypercare aynı zaman dilini kullanıyor) |
| Bloke ettiği | S5-03 (I-03 Cutover clock), S6-01 (I-04 KB) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `HypercareIncident.tenant_id` nullable durumunu kontrol et → `nullable=False` yap
- [ ] SLA breach notification — APScheduler vs webhook kararı verilmeli, FDD'ye ekle
- [ ] `Defect` severity ile `HypercareIncident` severity (p1/p2/p3/p4) terminolojisini hizala

**Kabul Kriterleri:**
- [x] Incident oluşturulduğunda priority'ye göre SLA deadline'ları otomatik hesaplanıyor
- [x] SLA ihlalinde `sla_response_breached = True` yazılıyor
- [x] `GET /hypercare/metrics` P1-P4 bazında açık incident sayılarını döndürüyor
- [x] Tenant isolation korunuyor

---

### S4-02 · `FDD-F07 Faz B` · P2 · Effort: L (6-8 gün)

**Cloud ALM — Gerçek OAuth2 + SAP Cloud ALM API Entegrasyonu**

| Alan | Değer |
|---|---|
| Dosya | `app/integrations/alm_gateway.py` (yeni), `app/utils/crypto.py` (yeni/genişlet), `app/models/explore/infrastructure.py` |
| Bağımlılıklar | S3-04 (Faz A tamamlanmış), S1-01 (tenant izolasyonu) |
| Bloke ettiği | S5-02 (ADR-003 gateway pattern referans) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `app/integrations/alm_gateway.py` oluştur — doğrudan `requests` çağrısı yasak
- [x] `app/utils/crypto.py` Fernet şifreleme — `CloudALMConfig.encrypted_secret` için
- [x] Circuit breaker: 5 hata / 1 dakika → 30 saniye bekle
- [x] OAuth2 token cache + refresh gateway içinde (her çağrıda yeni token alma)
- [x] Her push/pull `CloudALMSyncLog`'a: `tenant_id`, `user_id`, `payload_hash`, `response_code`, `latency_ms`

**Kabul Kriterleri:**
- [x] Test connection endpoint OAuth2 token alıyor ve OK döndürüyor
- [x] Push requirements sonrası `external_id` alanları doluyor
- [x] `encrypted_secret` hiçbir API response'da görünmüyor
- [x] Her sync işlemi `CloudALMSyncLog`'a yazılıyor

---

## 🔵 SPRINT 5 — P3 Başlangıcı + ADR'lar

---

### S5-01 · ADR · Effort: S (1 gün)

**I-02 Mimari Genişleme Noktaları Kararı**

| Alan | Değer |
|---|---|
| Çıktı | `docs/plans/ADR-002-sap-auth-concept-extension.md` |
| Bağımlılıklar | **Yok** — Sprint 9'dan önce yazılmazsa API breaking change riski |
| Bloke ettiği | S7-02 (I-02 Auth Concept) |

**Yapılacaklar:**
- [x] `SapAuthRole` vs `AuthRole` adlandırma kararını belgele
- [x] Platform RBAC (`permission_service.py`) ile SAP auth concept ayrımını dokümante et
- [x] SOD matrix için SQLite test mock stratejisini ADR'a ekle

---

### S5-02 · ADR · Effort: S (yarım gün)

**I-05 Gateway Pattern Kararı**

| Alan | Değer |
|---|---|
| Çıktı | `docs/plans/ADR-003-integration-gateway-pattern.md` |
| Bağımlılıklar | S4-02 (F-07 Faz B — ALM gateway pattern referans alınacak) |
| Bloke ettiği | S8-01 (I-05 Faz B) |

**Yapılacaklar:**
- [x] `ProcessMiningGateway` ayrı mı, yoksa unified `IntegrationGateway` mı?
- [x] F-07 `ALMGateway` referans alınarak karar verilecek

---

### S5-03 · `FDD-I03` · P3 · Effort: L (6-8 gün)

**Cutover Clock — War Room Gerçek Zamanlı UI**

| Alan | Değer |
|---|---|
| Dosya | `app/models/cutover.py` (RunbookTask genişlet), `app/services/cutover_service.py`, `static/js/views/cutover.js` |
| Bağımlılıklar | S1-01 (`get_scoped`), S4-01 (B-03 — hypercare modelleri stable) |
| Bloke ettiği | S6-01 (I-04 KB — cutover close entegrasyonu) |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Polling vs SSE kararı infrastructure kısıtlarına göre FDD'ye yaz
- [x] `calculate_critical_path()` içine cycle detection ekle (A → B → A sonsuz döngü riski)
- [x] `delay_minutes` için optimistic locking stratejisi belirle
- [x] `app/ai/assistants/cutover_optimizer.py` → `LLMGateway` kullanımını doğrula

**Kabul Kriterleri:**
- [x] Cutover countdown timer çalışıyor
- [x] War room: workstream columns + critical path görünüyor
- [x] Gecikmiş kritik path task'ları kırmızı
- [x] `GET /live-status` polling/SSE ile frontend güncelleniyor

---

### S5-04 · `FDD-I01` · P3 · Effort: L (4-5 gün)

**Transport / CTS Tracking — Platform-Side Model ve UI**

| Alan | Değer |
|---|---|
| Dosya | `app/models/transport.py` (yeni), `app/services/transport_service.py` (yeni), `app/blueprints/transport_bp.py` (yeni) |
| Bağımlılıklar | S1-05 (B-01 — WRICEF ve ConfigItem canonical model gerekli), S1-01 (`get_scoped`) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] Gerçek CTS API bağlantısı → ilk müşteri pilot'una bırak (SAP Basis erişimi gerekli)
- [x] `TransportRequest.tenant_id → nullable=False`
- [x] Transport number regex: `re.match(r'^[A-Z]{3}K\d{6}$', transport_number)` zorunlu

**Kabul Kriterleri:**
- [x] Transport request CRUD çalışıyor
- [x] BacklogItem → transport atanabiliyor
- [x] Tenant isolation korunuyor

---

### S5-05 · `FDD-I08` · P3 · Effort: M (4-5 gün)

**Stakeholder Management Modülü**

| Alan | Değer |
|---|---|
| Dosya | `app/models/program.py` (Stakeholder yeni), `app/services/stakeholder_service.py` (yeni) |
| Bağımlılıklar | S3-01 (B-02 — Discover fazı tamamlanmış; Stakeholder Prepare fazı çıktısı) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `Stakeholder.tenant_id → nullable=False`
- [x] `influence_level`, `interest_level` için check constraint ekle (sadece `high`/`low`)
- [x] Proje silme → cascade veya anonymization hook (GDPR — kişisel veri)
- [x] TeamMember + Stakeholder overlap için UI birleşik view notu backlog'a

**Kabul Kriterleri:**
- [x] Stakeholder register CRUD çalışıyor
- [x] Influence/Interest matrix görünüyor
- [x] Tenant isolation korunuyor

---

## ⚫ SPRINT 6 — P3 Kapanışı

---

### S6-01 · `FDD-I04` · P3 · Effort: M (4-5 gün)

**Lessons Learned / Knowledge Base**

| Alan | Değer |
|---|---|
| Dosya | `app/models/run_sustain.py` (LessonLearned), `app/services/kb_service.py` (yeni) |
| Bağımlılıklar | S4-01 (B-03 — incident close entegrasyonu), S5-03 (I-03 — cutover close entegrasyonu) |
| Bloke ettiği | — |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `to_dict_public()` metodu ekle — `project_id`, `tenant_id` maskele
- [x] Upvote unique constraint (user + lesson) DB level ekle
- [x] B-02 Discover entegrasyonu (scope assessment → KB öneri) → AI feature olarak Sprint 7+ backlog'a not

**Kabul Kriterleri:**
- [x] Lesson oluşturulabiliyor ve KB'de listeleniyor
- [x] `is_public=True` lesson'lar diğer tenant'lara görünüyor ama hassas alanlar maskelendi
- [x] Incident ve cutover close flow'larında "Add to KB" butonu görünüyor
- [x] Tenant isolation: kendi private lesson'ları başka tenant'a görünmüyor

---

## ✅ SPRINT 7 — Tamamlandı (S7-01, S7-02)

---

### S7-01 · `FDD-I07` · ✅ Tamamlandı · Effort: M+L

**SAP 1YG Process Catalog — Seed Data Yönetimi**

| Alan | Değer |
|---|---|
| Dosya | `app/models/explore/process.py` (L1-L3 Catalog yeni), `scripts/data/seed/seed_sap_knowledge.py` (genişlet) |
| Bağımlılıklar | S3-01 (B-02 — Discover scope assessment ile tutarlı olmalı) |
| **BLOKER** | SAP Best Practices içerik lisansı → **Legal onay Sprint 7 başında alınmalı** |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `L1SeedCatalog`, `L2SeedCatalog`, `L3SeedCatalog` şema detayları — L4 ile tutarlı
- [x] Import akışı idempotent: aynı `process_code` varsa skip
- [x] Seed catalog global (tüm tenant'lara ortak) olarak tanımlanmalı

**Uygulanan ek geliştirmeler:**
- [x] JSON seed data: `fi_ap.json`, `fi_gl.json`, `fi_ar.json`, `fi_aa.json`, `mm_pur.json`, `mm_inv.json` (6 dosya, 56 L4 adımı)
- [x] `process_catalog_service.py` — `load_catalog_from_json`, `get_catalog_tree`, `seed_project_from_catalog`
- [x] Blueprint: `GET /catalog/modules`, `GET /catalog/tree`, `POST /projects/<pid>/seed-from-catalog`
- [x] Frontend: `ExploreAPI.catalog`, Quick Start wizard (boş hierarchy'de gösterilir)
- [x] Migration: `a57ae6490f32` — idempotent CREATE l1/l2/l3_seed_catalog + ALTER l4
- [x] 7 unit test — `tests/test_process_catalog_service.py`, tümü yeşil

---

### S7-02 · `FDD-I02` · ✅ Tamamlandı · Effort: XL

**SAP Authorization Concept Design Modülü**

| Alan | Değer |
|---|---|
| Dosya | `app/models/authorization.py` (yeni), `app/services/auth_concept_service.py` (yeni) |
| Bağımlılıklar | S5-01 (ADR-002 — extension points kararı), S1-05 (B-01 — process step → role bağlantısı) |
| **BLOKER** | SAP security danışmanı input'u zorunlu |

**Düzeltmeler (Reviewer Audit notlarından):**
- [x] `SapAuthRole` adlandırması kullan — platform `Role` modeli ile karışıklık önlenir
- [x] SOD matrix: PostgreSQL partial index → SQLite test mock ekle
- [x] Sprint 9 geçilirse API breaking change riski — ADR-002'de extension point rezerv edilmeli

---

### S8-01 · `FDD-I05 Faz B` · ✅ Tamamlandı · Effort: XL

**Process Mining Gerçek Entegrasyon (Celonis / SAP Signavio)**

| Alan | Değer |
|---|---|
| Dosyalar | `app/models/process_mining.py`, `app/integrations/process_mining_gateway.py`, `app/services/process_mining_service.py`, `app/blueprints/process_mining_bp.py`, `static/js/views/process_mining.js` |
| Migration | `38bd7a7610c9_s8_01_fdd_i05_process_mining.py` — applied |
| Testler | `tests/test_process_mining_service.py` — 15 test, tümü geçti |
| Bağımlılıklar | S5-02 (ADR-003 gateway pattern), S4-02 (F-07 Faz B — ALM gateway referans) |
| **Not** | Faz A (placeholder UI) → Sprint 3'te S3-04 ile birlikte tamamlandı |

**Tamamlananlar:**
- [x] Provider-agnostic `ProcessMiningGateway` — Celonis (API key) ve Signavio (OAuth2) adapter; circuit breaker, retry, timeout
- [x] `ProcessMiningConnection` + `ProcessVariantImport` modelleri; Fernet-encrypted credentials
- [x] Full CRUD servis + variant import → promote/reject workflow
- [x] 11 REST endpoint (`/api/v1/integrations/process-mining` + `/api/v1/projects/<id>/process-mining`)
- [x] 3-sekme SPA — Connection / Import Wizard / Imported Variants
- [x] L4 `ProcessLevel` oluşturma (promote) rule-based (parent L3 + sibling count code)
- [x] Her gateway çağrısı servis katmanında loglanıyor; audit trail için `last_tested_at`, `error_message`

---

## Özet Tablo

| ID | FDD | Öncelik | Sprint | Effort | Bloker mı? | Bağımlılıklar |
|---|---|---|---|---|---|---|
| S1-01 | P0-tenant (get_scoped) | P0 | 1 | S | ✅ Tüm servisler | — |
| S1-02 | P0-tenant (78 servis) | P0 | 1 | M | ✅ B-03 | S1-01 |
| S1-03 | B-01 ADR kararı | P0 | 1 | XS | ✅ F-01/02/03/05 | — |
| S1-04 | B-04 Sign-off | P0 | 1 | M | ✅ B-02 | S1-01 |
| S1-05 | B-01 Migration | P0 | 1 | XL | ✅ F-01/02/05 | S1-03, S1-01 |
| S2-01 | F-01 ConfigItem trace | P1 | 2 | S | ✅ F-02/F-05 | S1-05, S1-01 |
| S2-02 | F-02 Upstream trace | P1 | 2 | S | — | S1-05, S2-01 |
| S2-03 | F-05 Coverage | P1 | 2 | S | ✅ F-03 | S1-05, S2-01 |
| S2-04 | F-03 Export | P1 | 2 | M | — | S1-05, S2-03 |
| S3-01 | B-02 Discover | P1 | 3 | L | ✅ I-08 | S1-04 |
| S3-02 | F-04 Timeline | P2 | 3 | M | ✅ | — |
| S3-03 | F-06 RACI | P2 | 3 | M | — | S1-01 |
| S3-04 | F-07+I-05 Placeholder | P2 | 3 | S | ✅ F-07 Faz B | — |
| S4-01 | B-03 Hypercare | P2 | 4 | L | ✅ I-03, I-04 | S1-02, S3-02 |
| S4-02 | F-07 Faz B | P2 | 4 | L | ✅ ADR-003 | S3-04, S1-01 |
| S5-01 | ADR-002 (I-02) | — | 5 | S | ✅ I-02 | — |
| S5-02 | ADR-003 (I-05) | — | 5 | S | ✅ I-05 Faz B | S4-02 |
| S5-03 | I-03 Cutover clock | P3 | 5 | L | ✅ I-04 | S1-01, S4-01 |
| S5-04 | I-01 Transport | P3 | 5 | L | ✅ FDD-I01 | S1-05, S1-01 |
| S5-05 | I-08 Stakeholder | P3 | 5 | M | ✅ FDD-I08 | S3-01 |
| S6-01 | I-04 KB | P3 | 6 | M | ✅ FDD-I04 | S4-01, S5-03 |
| S7-01 | I-07 1YG Catalog | ✅ Tamamlandı | 7 | M+L | — | S3-01, Legal onay |
| S7-02 | I-02 Auth Concept | ✅ Tamamlandı | 7 | XL | — | S5-01, S1-05 |
| S8-01 | I-05 Faz B | ✅ Tamamlandı | 8 | XL | — | S5-02, S4-02 |

---

> **Son güncelleme:** 2025-07-16 · Sprint 8 COMPLETE (S8-01) · FDD-I05 Phase B — Process Mining Real Integration
