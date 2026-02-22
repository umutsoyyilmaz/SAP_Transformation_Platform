# FDD-B01: Requirement Model Konsolidasyonu

**Öncelik:** P0 — BLOCK (Ürün lansmanını engeller)
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → B-01
**Effort:** XL (3–4 sprint)
**Faz Etkisi:** Explore, Realize, Traceability
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Platformda **iki paralel Requirement sistemi** yaşıyor:

| Sistem | Dosya | Tablo | Durum |
|--------|-------|-------|-------|
| **Eski (Legacy)** | `app/models/requirement.py` | `requirements` | `@deprecated` dokstringleri var, frontend hâlâ aktif |
| **Yeni (Explore)** | `app/models/explore/requirement.py` | `explore_requirements` | Aktif geliştirme, state machine tam |

### Mevcut Sorunlar
1. `static/js/views/` içinde hem `explore_requirements.js` hem de (dolaylı) `requirement.js` var — kullanıcı hangi sistemi kullandığını bilemiyor.
2. `app/services/traceability.py` yalnızca `ExploreRequirement`'ı işliyor; eski `Requirement` modeli traceability dışında.
3. Veri bütünlüğü riski: bazı eski projelerde `requirements` tablosunda veri var, yeni projelerde `explore_requirements` tablosunda — raporlar tutarsız.
4. `app/blueprints/` içinde eski requirement endpoint'leri (`requirement.py` modelini döndürüyor) ile `explore/requirements.py` blueprint'i aynı anda çalışıyor.

---

## 2. İş Değeri

- Traceability raporlarının tek ve güvenilir bir kaynağı olmasını sağlar.
- Enterprise müşterilerin compliance audit'lerde tutarlı veri sunabilmesini sağlar.
- Geliştiricilerin hangi modeli kullandığı konusundaki belirsizliği ortadan kaldırır.
- SAP Cloud ALM / Jira entegrasyonları için tek bir requirement API contract oluşturur.

---

## 3. Hedef Mimari

```
[Tek Requirement Sistemi]
ExploreRequirement (explore_requirements tablosu)
    ↑
    └── Tüm mevcut Requirement (requirements) kayıtları migrate edilir
    └── requirements tablosu RENAME → requirements_legacy (arşiv)
    └── requirement.py modeli deprecated edilir, import'lar kaldırılır
```

### Korunacak Alanlar (`ExploreRequirement`'a eklenmesi gerekenler)
Eski `Requirement` modelinde olup yenide olmayan alanlar:

| Alan | Eski Model | Yeni Model'e Eklenecek mi? |
|------|-----------|--------------------------|
| `req_type` | `business/functional/technical/non_functional/integration` | ✅ Ekle: `requirement_type` |
| `moscow_priority` | `must_have/should_have/could_have/wont_have` | ✅ Ekle: `moscow_priority` |
| `source` | `workshop/stakeholder/regulation/...` | ✅ Ekle: `source` |
| `req_parent_id` (hiyerarşi) | Self-referential FK | ✅ Ekle: `parent_id` |
| `process_id` (L2 bağlantısı) | FK → processes | ⚠️ `process_step_id` (L4) var; L2 → `Process` bağlantısı opsiyonel ekle |
| `external_id` | Jira/SAP ALM ID | ✅ Ekle |

---

## 4. Veri Modeli Değişiklikleri

### 4.1 `ExploreRequirement` Modeli — Eklenen Alanlar
**Dosya:** `app/models/explore/requirement.py`

```python
# Yeni alanlar — mevcut sınıfa ekle
requirement_type = db.Column(
    db.String(32),
    nullable=True,
    default="functional",
    comment="business | functional | technical | non_functional | integration"
)
moscow_priority = db.Column(
    db.String(20),
    nullable=True,
    comment="must_have | should_have | could_have | wont_have (MoSCoW)"
)
source = db.Column(
    db.String(32),
    nullable=True,
    default="workshop",
    comment="workshop | stakeholder | regulation | gap_analysis | standard_process"
)
parent_id = db.Column(
    db.Integer,
    db.ForeignKey("explore_requirements.id", ondelete="SET NULL"),
    nullable=True,
    comment="Epic → Feature → User Story hiyerarşisi için self-referential FK"
)
external_id = db.Column(
    db.String(100),
    nullable=True,
    index=True,
    comment="SAP Cloud ALM / Jira / ServiceNow harici ID"
)
legacy_requirement_id = db.Column(
    db.Integer,
    nullable=True,
    index=True,
    comment="Migration sırasında eski requirements.id — geriye dönük izleme için"
)

# Self-referential relationship
children = db.relationship(
    "ExploreRequirement",
    backref=db.backref("parent", remote_side="ExploreRequirement.id"),
    lazy="select"
)
```

