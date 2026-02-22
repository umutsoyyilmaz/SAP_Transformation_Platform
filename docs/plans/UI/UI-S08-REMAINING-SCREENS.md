# UI-S08 — Remaining Screens Standardization

**Sprint:** UI-S08 / 9
**Süre:** 1.5 hafta
**Effort:** M
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md) tamamlanmış olmalı
**Sonraki:** [UI-S09](./UI-S09-ACCESSIBILITY-POLISH.md)

---

## Amaç

S01–S07'de dokunulmayan geri kalan ekranları token + component migration ile stabil hale getir.
Hedef: Hiçbir ekranda hardcoded renk, `--sap-*` token veya emoji ikonlar kalmamalı.

---

## Kapsaydaki Ekranlar

| View | Dosya | Durum |
|------|-------|-------|
| AI Asistanlar | `views/ai-assistants.js` veya `app.js` | 🔲 |
| Raporlar | `views/reports.js` veya `app.js` | 🔲 |
| Entegrasyon Cockpit | `views/integration.js` | 🔲 |
| Veri Yönetimi | `views/data-management.js` | 🔲 |
| Geçiş Yönetimi (Cutover) | `views/cutover.js` | 🔲 |
| Proje Kurulum | `views/setup.js` | 🔲 |
| Bildirimler | `views/notifications.js` | 🔲 |
| Admin Panel | `templates/admin/` | 🔲 |

---

## Görevler

### UI-S08-T01 — AI Asistanlar Arayüzü

**İlgili dosya:** AI asistan view

- Karşılama kartı: `pg-tokens.css` ile renk sistemi
- Asistan listesi: `PGEmptyState` ile boş durum
- Sohbet balonu: `--pg-color-primary-light` background + `border-radius: 16px 16px 0 16px`
- Yanıt yüklenirken: `PGSkeleton.line(100, 14)` × 3
- AI provider badge: `PGStatusRegistry.badge()` ile model türü (GPT-4, Claude, Gemini)

```css
/* Chat balonu stilleri */
.pg-chat-bubble {
    max-width: 80%;
    padding: var(--pg-sp-4) var(--pg-sp-5);
    border-radius: 16px;
    font-size: 13px;
    line-height: 1.6;
}
.pg-chat-bubble--user {
    background: var(--pg-color-primary);
    color: #fff;
    border-radius: 16px 16px 0 16px;
    align-self: flex-end;
}
.pg-chat-bubble--ai {
    background: var(--pg-color-bg);
    border: 1px solid var(--pg-color-border);
    color: var(--pg-color-text);
    border-radius: 16px 16px 16px 0;
    align-self: flex-start;
}
```

---

### UI-S08-T02 — Raporlar View

**İlgili dosya:** Raporlar view

- Rapor kart grid: `pg-dash-kpis` stiline benzer — `grid-template-columns: repeat(3, 1fr)`
- Export butonu: `PGButton.html('Dışa Aktar', 'secondary', { icon: PGIcon.html('export', 14) })`
- Boş durum: `PGEmptyState.html({ icon: 'reports', title: 'Rapor bulunamadı' })`
- Breadcrumb: `PGBreadcrumb.html([{ label: 'Raporlar' }])`

---

### UI-S08-T03 — Entegrasyon Cockpit

- Entegrasyon kartları: durum badge → `PGStatusRegistry.badge(integration.status)`
- Log tablosu: `TMDataGrid` + `pg-tokens.css`
- Bağlantı butonu: `PGButton.html('Bağlan', 'primary')`
- Hata durumu: kırmızı border + `PGStatusRegistry.badge('fail', { label: 'Bağlantı Hatası' })`

---

### UI-S08-T04 — Proje Kurulum (Setup) Wizard

- Multi-step form: `pg_form.js` input componentleri
- Adım göstergesi:

```javascript
function _stepIndicator(steps, current) {
    return `
        <div class="pg-step-indicator">
            ${steps.map((s, i) => `
                <div class="pg-step-indicator__step${i < current ? ' pg-step-indicator__step--done' : i === current ? ' pg-step-indicator__step--active' : ''}">
                    <div class="pg-step-indicator__dot">${i < current ? '✓' : i + 1}</div>
                    <span class="pg-step-indicator__label">${s}</span>
                </div>
                ${i < steps.length - 1 ? '<div class="pg-step-indicator__line"></div>' : ''}
            `).join('')}
        </div>
    `;
}
```

