# UI-S06 — Test Management & RAID Polish

**Sprint:** UI-S06 / 9
**Süre:** 1.5 hafta
**Effort:** M
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md) tamamlanmış olmalı
**Sonraki:** [UI-S07](./UI-S07-COMMAND-PALETTE-POWER-FEATURES.md)

---

## Amaç

Test yönetimi (test case, execution, defect) ve RAID ekranlarının component migration'ını
tamamla. Defect severity + test sonucu görselleştirmesini standartlaştır.
Audit skoru: Test Management 6/10, RAID 5/10 → Hedef: her ikisi için 7.5/10.

---

## Görevler

### UI-S06-T01 — Test Case Listesi Modernizasyonu

**İlgili view dosyaları:** `static/js/views/test-management.js` (veya `app.js` içindeki test render)

- Tüm `_statusBadge()` çağrıları → `PGStatusRegistry.badge()` ile değiştir
- Tablo: `TMDataGrid` kullanımını `pg-tokens.css` ile uyumlu hale getir
- Toolbar butonları: inline HTML → `PGButton.html('+ Test Case', 'primary', { onclick: 'openCreateTC()' })`
- Boş durum: `PGEmptyState.html({ icon: 'test', title: 'Test case bulunamadı' })`
- Breadcrumb: `PGBreadcrumb.html([{ label: 'Test Yönetimi', onclick: 'navigate("test-management")' }, { label: 'Test Case\'ler' }])`

---

### UI-S06-T02 — Test Execution Progress Bar

**Dosya:** test execution view

Test koşusu sırasında adım adım ilerleme gösterimi:

```javascript
function _renderProgressBar({ total, pass, fail, blocked, not_run }) {
    const pctPass    = total ? Math.round(pass    / total * 100) : 0;
    const pctFail    = total ? Math.round(fail    / total * 100) : 0;
    const pctBlocked = total ? Math.round(blocked / total * 100) : 0;
    const pctNotRun  = total ? Math.round(not_run / total * 100) : 0;

    return `
        <div class="pg-progress-bar" title="${pass} geçti · ${fail} başarısız · ${blocked} bloke · ${not_run} koşulmadı">
            <div class="pg-progress-bar__seg pg-progress-bar__seg--pass"    style="width:${pctPass}%"   ></div>
            <div class="pg-progress-bar__seg pg-progress-bar__seg--fail"    style="width:${pctFail}%"   ></div>
            <div class="pg-progress-bar__seg pg-progress-bar__seg--blocked" style="width:${pctBlocked}%"></div>
            <div class="pg-progress-bar__seg pg-progress-bar__seg--not-run" style="width:${pctNotRun}%" ></div>
        </div>
        <div class="pg-progress-legend">
            <span class="pg-progress-legend__item pg-progress-legend__item--pass">${pass} Geçti</span>
            <span class="pg-progress-legend__item pg-progress-legend__item--fail">${fail} Başarısız</span>
            <span class="pg-progress-legend__item pg-progress-legend__item--blocked">${blocked} Bloke</span>
            <span class="pg-progress-legend__item pg-progress-legend__item--not-run">${not_run} Bekliyor</span>
        </div>
    `;
}
```

```css
/* static/css/pg-progress.css */
.pg-progress-bar {
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    background: var(--pg-color-bg);
    gap: 1px;
}
.pg-progress-bar__seg { transition: width var(--pg-t-slow); height: 100%; }
.pg-progress-bar__seg--pass    { background: #16a34a; }
.pg-progress-bar__seg--fail    { background: #dc2626; }
.pg-progress-bar__seg--blocked { background: #ca8a04; }
.pg-progress-bar__seg--not-run { background: var(--pg-color-border-strong); }

.pg-progress-legend {
    display: flex;
    gap: var(--pg-sp-4);
    margin-top: var(--pg-sp-2);
    flex-wrap: wrap;
}
.pg-progress-legend__item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--pg-color-text-secondary);
}
.pg-progress-legend__item::before {
    content: '';
    width: 8px; height: 8px;
    border-radius: 2px;
    display: inline-block;
}
.pg-progress-legend__item--pass::before    { background: #16a34a; }
.pg-progress-legend__item--fail::before    { background: #dc2626; }
.pg-progress-legend__item--blocked::before { background: #ca8a04; }
.pg-progress-legend__item--not-run::before { background: var(--pg-color-border-strong); }
```

