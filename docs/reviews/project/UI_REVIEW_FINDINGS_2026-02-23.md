# UI Review Findings (Wave 1)

**Tarih:** 2026-02-23  
**Kapsam:** `static/js/views/*`, `static/js/app.js`, `static/css/main.css`  
**Referans Plan:** `docs/reviews/project/UI_REVIEW_PLAN_EXTENDED.md`

## Ozet Metrikler

- `class="table"` kullanim sayisi: **17** (6 dosya)
- Bootstrap-benzeri utility/class kullanimlari (`table-sm`, `table-hover`, `col-md-6`, `text-end`): **mevcut**, ancak app CSS'inde tanim yok
- Hardcoded hex renk kullanimi (view dosyalari): **706**
- Tablo a11y etiketi (`<caption>`, table `aria-label`, `role="table"`): **0**

## Remediation Update (2026-02-23)

- [Done] **Cutover modal standardizasyonu**: custom DOM modal kaldirildi, `App.openModal()` + `App.closeModal()` desenine tasindi (`static/js/views/cutover.js`).
- [Done] **Custom style injection kaldirildi**: `fiori-field`/`fiori-row` stilleri JS icinden cikartilip `main.css`'e tasindi (`static/css/main.css`).
- [Done] **Undefined token duzeltmeleri (P0 kapsam)**:
  - `var(--text-secondary)` -> `var(--sap-text-secondary)`
  - `var(--text-primary)` -> `var(--sap-text-primary)`
  - `var(--border)` -> `var(--sap-border)`
  - `var(--bg-secondary)` -> `var(--sap-bg)`
  - Uygulanan dosyalar: `static/js/views/program.js`, `static/js/views/timeline.js`, `static/js/views/integrations.js`, `static/css/main.css`
- [Done] **Header standardizasyonu (P1 parcali)**:
  - `view-header` -> `pg-view-header`
  - Uygulanan dosyalar: `static/js/views/ai_admin.js`, `static/js/views/hypercare.js`
- [Done] **Bootstrap-bagli tablo/layout class migration (P1 parcali)**:
  - `table table-sm table-hover table-bordered` -> `data-table`
  - `col-md-6` / `text-end` layouti -> app-uyumlu flex/inline
  - Uygulanan dosyalar: `static/js/views/authorization.js`, `static/js/views/transports.js`, `static/js/views/cutover.js`
- [Done] **Bootstrap kalinti temizligi (P1 devam)**:
  - `nav-tabs/nav-link`, `btn-outline-*`, `bg-*`, `progress/progress-bar`, `row/col-*` kaliplari hedef dosyalardan kaldirildi.
  - Toast/tab/badge davranislari app-standard desenlerine tasindi.
  - Uygulanan dosyalar: `static/js/views/authorization.js`, `static/js/views/transports.js`, `static/js/views/cutover.js`
- [Done] **Kalan `class="table"` temizligi (P2 parcali)**:
  - Kalan 9 kullanim `data-table` ile degistirildi.
  - Tablolara ek `aria-label` eklendi (ai_insights, raid, timeline).

## Bulgular (Severity Sirasi)

### 1. [Critical] Cutover modal standard disi ve event listener sizintisi riski

- **Kanit:** `static/js/views/cutover.js:613`, `static/js/views/cutover.js:661`, `static/js/views/cutover.js:669`, `static/js/views/cutover.js:675`, `static/js/views/cutover.js:678`
- **Durum:** Modal `App.openModal()` yerine custom DOM ile aciliyor/kapatiliyor. ESC listener sadece ESC ile kapanista remove ediliyor; close button/cancel/backdrop kapatmalarinda temizlenmiyor.
- **Etki:** Uzun oturumlarda tekrarlanan modal ac-kapa ile listener birikimi ve davranis tutarsizligi riski.
- **Oneri:** Cutover modalini `App.openModal()` standardina alin; custom modalde kalinacaksa listener cleanup her kapanis yolunda garanti edilmeli.

### 2. [Major] Design token tutarsizligi: tanimsiz `--text-*`/`--border` kullanimi

