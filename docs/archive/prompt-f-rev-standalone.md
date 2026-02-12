# PROMPT F-REV — KPI Dashboard Standardization (Revised)

Prompt F aynen geçerli, ek olarak tespit edilen sorunları da dahil ediyorum.

## Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `static/js/components/explore-shared.js` | kpiBlock v2 + metricBar yeni component |
| `static/css/explore-tokens.css` | .exp-kpi-strip nowrap, .exp-kpi-card compact, .exp-metric-bar yeni |
| `static/js/views/explore_hierarchy.js` | 4 KPI + metricBar (zaten fitBarMini var, metricBar ile replace) |
| `static/js/views/explore_workshops.js` | 8 KPI → 5 KPI + metricBar |
| `static/js/views/explore_dashboard.js` | 5 KPI → emoji kaldır, accent düzelt |
| `static/js/views/explore_requirements.js` | 9 KPI → 5 KPI + metricBar, 7 OI KPI → 4 KPI |
| `static/js/views/raid.js` | raid-kpi → ExpUI.kpiBlock (tutarlılık) |

## Bölüm 1: ExpUI.kpiBlock v2 (explore-shared.js)

Mevcut `kpiBlock` fonksiyonunu güncelle:

```javascript
function kpiBlock(opts = {}) {
    const accent = opts.accent || 'var(--sap-blue)';
    // icon parametresini artık render etme (backward compat: parametre kabul et, ignore et)
    const trendColors = { up: '#10B981', down: '#EF4444', flat: '#94A3B8' };
    const trendIcons  = { up: '↑', down: '↓', flat: '→' };
    const trendHtml = opts.trend
        ? `<span style="font-size:11px;font-weight:600;color:${trendColors[opts.trend] || '#94A3B8'};margin-left:6px">${trendIcons[opts.trend] || ''}${opts.trendValue ? ' ' + esc(opts.trendValue) : ''}</span>`
        : '';
    const suffix = opts.suffix ? `<span style="font-size:14px;font-weight:400">${esc(opts.suffix)}</span>` : '';
    const subHtml = opts.sub ? `<div class="exp-kpi-card__sub">${esc(opts.sub)}</div>` : '';

    return `<div class="exp-kpi-card">
        <div class="exp-kpi-card__value" style="color:${accent}">${esc(String(opts.value ?? '—'))}${suffix}${trendHtml}</div>
        <div class="exp-kpi-card__label">${esc(opts.label || '')}</div>
        ${subHtml}
    </div>`;
}
```

**Değişiklikler:**
- `icon` parametresi: kabul et ama artık HTML render etme (emoji yok)
- `sub` parametresi: yeni — alt metin (gri, küçük) — örnek: "2 critical"
- `accent`: varsayılan `var(--sap-blue)`

## Bölüm 2: ExpUI.metricBar (explore-shared.js — YENİ)

```javascript
/**
 * Compact distribution bar with inline legend
 * @param {Object} opts
 * @param {string} [opts.label] — "Fit Distribution"
 * @param {Array} opts.segments — [{value, label, color}]
 * @param {number} [opts.total] — auto-calculated if omitted
 * @param {number} [opts.height] — bar height px, default 6
 */
function metricBar(opts = {}) {
    const total = opts.total || opts.segments.reduce((s, seg) => s + (seg.value || 0), 0) || 1;
    const h = opts.height || 6;
    
    const barSegs = opts.segments.map(seg => {
        const pct = Math.round((seg.value / total) * 100);
        if (pct === 0) return '';
        return `<div style="flex:${seg.value};height:${h}px;background:${seg.color};border-radius:${h/2}px" title="${esc(seg.label)}: ${pct}%"></div>`;
    }).join('');
    
    const legend = opts.segments.map(seg => {
        const pct = Math.round((seg.value / total) * 100);
        return `<span style="display:inline-flex;align-items:center;gap:3px">
            <span style="width:6px;height:6px;border-radius:50%;background:${seg.color}"></span>
            <span>${esc(seg.label)} ${pct}%</span>
        </span>`;
    }).join('');
    
    return `<div class="exp-metric-bar">
        ${opts.label ? `<div class="exp-metric-bar__label">${esc(opts.label)}</div>` : ''}
        <div style="display:flex;gap:2px;border-radius:${h/2}px;overflow:hidden;background:#f1f5f9">${barSegs}</div>
        <div class="exp-metric-bar__legend">${legend}</div>
    </div>`;
}
```

