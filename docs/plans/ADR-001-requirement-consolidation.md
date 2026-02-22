# ADR-001: Requirement Model Konsolidasyonu — ExploreRequirement Canonical

**Durum:** ✅ Onaylandı  
**Tarih:** 2026-02-22  
**Yazar:** Umut Soyyılmaz  
**İlgili FDD:** `FDD-B01-requirement-model-consolidation.md`  
**Bloke Ettiği Sprint İtemleri:** S1-05, S2-01, S2-02, S2-03, S2-04, S5-04  
**Kapsam:** `Requirement`, `ExploreRequirement`, traceability, backlog, testing model katmanı

---

## 1. Karar Özeti

| # | Karar | Gerekçe |
|---|-------|---------|
| **D1** | `ExploreRequirement` **tek canonical requirement kaynağı** olarak belirlendi | Traceability, coverage raporlama ve SAP Activate workflow tam state machine'e sahip |
| **D2** | Legacy `requirements` tablosu `requirements_legacy` olarak rename edilecek, **yazma kapatılacak** | Veri bütünlüğü ve audit izlenebilirliği — silme değil, arşivleme |
| **D3** | `backlog.py` ve `testing.py` modellerindeki ikili FK (`requirement_id` + `explore_requirement_id`) `explore_requirement_id` tek FK'a indirilecek | Mevcut çift FK durumu Option B'nin ad-hoc uygulaması — kontrol dışı teknik borç |
| **D4** | `FDD-B01 §3`'deki eksik alanlar (`moscow_priority`, `requirement_type`, `source`, `parent_id`, `external_id`, `legacy_requirement_id`) `ExploreRequirement` modeline eklenecek | Legacy modelden feature parity sağlanması zorunlu, aksi hâlde migration kayıpsız yapılamaz |

**Seçilen Yol:** Option A — Tam Konsolidasyon (phased, 3 sprint)

---

## 2. Bağlam — Neden Karar Gerekti

Platformda **iki paralel Requirement sistemi** mevcuttu:

| Sistem | Model | Tablo | PK Tipi | Durum |
|--------|-------|-------|---------|-------|
| Legacy | `app/models/requirement.py` | `requirements` | `INTEGER` | `@deprecated` docstring var; frontend hâlâ aktif |
| Yeni | `app/models/explore/requirement.py` | `explore_requirements` | `UUID (String)` | Aktif geliştirme; tam state machine |

### Codebase Kanıtları (2026-02-22 tarihli audit)

**Sorun 1 — İkili FK proliferasyonu (ad-hoc bridge pattern)**

`app/models/backlog.py` ve `app/models/testing.py` modelleri aynı anda her iki sisteme FK tutuyor:

```python
# app/models/backlog.py:152,157 — BacklogItem (her iki FK var)
requirement_id = db.Column(db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"), ...)
explore_requirement_id = db.Column(db.String(36), db.ForeignKey("explore_requirements.id", ...), ...)

# app/models/testing.py:385,390 — TestCase (her iki FK var)
requirement_id = db.Column(db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"), ...)
explore_requirement_id = db.Column(db.String(36), db.ForeignKey("explore_requirements.id", ...), ...)
```

Bu durum Option B'nin (bridge pattern) zaten ve kontrolsüz biçimde hayata geçirildiğini gösteriyor.
Sonuç: traceability sorguları her iki FK'yı kontrol etmek zorunda kalıyor, raporlar tutarsız.

**Sorun 2 — 12 servis / blueprint dosyası legacy modeli import ediyor**

```
grep -rn "from app.models.requirement import" app/
  app/services/test_planning_service.py       (3 import)
  app/services/traceability.py                (2 import)
  app/services/spec_template_service.py       (1 import)
  app/services/testing_service.py             (1 import)
  app/ai/assistants/test_case_generator.py    (1 import)
  app/ai/assistants/requirement_analyst.py    (1 import)
  app/ai/assistants/change_impact.py          (1 import)
  app/blueprints/testing_bp.py                (1 import)
```

`traceability.py` zaten S1-02'de ExploreRequirement'a geçirildi. Kalan 7 dosya S1-05'in konusu.

**Sorun 3 — `scope.py:RequirementProcessMapping` tablosu legacy FK tutuyor**

```python
# app/models/scope.py:249
db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE")
```

L3 process mapping traceability için kritik — ExploreRequirement'a taşınması gerekiyor.

**Sorun 4 — Frontend dual-path**

`static/js/views/requirement.js` legacy modeli çağırıyor.
`static/js/views/explore_requirements.js` yeni modeli kullanıyor.
Kullanıcı hangi veriye baktığını bilemiyor; raporlarda kayıt eksikliği.

---

## 3. Değerlendirilen Seçenekler

### Option A — Tam Konsolidasyon (ExploreRequirement Canonical)