```css
/* static/css/pg-steps.css */
.pg-step-indicator {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: var(--pg-sp-8);
}
.pg-step-indicator__step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
}
.pg-step-indicator__dot {
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px;
    font-weight: 600;
    background: var(--pg-color-bg);
    border: 2px solid var(--pg-color-border);
    color: var(--pg-color-text-secondary);
    transition: all var(--pg-t-normal);
}
.pg-step-indicator__step--active .pg-step-indicator__dot {
    background: var(--pg-color-primary);
    border-color: var(--pg-color-primary);
    color: #fff;
    box-shadow: 0 0 0 4px var(--pg-color-primary-light);
}
.pg-step-indicator__step--done .pg-step-indicator__dot {
    background: var(--pg-color-positive);
    border-color: var(--pg-color-positive);
    color: #fff;
}
.pg-step-indicator__label { font-size: 11px; color: var(--pg-color-text-tertiary); white-space: nowrap; }
.pg-step-indicator__step--active .pg-step-indicator__label { color: var(--pg-color-primary); font-weight: 600; }
.pg-step-indicator__line { flex: 1; height: 2px; background: var(--pg-color-border); margin-bottom: 20px; min-width: 32px; }
```

---

### UI-S08-T05 — Admin Panel Hardening

**`templates/admin/`** ve **`templates/platform_admin/`** dosyaları:

- `pg-tokens.css` ve `pg-button.css` link eklenmesi
- Form input'larını `pg-form.css` class'ları ile güncelle
- Admin panel header: `pg-header` class'ı ile uyumlu
- Jinja2 template'lerindeki hardcoded renk style="color:#..." ifadelerini temizle

---

### UI-S08-T06 — Global CSS Cleanup (Final Pass)

Bu sprint'te tüm CSS'e final tarama yapılır:

```bash
# Kalan hardcoded renk kullanımlarını bul
grep -r "#[0-9a-fA-F]\{3,6\}" static/css/ --include="*.css" | grep -v "pg-tokens.css" | grep -v "/\*" | head -50

# Kalan sap- kullanımlarını bul
grep -r "var(--sap-" static/ --include="*.css" --include="*.js"
grep -r "var(--tm-"  static/ --include="*.css" --include="*.js" | grep -v "alias"

# print() var mı? (debug leftovers)
grep -n "console.log(" static/js/ -r | grep -v ".test." | head -20
```

Hedef: sadece `pg-tokens.css` içinde primitive hex değerleri kalmalı, başka hiçbir yerde.

---

## Deliverables Kontrol Listesi

- [x] AI asistanlar view token migration tamamlandı (`ai_query.js` + `ai_insights.js` — `pg-view-header` + `PGBreadcrumb` + `PGEmptyState`)
- [x] Raporlar view breadcrumb + PGEmptyState ekli (`reports.js` — `ragBadge`/`statusBadge` → `PGStatusRegistry.badge()`)
- [x] Entegrasyon Cockpit durum badge'leri standart (`integration.js` — `_statusBadge()` + `_connBadge()` helpers)
- [x] Cutover view token migration tamamlandı (`cutover.js` — `badge()` → `PGStatusRegistry.badge()`)
- [x] Proje Kurulum wizard adım göstergesi çalışıyor (`project_setup.js` — `_stepIndicator()` eklendi)
- [x] `pg-steps.css` oluşturuldu, `index.html`'e eklendi
- [x] Admin panel template'leri `pg-tokens.css` ile güncellendi (`templates/admin/index.html`)
- [x] Global CSS cleanup: `console.log` taraması yapıldı — yalnızca `pwa.js`'te PWA registration log'ları (uygun, temizlenmedi)
- [x] `ai_insights.js` duplicate Ctrl+K listener kaldırıldı — `PGCommandPalette` (UI-S07) yönetiyor

---

*← [UI-S07](./UI-S07-COMMAND-PALETTE-POWER-FEATURES.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S09 →](./UI-S09-ACCESSIBILITY-POLISH.md)*
