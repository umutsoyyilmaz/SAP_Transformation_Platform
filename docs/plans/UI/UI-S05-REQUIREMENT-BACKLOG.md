# UI-S05 — Requirement & Backlog Modernizasyonu

**Sprint:** UI-S05 / 9
**Süre:** 2 hafta
**Effort:** L
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md) tamamlanmış olmalı
**Sonraki:** [UI-S06](./UI-S06-TEST-MANAGEMENT-RAID.md)

---

## Amaç

Platform'un en yoğun kullanılan ekranı (WRICEF Kanban + Backlog).
Mevcut durum: `backlog.js` 1559 satır, kendi renk sistemi, monolitik render.
Hedef: Token migration, inline-panel detail, filtre chip bar, sprint velocity chart.

---

## Görevler

### UI-S05-T01 — Backlog Token & Badge Migration

**Dosya:** `static/js/views/backlog.js`

**Kaldırılacak:**
```javascript
// SİL — 3. paralel renk sistemi
function _statusBadge(status) { ... }  // ~20 satır
function _priorityBadge(prio) { ... }  // ~20 satır
```

**Yerine:**
```javascript
// KULLAN — merkezi registry
const statusHtml   = PGStatusRegistry.badge(item.status);
const priorityHtml = PGStatusRegistry.badge(item.priority);
```

Ayrıca `_statusColor()` / `_statusText()` gibi yardımcı fonksiyonlar varsa kaldır.

---

### UI-S05-T02 — Filtre Chip Bar

