# UI-S04 — Dashboard & Program Management

**Sprint:** UI-S04 / 9
**Süre:** 2 hafta
**Effort:** L
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md) + [UI-S03](./UI-S03-LOGIN-SHELL-REDESIGN.md) tamamlanmış olmalı
**Sonraki:** [UI-S05](./UI-S05-REQUIREMENT-BACKLOG.md)

---

## Amaç

Karşılama ekranı (Dashboard) gerçek program sağlığını göstermeli; kullanıcı açıştığında
"bugün ne durumda ve ne yapmam gerekiyor?" sorusunu 5 saniyede yanıtlamalı.
Mevcut durum: 6 statik KPI card + emoji buton grid. Hedef: health score + cross-proje görünürlük.

---

## Görevler

### UI-S04-T01 — Dashboard Yeniden Tasarımı

**Dosya:** `static/js/app.js` — `renderDashboard()` fonksiyonu

```
┌──────────────────────────────────────────────────────────────┐
│  Günaydın, [Ad]  ·  [Proje Seç ▾]        Bugün: 15 Oca 2026│
├────────────────────────┬─────────────────────────────────────┤
│  Program Sağlığı       │  Aksiyon Gerektiren               │
│  ██████░░  72/100      │  ⚠ 3 Kritik defect açık           │
│  ● 245 Gereksinim      │  ⚠ 2 Onay bekleyen               │
│  ● 78% Test coverage   │  ⚠ 1 Bloke WRICEF                 │
│  ● 4 Kritik issue      │                                    │
├────┬────┬────┬────┬────┼─────────────────────────────────────┤
│ 📄 │ ⚙️ │ 🧪 │ 🐛 │ 🛡 │  Son Aktivite (24s)              │
│ Gereksinim │ Test│    │  • [User] GAP-042 oluşturdu         │
│ 245 │ 48 │ 192│ 7  │ 3│  • [User] TC-108 pass olarak işaretledi│
└────┴────┴────┴────┴────┴─────────────────────────────────────┘
```