**Ne yapılır:**
1. `ExploreRequirement` modeline eksik alanlar eklenir (FDD-B01 §4.1).
2. Tüm `requirements` tablosu kayıtları `explore_requirements`'a idempotent migration scripti ile taşınır.
3. `requirements` tablosu `requirements_legacy` olarak rename edilir; yeni yazma kapatılır.
4. Tüm `requirement_id` (legacy int FK) kolonları `explore_requirement_id` UUID FK ile değiştirilir.
5. Legacy import'lar kaldırılır; `ExploreRequirement` import edilerek yerini alır.
6. Frontend `requirement.js` → redirect + deprecation notice, `explore_requirements.js` tek giriş noktası.

**Artılar:**
- Tek canonical kaynak → traceability, coverage, ALM entegrasyonları tutarlı.
- İkili FK karmaşasına son verir.
- F-01, F-02, F-05 FDD'leri blokerdan çıkar.
- Service katmanı daha az koşul dalı → daha az bug.

**Eksiler:**
- Data migration riski (backup zorunlu).
- 12 dosyada refactor gerekiyor.
- UUID ↔ Integer PK tipi dönüşümü dikkat gerektiriyor.
- XL effort: 3-4 sprint.

---

### Option B — Bridge Pattern (Adapter Katmanı)

**Ne yapılır:**
1. Her iki model korunur.
2. `RequirementAdapter` servisi yazılır; hangi modelden okuyacağını çağrı bazında karar verir.
3. Raporlama servisleri her iki tabloyu UNION ile sorgular.

**Artılar:**
- Sıfır data migration riski.
- Kısa vadede düşük efor.

**Eksiler:**
- **Bu durum zaten codebaseda var ve sorunlara yol açıyor** (bkz. §2 Sorun 1).
- Zamanla üçüncü bir model çıkabilir; bridge karmaşıklaşır.
- `UNION` sorguları heterogen PK tiplerini (int vs uuid) yönetmek zorunda.
- F-01, F-02, F-05 FDD'leri ya sonsuz erktelenir ya da bridge üzerinde kırılgan implement edilir.
- Enterprise compliance audit'lerde "hangi sistemden veri?" sorusu yanıtsız kalır.

**Karar: Option B reddedildi.** Codebase analizi bu yaklaşımın zaten uygulandığını ve yukarıdaki sorunları ürettiğini kanıtlıyor. Devam etmek teknik borcu katlamak demek.

---

## 4. Uygulama Planı (Phased)

### Faz 1 — Model Hazırlığı (S1-05, ~2 gün)
Önkoşul: Bu ADR onayı.

- [ ] `ExploreRequirement` modeline FDD-B01 §4.1 alanlarını ekle (`moscow_priority`, `requirement_type`, `source`, `parent_id`, `external_id`, `legacy_requirement_id`) — tümü `nullable=True`
- [ ] `flask db migrate -m "add moscow_priority parent_id and legacy fields to explore_requirements"`
- [ ] Migration'ı review et, `flask db upgrade` çalıştır
- [ ] `requirements` tablosuna `migrated = db.Column(db.Boolean, default=False)` ekle (migration tracking)

### Faz 2 — Data Migration (S2-01, ~3 gün)
Önkoşul: Faz 1 tamamlandı, production backup alındı.

- [ ] `scripts/migrate_legacy_requirements.py` yaz (idempotent)
  - Her `Requirement` kaydı için eşleşen `ExploreRequirement` oluştur
  - `legacy_requirement_id` alanına eski `requirements.id` yaz
  - `backlog_items.requirement_id` → `backlog_items.explore_requirement_id` güncelle
  - `test_cases.requirement_id` → `test_cases.explore_requirement_id` güncelle
  - `RequirementProcessMapping` kayıtlarını `ExploreRequirement` FK'a güncelle
- [ ] Script idempotency testi: iki kez çalıştırıldığında duplicate oluşmamalı
- [ ] `requirements` tablosunu `requirements_legacy` olarak rename et
- [ ] `requirements_legacy.migrated_at` kolonu ekle

### Faz 3 — Kod Refactor (S2-02, ~3 gün)
Önkoşul: Data migration doğrulandı.

- [ ] 12 service/blueprint dosyasındaki `from app.models.requirement import Requirement` → `ExploreRequirement` ile değiştir
- [ ] `backlog.py`: `requirement_id` INTEGER FK kolonunu kaldır (migration'dan sonra)
- [ ] `testing.py`: `requirement_id` INTEGER FK kolonunu kaldır
- [ ] `scope.py:RequirementProcessMapping` → `explore_requirement_id` FK kullan
- [ ] `requirement.js` frontend: deprecation notice + redirect ekle
- [ ] Tüm etkilenen test dosyalarını güncelle (`grep -r "from app.models.requirement import" tests/`)

### Faz 4 — Temizlik (S2-03, ~1 gün)
Önkoşul: Faz 3 testleri geçiyor.

- [ ] `requirement.py` modeline `@deprecated` flag'ını güçlendir, yorum ekle: "READ-ONLY arşiv"
- [ ] Legacy blueprint endpoint'lerini 301 redirect middleware ile `explore/requirements` adresine yönlendir
- [ ] `requirement.js` view'ı sil (ya da nihai redirect'e dönüştür)
- [ ] Eski `requirements_legacy` tablosunu okuma dışı kullanım için kilitle (uygulama katmanında)

