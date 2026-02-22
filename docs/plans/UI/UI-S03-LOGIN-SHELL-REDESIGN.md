# UI-S03 — Login & Shell Redesign

**Sprint:** UI-S03 / 9
**Süre:** 1.5 hafta
**Effort:** M
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S01](./UI-S01-DESIGN-SYSTEM-FOUNDATION.md) tamamlanmış olmalı
**Sonraki:** [UI-S04](./UI-S04-DASHBOARD-PROGRAM-MANAGEMENT.md)

---

## Amaç

İlk izlenim (login) ve kalıcı çerçeve (shell) enterprise güven standardına yükselt.
Bu iki alan platformun tüm kullanıcılarının her oturumda gördüğü alanlardır.
Audit skoru: Login 4/10, Shell 5/10 → Hedef: her ikisi için 8/10.

---

## Görevler

### UI-S03-T01 — Login: Split-Screen Layout

**Dosya:** `templates/login.html` + `static/css/login.css`

Mevcut durum: Tek sütun ortalanmış kart, gradient arka plan.
Hedef: Sol taraf marka/değer mesajı, sağ taraf form.

```
┌─────────────────────┬────────────────────┐
│  PERGA              │                    │
│  Navigate Complexity│   Hoş Geldiniz     │
│                     │  ─────────────     │
│  • Gereksinim takibi│  [Email          ] │
│  • GAP analizi      │  [Şifre          ] │
│  • Test yönetimi    │                    │
│  • WRICEF takibi    │  [  Giriş Yap   ]  │
│                     │                    │
│  SAP S/4HANA dönüşüm│  ── veya ──       │
│  projelerinizi      │  [  SSO ile Gir  ] │
│  güvenle yönetin.   │                    │
│                     │  Şifremi Unuttum   │
└─────────────────────┴────────────────────┘
```

**`login.html`:**
```html
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Perga — Navigate Complexity</title>
    <link rel="stylesheet" href="/static/css/pg-tokens.css">
    <link rel="stylesheet" href="/static/css/login.css">
    <link rel="stylesheet" href="/static/css/pg-form.css">
    <link rel="stylesheet" href="/static/css/pg-button.css">
</head>
<body class="pg-login-body">
<div class="pg-login-shell">
    <!-- Sol: Marka paneli -->
    <aside class="pg-login-brand">
        <div class="pg-login-brand__inner">
            <div class="pg-login-brand__logo">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                    <rect width="32" height="32" rx="8" fill="rgba(255,255,255,0.15)"/>
                    <path d="M8 8h10a6 6 0 0 1 0 12H8V8z" fill="white"/>
                    <path d="M8 20h12a4 4 0 0 1 0 8H8v-8z" fill="rgba(255,255,255,0.6)"/>
                </svg>
                <span class="pg-login-brand__name">Perga</span>
            </div>
            <h1 class="pg-login-brand__tagline">Navigate<br>Complexity</h1>
            <ul class="pg-login-brand__features">
                <li>SAP S/4HANA dönüşüm yönetimi</li>
                <li>Gereksinim ve GAP analizi</li>
                <li>WRICEF ve konfigürasyon takibi</li>
                <li>Test senaryosu ve defect yönetimi</li>
                <li>RAID log ve onay akışları</li>
            </ul>
            <div class="pg-login-brand__badge">Enterprise SaaS</div>
        </div>
    </aside>

    <!-- Sağ: Form paneli -->
    <main class="pg-login-form-panel">
        <div class="pg-login-card">
            <h2 class="pg-login-card__title">Hoş Geldiniz</h2>
            <p class="pg-login-card__sub">Devam etmek için giriş yapın</p>

            {% if error %}
            <div class="pg-login-alert">{{ error }}</div>
            {% endif %}

            <form method="POST" action="/login" class="pg-login-form">
                <div class="pg-field">
                    <label class="pg-label" for="email">E-posta</label>
                    <input class="pg-input" id="email" name="email" type="email" placeholder="ad@sirket.com" required autofocus>
                </div>
                <div class="pg-field">
                    <label class="pg-label" for="password">Şifre</label>
                    <div class="pg-input-wrap">
                        <input class="pg-input" id="password" name="password" type="password" placeholder="••••••••" required>
                        <button type="button" class="pg-input-toggle" onclick="togglePwd(this)" aria-label="Şifreyi göster/gizle">👁</button>
                    </div>
                </div>
                <button type="submit" class="pg-btn pg-btn--primary" style="width:100%;justify-content:center;padding:10px">
                    Giriş Yap
                </button>
            </form>

            {% if sso_enabled %}
            <div class="pg-login-divider"><span>veya</span></div>
            <a href="/auth/sso" class="pg-btn pg-btn--secondary" style="width:100%;justify-content:center;padding:10px;text-decoration:none">
                SSO ile Giriş
            </a>
            {% endif %}

            <a class="pg-login-forgot" href="/forgot-password">Şifremi Unuttum</a>
        </div>
    </main>
</div>
<script>
function togglePwd(btn) {
    const input = btn.previousElementSibling;
    input.type = input.type === 'password' ? 'text' : 'password';
    btn.textContent = input.type === 'password' ? '👁' : '🙈';
}
</script>
</body>
</html>
```

