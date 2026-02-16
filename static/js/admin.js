/* ═══════════════════════════════════════════════════════════════
   Admin SPA — SAP Transformation Platform
   Sprint 4: Tenant Admin MVP
   ═══════════════════════════════════════════════════════════════ */

// ── Auth Manager ────────────────────────────────────────────
const AdminAuth = {
    TOKEN_KEY: "admin_access_token",
    REFRESH_KEY: "admin_refresh_token",
    USER_KEY: "admin_user",
    _refreshTimer: null,

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY) || localStorage.getItem('sap_access_token');
    },

    getUser() {
        try {
            return JSON.parse(localStorage.getItem(this.USER_KEY) || "null");
        } catch { return null; }
    },

    setTokens(access, refresh) {
        localStorage.setItem(this.TOKEN_KEY, access);
        if (refresh) localStorage.setItem(this.REFRESH_KEY, refresh);
        this._scheduleRefresh();
    },

    setUser(user) {
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    },

    headers() {
        const t = this.getToken();
        return t ? { "Authorization": "Bearer " + t, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    async checkAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = "/admin/login";
            return false;
        }
        try {
            const res = await fetch("/api/v1/auth/me", { headers: this.headers() });
            if (!res.ok) throw new Error("Unauthorized");
            const data = await res.json();
            this.setUser(data.user);
            return true;
        } catch {
            await this.tryRefresh();
            return this.isAuthenticated();
        }
    },

    async tryRefresh() {
        const rt = localStorage.getItem(this.REFRESH_KEY);
        if (!rt) return this.logout();
        try {
            const res = await fetch("/api/v1/auth/refresh", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: rt }),
            });
            if (!res.ok) throw new Error("Refresh failed");
            const data = await res.json();
            this.setTokens(data.access_token, data.refresh_token);
        } catch {
            this.logout();
        }
    },

    _scheduleRefresh() {
        if (this._refreshTimer) clearTimeout(this._refreshTimer);
        // Refresh 1 minute before expiry (token lives 15min = 900s)
        this._refreshTimer = setTimeout(() => this.tryRefresh(), 13 * 60 * 1000);
    },

    logout() {
        const token = this.getToken();
        if (token) {
            fetch("/api/v1/auth/logout", {
                method: "POST",
                headers: { "Authorization": "Bearer " + token, "Content-Type": "application/json" },
            }).catch(() => {});
        }
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_KEY);
        localStorage.removeItem(this.USER_KEY);
        if (this._refreshTimer) clearTimeout(this._refreshTimer);
        window.location.href = "/admin/login";
    },
};

// ── API helper ──────────────────────────────────────────────
async function api(path, opts = {}) {
    const { method = "GET", body } = opts;
    const config = { method, headers: AdminAuth.headers() };
    if (body) config.body = JSON.stringify(body);
    const res = await fetch(path, config);
    const data = res.headers.get("content-type")?.includes("json") ? await res.json() : {};
    if (!res.ok) {
        const msg = data.error || `HTTP ${res.status}`;
        throw new Error(msg);
    }
    return data;
}