---

### UI-S06-T03 — Defect Management Refresh

İlgili view: defect listesi ve defect detay

- Severity badge: `PGStatusRegistry.badge(defect.severity)` — S1, S2, S3, S4 renkleri mevcut
- Status badge: `PGStatusRegistry.badge(defect.status)`
- Kart layout: aynı inline panel yaklaşımı (UI-S05-T03 — `PGPanel.open()`)
- Tablo sıralaması: Severity > Priority > Açılış tarihi (varsayılan)
- Filter chips: status + severity + atanan

```javascript
// Defect satırı render örneği (tokene geçiş)
function _renderDefectRow(d) {
    return `
        <tr class="pg-table-row pg-table-row--clickable" onclick="openDefectDetail(${d.id})">
            <td>${_esc(d.code)}</td>
            <td>${_esc(d.title)}</td>
            <td>${PGStatusRegistry.badge(d.severity)}</td>
            <td>${PGStatusRegistry.badge(d.status)}</td>
            <td>${_esc(d.assignee_name || '–')}</td>
            <td class="pg-table-cell--muted">${_relTime(d.created_at)}</td>
        </tr>
    `;
}
```

---

### UI-S06-T04 — RAID Log Görsel Standardizasyonu

İlgili view: RAID (Risk / Assumption / Issue / Dependency)

Her tür farklı renk ile gösterilmeli:

| Tür | Registry Key | Renk |
|-----|-------------|------|
| Risk | `risk` | Kırmızı |
| Assumption | `assumption` | Mavi |
| Issue | `issue` | Turuncu |
| Dependency | `dependency` | Mor |

```javascript
// RAID item tipi rozeti
function _raidTypeBadge(type) {
    const LABELS = {
        R: 'Risk', A: 'Assumption', I: 'Issue', D: 'Dependency'
    };
    const KEYS = { R: 'risk', A: 'assumption', I: 'issue', D: 'dependency' };
    return PGStatusRegistry.badge(KEYS[type] || type, { label: LABELS[type] || type });
}
```

- RAID grid: 4 sütun (R / A / I / D) ya da toggle list
- Her item satırında: kod, başlık, tür rozeti, etki, sahibi, son güncelleme
- Filtre: tür + etki + durum
- Boş durum per tür: `PGEmptyState.html({ icon: 'raid', title: 'Risk bulunamadı' })`

---

### UI-S06-T05 — Approval View Token Migration

- Bekleyen item'lar: `PGStatusRegistry.badge('pending')` ile işaretlenmiş
- Toolbar: `PGButton.html('Onayla', 'primary')` / `PGButton.html('Reddet', 'danger')`
- List item üzerine gelince satır vurgusu: `background: var(--pg-color-primary-light)`

---

## Deliverables Kontrol Listesi

- [x] Test case listesi tüm badge'leri `PGStatusRegistry` kullanıyor
- [x] Test execution progress bar component tamamlandı
- [x] `pg-progress.css` oluşturuldu, `index.html`'e eklendi
- [x] Defect listesi + severity badge migration tamamlandı
- [x] Defect detail slide panel (`PGPanel`) ile açılıyor
- [x] RAID 4 tip rozeti standartlaştırıldı
- [x] Approval view token migration tamamlandı
- [x] Tüm bu view'larda breadcrumb (`PGBreadcrumb`) eklendi

---

*← [UI-S05](./UI-S05-REQUIREMENT-BACKLOG.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S07 →](./UI-S07-COMMAND-PALETTE-POWER-FEATURES.md)*