**`login.css`** — split-screen styles:
```css
/* static/css/login.css */
.pg-login-body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    background: var(--pg-color-bg, #f5f6f7);
    min-height: 100vh;
}

.pg-login-shell {
    display: grid;
    grid-template-columns: 1fr 1fr;
    min-height: 100vh;
}

/* Brand panel */
.pg-login-brand {
    background: linear-gradient(145deg, #1d2d3e 0%, #2c4a6b 60%, #1a3a5c 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px;
    position: relative;
    overflow: hidden;
}
.pg-login-brand::before {
    content: '';
    position: absolute;
    width: 400px; height: 400px;
    right: -100px; top: -100px;
    background: rgba(255,255,255,0.03);
    border-radius: 50%;
}
.pg-login-brand__inner { position: relative; z-index: 1; max-width: 360px; }

.pg-login-brand__logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 40px;
}
.pg-login-brand__name {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.5px;
}

.pg-login-brand__tagline {
    font-size: 36px;
    font-weight: 800;
    color: #fff;
    line-height: 1.15;
    margin: 0 0 32px;
    letter-spacing: -1px;
}

.pg-login-brand__features {
    list-style: none;
    margin: 0 0 36px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
}
.pg-login-brand__features li {
    color: rgba(255,255,255,0.75);
    font-size: 14px;
    padding-left: 20px;
    position: relative;
}
.pg-login-brand__features li::before {
    content: '→';
    position: absolute;
    left: 0;
    color: rgba(255,255,255,0.4);
    font-size: 12px;
}

.pg-login-brand__badge {
    display: inline-block;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.7);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 20px;
}

/* Form panel */
.pg-login-form-panel {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px;
    background: #fff;
}

.pg-login-card {
    width: 100%;
    max-width: 360px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.pg-login-card__title {
    font-size: 24px;
    font-weight: 700;
    color: var(--pg-color-text, #32363a);
    margin: 0;
    letter-spacing: -0.5px;
}
.pg-login-card__sub {
    font-size: 14px;
    color: var(--pg-color-text-secondary, #6a6d70);
    margin: 0;
}

.pg-login-alert {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
}

.pg-login-form { display: flex; flex-direction: column; gap: 16px; }

.pg-input-wrap { position: relative; }
.pg-input-wrap .pg-input { padding-right: 38px; }
.pg-input-toggle {
    position: absolute;
    right: 8px; top: 50%;
    transform: translateY(-50%);
    background: none; border: none;
    cursor: pointer;
    font-size: 14px;
    color: var(--pg-color-text-tertiary);
    padding: 4px;
    line-height: 1;
}

.pg-login-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--pg-color-text-tertiary);
    font-size: 12px;
}
.pg-login-divider::before,
.pg-login-divider::after { content: ''; flex: 1; height: 1px; background: var(--pg-color-border, #d9d9d9); }

.pg-login-forgot {
    font-size: 12px;
    color: var(--pg-color-primary);
    text-decoration: none;
    text-align: center;
}
.pg-login-forgot:hover { text-decoration: underline; }

/* Mobile: tek sütun */
@media (max-width: 768px) {
    .pg-login-shell { grid-template-columns: 1fr; }
    .pg-login-brand { display: none; }
    .pg-login-form-panel { padding: 24px; }
}
```

---

### UI-S03-T02 — Shell Header: Branding + Notifications

**Dosya:** `templates/index.html` — header section

Mevcut: `<h1 class="header__title">SAP Transformation Platform</h1>` + select dropdown
Hedef: Perga logo + breadcrumb + user avatar

```html
<!-- header içeriği -->
<header class="pg-header" id="shell-header">
    <div class="pg-header__left">
        <!-- Logo / Brand -->
        <div class="pg-header__brand">
            <svg width="24" height="24" viewBox="0 0 32 32" fill="none">
                <rect width="32" height="32" rx="6" fill="#0070f2"/>
                <path d="M8 8h10a6 6 0 0 1 0 12H8V8z" fill="white"/>
                <path d="M8 20h12a4 4 0 0 1 0 8H8v-8z" fill="rgba(255,255,255,0.6)"/>
            </svg>
            <span class="pg-header__brand-name">Perga</span>
        </div>
        <!-- Breadcrumb — JS tarafından güncellenir -->
        <div id="shell-breadcrumb" class="pg-header__breadcrumb"></div>
    </div>
    <div class="pg-header__center">
        <!-- Global search trigger (UI-S07'de komut paletiyle birleşecek) -->
        <button class="pg-header__search-btn" id="searchTrigger" onclick="openCommandPalette()" title="Ara (⌘K)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <span>Ara veya git...</span>
            <kbd>⌘K</kbd>
        </button>
    </div>
    <div class="pg-header__right">
        <!-- Notifications -->
        <button class="pg-header__icon-btn" id="notifBtn" title="Bildirimler">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            <span class="pg-header__notif-dot" id="notifDot" style="display:none"></span>
        </button>
        <!-- User avatar -->
        <button class="pg-header__avatar" id="userMenuBtn" title="Hesap">
            <span id="userAvatarText">U</span>
        </button>
    </div>
</header>
```