### 4.2 Migration Scripti (Alembic)
```
flask db migrate -m "add moscow_priority and parent_id to explore_requirements"
```

Migration'da yapılacaklar:
1. Yukarıdaki yeni kolonları `explore_requirements` tablosuna ekle.
2. `requirements` tablosunu `requirements_legacy` olarak yeniden adlandır.
3. `requirements_legacy.migrated_at` kolonu ekle.

### 4.3 Data Migration Scripti
**Dosya:** `scripts/migrate_legacy_requirements.py`

Her `Requirement` kaydı için:
1. Aynı `program_id` ve `workshop_id`'ye sahip `Project` bul.
2. `ExploreRequirement` oluştur (alanları eşle).
3. Eski kaydın `id`'sini `legacy_requirement_id`'ye yaz.
4. Eski `RequirementTrace` kayıtlarını yeni `TestCaseTraceLink` formatına dönüştür.

---

## 5. API Değişiklikleri

### 5.1 Kaldırılacak Endpoint'ler (Deprecate + Redirect)
Eski endpoint'leri yeni explore API'ye 301 redirect et — hard-coded silme değil.

| Eski Endpoint | Yeni Endpoint |
|---------------|---------------|
| `GET /api/v1/programs/{prog_id}/requirements` | `GET /api/v1/projects/{proj_id}/explore/requirements` |
| `POST /api/v1/programs/{prog_id}/requirements` | `POST /api/v1/projects/{proj_id}/explore/requirements` |
| `GET /api/v1/requirements/{req_id}` | `GET /api/v1/projects/{proj_id}/explore/requirements/{req_id}` |
| `PUT /api/v1/requirements/{req_id}` | `PUT /api/v1/projects/{proj_id}/explore/requirements/{req_id}` |

### 5.2 `explore/requirements.py` Blueprint — Genişletme
Mevcut blueprint'e eklenecek endpoint'ler:

```python
# Hiyerarşi: alt requirement'ları listele
GET /api/v1/projects/<project_id>/explore/requirements/<req_id>/children

# MoSCoW özet raporu
GET /api/v1/projects/<project_id>/explore/requirements/moscow-summary

# Source bazlı filter (var olan list endpoint'e query param ekle)
GET /api/v1/projects/<project_id>/explore/requirements?source=workshop&moscow=must_have
```

---

## 6. Frontend Değişiklikleri

### 6.1 `static/js/views/explore_requirements.js`
- `moscow_priority` alanı için UI ekle (dropdown + badge rengi: kırmızı/turuncu/mavi/gri).
- `requirement_type` için badge gösterimi ekle.
- Parent-child hiyerarşi için collapsible tree view ekle (basit indent yeter, Gantt değil).
- `source` alanı için filter chip ekle.

### 6.2 `static/js/views/requirement.js` (Eski View)
Dosyayı kaldırma — yerine deprecation notice + redirect linki ekle:
```javascript
// DEPRECATED: Bu view kaldırılacak.
// Yeni URL: /#/projects/{projectId}/explore/requirements
console.warn("Legacy requirement view — lütfen Explore > Requirements kullanın");
window.location.hash = '#/projects/' + projectId + '/explore/requirements';
```

### 6.3 Navigation
Sidebar'daki "Requirements" menü öğesini `explore/requirements` rotasına yönlendir.

---

## 7. Servis Değişiklikleri

### 7.1 `app/services/traceability.py`
`trace_explore_requirement()` fonksiyonu zaten var. Ek olarak:
- `legacy_requirement_id` üzerinden geriye dönük trace desteği ekle.

### 7.2 Eski Requirement Blueprint (`app/blueprints/` altındaki eski dosya)
Eğer `requirements_bp.py` varsa: 301 redirect middleware ekle, yeni blueprint'e yönlendir.

---

## 8. Test Gereksinimleri

