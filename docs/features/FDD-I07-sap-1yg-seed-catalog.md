# FDD-I07: SAP 1YG Process Catalog — Seed Data Yönetimi

**Öncelik:** Backlog
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-07
**Effort:** M+L (teknik 1 sprint + içerik kürasyonu 1 sprint)
**Faz Etkisi:** Explore — L1-L4 Süreç Hiyerarşisi Bootstrap
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform'da `L4SeedCatalog` modeli (`app/models/explore/process.py`) mevcut ama:
- L1, L2, L3 düzeylerinde seed catalog modeli yok — yalnızca L4 var.
- Catalog'dan projeye otomatik import akışı yok.
- SAP Best Practices içeriği (SAP Activate Scope Items) platforma girilmemiş.

Mevcut durum: Her proje açıldığında danışman L1→L4 hiyerarşisini sıfırdan elle doldurur.
Hedef: Seçilen SAP modüllerine göre katalogdan tek tıkla standart süreç hiyerarşisi oluşturulsun.

---

## 2. İş Değeri

- Explore Workshop Workshop hazırlığı için L4 adımları birkaç saatte değil birkaç dakikada oluşturulur.
- SAP Best Practices baseline ile başlanır, proje özeline göre özelleştirilir.
- Tutarlılık: Farklı danışmanlar aynı naming convention ile çalışır.
- Quality gate: Katalogdaki L4 adımları "known scope" olarak işaretlenebilir.

---

## 3. Mevcut Model Durumu

`app/models/explore/process.py`:
```python
class L4SeedCatalog(db.Model):
    __tablename__ = "l4_seed_catalog"
    id, sap_module, process_code, process_name, description, typical_wricef_type,
    complexity_hint, data_migration_typical, source_system
```

Eksik: `L1SeedCatalog`, `L2SeedCatalog`, `L3SeedCatalog` — tam hiyerarşi yok.

---

## 4. Veri Modeli

### 4.1 Yeni Modeller: `app/models/explore/process.py` içine ekle

```python
class L1SeedCatalog(db.Model):
    """
    SAP Süreç Kataloğu — Seviye 1 (İş Alanı).
    Örn: "Finansal Yönetim", "Tedarik ve Satın Alma", "Satış Yönetimi"

    Bu veri tüm tenant'lara ortaktır — tenant_id yok.
    Kaynak: SAP Activate Best Practices Catalog, S/4HANA 2023.
    """
    __tablename__ = "l1_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False, unique=True,
                     comment="Örn: L1-FI")
    name = db.Column(db.String(200), nullable=False)
    sap_module_group = db.Column(db.String(50), nullable=False,
                                  comment="FI_CO | MM_WM | SD_CS | HR | BASIS | ...")
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    children = db.relationship("L2SeedCatalog", back_populates="parent_l1",
                                lazy="select", order_by="L2SeedCatalog.sort_order")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class L2SeedCatalog(db.Model):
    """
    SAP Süreç Kataloğu — Seviye 2 (Süreç Grubu).
    Örn: "Accounts Payable", "Accounts Receivable", "General Ledger"
    """
    __tablename__ = "l2_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    parent_l1_id = db.Column(db.Integer, db.ForeignKey("l1_seed_catalog.id",
                                                         ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(15), nullable=False, unique=True,
                     comment="Örn: L2-FI-AP")
    name = db.Column(db.String(200), nullable=False)
    sap_module = db.Column(db.String(10), nullable=False, comment="FI, MM, SD, ...")
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_s4_mandatory = db.Column(db.Boolean, nullable=False, default=False,
                                 comment="S/4HANA migration'da zorunlu mu?")

    parent_l1 = db.relationship("L1SeedCatalog", back_populates="children")
    children = db.relationship("L3SeedCatalog", back_populates="parent_l2",
                                lazy="select", order_by="L3SeedCatalog.sort_order")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class L3SeedCatalog(db.Model):
    """
    SAP Süreç Kataloğu — Seviye 3 (Süreç).
    Örn: "Vendor Invoice Processing", "Payment Run", "Period End Closing"
    """
    __tablename__ = "l3_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    parent_l2_id = db.Column(db.Integer, db.ForeignKey("l2_seed_catalog.id",
                                                         ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False, unique=True,
                     comment="Örn: L3-FI-AP-01")
    name = db.Column(db.String(200), nullable=False)
    sap_scope_item_id = db.Column(db.String(20), nullable=True,
                                   comment="SAP Activate Scope Item ID: J45, BKC, ...")
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    typical_complexity = db.Column(db.String(10), nullable=True,
                                    comment="low | medium | high")

    parent_l2 = db.relationship("L2SeedCatalog", back_populates="children")
    l4_steps = db.relationship("L4SeedCatalog", back_populates="parent_l3",
                                lazy="select", order_by="L4SeedCatalog.sort_order")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 4.2 `L4SeedCatalog` Güncellemesi

```python
# Mevcut L4SeedCatalog modeline EKLENECEKler:
parent_l3_id = db.Column(db.Integer, db.ForeignKey("l3_seed_catalog.id",
                          ondelete="SET NULL"), nullable=True, index=True)