```css
/* pg-layout.css additions */
.pg-header {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-4);
    height: var(--pg-header-height, 48px);
    background: var(--pg-header-bg, #354a5f);
    padding: 0 var(--pg-sp-6);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    position: sticky;
    top: 0;
    z-index: var(--pg-z-header, 100);
}
.pg-header__left  { display: flex; align-items: center; gap: var(--pg-sp-4); flex: 1; min-width: 0; }
.pg-header__center { flex: 0 0 auto; }
.pg-header__right { display: flex; align-items: center; gap: var(--pg-sp-2); flex-shrink: 0; }

.pg-header__brand { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.pg-header__brand-name { font-weight: 700; font-size: 15px; color: #fff; letter-spacing: -0.3px; }
.pg-header__breadcrumb { display: flex; align-items: center; font-size: 12px; color: rgba(255,255,255,0.5); gap: 4px; min-width: 0; overflow: hidden; white-space: nowrap; }

.pg-header__search-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.55);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all var(--pg-t-normal);
    white-space: nowrap;
}
.pg-header__search-btn:hover { background: rgba(255,255,255,0.14); color: rgba(255,255,255,0.8); }
.pg-header__search-btn kbd {
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 11px;
    font-family: inherit;
}

.pg-header__icon-btn {
    position: relative;
    background: none; border: none;
    color: rgba(255,255,255,0.6);
    width: 32px; height: 32px;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    transition: all var(--pg-t-normal);
}
.pg-header__icon-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.pg-header__notif-dot {
    position: absolute;
    top: 5px; right: 5px;
    width: 7px; height: 7px;
    background: #ef4444;
    border-radius: 50%;
    border: 1.5px solid var(--pg-header-bg);
}

.pg-header__avatar {
    width: 30px; height: 30px;
    border-radius: 50%;
    background: var(--pg-color-primary, #0070f2);
    border: 2px solid rgba(255,255,255,0.2);
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--pg-t-normal);
}
.pg-header__avatar:hover { border-color: rgba(255,255,255,0.5); transform: scale(1.05); }
```

---

### UI-S03-T03 — Sidebar: Collapse + Section Grouping

**Dosya:** `app.js` + `templates/index.html` sidebar section

Sidebar 3 section'a bölünür: Project, Management, Platform.
Collapse (56px icon-only mode) butonu eklenir.

```javascript
// app.js — sidebar collapse
function initSidebarCollapse() {
    const sidebar  = document.getElementById('sidebar');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    const stored   = localStorage.getItem('pg_sidebar_collapsed') === 'true';
    if (stored) sidebar.classList.add('sidebar--collapsed');

    collapseBtn.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.toggle('sidebar--collapsed');
        localStorage.setItem('pg_sidebar_collapsed', isCollapsed);
    });
}
```

```css
/* sidebar collapse styles */
.sidebar { transition: width var(--pg-t-slow, 250ms ease); width: var(--pg-sidebar-width, 260px); overflow: hidden; }
.sidebar--collapsed { width: var(--pg-sidebar-collapsed, 56px); }
.sidebar--collapsed .sidebar__label,
.sidebar--collapsed .sidebar__section-title,
.sidebar--collapsed .sidebar__badge { display: none; }
.sidebar--collapsed .sidebar__item { justify-content: center; padding: 8px; }
.sidebar--collapsed .sidebar__item-icon { margin: 0; }
.sidebar--collapsed #sidebarCollapseBtn svg { transform: rotate(180deg); }
```

---

## Deliverables Kontrol Listesi

- [x] `templates/login.html` split-screen layout ile güncellendi
- [x] `static/css/login.css` yeniden yazıldı
- [x] Mobile login (<768px) tek sütun çalışıyor
- [x] `templates/index.html` header: Perga logo + search trigger + notifications + avatar
- [x] Sidebar collapse (56px) button eklendi, localStorage'da persist
- [x] Sidebar section grouping korundu (Program Management / Explore Phase / Delivery / Go-Live / AI)
- [x] `pg-layout.css` header + collapse stilleri güncellendi
- [x] `app.js` `initSidebarCollapse()` fonksiyonu eklendi

---

*← [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S04 →](./UI-S04-DASHBOARD-PROGRAM-MANAGEMENT.md)*