**Return statement'a ekle:** `metricBar,`

## Bölüm 3: CSS (explore-tokens.css)

### .exp-kpi-strip — nowrap
```css
/* REPLACE existing .exp-kpi-strip */
.exp-kpi-strip {
    display: flex;
    gap: var(--exp-space-sm);       /* md → sm: daha sıkı */
    flex-wrap: nowrap;              /* wrap → nowrap: TEK SATIR */
    overflow-x: auto;              /* YENİ: çok sıkışırsa scroll */
    padding-bottom: 2px;
    margin-bottom: var(--exp-space-md);
}
```

### .exp-kpi-card — compact
```css
/* REPLACE existing .exp-kpi-card */
.exp-kpi-card {
    flex: 1 1 0;                   /* 1 1 140px → 1 1 0: eşit dağılım */
    min-width: 100px;              /* 130 → 100: daha dar */
    max-width: 200px;              /* YENİ: max genişlik */
    background: var(--exp-kpi-bg);
    border: 1px solid var(--exp-kpi-border);
    border-radius: var(--exp-kpi-radius);
    padding: 14px 16px;            /* var(--exp-kpi-padding) → sabit compact */
    box-shadow: var(--exp-kpi-shadow);
    transition: box-shadow var(--exp-transition);
}

/* YENİ sub class */
.exp-kpi-card__sub {
    font-size: 11px;
    color: #94a3b8;
    margin-top: 2px;
}
```

### .exp-kpi-card__value — smaller
```css
/* REPLACE */
.exp-kpi-card__value {
    font-size: 24px;               /* 28 → 24 */
    font-weight: 700;
    line-height: 1;
    color: var(--sap-text-primary);
}
```

### .exp-kpi-card__label — tighter
```css
/* REPLACE */
.exp-kpi-card__label {
    font-size: 11px;               /* 12 → 11 */
    font-weight: 600;
    color: var(--sap-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-top: 4px;
}
```

### .exp-metric-bar — YENİ
```css
.exp-metric-bar {
    padding: 12px 16px;
    background: #fff;
    border: 1px solid var(--exp-kpi-border);
    border-radius: var(--exp-kpi-radius);
    margin-bottom: var(--exp-space-md);
}
.exp-metric-bar__label {
    font-size: 11px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 8px;
}
.exp-metric-bar__legend {
    display: flex; gap: 16px; flex-wrap: wrap;
    margin-top: 6px; font-size: 11px; color: #64748b;
}
```

### Responsive — mobile'da da uygun
```css
/* Mevcut @media bloğu içine ekle/güncelle */
@media (max-width: 768px) {
    .exp-kpi-strip {
        gap: var(--exp-space-xs);
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    .exp-kpi-card {
        min-width: 90px;
        padding: 10px 12px;
    }
    .exp-kpi-card__value {
        font-size: 20px;
    }
}
```

## Bölüm 4: Explore Dashboard (explore_dashboard.js)

**Sadece emoji kaldır, sayı tutarlı (5 KPI — zaten ideal):**

FIND:
```javascript
${ExpUI.kpiBlock({ value: wsTotal, label: 'Workshops', icon: '📋' })}
${ExpUI.kpiBlock({ value: wsRate + '%', label: 'WS Completion', accent: wsRate >= 80 ? 'var(--exp-fit)' : wsRate >= 50 ? 'var(--exp-partial)' : 'var(--exp-gap)' })}
${ExpUI.kpiBlock({ value: reqTotal, label: 'Requirements', icon: '📝' })}
${ExpUI.kpiBlock({ value: oiOpen, label: 'Open Items', accent: 'var(--exp-open-item)' })}
${ExpUI.kpiBlock({ value: oiOverdue, label: 'Overdue OIs', accent: oiOverdue > 0 ? 'var(--exp-gap)' : 'var(--exp-fit)', icon: oiOverdue > 0 ? '🔴' : '✅' })}
```
REPLACE:
```javascript
${ExpUI.kpiBlock({ value: wsTotal, label: 'Workshops', accent: 'var(--exp-l2)' })}
${ExpUI.kpiBlock({ value: wsRate + '%', label: 'WS Completion', accent: wsRate >= 80 ? 'var(--exp-fit)' : wsRate >= 50 ? '#f59e0b' : 'var(--exp-gap)' })}
${ExpUI.kpiBlock({ value: reqTotal, label: 'Requirements', accent: 'var(--exp-requirement)' })}
${ExpUI.kpiBlock({ value: oiOpen, label: 'Open Items', accent: 'var(--exp-open-item)' })}
${ExpUI.kpiBlock({ value: oiOverdue, label: 'Overdue OIs', accent: oiOverdue > 0 ? 'var(--exp-gap)' : 'var(--exp-fit)' })}
```