- **Kanit:** `static/css/main.css:759`, `static/css/main.css:771`, `static/css/main.css:798`, `static/css/main.css:820`, `static/js/views/program.js:251`, `static/js/views/timeline.js:222`, `static/js/views/integrations.js:369`
- **Durum:** `var(--text-secondary)`, `var(--text-primary)`, `var(--border)` gibi tokenlar root'ta tanimli degil (fallback verilmedigi yerler var).
- **Etki:** Tarayicida property'nin gecersiz kalmasi nedeniyle stilin beklenmedik sekilde dusmesi.
- **Oneri:** `--sap-text-secondary`, `--sap-text-primary`, `--sap-border` veya `--pg-*` tokenlariyla standardize edin.

### 3. [Major] Bootstrap class'lari ana uygulamada kullaniliyor, ancak Bootstrap tanimli degil

- **Kanit:** `static/js/views/authorization.js:290`, `static/js/views/transports.js:126`, `static/js/views/transports.js:167`, `static/js/views/cutover.js:1209`, `static/js/views/cutover.js:1218`
- **Durum:** `table-sm`, `table-hover`, `table-bordered`, `col-md-6`, `text-end` gibi class'lar kullaniliyor; `static/css/main.css` ve diger app CSS dosyalarinda tanim bulunmuyor.
- **Etki:** Beklenen spacing/grid/table varyantlari render edilmiyor; sayfalar arasi UI drift olusuyor.
- **Oneri:** Ya bu class'lar icin app CSS'te karsiliklar yazin ya da mevcut design system class'larina migrate edin.

### 4. [Major] Header class standardi kirik: `view-header` tanimsiz

- **Kanit:** `static/js/views/ai_admin.js:12`, `static/js/views/hypercare.js:496`
- **Durum:** Bu gorunumler `view-header` kullaniyor; app CSS'te `.view-header` tanimi yok.
- **Etki:** Header spacing/alignment, diger sayfalarla tutarsiz kalıyor.
- **Oneri:** `page-header` veya `pg-view-header` ile tek standarda gecin.

### 5. [Major] Tablo erisilebilirlik semantik eksigi (global)

- **Kanit:** `static/js/views/*` taramasinda `<caption>`, table `aria-label`, `role="table"` kullanimi bulunmadi.
- **Durum:** Verisel tablolar ekran okuyucular icin baglamsiz.
- **Etki:** WCAG 2.2 AA hedefiyle uyumsuzluk riski.
- **Oneri:** Her tabloya en az bir semantic etiketleme standardi ekleyin (`caption` tercih edilir).

### 6. [Major] Hardcoded renk kullanimi cok yuksek

- **Kanit:** `static/js/views/*` altinda hex kullanimi: **706** tekrar.
- **Ornek:** `static/js/views/data_factory.js:646`, `static/js/views/reports.js:13`, `static/js/views/raid.js:376`
- **Etki:** Theme/token yonetimi zorlasiyor, tutarlilik ve bakim maliyeti artiyor.
- **Oneri:** Renkleri token map'e tasiyin; ozellikle badge/RAG/chart paletlerini ortaklastirin.

### 7. [Minor] Icon-only aksiyon butonlarinda `aria-label` eksigi yaygin

- **Kanit:** `static/js/views/raid.js:449`, `static/js/views/backlog.js:374`, `static/js/views/project_setup.js:259`, `static/js/views/hypercare.js:281`
- **Durum:** `title` var ama `aria-label` yok olan ornekler bulunuyor.
- **Etki:** Screen reader deneyimi zayifliyor.
- **Oneri:** Icon-only butonlar icin `aria-label` zorunlu hale getirilsin.

## Onceki Auditten Kapanan/Olumlu Gozlemler

- `form-control` artik tanimli: `static/css/main.css:520`
- `data_factory.js` modal akisi `App.openModal()` ile hizalanmis: `static/js/views/data_factory.js:673`
- `text-muted` class'i tanimli: `static/css/main.css:168`

## Onerilen Sonraki Adim (Wave 2)

1. Cutover modalin standarda alinmasi (P0)
2. Token temizligi (`--text-*`, `--border`) ve fallback stratejisi (P1)
3. Bootstrap class kullanan 6 view icin migration matrix (P1)
4. Table + icon-button a11y checklistinin PR gate'e alinmasi (P1)
