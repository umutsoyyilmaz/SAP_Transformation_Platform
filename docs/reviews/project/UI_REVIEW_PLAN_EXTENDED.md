# UI Review Plani (Extended v2)

**Tarih:** 2026-02-23  
**Referans:** `docs/reviews/project/UI_CONSISTENCY_AUDIT.md` (2026-02-13)  
**Amac:** Onceki UI consistency denetimini daha kapsamli, olculebilir ve tekrarlanabilir bir UI Review programina donusturmek.

## 1. Hedefler

1. UI tutarliligini dosya bazli duzeltmelerden cikartip sistem seviyesinde yonetmek.
2. UI kaliteyi 5 eksende olcmek: tutarlilik, erisilebilirlik, kullanilabilirlik, performans, surdurulebilirlik.
3. Kritik UI hatalarini sprint-bazli kapatirken, yeni regresyonlari otomatik yakalamak.
4. Design token ve component sozlesmelerini olusturarak tek kaynak dogruluk modeli kurmak.

## 2. Kapsam

**In scope**
- `static/js/views/` altindaki tum gorunumler (21+ dosya)
- `static/js/app.js`, `static/js/mobile.js`, `static/css/main.css`
- Explore varyanti (`ExpUI`) ve core UI patternleri
- Modal, form, table, badge, button, empty-state, KPI card, chart renk semalari
- Desktop + mobile (320, 375, 768, 1024, 1280, 1440)

**Out of scope (bu fazda)**
- Backend API semantik degisiklikleri
- Is kurali refactorlari (UI davranisini etkilemiyorsa)
- Buyuk UX yeniden tasarimlari (IA degisikligi, yeni akislar)

## 3. Onceki Auditten Gelen Baslangic Noktasi

Mevcut rapordaki 10 kategori korunur ve 6 yeni kategori eklenir:

1. CSS variable/class tutarliligi  
2. Modal pattern standardizasyonu  
3. Table/Form/Badge/Button patternleri  
4. Inline style ve hardcoded color temizligi  
5. Erisilebilirlik (ARIA, keyboard, color contrast)  
6. Ortak utility (escape, badge helper) standardizasyonu  
7. Responsive layout ve breakpoint davranisi  
8. Interaction consistency (loading, empty, error, success states)  
9. Data visualization consistency (chart palette, legend, axis, tooltip pattern)  
10. Content consistency (label, terminoloji, microcopy tonu)  
11. Performance budget (LCP/FCP/INP etkileyen UI kodu)  
12. Testability (stable selectors, deterministic render)  
13. I18n readiness (metin birimleri, tarih/sayi formatlari)  
14. Motion consistency (transition timing, reduced-motion uyumu)  
15. Theme readiness (token tabanli light/dark veya brand varyanti)  
16. Governance (review checklist, quality gate, ownership)

## 4. Calisma Metodu (4 Katman)

1. **Static Audit:** Kod tarama, pattern envanteri, token kullanim analizi.  
2. **Runtime Audit:** Ekran gezisi, modal/form/tablo davranis testleri, keyboard-only test.  
3. **Visual Audit:** Snapshot/visual regression ile ekranlar arasi fark analizi.  
4. **Experience Audit:** Heuristic UX kontrolu (Nielsen + SAP/Fiori uyumlulugu) ve gorev bazli akis testleri.

## 5. Is Paketleri (Workstreams)

### WS1: Design Token Governance
- Tek token haritasi: renk, spacing, radius, shadow, typography.
- Yasakli kullanimlar: hardcoded hex, inline kritik stil.
- Cikti: `UI_TOKEN_MAP.md`, degisim kurallari, migration listesi.

### WS2: Component Contract Standardization
- Modal, form field, table, badge, button, card, empty-state contractlari.
- Her komponent icin zorunlu class + erisilebilirlik minimumu.
- Cikti: `UI_COMPONENT_CONTRACTS.md`.

### WS3: Accessibility (WCAG 2.2 AA)
- Keyboard ulasilabilirlik, focus order, aria-label, dialog semantics.
- Contrast kontrolleri ve color-only durumlarin metinsel desteklenmesi.
- Cikti: `ACCESSIBILITY_UI_FINDINGS.md` + onceliklendirme.

### WS4: Responsive & Mobile Behavior
- Breakpoint bazli layout bozulma ve overflow tespiti.
- Table/mobile fallback patternleri ve touch-target boyutlari.
- Cikti: `RESPONSIVE_GAP_REPORT.md`.

### WS5: Interaction & State Consistency
- Loading/empty/error/success state kaliplari.
- Confirmation, destructive action, undo pattern standardi.
- Cikti: `STATE_PATTERN_GUIDE.md`.

### WS6: Data Viz Consistency
- RAG renk haritasi tekillestirme.
- Chart legend/tooltip formati ve okunabilirlik.
- Cikti: `DATA_VIZ_STYLE_GUIDE.md`.

