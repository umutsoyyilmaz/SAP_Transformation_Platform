/**
 * Authorization Concept View (FDD-I02 / S7-02)
 *
 * SAP authorization concept design tool:
 *   - Tab 1: Role Matrix — list, create, edit SapAuthRoles + manage auth objects
 *   - Tab 2: SOD Matrix  — detect and accept Segregation of Duties risks
 *
 * API base: /api/v1/projects/<pid>/auth
 *
 * NOTE: This manages SAP authorization concept roles (SapAuthRole),
 *       NOT platform RBAC roles (app/models/user.py::Role).
 *       See ADR-002 for the rationale behind this separation.
 */

const AuthorizationView = (() => {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────────

  let _tenantId = null;
  let _projectId = null;
  let _currentTab = 'roles';
  let _roles = [];
  let _sodRows = [];

  // ── Constants ────────────────────────────────────────────────────────────

  const _ROLE_TYPES = ['single', 'composite'];
  const _STATUSES = ['draft', 'in_review', 'approved', 'implemented'];
  const _RISK_COLORS = {
    critical: '#dc3545',
    high:     '#fd7e14',
    medium:   '#ffc107',
    low:      '#28a745',
  };

  // ── Helpers ──────────────────────────────────────────────────────────────

  function _api(method, path, body) {
    const sep = path.includes('?') ? '&' : '?';
    const url = `/api/v1/projects/${_projectId}/auth${path}${sep}tenant_id=${_tenantId}`;
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify({ ...body, tenant_id: _tenantId });
    return fetch(url, opts).then(r => r.json());
  }

  function _toast(msg, type = 'success') {
    if (typeof App !== 'undefined' && typeof App.toast === 'function') {
      const mapped = type === 'danger' ? 'error' : type;
      App.toast(msg, mapped);
      return;
    }
    const el = document.createElement('div');
    el.style.cssText = 'position:fixed;top:12px;right:12px;z-index:9999;min-width:280px;padding:10px 12px;border-radius:8px;background:#32363a;color:#fff;';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  function _statusBadge(status) {
    const colors = {
      draft: '#6a6d70',
      in_review: '#0070f2',
      approved: '#107e3e',
      implemented: '#0a6ed1',
    };
    return `<span class="badge" style="background:${colors[status] || '#6a6d70'};color:#fff">${status}</span>`;
  }

  function _riskBadge(level) {
    const icons = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' };
    return `<strong style="color:${_RISK_COLORS[level] || '#666'}">${icons[level] || '•'} ${level.toUpperCase()}</strong>`;
  }

  // ── Initialise ───────────────────────────────────────────────────────────

  /**
   * Entry point called by the SPA router when navigating to the auth view.
   *
   * @param {number|null} tenantId   — tenant context
   * @param {number|null} projectId  — program ID (programs.id)
   */
  function init(tenantId, projectId) {
    _tenantId = tenantId || window.currentTenantId || null;
    _projectId = projectId || window.currentProjectId || null;
    _currentTab = 'roles';
    _render();
    loadRoles();
  }

  // ── Shell render ─────────────────────────────────────────────────────────

  function _render() {
    const container = document.getElementById('main-content') || document.getElementById('mainContent');
    if (!container) return;

    container.innerHTML = `
<div id="auth-view">

  <!-- Header -->
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;">
    <div>
      <h2 style="margin:0;font-size:1.4rem;">🔐 Authorization Concept</h2>
      <p style="margin:0.25rem 0 0;color:var(--sap-text-secondary,#666);font-size:0.85rem;">
        SAP role design and Segregation of Duties analysis
      </p>
    </div>
    <div style="display:flex;gap:0.5rem;align-items:center;">
      <span id="auth-coverage-badge" class="badge" style="font-size:0.85rem;background:var(--sap-bg);color:var(--sap-text-primary);border:1px solid var(--sap-border);">
        Coverage: —
      </span>
      <button class="btn btn-secondary btn-sm" onclick="AuthorizationView.exportExcel()">
        ⬇ Export Excel
      </button>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs" id="auth-tabs" style="margin-bottom:12px">
    <button class="tab-btn active" onclick="AuthorizationView.switchTab('roles');return false;">👤 Role Matrix</button>
    <button class="tab-btn" onclick="AuthorizationView.switchTab('sod');return false;">
      ⚠️ SOD Matrix
      <span id="auth-sod-crit-badge" class="badge" style="display:none;background:var(--sap-negative);color:#fff;margin-left:4px;"></span>
    </button>
  </div>

  <!-- Role Matrix tab -->
  <div id="auth-tab-roles">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
      <span style="color:var(--text-secondary,#666);font-size:0.85rem;" id="auth-role-count"></span>
      <button class="btn btn-primary btn-sm" onclick="AuthorizationView.openAddRoleModal()">
        + New Role
      </button>
    </div>
    <div id="auth-role-list">
      <div style="text-align:center;color:var(--sap-text-secondary);padding:16px 0">Loading…</div>
    </div>
  </div>

  <!-- SOD Matrix tab -->
  <div id="auth-tab-sod" style="display:none;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
      <span style="color:var(--text-secondary,#666);font-size:0.85rem;" id="auth-sod-count"></span>
      <button class="btn btn-secondary btn-sm" onclick="AuthorizationView.refreshSod()">
        🔄 Run SOD Analysis
      </button>
    </div>
    <div id="auth-sod-list">
      <div style="text-align:center;color:var(--sap-text-secondary);padding:16px 0">Run SOD Analysis to detect conflicts.</div>
    </div>
  </div>

</div>

<!-- Add/Edit Role Modal (hidden) -->
<div id="auth-role-modal" class="modal" tabindex="-1" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1050;">
  <div style="margin:5vh auto;max-width:640px;background:var(--sap-card-bg);border-radius:8px;padding:16px;">
    <h5 id="auth-role-modal-title" style="margin-bottom:12px;">New SAP Auth Role</h5>
    <form id="auth-role-form" onsubmit="AuthorizationView.submitRoleForm(event)">
      <div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px;margin-bottom:8px;">
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Role Name *</label>
          <input id="arf-name" type="text" class="form-control"
                 placeholder="Z_FI_AR_CLERK" maxlength="30" required />
          <small class="text-muted">Max 30 chars (SAP PFCG limit)</small>
        </div>
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Type</label>
          <select id="arf-type" class="form-control">
            <option value="single">Single</option>
            <option value="composite">Composite</option>
          </select>
        </div>
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">SAP Module</label>
          <input id="arf-module" type="text" class="form-control"
                 placeholder="FI" maxlength="10" />
        </div>
      </div>
      <div style="margin-bottom:8px;">
        <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Business Role Description</label>
        <input id="arf-bizrole" type="text" class="form-control"
               placeholder="Accounts Receivable Clerk" maxlength="200" />
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Status</label>
          <select id="arf-status" class="form-control">
            ${_STATUSES.map(s => `<option value="${s}">${s}</option>`).join('')}
          </select>
        </div>
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Est. Users</label>
          <input id="arf-users" type="number" min="0" class="form-control" />
        </div>
      </div>
      <div style="margin-bottom:8px;">
        <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Description</label>
        <textarea id="arf-desc" class="form-control" rows="2" maxlength="500"></textarea>
      </div>
      <input type="hidden" id="arf-id" value="" />
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:12px;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="AuthorizationView.closeRoleModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm">Save Role</button>
      </div>
    </form>
  </div>
</div>

<!-- Add Auth Object Modal (hidden) -->
<div id="auth-obj-modal" class="modal" tabindex="-1" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1050;">
  <div style="margin:10vh auto;max-width:520px;background:var(--sap-card-bg);border-radius:8px;padding:16px;">
    <h5 style="margin-bottom:12px;">Add Authorization Object</h5>
    <form id="auth-obj-form" onsubmit="AuthorizationView.submitObjForm(event)">
      <div style="display:grid;grid-template-columns:1fr 1.4fr;gap:8px;margin-bottom:8px;">
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Auth Object *</label>
          <input id="aof-object" type="text" class="form-control"
                 placeholder="F_BKPF_BUK" maxlength="10" required />
        </div>
        <div>
          <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Description</label>
          <input id="aof-desc" type="text" class="form-control"
                 placeholder="FI document authorization" maxlength="200" />
        </div>
      </div>
      <div style="margin-bottom:8px;">
        <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">
          Field Values (JSON)
          <small class="text-muted" style="margin-left:4px;">e.g. {"ACTVT":["01","02"],"BUKRS":["1000"]}</small>
        </label>
        <textarea id="aof-fv" class="form-control font-monospace" rows="3"
                  placeholder='{"ACTVT": ["01", "02", "03"], "BUKRS": ["1000"]}'></textarea>
      </div>
      <div style="margin-bottom:8px;">
        <label style="display:block;font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px;">Source</label>
        <select id="aof-source" class="form-control">
          <option value="">— select —</option>
          <option value="su24">SU24 Proposal</option>
          <option value="su25_template">SU25 Template</option>
          <option value="manual">Manual</option>
        </select>
      </div>
      <input type="hidden" id="aof-role-id" value="" />
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:12px;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="AuthorizationView.closeObjModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm">Add Object</button>
      </div>
    </form>
  </div>
</div>
`;
  }

  // ── Role Matrix ──────────────────────────────────────────────────────────

  function loadRoles() {
    _api('GET', '/roles').then(data => {
      _roles = data.items || [];
      _renderRoleTable();
      _updateCoverageBadge();
    }).catch(err => {
      console.error('AuthorizationView: load roles failed', err);
      document.getElementById('auth-role-list').innerHTML =
        '<p style="color:var(--sap-negative);">Failed to load roles.</p>';
    });
  }

  function _renderRoleTable() {
    const count = document.getElementById('auth-role-count');
    if (count) count.textContent = `${_roles.length} role(s)`;

    const el = document.getElementById('auth-role-list');
    if (!el) return;

    if (!_roles.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--sap-text-secondary);padding:16px 0">No roles yet. Click "New Role" to start.</div>';
      return;
    }

    el.innerHTML = `
<div style="overflow-x:auto">
<table class="data-table" style="font-size:13px">
  <thead>
    <tr>
      <th>Role Name</th><th>Type</th><th>Module</th><th>Status</th>
      <th>Objects</th><th>SOD Risks</th><th>Est. Users</th><th></th>
    </tr>
  </thead>
  <tbody>
    ${_roles.map(r => `
    <tr>
      <td>
        <strong>${r.role_name}</strong>
        ${r.business_role_description ? `<br><small style="color:var(--sap-text-secondary)">${r.business_role_description}</small>` : ''}
      </td>
      <td><span class="badge bg-${r.role_type === 'single' ? 'primary' : 'info'}">${r.role_type}</span></td>
      <td>${r.sap_module || '—'}</td>
      <td>${_statusBadge(r.status)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" style="font-size:0.75rem;padding:0.1rem 0.4rem;"
                onclick="AuthorizationView.openObjModal(${r.id})">
          ${r.auth_object_count || 0} ⚙
        </button>
      </td>
      <td>${r.sod_risk_count > 0 ? `<span style="color:var(--sap-negative)">${r.sod_risk_count} ⚠</span>` : '—'}</td>
      <td>${r.user_count_estimate != null ? r.user_count_estimate : '—'}</td>
      <td>
        <button class="btn btn-primary btn-sm" style="font-size:0.7rem;padding:0.1rem 0.35rem;"
                onclick="AuthorizationView.editRole(${r.id})" title="Edit">✏</button>
        <button class="btn btn-danger btn-sm" style="font-size:0.7rem;padding:0.1rem 0.35rem;"
                onclick="AuthorizationView.deleteRole(${r.id})" title="Delete">🗑</button>
      </td>
    </tr>`).join('')}
  </tbody>
</table>
</div>`;
  }

  function _updateCoverageBadge() {
    _api('GET', '/coverage').then(data => {
      const badge = document.getElementById('auth-coverage-badge');
      if (!badge) return;
      const pct = data.coverage_pct ?? 0;
      const color = pct >= 80 ? 'success' : pct >= 50 ? 'warning' : 'danger';
      badge.className = 'badge';
      badge.style.background = color === 'success' ? '#107e3e' : color === 'warning' ? '#e9730c' : '#c4314b';
      badge.style.color = '#fff';
      badge.textContent = `Coverage: ${pct}% (${data.covered_steps}/${data.total_steps} steps)`;
    }).catch(() => {});
  }

  // ── Role Modal ───────────────────────────────────────────────────────────

  function openAddRoleModal() {
    document.getElementById('arf-id').value = '';
    document.getElementById('arf-name').value = '';
    document.getElementById('arf-type').value = 'single';
    document.getElementById('arf-module').value = '';
    document.getElementById('arf-bizrole').value = '';
    document.getElementById('arf-status').value = 'draft';
    document.getElementById('arf-users').value = '';
    document.getElementById('arf-desc').value = '';
    document.getElementById('auth-role-modal-title').textContent = 'New SAP Auth Role';
    document.getElementById('auth-role-modal').style.display = 'block';
  }

  function editRole(roleId) {
    const role = _roles.find(r => r.id === roleId);
    if (!role) return;
    document.getElementById('arf-id').value = roleId;
    document.getElementById('arf-name').value = role.role_name || '';
    document.getElementById('arf-type').value = role.role_type || 'single';
    document.getElementById('arf-module').value = role.sap_module || '';
    document.getElementById('arf-bizrole').value = role.business_role_description || '';
    document.getElementById('arf-status').value = role.status || 'draft';
    document.getElementById('arf-users').value = role.user_count_estimate ?? '';
    document.getElementById('arf-desc').value = role.description || '';
    document.getElementById('auth-role-modal-title').textContent = `Edit Role: ${role.role_name}`;
    document.getElementById('auth-role-modal').style.display = 'block';
  }

  function closeRoleModal() {
    document.getElementById('auth-role-modal').style.display = 'none';
  }

  function submitRoleForm(e) {
    e.preventDefault();
    const roleId = document.getElementById('arf-id').value;
    const payload = {
      role_name:                  document.getElementById('arf-name').value.trim(),
      role_type:                  document.getElementById('arf-type').value,
      sap_module:                 document.getElementById('arf-module').value.trim() || null,
      business_role_description:  document.getElementById('arf-bizrole').value.trim() || null,
      status:                     document.getElementById('arf-status').value,
      user_count_estimate:        parseInt(document.getElementById('arf-users').value) || null,
      description:                document.getElementById('arf-desc').value.trim() || null,
    };

    const isEdit = !!roleId;
    const method = isEdit ? 'PUT' : 'POST';
    const path   = isEdit ? `/roles/${roleId}` : '/roles';

    _api(method, path, payload).then(data => {
      if (data.error) { _toast(`Error: ${data.error}`, 'danger'); return; }
      _toast(isEdit ? 'Role updated.' : 'Role created.');
      closeRoleModal();
      loadRoles();
    }).catch(() => _toast('Request failed.', 'danger'));
  }

  function deleteRole(roleId) {
    const role = _roles.find(r => r.id === roleId);
    if (!role) return;
    if (!confirm(`Delete role "${role.role_name}"? This also removes its auth objects and SOD rows.`)) return;

    fetch(`/api/v1/projects/${_projectId}/auth/roles/${roleId}?tenant_id=${_tenantId}`, {
      method: 'DELETE',
    }).then(r => {
      if (r.status === 204) {
        _toast('Role deleted.');
        loadRoles();
      } else {
        _toast('Delete failed.', 'danger');
      }
    }).catch(() => _toast('Request failed.', 'danger'));
  }

  // ── Auth Object Modal ────────────────────────────────────────────────────

  function openObjModal(roleId) {
    document.getElementById('aof-role-id').value = roleId;
    document.getElementById('aof-object').value = '';
    document.getElementById('aof-desc').value = '';
    document.getElementById('aof-fv').value = '';
    document.getElementById('aof-source').value = '';
    document.getElementById('auth-obj-modal').style.display = 'block';
  }

  function closeObjModal() {
    document.getElementById('auth-obj-modal').style.display = 'none';
  }

  function submitObjForm(e) {
    e.preventDefault();
    const roleId = parseInt(document.getElementById('aof-role-id').value);
    let fieldValues = {};
    const fvRaw = document.getElementById('aof-fv').value.trim();
    if (fvRaw) {
      try {
        fieldValues = JSON.parse(fvRaw);
      } catch {
        _toast('Field Values must be valid JSON.', 'danger');
        return;
      }
    }
    const payload = {
      auth_object:            document.getElementById('aof-object').value.trim().toUpperCase(),
      auth_object_description: document.getElementById('aof-desc').value.trim() || null,
      field_values:           fieldValues,
      source:                 document.getElementById('aof-source').value || null,
    };

    _api('POST', `/roles/${roleId}/objects`, payload).then(data => {
      if (data.error) { _toast(`Error: ${data.error}`, 'danger'); return; }
      _toast('Auth object added.');
      closeObjModal();
      loadRoles();
    }).catch(() => _toast('Request failed.', 'danger'));
  }

  // ── SOD Matrix ───────────────────────────────────────────────────────────

  function loadSod() {
    _api('GET', '/sod-matrix').then(data => {
      _sodRows = data.items || [];
      _renderSodTable();
      const critBadge = document.getElementById('auth-sod-crit-badge');
      if (critBadge && data.unaccepted_critical > 0) {
        critBadge.textContent = data.unaccepted_critical;
        critBadge.style.display = 'inline';
      } else if (critBadge) {
        critBadge.style.display = 'none';
      }
    }).catch(err => {
      console.error('AuthorizationView: load SOD failed', err);
    });
  }

  function _renderSodTable() {
    const count = document.getElementById('auth-sod-count');
    if (count) count.textContent = `${_sodRows.length} conflict(s)`;

    const el = document.getElementById('auth-sod-list');
    if (!el) return;

    if (!_sodRows.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--sap-text-secondary);padding:16px 0">No SOD conflicts detected. Run SOD Analysis to check.</div>';
      return;
    }

    el.innerHTML = `
<div style="overflow-x:auto">
<table class="data-table" style="font-size:13px">
  <thead>
    <tr>
      <th>Role A</th><th>Role B</th><th>Auth Object</th><th>Risk</th>
      <th>Description</th><th>Control</th><th>Accepted</th><th></th>
    </tr>
  </thead>
  <tbody>
    ${_sodRows.map(r => `
    <tr style="${r.is_accepted ? 'opacity:.75' : (r.risk_level === 'critical' ? 'background:#fff5f5' : '')}">
      <td><code>${r.role_a_name || r.role_a_id}</code></td>
      <td><code>${r.role_b_name || r.role_b_id}</code></td>
      <td><code>${r.conflicting_auth_object || '—'}</code></td>
      <td>${_riskBadge(r.risk_level)}</td>
      <td style="max-width:200px;font-size:0.8rem;">${r.risk_description || '—'}</td>
      <td style="max-width:160px;font-size:0.8rem;">${r.mitigating_control || '<em style="color:var(--sap-text-secondary)">None</em>'}</td>
      <td>${r.is_accepted ? '✅ Yes' : '<span style="color:var(--sap-negative)">No</span>'}</td>
      <td>
        ${!r.is_accepted ? `
        <button class="btn btn-primary btn-sm" style="font-size:0.7rem;padding:0.1rem 0.35rem;"
                onclick="AuthorizationView.acceptRisk(${r.id})" title="Accept risk">✓ Accept</button>
        ` : ''}
      </td>
    </tr>`).join('')}
  </tbody>
</table>
</div>`;
  }

  function refreshSod() {
    const btn = document.querySelector('[onclick="AuthorizationView.refreshSod()"]');
    if (btn) btn.disabled = true;
    _api('POST', '/sod-matrix/refresh', {}).then(data => {
      _sodRows = data.items || [];
      _renderSodTable();
      _toast(`SOD Analysis complete: ${data.conflicts_detected} conflict(s) detected.`,
             data.conflicts_detected > 0 ? 'warning' : 'success');
      const critBadge = document.getElementById('auth-sod-crit-badge');
      const critCount = _sodRows.filter(r => r.risk_level === 'critical' && !r.is_accepted).length;
      if (critBadge) {
        critBadge.textContent = critCount;
        critBadge.style.display = critCount > 0 ? 'inline' : 'none';
      }
    }).catch(() => _toast('SOD analysis failed.', 'danger'))
      .finally(() => { if (btn) btn.disabled = false; });
  }

  function acceptRisk(sodId) {
    const control = prompt('Describe the mitigating control (compensating measure):');
    if (!control || !control.trim()) return;
    const userId = window.currentUserId || 1;
    _api('POST', `/sod-matrix/${sodId}/accept-risk`, {
      accepted_by_id: userId,
      mitigating_control: control.trim(),
    }).then(data => {
      if (data.error) { _toast(`Error: ${data.error}`, 'danger'); return; }
      _toast('SOD risk accepted.');
      loadSod();
    }).catch(() => _toast('Request failed.', 'danger'));
  }

  // ── Tab switching ────────────────────────────────────────────────────────

  function switchTab(tab) {
    _currentTab = tab;
    document.getElementById('auth-tab-roles').style.display = tab === 'roles' ? '' : 'none';
    document.getElementById('auth-tab-sod').style.display   = tab === 'sod'   ? '' : 'none';

    document.querySelectorAll('#auth-tabs .tab-btn').forEach((a, i) => {
      a.classList.toggle('active', (i === 0 && tab === 'roles') || (i === 1 && tab === 'sod'));
    });

    if (tab === 'sod' && !_sodRows.length) loadSod();
  }

  // ── Export ───────────────────────────────────────────────────────────────

  function exportExcel() {
    const url = `/api/v1/projects/${_projectId}/auth/export?tenant_id=${_tenantId}`;
    window.open(url, '_blank');
  }

  // ── Public API ───────────────────────────────────────────────────────────

  return {
    init,
    switchTab,
    loadRoles,
    openAddRoleModal,
    editRole,
    closeRoleModal,
    submitRoleForm,
    deleteRole,
    openObjModal,
    closeObjModal,
    submitObjForm,
    refreshSod,
    acceptRisk,
    exportExcel,
  };
})();