**`renderDashboard()` yeniden yazılacak:**
```javascript
async function renderDashboard() {
    const main = document.getElementById('main-content');
    // Skeleton göster
    main.innerHTML = `
        <div class="pg-view-header">
            ${PGBreadcrumb.html([{ label: 'Dashboard' }])}
            <h2 class="pg-view-title">Dashboard</h2>
        </div>
        <div id="dashboard-grid" class="pg-dashboard-grid">
            ${PGSkeleton.card()}${PGSkeleton.card()}${PGSkeleton.card()}
        </div>
    `;

    try {
        // Paralel API çağrıları
        const [summary, actions, recent] = await Promise.all([
            api('/api/v1/dashboard/summary'),
            api('/api/v1/dashboard/actions'),
            api('/api/v1/dashboard/recent-activity')
        ]);
        _renderDashboardContent(summary, actions, recent);
    } catch (err) {
        document.getElementById('dashboard-grid').innerHTML =
            PGEmptyState.html({ icon: 'dashboard', title: 'Veri yüklenemedi', description: err.message });
    }
}

function _renderDashboardContent(summary, actions, recent) {
    const score = summary.health_score || 0;
    const scoreColor = score >= 75 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626';

    document.getElementById('dashboard-grid').innerHTML = `
        <!-- Health Score Card -->
        <div class="pg-dash-card pg-dash-card--health">
            <div class="pg-dash-card__header">Program Sağlığı</div>
            <div class="pg-health-score">
                <svg class="pg-health-score__ring" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="34" fill="none" stroke="var(--pg-color-border)" stroke-width="6"/>
                    <circle cx="40" cy="40" r="34" fill="none" stroke="${scoreColor}" stroke-width="6"
                        stroke-dasharray="${Math.round(2 * Math.PI * 34 * score / 100)} ${Math.round(2 * Math.PI * 34 * (1 - score / 100))}"
                        stroke-dashoffset="${Math.round(2 * Math.PI * 34 * 0.25)}"
                        stroke-linecap="round"/>
                    <text x="40" y="40" dominant-baseline="middle" text-anchor="middle"
                        font-size="16" font-weight="700" fill="${scoreColor}">${score}</text>
                </svg>
                <div class="pg-health-score__meta">
                    <span style="color:${scoreColor};font-weight:700">${_healthLabel(score)}</span>
                    <span class="pg-health-score__items">${summary.requirements || 0} gereksinim · ${Math.round((summary.test_coverage || 0))}% test</span>
                </div>
            </div>
        </div>

        <!-- KPI Cards -->
        <div class="pg-dash-kpis">
            ${_kpi('Gereksinim', summary.requirements, 'requirements', 'requirements')}
            ${_kpi('WRICEF', summary.wricef_items, 'backlog', 'build')}
            ${_kpi('Test Case', summary.test_cases, 'test-management', 'test')}
            ${_kpi('Defect', summary.open_defects, 'defects', 'defect')}
            ${_kpi('RAID', summary.open_risks, 'raid', 'raid')}
        </div>

        <!-- Actions -->
        <div class="pg-dash-card pg-dash-card--actions">
            <div class="pg-dash-card__header">Aksiyon Gerektiren</div>
            ${!actions.length
                ? '<p class="pg-dash-empty">Bekleyen aksiyon yok 🎉</p>'
                : actions.slice(0, 5).map(a => `
                    <div class="pg-dash-action" onclick="navigate('${a.view}')">
                        <span class="pg-dash-action__icon">${PGStatusRegistry.badge(a.severity || 'warning')}</span>
                        <span class="pg-dash-action__text">${_esc(a.message)}</span>
                        <span class="pg-dash-action__arrow">→</span>
                    </div>
                `).join('')
            }
        </div>

        <!-- Recent Activity -->
        <div class="pg-dash-card pg-dash-card--activity">
            <div class="pg-dash-card__header">Son Aktivite <span class="pg-dash-card__meta">24 saat</span></div>
            ${!recent.length
                ? '<p class="pg-dash-empty">Aktivite bulunamadı</p>'
                : recent.slice(0, 8).map(r => `
                    <div class="pg-dash-activity-row">
                        <div class="pg-dash-activity-row__avatar">${(r.user_name || 'U')[0].toUpperCase()}</div>
                        <div class="pg-dash-activity-row__body">
                            <span class="pg-dash-activity-row__user">${_esc(r.user_name || 'Sistem')}</span>
                            <span class="pg-dash-activity-row__action">${_esc(r.action)}</span>
                            <span class="pg-dash-activity-row__object">${_esc(r.object_code || '')}</span>
                        </div>
                        <span class="pg-dash-activity-row__time">${_relTime(r.created_at)}</span>
                    </div>
                `).join('')
            }
        </div>
    `;
}

function _kpi(label, value, view, icon) {
    return `
        <div class="pg-kpi-card" onclick="navigate('${view}')" role="button" tabindex="0">
            <div class="pg-kpi-card__icon">${PGIcon ? PGIcon.html(icon, 20) : ''}</div>
            <div class="pg-kpi-card__value">${value ?? '–'}</div>
            <div class="pg-kpi-card__label">${label}</div>
        </div>
    `;
}

function _healthLabel(score) {
    if (score >= 85) return 'Mükemmel';
    if (score >= 70) return 'İyi';
    if (score >= 50) return 'Orta';
    return 'İyileştirme Gerekli';
}

function _relTime(iso) {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Az önce';
    if (mins < 60) return `${mins}d önce`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}s önce`;
    return `${Math.floor(hrs / 24)}g önce`;
}
```

---

### UI-S04-T02 — Dashboard CSS

**Dosya:** `static/css/pg-dashboard.css`

```css
/* static/css/pg-dashboard.css */
.pg-view-header { margin-bottom: var(--pg-sp-6); }
.pg-view-title { font-size: 20px; font-weight: 700; color: var(--pg-color-text); margin: 0 0 var(--pg-sp-2); }

/* Dashboard grid */
.pg-dashboard-grid {
    display: grid;
    grid-template-columns: 280px 1fr 300px;
    grid-template-rows: auto auto;
    gap: var(--pg-sp-5);
    align-items: start;
}

/* Base card */
.pg-dash-card {
    background: var(--pg-color-surface);
    border: 1px solid var(--pg-color-border);
    border-radius: var(--pg-radius-lg);
    padding: var(--pg-sp-6);
    box-shadow: var(--pg-shadow-sm);
}
.pg-dash-card__header {
    font-size: 11px;
    font-weight: 600;
    color: var(--pg-color-text-tertiary);
    letter-spacing: 0.6px;
    text-transform: uppercase;
    margin-bottom: var(--pg-sp-4);
    display: flex;
    align-items: center;
    gap: var(--pg-sp-2);
}
.pg-dash-card__meta { font-weight: 400; font-size: 11px; color: var(--pg-color-text-tertiary); margin-left: auto; }