### WS7: UI Performance
- Render agir noktalar, tekrar eden DOM/inline style maliyeti.
- Basit budget: ilk acilista kritik ekranlarda algisal hiz.
- Cikti: `UI_PERFORMANCE_NOTES.md`.

### WS8: Test Automation & Quality Gates
- UI lint kurallari (class/token ihlali).
- E2E smoke + visual regression temel seti.
- PR quality gate checklist.
- Cikti: `UI_QUALITY_GATE.md`.

## 6. Fazli Uygulama Plani (6 Hafta)

### Faz 0 (2 gun): Kickoff + Baseline
- Audit kapsam/dogrulama.
- Mevcut issue listesini normalize etme.
- KPI baseline olcumu.

### Faz 1 (Hafta 1): Critical Stabilization
- `form-control`/`form-input`, undefined variable, custom modal sorunlari.
- Acil regresyon engelleme hedefi.
- Cikis kriteri: kritik bulgu sayisi 0.

### Faz 2 (Hafta 2): Core Pattern Alignment
- Table, badge, button, page-header, modal-close standardizasyonu.
- Duplicate helperlarin merkezi utilitye alinmasi.
- Cikis kriteri: major bulgu sayisinda en az %50 azalis.

### Faz 3 (Hafta 3): Accessibility + Responsive Sprint
- Dialog/table/button erisilebilirlik minimumlari.
- Mobile breakpoint duzeltmeleri.
- Cikis kriteri: A11y major bulgu sayisi 0.

### Faz 4 (Hafta 4): Color/Token Consolidation
- Hardcoded color temizligi ve chart palette birlestirme.
- Cikis kriteri: core viewlerde hardcoded color = 0.

### Faz 5 (Hafta 5): Visual Regression + E2E Guardrails
- Kritik ekranlar icin snapshot baseline.
- UI smoke testlerinin CI entegrasyonu.
- Cikis kriteri: PR quality gate aktif.

### Faz 6 (Hafta 6): Governance Hand-off
- Dokumantasyon, checklist, sahiplik matrisi.
- Sprint sonrasi calisma modeli.
- Cikis kriteri: operasyonel review ritmi tanimli.

## 7. RACI (Oneri)

- **Responsible:** UI gelistirici(ler), frontend owner  
- **Accountable:** Tech lead / architect  
- **Consulted:** UX, QA, accessibility sorumlusu  
- **Informed:** Product owner, proje yonetimi

## 8. Olcumleme ve KPI

1. Critical issue count (hedef: 0)
2. Major issue count (hedef: %70+ azalis)
3. Token compliance rate (hedef: %95+)
4. Accessibility pass rate (hedef: %90+ kontrol maddesi)
5. Visual regression false positive orani (hedef: <%10)
6. UI regression leakage (hedef: sprint basina 0 kritik)

## 9. Severity + Onceliklendirme Modeli

- **Severity:** Critical / Major / Minor
- **Priority skor:** `Impact x Frequency x Risk / Effort`
- `P0`: 72 saat icinde cozulmeli  
- `P1`: aktif sprintte cozulmeli  
- `P2`: iki sprint icinde kapatilmali

## 10. Deliverable Listesi

1. `docs/reviews/project/UI_REVIEW_PLAN_EXTENDED.md` (bu dosya)
2. `docs/reviews/project/UI_COMPONENT_CONTRACTS.md`
3. `docs/reviews/project/UI_TOKEN_MAP.md`
4. `docs/reviews/project/ACCESSIBILITY_UI_FINDINGS.md`
5. `docs/reviews/project/RESPONSIVE_GAP_REPORT.md`
6. `docs/reviews/project/UI_QUALITY_GATE.md`

## 11. Review Checklist (PR Kapisi)

1. Undefined class/variable yok
2. Hardcoded hex yok (izinli istisnalar disinda)
3. Modal pattern `App.openModal()` uyumlu
4. Form/table/button class sozlesmesine uyumlu
5. Keyboard + aria temel gereksinimleri saglaniyor
6. Responsive smoke kontrolu tamam
7. Visual diff kabul edilebilir
8. Yeni pattern dokumante edildi

## 12. Riskler ve Azaltma

1. **Risk:** Buyuk toplu refactor regresyon uretebilir  
   **Aksiyon:** Fazli rollout + visual regression + smoke test
2. **Risk:** Explore ve core design dilleri cakisabilir  
   **Aksiyon:** Ortak minimum contract, bagimsiz tema ozgurlugu
3. **Risk:** Sprint kapasitesi yetersiz kalabilir  
   **Aksiyon:** P0/P1 odakli backlog ve kapsam kilitleme

## 13. Beklenen Sonuc

- UI review tek seferlik audit olmaktan cikar, surekli kalite mekanizmasina donusur.
- Kod tabaninda tutarlilik artisiyla birlikte UI degisikligi hizi artar, regresyon maliyeti azalir.
- Erisilebilirlik ve responsive kalite sonradan eklenen degil, default gelistirme standardi olur.