**Dosya:** `static/js/views/backlog.js` (list ve board view'larının üstüne ekle)

```javascript
function _renderFilterBar(filters, onChange) {
    /**
     * Aktif filtreleri chip olarak göster.
     * Her chip "x" ile temizlenebilir.
     * "+ Filtre" butonu filtre panelini açar.
     */
    const chips = Object.entries(filters)
        .filter(([, v]) => v && v !== 'all')
        .map(([k, v]) => `
            <span class="pg-filter-chip">
                <span class="pg-filter-chip__key">${_filterKeyLabel(k)}</span>
                <span class="pg-filter-chip__val">${v}</span>
                <button class="pg-filter-chip__clear" onclick="clearFilter('${k}')" aria-label="Filtreyi kaldır">×</button>
            </span>
        `).join('');

    return `
        <div class="pg-filter-bar">
            <div class="pg-filter-bar__chips" id="activeFilters">
                ${chips || '<span class="pg-filter-bar__empty">Filtre yok — tümü gösteriliyor</span>'}
            </div>
            <div class="pg-filter-bar__actions">
                ${chips ? '<button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="clearAllFilters()">Tümünü Temizle</button>' : ''}
                <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="openFilterPanel()">
                    ${PGIcon.html('filter', 12)} Filtre
                </button>
            </div>
        </div>
    `;
}

function _filterKeyLabel(key) {
    const MAP = {
        status: 'Durum', priority: 'Öncelik', type: 'Tür',
        sprint: 'Sprint', assignee: 'Atanan', module: 'Modül'
    };
    return MAP[key] || key;
}
```

```css
/* static/css/pg-filter.css */
.pg-filter-bar {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-3) var(--pg-sp-4);
    background: var(--pg-color-bg);
    border: 1px solid var(--pg-color-border);
    border-radius: var(--pg-radius-md);
    margin-bottom: var(--pg-sp-4);
    flex-wrap: wrap;
}
.pg-filter-bar__chips { display: flex; gap: var(--pg-sp-2); flex-wrap: wrap; flex: 1; align-items: center; }
.pg-filter-bar__empty { font-size: 12px; color: var(--pg-color-text-tertiary); }
.pg-filter-bar__actions { display: flex; gap: var(--pg-sp-2); flex-shrink: 0; }

.pg-filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--pg-color-surface);
    border: 1px solid var(--pg-color-border-strong);
    border-radius: 20px;
    padding: 3px 8px 3px 10px;
    font-size: 12px;
    color: var(--pg-color-text);
}
.pg-filter-chip__key { color: var(--pg-color-text-tertiary); }
.pg-filter-chip__val { font-weight: 500; }
.pg-filter-chip__clear {
    background: none; border: none;
    color: var(--pg-color-text-tertiary);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 0 2px;
    border-radius: 50%;
    display: flex; align-items: center;
}
.pg-filter-chip__clear:hover { background: var(--pg-color-bg); color: var(--pg-color-negative); }
```

---

### UI-S05-T03 — Inline Detail Panel (Slide-in)

**Dosya:** `static/js/views/backlog.js` + `static/css/pg-panel.css`

Mevcut: item tıklandığında modal açılıyor.
Hedef: Sağ taraftan slide-in panel — kullanıcı listeye bakarken detayı okuyabilir.

```
┌─────────────────────────────────┬───────────────────────┐
│  WRICEF Listesi                 │  WRICEF-042           │
│  ┌─────────────────────────┐    │  ══════════════════   │
│  │ WRICEF-041  GAP  high   │    │  Report               │
│  ├─────────────────────────┤    │  [high] [build]       │
│  │ WRICEF-042  GAP  high   │←── │  Açıklama: ...        │
│  ├─────────────────────────┤    │  Atanan: Ali Y.       │
│  │ WRICEF-043  GAP  medium │    │  Sprint: S3           │
│  └─────────────────────────┘    │  ─────────────────    │
│                                 │  [Düzenle][Kapat ×]   │
└─────────────────────────────────┴───────────────────────┘
```

```javascript
// pg_panel.js — inline slide panel
const PGPanel = (() => {
    let _panelEl = null;

    function open({ title, content, onClose }) {
        close(); // mevcut paneli kapat
        _panelEl = document.createElement('div');
        _panelEl.className = 'pg-panel pg-panel--open';
        _panelEl.innerHTML = `
            <div class="pg-panel__header">
                <h3 class="pg-panel__title">${title}</h3>
                <button class="pg-btn pg-btn--icon pg-panel__close" onclick="PGPanel.close()" aria-label="Kapat">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <div class="pg-panel__body">${content}</div>
        `;
        document.getElementById('main-content').appendChild(_panelEl);
        document.getElementById('main-content').classList.add('has-panel');
        if (typeof onClose === 'function') _panelEl._onClose = onClose;
        // Escape ile kapat
        document.addEventListener('keydown', _escHandler);
    }

    function close() {
        if (!_panelEl) return;
        if (typeof _panelEl._onClose === 'function') _panelEl._onClose();
        _panelEl.classList.remove('pg-panel--open');
        setTimeout(() => { _panelEl && _panelEl.remove(); _panelEl = null; }, 200);
        document.getElementById('main-content').classList.remove('has-panel');
        document.removeEventListener('keydown', _escHandler);
    }

    function _escHandler(e) { if (e.key === 'Escape') close(); }

    return { open, close };
})();
```

```css
/* static/css/pg-panel.css */
.pg-panel {
    position: fixed;
    right: 0; top: var(--pg-header-height, 48px); bottom: 0;
    width: 420px;
    background: var(--pg-color-surface);
    border-left: 1px solid var(--pg-color-border);
    box-shadow: var(--pg-shadow-xl);
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform var(--pg-t-slow, 250ms ease);
    z-index: var(--pg-z-dropdown, 100);
}
.pg-panel--open { transform: translateX(0); }

.pg-panel__header {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-4) var(--pg-sp-5);
    border-bottom: 1px solid var(--pg-color-border);
    background: var(--pg-color-bg);
}
.pg-panel__title { flex: 1; font-size: 14px; font-weight: 600; color: var(--pg-color-text); margin: 0; }
.pg-panel__body  { flex: 1; overflow-y: auto; padding: var(--pg-sp-5); }

/* main-content shrinks when panel is open */
.has-panel { margin-right: 420px; transition: margin-right var(--pg-t-slow); }

@media (max-width: 900px) {
    .pg-panel { width: 100%; }
    .has-panel { margin-right: 0; }
}
```

---

### UI-S05-T04 — Kanban Board Card Refresh

**Dosya:** `static/js/views/backlog.js` — `_renderKanbanCard()` veya benzeri

- Hardcoded border-left renk → `PGStatusRegistry.colors(status).bg`
- Priority badge → `PGStatusRegistry.badge(priority)`
- Kart hover: `transform: translateY(-3px); box-shadow: var(--pg-shadow-md)`
- Boş sütun: `PGEmptyState.html({ icon: 'build', title: 'Bu sütunda item yok' })`

---

### UI-S05-T05 — Sprint Velocity Mikro-Chart

**Dosya:** `static/js/views/backlog.js` — Sprint Planning tab'ında alt widget

Gerçek chart kütüphanesi gerekmez — SVG spark chart yeterli:

```javascript
function _sparkBar(values, color = '#0070f2', height = 32) {
    const max = Math.max(...values, 1);
    const barW = 20;
    const gap  = 4;
    const w    = values.length * (barW + gap) - gap;
    const bars = values.map((v, i) => {
        const h = Math.round(v / max * height);
        const y = height - h;
        return `<rect x="${i * (barW + gap)}" y="${y}" width="${barW}" height="${h}" rx="2" fill="${color}" opacity="${i === values.length - 1 ? 1 : 0.5}"/>`;
    }).join('');
    return `<svg width="${w}" height="${height}" viewBox="0 0 ${w} ${height}" style="overflow:visible">${bars}</svg>`;
}
```

---

## Deliverables Kontrol Listesi

- [x] `backlog.js` `_statusBadge()` / `_priorityBadge()` kaldırıldı
- [x] Tüm backlog badge'leri `PGStatusRegistry.badge()` kullanıyor
- [x] Filtre chip bar list view'da gösteriliyor (aktif filtreler dismissible chip olarak)
- [x] Inline slide panel açılıyor (item tıklanınca — PGPanel)
- [x] Kanban kart hover animasyonu eklendi (`pg-panel.css`)
- [x] Sprint velocity spark bar chart Sprint Planning tab'ında
- [x] Boş Kanban sütunları `PGEmptyState` ile gösteriliyor
- [x] `pg-filter.css` + `pg-panel.css` oluşturuldu, `index.html`'e eklendi
- [x] `pg_panel.js` oluşturuldu, `index.html`'e eklendi

---

*← [UI-S04](./UI-S04-DASHBOARD-PROGRAM-MANAGEMENT.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S06 →](./UI-S06-TEST-MANAGEMENT-RAID.md)*