/* Health card */
.pg-health-score { display: flex; align-items: center; gap: var(--pg-sp-4); }
.pg-health-score__ring { width: 80px; height: 80px; flex-shrink: 0; }
.pg-health-score__meta { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.pg-health-score__items { font-size: 11px; color: var(--pg-color-text-tertiary); line-height: 1.5; }

/* KPI row */
.pg-dash-kpis {
    display: grid;
    grid-column: 1 / -1;
    grid-template-columns: repeat(5, 1fr);
    gap: var(--pg-sp-4);
}

.pg-kpi-card {
    background: var(--pg-color-surface);
    border: 1px solid var(--pg-color-border);
    border-radius: var(--pg-radius-lg);
    padding: var(--pg-sp-5) var(--pg-sp-4);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--pg-sp-1);
    cursor: pointer;
    transition: all var(--pg-t-normal);
    box-shadow: var(--pg-shadow-sm);
}
.pg-kpi-card:hover { border-color: var(--pg-color-primary); box-shadow: var(--pg-shadow-md); transform: translateY(-2px); }
.pg-kpi-card__icon { color: var(--pg-color-text-tertiary); }
.pg-kpi-card__value { font-size: 28px; font-weight: 800; color: var(--pg-color-text); letter-spacing: -1px; line-height: 1; }
.pg-kpi-card__label { font-size: 12px; color: var(--pg-color-text-secondary); }

/* Action rows */
.pg-dash-action {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-3) 0;
    border-bottom: 1px solid var(--pg-color-border);
    cursor: pointer;
    transition: background var(--pg-t-fast);
    border-radius: var(--pg-radius-sm);
}
.pg-dash-action:last-child { border-bottom: none; }
.pg-dash-action:hover { background: var(--pg-color-bg); }
.pg-dash-action__text { flex: 1; font-size: 13px; color: var(--pg-color-text); }
.pg-dash-action__arrow { color: var(--pg-color-text-tertiary); font-size: 14px; }

/* Activity feed */
.pg-dash-activity-row {
    display: flex;
    align-items: flex-start;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-3) 0;
    border-bottom: 1px solid var(--pg-color-border);
}
.pg-dash-activity-row:last-child { border-bottom: none; }
.pg-dash-activity-row__avatar {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: var(--pg-color-primary-light, #ebf5ff);
    color: var(--pg-color-primary);
    font-size: 11px;
    font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.pg-dash-activity-row__body { flex: 1; font-size: 12px; line-height: 1.5; color: var(--pg-color-text-secondary); }
.pg-dash-activity-row__user { font-weight: 600; color: var(--pg-color-text); }
.pg-dash-activity-row__time { font-size: 11px; color: var(--pg-color-text-tertiary); white-space: nowrap; }

.pg-dash-empty { color: var(--pg-color-text-tertiary); font-size: 13px; padding: var(--pg-sp-4) 0; text-align: center; }
```

---

### UI-S04-T03 — Program Management View Güncelleme

**Dosya:** `static/js/views/programs.js` (var ise) veya `app.js` içindeki program render fonksiyonu

- `TMDataGrid` kullanımını doğrula, yeni token'lar ile test et
- Program kartları üzerinde health score chip: `PGStatusRegistry.badge()`
- Boş durum: `PGEmptyState.html({ icon: 'programs', title: 'Henüz program yok', action: { label: '+ Yeni Program', onclick: 'openCreateProgram()' } })`

---

## Deliverables Kontrol Listesi

- [x] `renderDashboard()` yeniden yazıldı, API endpoint'leri mevcut
- [x] Health score ring SVG animasyonlu
- [x] KPI card'lar ilgili view'a navigate ediyor
- [x] Action feed çalışıyor (API varsa)
- [x] Recent activity feed 24 saatlik aktivite gösteriyor
- [x] `pg-dashboard.css` oluşturuldu ve `index.html`'e eklendi
- [x] Skeleton loader gösteriliyor API çağrısı süresince
- [x] Error state `PGEmptyState` ile gösteriliyor
- [x] Program management view token migration tamamlandı

---

*← [UI-S03](./UI-S03-LOGIN-SHELL-REDESIGN.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S05 →](./UI-S05-REQUIREMENT-BACKLOG.md)*