sort_order = db.Column(db.Integer, nullable=False, default=0)
is_customer_facing = db.Column(db.Boolean, nullable=False, default=False)
typical_fit_decision = db.Column(db.String(20), nullable=True,
                                  comment="fit | partial_fit | gap — SAP best practice tahmini")
# Back-reference:
parent_l3 = db.relationship("L3SeedCatalog", back_populates="l4_steps")
```

### 4.3 Seed Data Dosyaları

```
app/data/sap_process_catalog/
  fi_ap.json    # FI-AP L1→L4 hierarchy
  fi_ar.json
  fi_gl.json
  fi_aa.json    # Asset Accounting
  mm_pur.json   # Purchasing
  mm_inv.json   # Inventory Management
  sd_ord.json   # Order Management
  sd_bil.json   # Billing
  co_cca.json   # Cost Center Accounting
  co_pca.json   # Profit Center Accounting
  pp_sfg.json   # Production planning (optional)
```

**Örnek `fi_ap.json` yapısı:**
```json
{
  "l1": {"code": "L1-FI", "name": "Financial Management", "sap_module_group": "FI_CO"},
  "l2": {"code": "L2-FI-AP", "name": "Accounts Payable", "sap_module": "FI"},
  "l3_list": [
    {
      "code": "L3-FI-AP-01",
      "name": "Vendor Invoice Processing",
      "sap_scope_item_id": "J45",
      "l4_list": [
        {
          "code": "L4-FI-AP-01-01",
          "process_name": "Post incoming vendor invoice (MIRO)",
          "typical_wricef_type": null,
          "typical_fit_decision": "fit",
          "complexity_hint": "low"
        }
      ]
    }
  ]
}
```

### 4.4 Migration
```
flask db migrate -m "add l1_l2_l3_seed_catalog tables, extend l4_seed_catalog"
```

---

## 5. Servis Katmanı

### 5.1 Mevcut / Yeni: `app/services/process_catalog_service.py`

```python
def load_catalog_from_json(json_file_path: str) -> dict:
    """
    JSON katalog dosyasını parse eder.
    Mevcut kayıtları günceller (upsert by code), eksikleri ekler.
    Idempotent — birden çok çalıştırılabilir.
    """

def get_catalog_modules() -> list[dict]:
    """Mevcut L1 gruplarını ve L2 modüllerini listeler."""

def get_catalog_tree(sap_module: str | None = None) -> list[dict]:
    """L1 → L2 → L3 → L4 tam ağacı, opsiyonel modül filtresi ile."""

def seed_project_from_catalog(
    tenant_id: int,
    project_id: int,
    analysis_id: int,
    selected_modules: list[str],
    importer_id: int
) -> dict:
    """
    Seçilen SAP modülleri için kataloğu ProjectLevel instance'larına dönüştürür.

    L1SeedCatalog → ProcessLevel(level=1)
    L2SeedCatalog → ProcessLevel(level=2)
    L3SeedCatalog → ProcessLevel(level=3)
    L4SeedCatalog → ProcessStep

    Mevcut L1/L2/L3 kodu varsa skip eder (idempotent).

    Returns:
        {
          "created": {"l1": 2, "l2": 5, "l3": 18, "l4": 120},
          "skipped": {"l1": 0, "l2": 1, "l3": 2, "l4": 15},
          "elapsed_ms": 450
        }
    """
```

### 5.2 CLI Komutu: `scripts/seed_sap_catalog.py`

```python
# Kullanım:
# python scripts/seed_sap_catalog.py --module FI --module MM
def main():
    for module in selected_modules:
        load_catalog_from_json(f"app/data/sap_process_catalog/{module.lower()}.json")
```

---

## 6. API Endpoint'leri

**Dosya:** `app/blueprints/explore/process_bp.py` içine ekle

```
# Katalog Browsing
GET    /api/v1/explore/catalog/modules
       Response: L1 grupları + L2 modülleri + step sayıları

GET    /api/v1/explore/catalog/tree?module=FI
       Response: Tam L1→L4 ağacı (module filtresi opsiyonel)