// ── Toast ───────────────────────────────────────────────────
function showToast(message, type = "success") {
    let container = document.querySelector(".toast-container");
    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `${type === "success" ? "✓" : "✕"} ${_esc(message)}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── HTML escape ─────────────────────────────────────────────
function _esc(s) {
    if (s == null) return "";
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
}

// ── Main Admin Module ───────────────────────────────────────
const Admin = {
    currentView: "dashboard",
    _cache: {},

    // ── Init ────────────────────────────────────────────────
    async init() {
        const ok = await AdminAuth.checkAuth();
        if (!ok) return;

        const user = AdminAuth.getUser();
        if (user) {
            document.getElementById("userName").textContent = user.full_name || user.email;
            document.getElementById("tenantBadge").textContent = user.tenant_slug || "—";
        }

        // Determine initial view from URL hash
        const hash = window.location.hash.replace("#", "") || "dashboard";
        this.navigate(hash);
    },

    // ── Navigation ──────────────────────────────────────────
    navigate(view) {
        this.currentView = view;
        window.location.hash = view;

        // Update sidebar active state
        document.querySelectorAll(".admin-nav-item[data-view]").forEach(el => {
            el.classList.toggle("active", el.dataset.view === view);
        });

        const main = document.getElementById("adminMain");
        main.innerHTML = '<div style="text-align:center;padding:60px;color:var(--admin-text-muted)">Loading…</div>';

        switch (view) {
            case "dashboard": this.renderDashboard(); break;
            case "users": this.renderUsers(); break;
            case "roles": this.renderRoles(); break;
            default: this.renderDashboard();
        }
    },

    // ── Dashboard ───────────────────────────────────────────
    async renderDashboard() {
        const main = document.getElementById("adminMain");
        try {
            const data = await api("/api/v1/admin/dashboard");
            const s = data.stats;
            const t = data.tenant;

            let roleHtml = "";
            for (const [role, count] of Object.entries(data.role_distribution || {})) {
                roleHtml += `<tr><td>${_esc(role)}</td><td style="text-align:right;font-weight:600">${count}</td></tr>`;
            }

            main.innerHTML = `
                <h1 style="margin-bottom:8px">Dashboard</h1>
                <p style="color:var(--admin-text-muted);margin-bottom:24px">
                    ${_esc(t.name)} — ${_esc(t.plan)} plan
                </p>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${s.total_users}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${s.active_users}</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${s.invited_users}</div>
                        <div class="stat-label">Invited</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${s.inactive_users}</div>
                        <div class="stat-label">Inactive</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${s.total_projects}</div>
                        <div class="stat-label">Projects</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${t.max_users || "∞"}</div>
                        <div class="stat-label">User Limit</div>
                    </div>
                </div>

                <div class="admin-card">
                    <h2>Role Distribution</h2>
                    <table class="admin-table">
                        <thead><tr><th>Role</th><th style="text-align:right">Users</th></tr></thead>
                        <tbody>${roleHtml || '<tr><td colspan="2" style="color:var(--admin-text-muted)">No role assignments yet</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            main.innerHTML = `<div class="admin-card" style="color:var(--admin-danger)">Failed to load dashboard: ${_esc(e.message)}</div>`;
        }
    },

    // ── Users ───────────────────────────────────────────────
    async renderUsers() {
        const main = document.getElementById("adminMain");
        try {
            const data = await api("/api/v1/admin/users");
            this._cache.users = data.users;

            main.innerHTML = `
                <h1 style="margin-bottom:16px">Users</h1>
                <div class="toolbar">
                    <input type="text" class="search-input" id="userSearch" placeholder="Search users…"
                           oninput="Admin._filterUsers()">
                    <select id="userStatusFilter" onchange="Admin._filterUsers()">
                        <option value="">All Status</option>
                        <option value="active">Active</option>
                        <option value="invited">Invited</option>
                        <option value="inactive">Inactive</option>
                        <option value="suspended">Suspended</option>
                    </select>
                    <div style="flex:1"></div>
                    <button class="btn btn-primary" onclick="Admin.openInviteModal()">+ Invite User</button>
                </div>
                <div class="admin-card" style="padding:0;overflow:hidden">
                    <table class="admin-table">
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Status</th>
                                <th>Roles</th>
                                <th>Created</th>
                                <th style="text-align:right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="userTableBody">
                            ${this._buildUserRows(data.users)}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            main.innerHTML = `<div class="admin-card" style="color:var(--admin-danger)">Failed to load users: ${_esc(e.message)}</div>`;
        }
    },

    _buildUserRows(users) {
        if (!users.length) return '<tr><td colspan="5" style="text-align:center;color:var(--admin-text-muted);padding:32px;">No users found</td></tr>';
        return users.map(u => `
            <tr>
                <td>
                    <div style="font-weight:500">${_esc(u.full_name || "—")}</div>
                    <div style="font-size:12px;color:var(--admin-text-muted)">${_esc(u.email)}</div>
                </td>
                <td><span class="badge badge-${u.status}">${_esc(u.status)}</span></td>
                <td>${(u.roles || []).map(r => `<span class="badge badge-role">${_esc(r.name || r)}</span>`).join("")}</td>
                <td style="font-size:13px;color:var(--admin-text-muted)">${u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                <td style="text-align:right">
                    <button class="btn btn-secondary btn-sm" onclick="Admin.viewUser(${u.id})">View</button>
                    <button class="btn btn-secondary btn-sm" onclick="Admin.openRoleModal(${u.id})">Roles</button>
                </td>
            </tr>
        `).join("");
    },

    _filterUsers() {
        const q = (document.getElementById("userSearch")?.value || "").toLowerCase();
        const status = document.getElementById("userStatusFilter")?.value || "";
        let users = this._cache.users || [];
        if (q) users = users.filter(u =>
            (u.email || "").toLowerCase().includes(q) ||
            (u.full_name || "").toLowerCase().includes(q)
        );
        if (status) users = users.filter(u => u.status === status);
        document.getElementById("userTableBody").innerHTML = this._buildUserRows(users);
    },

    // ── User Detail ─────────────────────────────────────────
    async viewUser(userId) {
        const main = document.getElementById("adminMain");
        try {
            const data = await api(`/api/v1/admin/users/${userId}`);
            const u = data.user;
            const initials = (u.full_name || u.email || "?").substring(0, 2).toUpperCase();

            let rolesHtml = (u.roles || []).map(r =>
                `<span class="badge badge-role" style="font-size:13px;padding:6px 14px">${_esc(r.name || r)}
                 <button style="background:none;border:none;color:#ef4444;cursor:pointer;margin-left:4px" 
                         onclick="Admin.removeRole(${u.id},'${_esc(r.name || r)}')">✕</button>
                 </span>`
            ).join("") || '<span style="color:var(--admin-text-muted)">No roles assigned</span>';

            let permsHtml = "";
            if (u.permissions && u.permissions.length) {
                const grouped = {};
                u.permissions.forEach(p => {
                    const [cat] = p.split(".");
                    if (!grouped[cat]) grouped[cat] = [];
                    grouped[cat].push(p);
                });
                for (const [cat, ps] of Object.entries(grouped)) {
                    permsHtml += `<div style="margin-bottom:8px"><strong style="color:var(--admin-primary);text-transform:capitalize">${_esc(cat)}</strong><br>`;
                    permsHtml += ps.map(p => `<span class="badge" style="background:rgba(148,163,184,0.1);color:var(--admin-text-muted);margin:2px">${_esc(p)}</span>`).join("");
                    permsHtml += `</div>`;
                }
            } else {
                permsHtml = '<span style="color:var(--admin-text-muted)">Permissions resolved from roles</span>';
            }

            main.innerHTML = `
                <button class="btn btn-secondary" onclick="Admin.navigate('users')" style="margin-bottom:20px">← Back to Users</button>

                <div class="admin-card">
                    <div class="user-detail-header">
                        <div class="user-avatar">${initials}</div>
                        <div class="user-detail-info">
                            <h2>${_esc(u.full_name || u.email)}</h2>
                            <p>${_esc(u.email)} · <span class="badge badge-${u.status}">${_esc(u.status)}</span></p>
                        </div>
                        <div style="flex:1"></div>
                        ${u.status === "active" ? `<button class="btn btn-danger btn-sm" onclick="Admin.deactivateUser(${u.id})">Deactivate</button>` : ""}
                        ${u.status === "inactive" ? `<button class="btn btn-primary btn-sm" onclick="Admin.reactivateUser(${u.id})">Reactivate</button>` : ""}
                    </div>
                </div>

                <div class="admin-card">
                    <div class="detail-section">
                        <h3>Roles</h3>
                        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">
                            ${rolesHtml}
                            <button class="btn btn-secondary btn-sm" onclick="Admin.openRoleModal(${u.id})">+ Add Role</button>
                        </div>
                    </div>
                </div>

                <div class="admin-card">
                    <div class="detail-section">
                        <h3>Effective Permissions</h3>
                        ${permsHtml}
                    </div>
                </div>

                <div class="admin-card">
                    <div class="detail-section">
                        <h3>Details</h3>
                        <table class="admin-table" style="max-width:400px">
                            <tr><td style="color:var(--admin-text-muted)">ID</td><td>${u.id}</td></tr>
                            <tr><td style="color:var(--admin-text-muted)">Auth Provider</td><td>${_esc(u.auth_provider || "local")}</td></tr>
                            <tr><td style="color:var(--admin-text-muted)">Created</td><td>${u.created_at ? new Date(u.created_at).toLocaleString() : "—"}</td></tr>
                            <tr><td style="color:var(--admin-text-muted)">Last Login</td><td>${u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}</td></tr>
                        </table>
                    </div>
                </div>
            `;
        } catch (e) {
            showToast("Failed to load user: " + e.message, "error");
        }
    },

    // ── Deactivate / Reactivate ─────────────────────────────
    async deactivateUser(userId) {
        if (!confirm("Are you sure you want to deactivate this user?")) return;
        try {
            await api(`/api/v1/admin/users/${userId}`, { method: "DELETE" });
            showToast("User deactivated");
            this.viewUser(userId);
        } catch (e) {
            showToast(e.message, "error");
        }
    },

    async reactivateUser(userId) {
        try {
            await api(`/api/v1/admin/users/${userId}`, { method: "PUT", body: { status: "active" } });
            showToast("User reactivated");
            this.viewUser(userId);
        } catch (e) {
            showToast(e.message, "error");
        }
    },

    // ── Invite Modal ────────────────────────────────────────
    async openInviteModal() {
        document.getElementById("inviteEmail").value = "";
        await this._loadRoleCheckboxes("inviteRoles");
        document.getElementById("inviteModal").style.display = "flex";
    },

    async sendInvite() {
        const email = document.getElementById("inviteEmail").value.trim();
        if (!email) return showToast("Email is required", "error");

        const roles = Array.from(document.querySelectorAll("#inviteRoles input:checked")).map(cb => cb.value);

        try {
            const data = await api("/api/v1/admin/users/invite", {
                method: "POST",
                body: { email, roles },
            });
            this.closeModal("inviteModal");
            showToast(`Invitation sent to ${email}`);

            // Show invite token (in dev, no email service yet)
            if (data.invite_token) {
                const link = `${window.location.origin}/api/v1/auth/register?invite_token=${data.invite_token}`;
                prompt("Development: Copy invite link for the user", link);
            }

            this.renderUsers();
        } catch (e) {
            showToast(e.message, "error");
        }
    },

    // ── Role Modal ──────────────────────────────────────────
    async openRoleModal(userId) {
        this._roleModalUserId = userId;
        const body = document.getElementById("roleModalBody");
        body.innerHTML = '<p style="color:var(--admin-text-muted)">Loading…</p>';
        document.getElementById("roleModal").style.display = "flex";

        try {
            const [userData, rolesData] = await Promise.all([
                api(`/api/v1/admin/users/${userId}`),
                api("/api/v1/admin/roles"),
            ]);
            const currentRoles = new Set((userData.user.roles || []).map(r => r.name || r));

            body.innerHTML = `
                <p style="margin-bottom:16px">Managing roles for <strong>${_esc(userData.user.full_name || userData.user.email)}</strong></p>
                ${rolesData.roles.map(r => `
                    <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--admin-border)">
                        <div>
                            <span style="font-weight:500">${_esc(r.display_name || r.name)}</span>
                            <span style="font-size:12px;color:var(--admin-text-muted);margin-left:8px">Level ${r.level}</span>
                        </div>
                        ${currentRoles.has(r.name)
                            ? `<button class="btn btn-danger btn-sm" onclick="Admin.removeRole(${userId},'${_esc(r.name)}')">Remove</button>`
                            : `<button class="btn btn-primary btn-sm" onclick="Admin.addRole(${userId},'${_esc(r.name)}')">Assign</button>`
                        }
                    </div>
                `).join("")}
            `;
        } catch (e) {
            body.innerHTML = `<p style="color:var(--admin-danger)">${_esc(e.message)}</p>`;
        }
    },

    async addRole(userId, roleName) {
        try {
            await api(`/api/v1/admin/users/${userId}/roles`, {
                method: "POST",
                body: { role_name: roleName },
            });
            showToast(`Role '${roleName}' assigned`);
            this.openRoleModal(userId);
        } catch (e) {
            showToast(e.message, "error");
        }
    },

    async removeRole(userId, roleName) {
        try {
            await api(`/api/v1/admin/users/${userId}/roles/${roleName}`, { method: "DELETE" });
            showToast(`Role '${roleName}' removed`);
            // Refresh whichever view is showing
            if (document.getElementById("roleModal").style.display === "flex") {
                this.openRoleModal(userId);
            } else {
                this.viewUser(userId);
            }
        } catch (e) {
            showToast(e.message, "error");
        }
    },

    // ── Roles & Permissions View ────────────────────────────
    async renderRoles() {
        const main = document.getElementById("adminMain");
        try {
            const [rolesData, permsData] = await Promise.all([
                api("/api/v1/admin/roles"),
                api("/api/v1/admin/permissions"),
            ]);

            const roles = rolesData.roles;
            const permCategories = permsData.permissions;

            // Build permission matrix
            let matrixHead = `<th style="min-width:200px">Permission</th>`;
            roles.forEach(r => {
                matrixHead += `<th style="text-align:center;font-size:11px;max-width:80px;word-break:break-all">${_esc(r.display_name || r.name)}</th>`;
            });

            let matrixBody = "";
            for (const [category, perms] of Object.entries(permCategories)) {
                matrixBody += `<tr><td class="perm-category" colspan="${roles.length + 1}">${_esc(category)}</td></tr>`;
                for (const perm of perms) {
                    matrixBody += `<tr><td style="font-size:13px;padding-left:24px">${_esc(perm.codename)}</td>`;
                    for (const role of roles) {
                        const has = role.permissions?.includes(perm.codename);
                        matrixBody += `<td class="perm-check">${has ? "✓" : ""}</td>`;
                    }
                    matrixBody += `</tr>`;
                }
            }

            main.innerHTML = `
                <h1 style="margin-bottom:16px">Roles & Permissions</h1>

                <div class="admin-card">
                    <h2>System Roles</h2>
                    <table class="admin-table">
                        <thead><tr><th>Role</th><th>Level</th><th>Type</th><th style="text-align:right">Permissions</th></tr></thead>
                        <tbody>
                        ${roles.map(r => `
                            <tr>
                                <td>
                                    <div style="font-weight:500">${_esc(r.display_name || r.name)}</div>
                                    <div style="font-size:12px;color:var(--admin-text-muted)">${_esc(r.name)}</div>
                                </td>
                                <td>${r.level}</td>
                                <td><span class="badge ${r.is_system ? "badge-active" : "badge-invited"}">${r.is_system ? "System" : "Custom"}</span></td>
                                <td style="text-align:right">${r.permissions?.length || 0}</td>
                            </tr>
                        `).join("")}
                        </tbody>
                    </table>
                </div>

                <div class="admin-card perm-matrix">
                    <h2>Permission Matrix</h2>
                    <table class="admin-table">
                        <thead><tr>${matrixHead}</tr></thead>
                        <tbody>${matrixBody}</tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            main.innerHTML = `<div class="admin-card" style="color:var(--admin-danger)">Failed to load roles: ${_esc(e.message)}</div>`;
        }
    },

    // ── Shared Helpers ──────────────────────────────────────
    async _loadRoleCheckboxes(containerId) {
        try {
            const data = await api("/api/v1/admin/roles");
            const container = document.getElementById(containerId);
            container.innerHTML = data.roles.map(r => `
                <label><input type="checkbox" value="${_esc(r.name)}"> ${_esc(r.display_name || r.name)}</label>
            `).join("");
        } catch {
            document.getElementById(containerId).innerHTML = '<span style="color:var(--admin-danger)">Failed to load roles</span>';
        }
    },

    closeModal(id) {
        document.getElementById(id).style.display = "none";
    },
};

// ── Close modals on overlay click ───────────────────────────
document.addEventListener("click", e => {
    if (e.target.classList.contains("modal-overlay")) {
        e.target.style.display = "none";
    }
});

// ── Boot ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => Admin.init());
