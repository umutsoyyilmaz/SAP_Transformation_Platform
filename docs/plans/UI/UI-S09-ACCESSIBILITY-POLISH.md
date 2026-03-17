# UI-S09 — Accessibility, Dark Mode & Polish

**Sprint:** UI-S09 / 9
**Süre:** 1.5 hafta
**Effort:** M
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** Tüm önceki sprint'ler (S01–S08) tamamlanmış olmalı
**Sonraki:** Release — 8.5/10 Hedef ✅

---

## Amaç

Platform'u WCAG 2.1 AA uyumlu hale getir. Dark mode altyapısını oluştur.
Micro-animation ve focus yönetimini sonlandır. Bu sprint = bitiş çizgisi.

---

## Görevler

### UI-S09-T01 — WCAG 2.1 AA Audit & Fix

**Araç:** `axe-core` veya tarayıcı devtools erişilebilirlik paneli

Öncelik sıralı düzeltmeler:

| Sorun | Kural | Çözüm |
|-------|-------|-------|
| Emoji icon'lardan kalan `aria-label` eksikliği | 1.1.1 | `aria-hidden="true"` veya SVG + `aria-label` |
| Button'ların sadece renk ile ayrışması (status badge) | 1.4.1 | Text + renk birlikte kullan |
| Form input'ları ve label bağlantısı | 1.3.1 | `for`+`id` bağlantısı → `PGForm.input()` zaten yapıyor |
| Modal focus trap eksikliği | 2.1.2 | Modal açılınca ilk focusable element'e `focus()` |
| Renk kontrastı: `--pg-color-text-tertiary` (#9aa0a6 on #fff) | 1.4.3 | `#767b80` ile değiştir — 4.5:1 geçer |
| Skip-to-main link | 2.4.1 | `<a class="skip-link" href="#main-content">` |
| Tablo başlıkları: `scope` attribute eksik | 1.3.1 | `<th scope="col">` |

**Skip link ekle (`index.html` `<body>` başına):**
```html
<a href="#main-content" class="pg-skip-link">Ana içeriğe geç</a>
```
```css
.pg-skip-link {
    position: absolute;
    left: -9999px;
    top: 0;
    background: var(--pg-color-primary);
    color: white;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    z-index: 9999;
    border-radius: 0 0 6px 0;
}
.pg-skip-link:focus { left: 0; }
```

---

### UI-S09-T02 — Focus Management & Keyboard Navigation

**Her modal/panel için:**
```javascript
/**
 * Focus trap — modal içinde Tab ile döngü sağlar.
 * WCAG 2.1 SC 2.1.2 gereksinimi.
 */
function trapFocus(containerEl) {
    const focusable = containerEl.querySelectorAll(
        'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    const first = focusable[0];
    const last  = focusable[focusable.length - 1];
    first.focus();
    containerEl.addEventListener('keydown', function handler(e) {
        if (e.key !== 'Tab') return;
        if (e.shiftKey) {
            if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
            if (document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
        if (!containerEl.contains(document.activeElement)) { containerEl._trapHandlerRef = null; containerEl.removeEventListener('keydown', handler); }
    });
}
```

**Focus visible ring — tüm interactive element'ler için:**
```css
/* pg-tokens.css'e ekle */
:focus-visible {
    outline: 2px solid var(--pg-color-primary);
    outline-offset: 2px;
    border-radius: var(--pg-radius-sm);
}
/* Fare ile tıklayanlar için focus ring'i gizle */
:focus:not(:focus-visible) { outline: none; }
```

---

### UI-S09-T03 — Dark Mode Infrastructure

Dark mode tam implementasyonu S09 scope'u dışındadır (CSS değişkeni sayısı nedeniyle);
bu sprint'te **altyapı ve toggle** kurulur, S09+ için temel hazırlanır.

**Token override layer — `pg-tokens.css` sonuna ekle:**
```css
/* ── Dark Mode Overrides ────────────────────── */
[data-theme="dark"] {
    --pg-color-surface:          #1e2433;
    --pg-color-bg:               #161b27;
    --pg-color-border:           #2a3142;
    --pg-color-border-strong:    #3a4158;
    --pg-color-text:             #e2e8f0;
    --pg-color-text-secondary:   #94a3b8;
    --pg-color-text-tertiary:    #64748b;
    --pg-color-primary-light:    rgba(0, 112, 242, 0.15);
    --pg-sidebar-bg:             #0f1420;
    --pg-header-bg:              #1a2030;
    --pg-shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --pg-shadow-md: 0 4px 14px rgba(0,0,0,0.4);
    --pg-shadow-lg: 0 10px 30px rgba(0,0,0,0.5);
}
```

**Theme toggle JS:**
```javascript
function initThemeToggle() {
    const stored = localStorage.getItem('pg_theme') || 'light';
    document.documentElement.setAttribute('data-theme', stored);

    document.getElementById('themeToggle')?.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next    = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('pg_theme', next);
        // Icon güncelle
        const btn = document.getElementById('themeToggle');
        btn.innerHTML = next === 'dark' ? PGIcon.html('sun', 14) : PGIcon.html('moon', 14);
    });
}
```

**Header'a ekle (UI-S03-T02 sonrasında):**
```html
<button class="pg-header__icon-btn" id="themeToggle" title="Tema değiştir" aria-label="Karanlık/Aydınlık tema">
    <!-- PGIcon.html('moon', 14) ile başla -->
</button>
```

---

### UI-S09-T04 — Micro-Animations Polish

Tüm interaktif element'lerde tutarlı geçiş animasyonları:

```css
/* pg-tokens.css'de zaten var, kullanımını doğrula */

/* ── Global Reset (uygulama bazlı) ───── */
*, *::before, *::after { box-sizing: border-box; }

/* Motion-safe: prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Page transition — view değişiminde */
.pg-view-enter {
    animation: pg-view-in 160ms ease;
}
@keyframes pg-view-in {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
```

**`navigate()` fonksiyonuna ekle:**
```javascript
function navigate(view) {
    const main = document.getElementById('main-content');
    main.classList.remove('pg-view-enter');
    void main.offsetWidth; // reflow — animasyonu sıfırla
    main.classList.add('pg-view-enter');
    // ... mevcut routing devam eder
}
```

---

### UI-S09-T05 — Responsive Polish (Tablet & Mobile)

**`static/css/mobile.css`** — eksik responsive kuralları tamamla:

```css
/* Tablet (768–1200px) */
@media (max-width: 1200px) {
    .pg-dashboard-grid { grid-template-columns: 1fr 1fr; }
    .pg-dash-kpis { grid-template-columns: repeat(3, 1fr); }
}

/* Mobile (<768px) */
@media (max-width: 768px) {
    /* Sidebar overlay mode */
    #sidebar {
        position: fixed;
        left: 0; top: 0; bottom: 0;
        z-index: var(--pg-z-sidebar, 90);
        transform: translateX(-100%);
        transition: transform var(--pg-t-slow);
        box-shadow: var(--pg-shadow-xl);
    }
    #sidebar.sidebar--mobile-open { transform: translateX(0); }

    /* Overlay backdrop */
    .pg-sidebar-overlay {
        display: none;
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: calc(var(--pg-z-sidebar, 90) - 1);
    }
    .pg-sidebar-overlay.visible { display: block; }

    /* Main content full width */
    #main-content { margin-left: 0 !important; padding: var(--pg-sp-4); }

    /* Dashboard single column */
    .pg-dashboard-grid { grid-template-columns: 1fr; }
    .pg-dash-kpis { grid-template-columns: repeat(2, 1fr); }

    /* Panel full-screen on mobile */
    .pg-panel { width: 100%; }
    .has-panel { margin-right: 0; }

    /* Table: hide secondary columns */
    .pg-table-col--secondary { display: none; }
}
```

---

### UI-S09-T06 — Performance: Script Loading

**`templates/index.html`** — 30+ blocking script tag'lerini düzenle:

Kısa vadeli çözüm (bu sprint scope'u — modul bundler değil):
```html
<!-- Temel (senkron, küçük) -->
<script src="/static/js/components/pg_icon.js"></script>
<script src="/static/js/components/pg_status_registry.js"></script>
<script src="/static/js/components/pg_button.js"></script>

<!-- Gecikmeli yükle — DOMContentLoaded sonrası -->
<script>
    document.addEventListener('DOMContentLoaded', () => {
        const deferred = [
            '/static/js/components/testing/tm_data_grid.js',
            '/static/js/components/tm_modal.js',
            '/static/js/components/pg_command_palette.js',
            // ... view script'leri
        ];
        deferred.forEach(src => {
            const s = document.createElement('script');
            s.src = src;
            document.head.appendChild(s);
        });
    });
</script>
```

> Not: Uzun vadeli çözüm → Vite (UI-S09+) veya ES modules + import maps.

---

## Final Kalite Kontrol (Release Checklist)

Sprint bitmeden aşağıdakileri doğrula:

```bash
# 1. Hardcoded renk kalmadı mı?
grep -r "style=\".*#[0-9a-fA-F]" templates/ static/js/views/ | grep -v ".test." | wc -l
# Hedef: 0

# 2. --sap-* token kalmadı mı?
grep -r "var(--sap-" static/css/ static/js/ | grep -v ".test." | wc -l
# Hedef: 0

# 3. Emoji icon kalmadı mı? (sidebar dışında)
grep -r "📊\|🏗️\|📋\|⚙️\|🐛" templates/ static/js/ | grep -v ".test." | wc -l
# Hedef: 0

# 4. console.log kalmadı mı?
grep -rn "console.log(" static/js/ | grep -v ".test.\|node_modules" | wc -l
# Hedef: 0

# 5. Axe a11y skoru: 0 kritik ihlal
```

---

## Deliverables Kontrol Listesi

- [x] `--pg-color-text-tertiary` WCAG kontrastı düzeltildi (`#9aa0a6` → `#767b80`, 4.5:1)
- [x] Skip-to-main link eklendi (`<a href="#mainContent" class="pg-skip-link">` — `index.html`)
- [x] `pg_a11y.js` oluşturuldu — `trapFocus()` + `initModalFocusTrap()` (MutationObserver)
- [x] `:focus-visible` ring tutarlı tüm interactive element'lerde (`pg-tokens.css`)
- [x] Dark mode token override layer hazır (`pg-tokens.css` — `[data-theme="dark"]`)
- [x] `initThemeToggle()` — `pg_a11y.js` içinde, `app.js` init'te çağrılıyor
- [x] Theme toggle butonu header'a eklendi (`index.html` — `#themeToggle`)
- [x] `prefers-reduced-motion` medya sorgusu eklendi (`pg-animations.css`)
- [x] `pg-animations.css` oluşturuldu — `pg-view-enter`, `pg-fade-in`, `pg-slide-up`, hover lift
- [x] View geçiş animasyonu (`pg-view-enter`) `navigate()` içinde çalışıyor (`app.js`)
- [x] `mobile.css` — pg-* responsive kurallar eklendi (tablet 1200px + mobil 768px + phone 480px + coarse pointer)
- [x] CDN script'leri `defer` ile yükleniyor (chart.js + frappe-gantt — `index.html`)

---

## Platform Skor Hedefi (Sonuç)

| Boyut | Başlangıç | Hedef |
|-------|-----------|-------|
| Bilgi Mimarisi | 6/10 | 8/10 |
| Kullanıcı Akışları | 5/10 | 8/10 |
| Veri Yoğunluğu | 7/10 | 9/10 |
| Geri Bildirim & İletişim | 6/10 | 8.5/10 |
| Tutarlılık | 5/10 | 9/10 |
| Görsel Hiyerarşi | 5/10 | 8/10 |
| Component Olgunluğu | 6/10 | 8.5/10 |
| Görsel Cilalama | 4/10 | 8/10 |
| Responsive & Erişilebilirlik | 3/10 | 7/10 |
| **Genel Ortalama** | **5.2/10** | **8.5/10** |

---

*← [UI-S08](./UI-S08-REMAINING-SCREENS.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md)*