# Proje Import
POST   /api/v1/projects/<proj_id>/explore/seed-from-catalog
       Body: {
         "analysis_id": 1,
         "modules": ["FI", "MM"]
       }
       Permission: explore.edit
       Response: seed_project_from_catalog() çıktısı
```

---

## 7. Frontend Değişiklikleri

### 7.1 `explore_hierarchy.js` Genişletme — Seed Wizard

**"Hızlı Başlat" Butonu** (Boş proje L1 listesi yoksa görünür):
```
Proje süreç hiyerarşisi henüz boş.
[🌱 SAP Katalogdan Başlat]
```

**Wizard Modalı:**
```
SAP Katalogdan Süreç Hiyerarşisi Oluştur

Adım 1: Modül Seçimi
  ☑ FI — Financial Management (45 L4 adım)
  ☑ MM — Materials Management (38 L4 adım)
  ☐ SD — Sales & Distribution (52 L4 adım)
  ☐ CO — Controlling (30 L4 adım)
  ☐ PP — Production Planning (28 L4 adım)

Seçilen: 83 L4 adım, 12 L3 süreç, 8 L2 grup oluşturulacak

Adım 2: Özet & Onay
  ⚠️ Mevcut hiyerarşiniz korunacak (duplicate skip edilir).

  [İptal]  [Kataloğu İçe Aktar ✅]
```

**Başarı Bildirimi:**
```
✅ 83 L4 adım, 18 L3 süreç oluşturuldu (15 mevcut skip edildi). [Hiyerarşiyi Gör]
```

---

## 8. Test Gereksinimleri

```python
def test_load_catalog_from_json_creates_l1_l2_l3_l4_records():
def test_load_catalog_is_idempotent_second_run_no_duplicates():
def test_seed_project_creates_process_levels_and_steps():
def test_seed_project_skips_existing_matching_codes():
def test_get_catalog_tree_filters_by_module():
def test_seed_project_returns_created_and_skipped_counts():
def test_seed_project_tenant_isolation():
```

---

## 9. Kabul Kriterleri

- [ ] L1, L2, L3 seed catalog tabloları oluşturuldu.
- [ ] FI ve MM için JSON katalog dosyaları hazır ve `load_catalog_from_json()` çalışıyor.
- [ ] `seed_project_from_catalog()` L1→L4 hiyerarşiyi ProjectLevel + ProcessStep'e dönüştürüyor.
- [ ] Duplicate skip çalışıyor (idempotent).
- [ ] `POST /explore/seed-from-catalog` endpoint çalışıyor.
- [ ] Explore hierarchy view'ında seed wizard görünüyor ve çalışıyor.
- [ ] Tenant isolation korunuyor (global catalog → tenant'a kopyala pattern).


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** Backlog — I-07 · Sprint 7 · Effort M+L
**Reviewer Kararı:** 🔵 KABUL EDİLİR — İçerik lisans riski Sprint 7'de çözülmeli

### Tespit Edilen Bulgular

1. **SAP Best Practices içerik lisansı — kritik risk.**
   SAP Activate content (Scope Items, Best Practice konfigürasyonları) SAP'ın ticari içeriğidir. Platformda verbatim kopyalanamaz. Seed içeriği SAP terminolojisi kullanılarak özgün yazılmalı ya da SAP'tan lisans alınmalı. Bu konuda hukuki onay olmadan Sprint 7'de katalog içeriği eklenememeli.

2. **`L1SeedCatalog`, `L2SeedCatalog`, `L3SeedCatalog` — 3 yeni model.**
   FDD'de bu modellerin şema detayı eksik. `L4SeedCatalog` ile tutarlı alan yapısı olmalı. Tüm seed catalog modelleri `db.Model`'den (global, tenant-bağımsız) mı miras almalı? Seed data tüm tenant'lara ortak mı, tenant-specific mi? Bu karar FDD'ye eklenmeli.

3. **Katalog → Proje import akışı — idempotency.**
   "Tek tıkla import" iki kez çalıştırılırsa duplicate process level oluşur. Import akışı idempotent olmalı: aynı `process_code` varsa skip et, yoksa ekle.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | SAP Best Practices içerik lisans onayını Sprint 7 başında al | PM / Legal | Sprint 7 |
| A2 | `L1-L3SeedCatalog` şema detaylarını FDD'ye ekle (L4 ile tutarlı) | Architect | Sprint 7 |
| A3 | Import akışına idempotency kontrolü ekle (`process_code` unique check) | Coder | Sprint 7 |
| A4 | Seed catalog'un global (tüm tenant'lara ortak) olduğunu FDD'ye yaz | Architect | Sprint 7 |