## Bölüm 5: Process Hierarchy (explore_hierarchy.js)

Zaten fitBarMini var — ama hâlâ emoji ikonları kullanıyor. Bunları kaldır:

FIND (4 satır):
```javascript
${ExpUI.kpiBlock({ value: _l1List.length, label: 'L1 Areas', icon: '🏛️' })}
${ExpUI.kpiBlock({ value: _l2List.length, label: 'L2 Groups', icon: '📂' })}
${ExpUI.kpiBlock({ value: _l3List.length, label: 'L3 Scope Items', icon: '📋' })}
${ExpUI.kpiBlock({ value: _l4List.length, label: 'L4 Steps', icon: '⚙️' })}
```
REPLACE:
```javascript
${ExpUI.kpiBlock({ value: _l1List.length, label: 'L1 Areas', accent: 'var(--exp-l1, #8b5cf6)' })}
${ExpUI.kpiBlock({ value: _l2List.length, label: 'L2 Groups', accent: 'var(--exp-l2, #3b82f6)' })}
${ExpUI.kpiBlock({ value: _l3List.length, label: 'L3 Scope Items', accent: 'var(--exp-l3, #10b981)' })}
${ExpUI.kpiBlock({ value: _l4List.length, label: 'L4 Steps', accent: 'var(--exp-l4, #f59e0b)' })}
```

**Fit Distribution bölümü:** Zaten fitBarMini ile yapılmış, dokunmaya gerek yok. ✅

## Bölüm 6: Workshop Hub (explore_workshops.js) — EN BÜYÜK DEĞİŞİKLİK

Mevcut: 8 KPI — taşma sorunu var
Hedef: 5 KPI + metricBar

FIND (~line 88-96):
```javascript
return `<div class="exp-kpi-strip">
    ${ExpUI.kpiBlock({ value: total, label: 'Total Workshops', icon: '📋' })}
    ${ExpUI.kpiBlock({ value: `${pct}%`, label: 'Progress', accent: 'var(--exp-fit)', icon: '📈' })}
    ${ExpUI.kpiBlock({ value: active, label: 'Active', accent: 'var(--exp-partial)', icon: '▶️' })}
    ${ExpUI.kpiBlock({ value: scheduled, label: 'Scheduled', accent: 'var(--exp-requirement)', icon: '📅' })}
    ${ExpUI.kpiBlock({ value: draft, label: 'Draft', icon: '📝' })}
    ${ExpUI.kpiBlock({ value: totalOI, label: 'Open Items', accent: 'var(--exp-open-item)', icon: '⚠️' })}
    ${ExpUI.kpiBlock({ value: totalGaps, label: 'Gaps', accent: 'var(--exp-gap)', icon: '🔴' })}
    ${ExpUI.kpiBlock({ value: totalReq, label: 'Requirements', accent: 'var(--exp-requirement)', icon: '📝' })}
</div>`;
```

REPLACE:
```javascript
return `<div class="exp-kpi-strip">
    ${ExpUI.kpiBlock({ value: total, label: 'Workshops', accent: 'var(--exp-l2, #3b82f6)' })}
    ${ExpUI.kpiBlock({ value: pct + '%', label: 'Progress', accent: pct >= 80 ? 'var(--exp-fit)' : pct >= 50 ? '#f59e0b' : 'var(--exp-gap)' })}
    ${ExpUI.kpiBlock({ value: active, label: 'Active', accent: '#3b82f6' })}
    ${ExpUI.kpiBlock({ value: totalOI, label: 'Open Items', accent: 'var(--exp-open-item)' })}
    ${ExpUI.kpiBlock({ value: totalGaps, label: 'Gaps', accent: 'var(--exp-gap)' })}