---

## 5. Etkilenen Dosyalar

### Model Katmanı
| Dosya | Değişiklik | Faz |
|-------|-----------|-----|
| `app/models/explore/requirement.py` | 6 alan eklenir (`moscow_priority`, `requirement_type`, `source`, `parent_id`, `external_id`, `legacy_requirement_id`) | F1 |
| `app/models/requirement.py` | `migrated` kolonu ekle; F4'te read-only | F1/F4 |
| `app/models/backlog.py` | `requirement_id` INT FK kaldırılır | F3 |
| `app/models/testing.py` | `requirement_id` INT FK kaldırılır | F3 |
| `app/models/scope.py` | `RequirementProcessMapping.requirement_id` → UUID FK | F3 |

### Servis / Blueprint Katmanı
| Dosya | Değişiklik | Faz |
|-------|-----------|-----|
| `app/services/test_planning_service.py` | Legacy import → ExploreRequirement | F3 |
| `app/services/testing_service.py` | Legacy import → ExploreRequirement | F3 |
| `app/services/spec_template_service.py` | Legacy import → ExploreRequirement | F3 |
| `app/services/traceability.py` | Kısmen zaten ExploreRequirement (S1-02); legacy trace backup kaldırılır | F3 |
| `app/blueprints/testing_bp.py` | Legacy import → ExploreRequirement | F3 |
| `app/ai/assistants/test_case_generator.py` | Legacy import → ExploreRequirement | F3 |
| `app/ai/assistants/requirement_analyst.py` | Legacy import → ExploreRequirement | F3 |
| `app/ai/assistants/change_impact.py` | Legacy import → ExploreRequirement | F3 |

### Migration / Script
| Dosya | Değişiklik | Faz |
|-------|-----------|-----|
| `migrations/versions/*.py` | Yeni Alembic revision (F1 + F2 için ayrı) | F1, F2 |
| `scripts/migrate_legacy_requirements.py` | Yeni data migration scripti (idempotent) | F2 |

### Frontend
| Dosya | Değişiklik | Faz |
|-------|-----------|-----|
| `static/js/views/explore_requirements.js` | MoSCoW badge, parent-child tree, source filter | F3 |
| `static/js/views/requirement.js` | Deprecation + redirect | F3/F4 |

---

## 6. Riskler ve Azaltma

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Data migration sırasında kayıt kaybı | Orta | Yüksek | Production backup zorunlu; idempotent script; test ortamında dry-run |
| UUID ↔ Integer traceability kırılması | Düşük | Yüksek | `legacy_requirement_id` alanı her zaman eski ID'yi tutar; geriye dönük lookup mümkün |
| `nullable=True` ile başlayan alanlar validation boşluğu yaratır | Düşük | Orta | F3 sonrası `nullable=False` constraint'i sıkılaştırmak için ayrı migration planla |
| Frontend redirect müşteri workflow'unu bozar | Orta | Orta | Kullanıcı bilgilendirmesi + 301 redirect (hard delete değil) |
| Test dosyalarında legacy Requirement import'ları gözden kaçar | Düşük | Düşük | `grep -r "from app.models.requirement import" tests/` CI check'e ekle |

---

## 7. Kabul Kriterleri (Tüm Fazlar Tamamlandığında)

- [ ] `requirements` tablosunda yeni kayıt oluşturulamıyor (write-blocked uygulama katmanında).
- [ ] Tüm `requirements` kayıtları `explore_requirements`'a taşındı; veri bütünlüğü doğrulandı.
- [ ] `backlog_items` ve `test_cases` tablolarında `requirement_id` (legacy int FK) kolonu yok.
- [ ] `traceability.py` yalnızca `ExploreRequirement` modeli üzerinden çalışıyor.
- [ ] `requirement.js` frontend view'ı redirect edildi veya kaldırıldı.
- [ ] MoSCoW priority ve parent-child hiyerarşisi `explore_requirements.js`'de görünüyor.
- [ ] Mevcut tüm test'ler (`tests/`) geçiyor.
- [ ] F-01, F-02, F-05 FDD'leri artık tek canonical kaynağa dayandığı için implement edilebilir.

---

## 8. Onay Kaydı

| Rol | İsim | Tarih | Karar |
|-----|------|-------|-------|
| Tech Lead / Architect | Umut Soyyılmaz | 2026-02-22 | ✅ Option A Onaylandı |

**Not:** Bu ADR imzalandı. S1-05, S2-01, S2-02, S2-03 sprint item'ları bu karar temel alınarak uygulanacak.