### Unit Test — `tests/test_requirement_consolidation.py`
```python
def test_explore_requirement_accepts_moscow_priority():
def test_explore_requirement_accepts_parent_id_self_reference():
def test_explore_requirement_source_field_validates_enum():
def test_legacy_requirement_returns_404_after_deprecation():
def test_legacy_redirect_points_to_explore_requirements():
def test_migration_script_maps_all_legacy_fields_correctly():
def test_migration_preserves_legacy_requirement_id():
```

### Integration Test
```python
def test_traceability_works_for_migrated_requirements():
def test_moscow_summary_endpoint_returns_correct_counts():
def test_tenant_isolation_on_explore_requirements_with_parent():
```

---

## 9. Kabul Kriterleri

- [ ] `requirements` tablosunda yeni kayıt oluşturulamıyor (write-blocked).
- [ ] Tüm `requirements` kayıtları `explore_requirements`'a migrate edildi.
- [x] `traceability.py` yalnızca `ExploreRequirement` modeli üzerinden çalışıyor.
- [ ] `requirement.js` frontend view'ı kaldırıldı / redirect edildi.
- [ ] MoSCoW priority ve parent-child hiyerarşi `explore_requirements.js`'de görünüyor.
- [ ] Mevcut tüm `explore/requirements` testleri geçiyor.
- [ ] Yeni migration scripti çalıştırıldıktan sonra veri bütünlüğü doğrulandı.

---

## 10. Dikkat Edilmesi Gereken Riskler

1. **Veri kaybı riski:** Migration öncesi `requirements` tablosunun tam backup'ı alınmalı.
2. **Foreign key zinciri:** `requirements` tablosuna FK olan tablolar (`backlog_items.requirement_id`, `test_cases.requirement_id` vb.) güncellenmeli — migration script tüm FK'ları güncellemelidir.
3. **Test uyumluluğu:** `tests/` içinde `Requirement` (eski model) kullanan test'ler refactor edilmeli. `grep -r "from app.models.requirement import" tests/` ile tespit edilebilir.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P0 — B-01 · Sprint 1-2 · Effort XL
**Reviewer Kararı:** ⛔ BAŞLAMADAN ÖNCE MİMAR ONAY GEREKLİ

### Tespit Edilen Bulgular

1. **Kritik Bağımlılık — F-01, F-02, F-05 bu FDD'yi bekliyor.**
   Traceability (F-01, F-02) ve coverage raporlama (F-05) FDD'leri doğrudan `ExploreRequirement`'ı canonical kaynak kabul ediyor. B-01 tamamlanmadan bu feature'lar güvenilir şekilde implement edilemez. Sprint planlamada B-01 bloker olarak işaretlenmeli.

2. **Migration script — tüm FK referansları kapsamalı.**
   `backlog_items.requirement_id`, `test_cases.requirement_id` ve diğer FK'lar script içinde güncellenmezse migration sonrası integrity hatası kaçınılmaz. Script idempotent olmalı (birden fazla çalıştırmaya dayanıklı).

3. **Yeni alanlar `nullable=True` başlamalı.**
   `requirement_type`, `moscow_priority`, `source`, `parent_id` — mevcut kayıtlarda boş olacak. `nullable=False` ile başlanırsa Alembic migration fail eder. Constraint'ler sonradan sıkılaştırılmalı.

4. **`static/js/views/requirement.js` kaldırma planı eksik.**
   FDD backend modelin deprecated edilmesini kapsıyor ancak frontend dosyasının akıbeti belirtilmemiş. 301 redirect mi, silme mi? Sprint 2 kapanmadan bu dosya kaldırılmadan merge yapılmamalı.

5. **Test impact ölçümü Sprint 1 başında yapılmalı.**
   `grep -r "from app.models.requirement import" tests/` çalıştır, impacted test sayısını belirle, Sprint planına refactor effort'ı dahil et.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Mimar onayı: ExploreRequirement canonical kararını belgele | Tech Lead | Sprint 1 Öncesi |
| A2 | Migration script — tüm FK referansları güncellenmeli | Coder | Sprint 1 |
| A3 | Tüm yeni `ExploreRequirement` alanları `nullable=True` ile başlat | Coder | Sprint 1 |
| A4 | `requirement.js` kaldırma / redirect planını FDD'ye ekle | Architect | Sprint 1 |
| A5 | Impacted test dosyalarını `grep` ile say, Sprint planına ekle | QA | Sprint 1 |
