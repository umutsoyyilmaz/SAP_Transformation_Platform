# FDD-F03: Fit-Gap Raporu Excel/PDF Export

**Öncelik:** P1
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-03
**Effort:** M (1 sprint)
**Faz Etkisi:** Explore — Workshop çıktısı müşteriye sunumu
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform Fit-Gap analizini tam olarak yapıyor: workshop bazlı, L3/L4 granülüde, requirement sınıflandırmasıyla. Ancak bu verinin **müşteriye sunulabilir formatlarda** dışarı aktarılması mümkün değil.

Mevcut durum:
- API üzerinden JSON olarak Fit-Gap datasına erişilebilir.
- Hiçbir export mekanizması (`export_service.py` var ama kapsam sınırlı).
- Müşteriler/danışmanlar Fit-Gap'i Excel'e manuel kopyalamak zorunda.

---

## 2. İş Değeri

- Steering committee sunumları için hazır çıktı.
- Müşteri design sign-off sürecinde standart formatlı doküman.
- SAP projesinin Design Freeze milestone'unda teslim edilen "Fit-Gap Analysis Document" doğrudan platformdan üretilir.
- Excel formatı: müşteri SAP ekipleri kendi eklentileri için kullanabilir.

---

## 3. Teknik Tasarım

### 3.1 Export Kütüphanesi
- **Excel:** `openpyxl` (zaten büyük ihtimalle `requirements.txt`'te) veya `xlsxwriter`
- **PDF:** `weasyprint` (HTML → PDF) veya `reportlab`
- Öneri: Excel için `openpyxl`, PDF için `weasyprint` (HTML template'den)

```
# requirements.txt'e eklenecekler (yoksa):
openpyxl>=3.1.0
weasyprint>=60.0
```

### 3.2 Yeni Servis: `app/services/export_service.py`
Dosya zaten var → genişlet.

```python
"""
Fit-Gap raporu ve diğer export'lar için servis.

Export formatları: excel | pdf | csv
Fit-Gap raporu Excel yapısı SAP standart Fit-Gap template'i baz alınarak tasarlandı:
  - Tab 1: Executive Summary (özet tablo)
  - Tab 2: L1-L2-L3 Process bazlı Fit-Gap (scope hiyerarşisi)
  - Tab 3: Requirements Listesi (tam detay)
  - Tab 4: WRICEF Listesi (gap olan requirement'lardan türetilmiş)
  - Tab 5: Config Items (fit olan requirement'lardan türetilmiş)
"""

def generate_fitgap_excel(
    project_id: int,
    tenant_id: int,
    include_wricef: bool = True,
    include_config: bool = True,
    classification_filter: list[str] | None = None,
    sap_module_filter: list[str] | None = None,
) -> bytes:
    """
    Standart SAP Fit-Gap raporu Excel dosyası üretir.

    Returns:
        bytes: Excel dosyasının binary içeriği (.xlsx)
    """
    ...


def generate_fitgap_pdf(
    project_id: int,
    tenant_id: int,
    include_executive_summary: bool = True,
    include_wricef: bool = True,
) -> bytes:
    """
    Fit-Gap raporu PDF üretir (HTML template → weasyprint).

    Returns:
        bytes: PDF dosyasının binary içeriği
    """
    ...


def generate_requirement_csv(
    project_id: int,
    tenant_id: int,
    workshop_id: int | None = None,
    classification_filter: list[str] | None = None,
) -> str:
    """
    Requirement listesini CSV olarak döner.
    Hızlı export için sade format.
    """
    ...
```

### 3.3 Excel Dosya Yapısı

**Tab 1: Executive Summary**
| Alan | Değer |
|------|-------|
| Proje Adı | ... |
| Export Tarihi | ... |
| Toplam Requirement | 120 |
| Fit | 40 (%33) |
| Partial Fit | 20 (%17) |
| Gap (WRICEF) | 60 (%50) |
| Toplam WRICEF | 45 |
| - Workflow | 5 |
| - Report | 12 |
| - Interface | 8 |
| - Conversion | 10 |
| - Enhancement | 8 |
| - Form | 2 |
| Toplam Config Item | 38 |

**Tab 2: L3 Süreç Bazlı Özet**
| L1 | L2 | L3 | Fit | Partial | Gap | Total | Gap % |
|----|----|----|-----|---------|-----|-------|-------|
| Finance | Accounts Payable | Invoice Processing | 5 | 2 | 3 | 10 | 30% |
| ...

**Tab 3: Requirement Detay**
| No | Kodu | Başlık | Sınıf | Öncelik | Status | Workshop | SAP Modülü | WRICEF/Config | Açıklama |
|----|------|--------|-------|---------|--------|---------|-----------|--------------|----------|

**Tab 4: WRICEF Listesi**
| WRICEF No | Tip | Başlık | Kaynak Req | Öncelik | Status | SAP Modülü | TS Durumu |
|-----------|-----|--------|-----------|---------|--------|-----------|----------|

**Tab 5: Config Items**
| Config No | Başlık | Kaynak Req | SAP Modülü | IMG Path | Status |
|-----------|--------|-----------|-----------|---------|--------|

### 3.4 PDF Template
**Dosya:** `templates/exports/fitgap_report.html`

Jinja2 template  — şirket logo'su, proje adı, tarih, tablo formatları, sayfa numaraları.

---

## 4. API Endpoint'leri

**Dosya:** `app/blueprints/audit_bp.py` veya yeni `app/blueprints/export_bp.py`

```
GET /api/v1/projects/<project_id>/export/fitgap
    Query params:
      - format: excel | pdf | csv (default: excel)
      - include_wricef: true|false (default true)
      - include_config: true|false (default true)
      - classification: fit,gap,partial_fit (CSV, opsiyonel)
      - sap_module: FI,MM,SD (CSV, opsiyonel)
      - workshop_id: int (opsiyonel — tek workshop export)
    Permission: export.fitgap
    Response Headers:
      Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
      Content-Disposition: attachment; filename="FitGap_<ProjectCode>_<Date>.xlsx"
    Response: Binary file content
```

---

## 5. Frontend Değişiklikleri

### 5.1 `explore_dashboard.js` — Export Butonu
Dashboard sayfasında "Export Fit-Gap Report" butonu:
```
[📥 Export ▾]
  → Excel (.xlsx)
  → PDF (.pdf)
  → Requirements CSV
```

### 5.2 Export Options Modal
Filtreler: Sınıflandırma multi-select, SAP modül multi-select, workshop seçimi.
"Include WRICEF detail" ve "Include Config detail" toggleleri.

### 5.3 `explore_workshop_detail.js`
Her workshop detay sayfasında "Export Bu Workshop Fit-Gap" butonu (workshop_id parametresiyle).

---

## 6. Test Gereksinimleri

```python
# tests/test_export_service.py

def test_generate_fitgap_excel_returns_bytes():
def test_fitgap_excel_contains_5_tabs():
def test_fitgap_excel_executive_summary_correct_counts():
def test_fitgap_excel_filter_by_classification_gap_only():
def test_fitgap_csv_returns_comma_separated_requirements():
def test_export_endpoint_returns_xlsx_content_type():
def test_export_endpoint_returns_correct_filename_header():
def test_export_endpoint_returns_403_without_export_permission():
def test_tenant_isolation_export_blocks_cross_tenant_project():
```

---

## 7. Kabul Kriterleri

- [ ] `GET /export/fitgap?format=excel` çalışıyor, `.xlsx` dosyası indiriliyor.
- [ ] Excel dosyası 5 tab içeriyor: Executive Summary, L3 Özet, Req Detay, WRICEF, Config.
- [ ] `format=pdf` parametresiyle PDF indiriliyor.
- [ ] `format=csv` requirements CSV olarak indiriliyor.
- [ ] `explore_dashboard.js`'deki Export butonu çalışıyor.
- [ ] Classification ve SAP modül filtreleri doğru çalışıyor.
- [ ] Tenant isolation korunuyor.
- [ ] Tüm testler geçiyor.

---

## 8. Bağımlılıklar

- `openpyxl` veya `xlsxwriter` `requirements.txt`'e eklenmiş olmalı.
- `weasyprint` veya PDF kütüphanesi kurulu olmalı.
- Alternatif minimal yaklaşım: PDF yerine ilk fazda sadece Excel + CSV yeterli.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P1 — F-03 · Sprint 2 · Effort M
**Reviewer Kararı:** 🟡 ONAYLANIR — Kütüphane seçimi Sprint 2 başında kesinleştirilmeli

### Tespit Edilen Bulgular

1. **`weasyprint` — ağır bağımlılık, production risk.**
   `weasyprint` sistem-level bağımlılıkları var (Pango, Cairo, GLib). Railway/Docker ortamında bu kütüphane production'da sorun çıkarabilir. Railway'in buildpack'i bu bağımlılıkları otomatik çözmez. İlk fazda PDF yerine sadece Excel + CSV ile başlamak (FDD §8'deki alternatif öneri) daha güvenli.

2. **Export async mı sync mı?**
   Büyük projeler için Excel export birkaç saniye sürebilir (100+ requirement, 5 Excel tab). Sync endpoint ile 30s timeout riski var. FDD bu konuda sessiz. Başlangıçta sync kabul edilebilir ama 200+ requirement eşiğinin üzerinde async task queue'ya alınmalı.

3. **`export_service.py` içinde tenant isolation.**
   Export fonksiyonları `project_id + tenant_id` ile scope'lanmalı. `os.path` / temp file kullanılıyorsa dosya adında `tenant_id` olmalı — farklı tenant'ların export dosyaları hiçbir zaman aynı tmp path'i paylaşmamalı.

4. **SAP IP lisans riski — içerik kürasyonu.**
   Excel template'inin SAP standart Fit-Gap template'i baz alındığı belirtilmiş. SAP marka/format içeriği lisans gerektiriyor olabilir. Hukuki onay alınmadan "SAP standard" ibaresi kullanılmamalı.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | İlk fazda PDF'i çıkar, sadece Excel + CSV ile başla | Architect | Sprint 2 |
| A2 | Async export eşiği ve task queue stratejisini FDD'ye ekle | Architect | Sprint 2 |
| A3 | Export temp dosyalarında `tenant_id` path izolasyonu ekle | Coder | Sprint 2 |
| A4 | "SAP standart template" ibaresi için hukuki onay al | PM | Sprint 2 |