</div>
${ExpUI.metricBar({
    label: 'Workshop Status',
    total: total || 1,
    segments: [
        {value: completed || 0, label: 'Completed', color: 'var(--exp-fit)'},
        {value: active || 0, label: 'Active', color: '#3b82f6'},
        {value: scheduled || 0, label: 'Scheduled', color: '#f59e0b'},
        {value: draft || 0, label: 'Draft', color: '#94a3b8'},
    ],
})}`;
```

**Not:** `completed` değişkenini hesaplamaya ekle — muhtemelen `data.completed` veya `total - active - scheduled - draft` gibi.

## Bölüm 7: Requirements (explore_requirements.js)

İki ayrı KPI strip var. İkisini de sadeleştir.

### Requirements Tab (~line 60-69, 9 KPI → 5 + metricBar)

FIND:
```javascript
${ExpUI.kpiBlock({ value: total, label: 'Total', icon: '📝' })}
${ExpUI.kpiBlock({ value: p1, label: 'P1 Critical', accent: 'var(--exp-p1)', icon: '🔴' })}
${ExpUI.kpiBlock({ value: draft, label: 'Draft' })}
${ExpUI.kpiBlock({ value: review, label: 'Under Review', accent: 'var(--exp-partial)' })}
${ExpUI.kpiBlock({ value: approved, label: 'Approved', accent: 'var(--exp-fit)' })}
${ExpUI.kpiBlock({ value: backlog, label: 'In Backlog', accent: 'var(--exp-requirement)' })}
${ExpUI.kpiBlock({ value: realized, label: 'Realized', accent: 'var(--exp-decision)' })}
${ExpUI.kpiBlock({ value: almSynced, label: 'ALM Synced', icon: '🔗' })}
${ExpUI.kpiBlock({ value: totalEffort, label: 'Total Effort', suffix: ' days' })}
```

REPLACE:
```javascript
${ExpUI.kpiBlock({ value: total, label: 'Requirements', accent: 'var(--exp-requirement)' })}
${ExpUI.kpiBlock({ value: p1, label: 'P1 Critical', accent: 'var(--exp-gap)' })}
${ExpUI.kpiBlock({ value: approved, label: 'Approved', accent: 'var(--exp-fit)' })}
${ExpUI.kpiBlock({ value: backlog, label: 'In Backlog', accent: '#3b82f6' })}
${ExpUI.kpiBlock({ value: totalEffort, label: 'Effort', accent: '#64748b', suffix: ' days' })}
</div>
${ExpUI.metricBar({
    label: 'Status Distribution',
    total: total || 1,
    segments: [
        {value: draft, label: 'Draft', color: '#94a3b8'},
        {value: review, label: 'Review', color: '#f59e0b'},
        {value: approved, label: 'Approved', color: 'var(--exp-fit)'},
        {value: backlog, label: 'Backlog', color: '#3b82f6'},
        {value: realized, label: 'Realized', color: 'var(--exp-decision)'},
    ],
})}
```
**Not:** Kapanış `</div>` ve `metricBar` strip'in dışına çıkmalı (return ifadesini düzenle).

### Open Items Tab (~line 218-225, 7 KPI → 4)

FIND:
```javascript
${ExpUI.kpiBlock({ value: total, label: 'Total', icon: '⚠️' })}
${ExpUI.kpiBlock({ value: open, label: 'Open', accent: 'var(--exp-open-item)' })}
${ExpUI.kpiBlock({ value: inProg, label: 'In Progress', accent: 'var(--exp-requirement)' })}
${ExpUI.kpiBlock({ value: blocked, label: 'Blocked', accent: 'var(--exp-gap)' })}
${ExpUI.kpiBlock({ value: closed, label: 'Closed', accent: 'var(--exp-fit)' })}
${ExpUI.kpiBlock({ value: overdue, label: 'Overdue', accent: 'var(--exp-gap)', icon: '🔴' })}
${ExpUI.kpiBlock({ value: p1Open, label: 'P1 Open', accent: 'var(--exp-p1)', icon: '🔴' })}
```

