/**
 * SAP Transformation Platform — Notification Panel (Sprint 6)
 *
 * Bell icon badge with unread count, dropdown panel,
 * mark-read actions, polling every 30 seconds.
 */
const NotificationPanel = (() => {
    let _pollInterval = null;
    const POLL_MS = 30000;

    // ── Init ─────────────────────────────────────────────────────────────
    function init() {
        const btn = document.querySelector('.shell-header__icon-btn[title="Notifications"]');
        if (!btn) return;

        // Wrap button for badge
        btn.style.position = 'relative';
        btn.insertAdjacentHTML('afterend', `
            <span id="notifBadge" class="notif-badge" style="display:none">0</span>
        `);

        // Build dropdown container
        btn.insertAdjacentHTML('afterend', `
            <div id="notifDropdown" class="notif-dropdown" style="display:none">
                <div class="notif-dropdown__header">
                    <strong>Notifications</strong>
                    <button class="btn btn-sm" onclick="NotificationPanel.markAllRead()">Mark all read</button>
                </div>
                <div class="notif-dropdown__body" id="notifList">
                    <p class="text-muted" style="padding:1rem">Loading…</p>
                </div>
            </div>
        `);

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown();
        });

        document.addEventListener('click', (e) => {
            const dd = document.getElementById('notifDropdown');
            if (dd && !dd.contains(e.target)) dd.style.display = 'none';
        });

        // Initial load + polling
        refreshBadge();
        _pollInterval = setInterval(refreshBadge, POLL_MS);
    }

    // ── Toggle Dropdown ──────────────────────────────────────────────────
    function toggleDropdown() {
        const dd = document.getElementById('notifDropdown');
        if (!dd) return;
        const visible = dd.style.display !== 'none';
        dd.style.display = visible ? 'none' : 'block';
        if (!visible) loadNotifications();
    }

    // ── Badge ────────────────────────────────────────────────────────────
    async function refreshBadge() {
        try {
            const res = await API.get('/notifications/unread-count');
            const badge = document.getElementById('notifBadge');
            if (!badge) return;
            if (res.unread_count > 0) {
                badge.textContent = res.unread_count > 99 ? '99+' : res.unread_count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        } catch {
            // Silently fail on badge refresh
        }
    }

    // ── Load Notifications ───────────────────────────────────────────────
    async function loadNotifications() {
        const list = document.getElementById('notifList');
        if (!list) return;
        try {
            const res = await API.get('/notifications?limit=20');
            if (!res.items.length) {
                list.innerHTML = '<p class="text-muted" style="padding:1rem">No notifications</p>';
                return;
            }
            list.innerHTML = res.items.map(n => `
                <div class="notif-item ${n.is_read ? 'notif-item--read' : ''}"
                     onclick="NotificationPanel.onClickItem(${n.id}, '${n.entity_type}', ${n.entity_id || 'null'})">
                    <div class="notif-item__icon">${_severityIcon(n.severity)}</div>
                    <div class="notif-item__content">
                        <div class="notif-item__title">${n.title}</div>
                        <div class="notif-item__message">${n.message || ''}</div>
                        <div class="notif-item__time">${_timeAgo(n.created_at)}</div>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            list.innerHTML = `<p class="text-muted" style="padding:1rem">⚠️ ${e.message}</p>`;
        }
    }

    // ── Mark Read ────────────────────────────────────────────────────────
    async function markAllRead() {
        try {
            await API.post('/notifications/mark-all-read', {});
            refreshBadge();
            loadNotifications();
            App.toast('All notifications marked as read', 'success');
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function onClickItem(id, entityType, entityId) {
        try {
            await API.patch(`/notifications/${id}/read`);
            refreshBadge();
        } catch { /* ok */ }

        // Navigate to source entity if possible
        const raidTypes = ['risk', 'action', 'issue', 'decision'];
        if (raidTypes.includes(entityType) && entityId) {
            document.getElementById('notifDropdown').style.display = 'none';
            App.navigate('raid');
            setTimeout(() => {
                RaidView.switchTab(entityType + 's');
                setTimeout(() => RaidView.openDetail(entityType + 's', entityId), 200);
            }, 200);
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────
    function _severityIcon(severity) {
        return {info: 'ℹ️', warning: '⚠️', error: '🔴', success: '✅'}[severity] || 'ℹ️';
    }

    function _timeAgo(isoStr) {
        if (!isoStr) return '';
        const diff = Date.now() - new Date(isoStr).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        return `${Math.floor(hrs / 24)}d ago`;
    }

    // ── Cleanup ──────────────────────────────────────────────────────────
    function destroy() {
        if (_pollInterval) clearInterval(_pollInterval);
    }

    return { init, refreshBadge, markAllRead, onClickItem, destroy };
})();