REPLACE:
```javascript
${ExpUI.kpiBlock({ value: total, label: 'Open Items', accent: 'var(--exp-open-item)' })}
${ExpUI.kpiBlock({ value: open, label: 'Open', accent: '#3b82f6' })}
${ExpUI.kpiBlock({ value: overdue, label: 'Overdue', accent: 'var(--exp-gap)' })}
${ExpUI.kpiBlock({ value: p1Open, label: 'P1 Open', accent: 'var(--exp-p1)' })}
```

## Bölüm 8: RAID (raid.js) — KPI Tutarlılık

Mevcut: Özel `.raid-kpi` CSS class'ı (Prompt E'de yapıldı)
Hedef: ExpUI.kpiBlock kullan — diğer sayfalarla tutarlı

**render() içinde** `<div id="raidStats"></div>` olarak bırak (değişmez).

**loadStats() içinde** FIND (~line 92-130):
```javascript
document.getElementById('raidStats').innerHTML = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;height:100%">
        <div class="raid-kpi">
            ... (4 adet raid-kpi card)
        </div>
    </div>
`;
```

REPLACE:
```javascript
document.getElementById('raidStats').innerHTML = `
    <div class="exp-kpi-strip" style="flex-wrap:wrap">
        ${ExpUI.kpiBlock({ value: s.risks.open, label: 'Open Risks', accent: '#dc2626', sub: s.risks.critical > 0 ? s.risks.critical + ' critical' : '' })}
        ${ExpUI.kpiBlock({ value: s.actions.open, label: 'Open Actions', accent: '#3b82f6', sub: s.actions.overdue > 0 ? s.actions.overdue + ' overdue' : '' })}
        ${ExpUI.kpiBlock({ value: s.issues.open, label: 'Open Issues', accent: '#f59e0b', sub: s.issues.critical > 0 ? s.issues.critical + ' critical' : '' })}
        ${ExpUI.kpiBlock({ value: s.decisions.pending, label: 'Pending Decisions', accent: '#8b5cf6', sub: s.decisions.total + ' total' })}
    </div>
`;
```

**Not:** RAID'de 4 KPI + yan yana heatmap olduğu için `flex-wrap:wrap` kalabilir (2x2 grid layout'u zaten grid ile yapılıyor).

**CSS temizliği:** `.raid-kpi`, `.raid-kpi__icon`, `.raid-kpi__value`, `.raid-kpi__label`, `.raid-kpi__alert`, `.raid-kpi__alert--warn` class'ları **main.css'ten KALDIRILABİLİR** — artık ExpUI.kpiBlock kullanılacak.

## Bölüm 9: CSS Variables — Semantic Level Colors

**explore-tokens.css'e ekle** (henüz yoksa):
```css
:root {
    --exp-l1: #8b5cf6;
    --exp-l2: #3b82f6;
    --exp-l3: #10b981;
    --exp-l4: #f59e0b;
}
```

---

## Verification Checklist

- [ ] `kpiBlock` emoji render etmiyor (icon param ignored)
- [ ] `kpiBlock` sub param çalışıyor
- [ ] `metricBar` component render oluyor (bar + legend)
- [ ] `.exp-kpi-strip` tek satır (nowrap)
- [ ] Dashboard: 5 KPI, emoji yok
- [ ] Hierarchy: 4 KPI + fit bar, emoji yok
- [ ] Workshop: 5 KPI + metricBar, 2. satır yok
- [ ] Requirements: 5 KPI + metricBar
- [ ] OIs: 4 KPI, emoji yok
- [ ] RAID: ExpUI.kpiBlock, sub label gösteriyor
- [ ] Mobile responsive (scroll/compact)
- [ ] CSS: .raid-kpi classes silinmiş (optional)
- [ ] CSS: --exp-l1..l4 variables tanımlı

## Commit
```
refactor(ui): standardize KPI dashboards — remove emojis, add metricBar, max 5 primary KPIs, flex-nowrap
```

## Effort: ~3h
