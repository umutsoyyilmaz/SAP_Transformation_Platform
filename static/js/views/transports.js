/**
 * Transport/CTS Tracking View (FDD-I01 / S5-04)
 *
 * Handles Transport Wave management and Transport Request CRUD,
 * backlog linkage, import result recording, and coverage analytics.
 *
 * API base: /api/v1/transports
 */

const TransportsView = (() => {
  "use strict";

  // ── State ────────────────────────────────────────────────────────────────

  let _tenantId = null;
  let _projectId = null;
  let _selectedTransportId = null;

  // ── Init ─────────────────────────────────────────────────────────────────

  /**
   * Initialize the transport view for a given tenant and project.
   *
   * @param {number} tenantId
   * @param {number} projectId
   */
  function init(tenantId, projectId) {
    _tenantId = tenantId;
    _projectId = projectId;
    loadWaves();
    loadTransports();
    loadCoverage();
  }

  // ── Wave management ───────────────────────────────────────────────────────

  /**
   * Load all transport waves and render into #waveList.
   */
  async function loadWaves() {
    try {
      const res = await fetch(
        `/api/v1/transports/waves?tenant_id=${_tenantId}&project_id=${_projectId}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      _renderWaveList(data.items || []);
    } catch (err) {
      console.error("[TransportsView] loadWaves failed:", err);
    }
  }

  /**
   * Create a new transport wave.
   *
   * @param {object} waveData  { name, target_system, planned_date?, notes? }
   * @returns {Promise<object>} Created wave dict.
   */
  async function createWave(waveData) {
    const res = await fetch("/api/v1/transports/waves", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: _tenantId,
        project_id: _projectId,
        ...waveData,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    const wave = await res.json();
    await loadWaves();
    return wave;
  }

  /**
   * Load and display full status for a specific wave (with transport list).
   *
   * @param {number} waveId
   * @returns {Promise<object>} Wave status dict.
   */
  async function loadWaveStatus(waveId) {
    const res = await fetch(
      `/api/v1/transports/waves/${waveId}/status?tenant_id=${_tenantId}&project_id=${_projectId}`
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    const status = await res.json();
    _renderWaveStatus(status);
    return status;
  }

  /**
   * Render the wave list into #waveList.
   *
   * @param {Array<object>} waves
   */
  function _renderWaveList(waves) {
    const container = document.getElementById("waveList");
    if (!container) return;
    if (!waves.length) {
      container.innerHTML = '<p class="text-muted">No transport waves defined.</p>';
      return;
    }
    const rows = waves
      .map(
        (w) => `
      <tr data-wave-id="${w.id}">
        <td>${_escHtml(w.name)}</td>
        <td><span class="badge bg-primary">${_escHtml(w.target_system)}</span></td>
        <td>${w.planned_date || "—"}</td>
        <td><span class="badge bg-secondary">${_escHtml(w.status)}</span></td>
        <td>
          <button class="btn btn-sm btn-outline-info" onclick="TransportsView.loadWaveStatus(${w.id})">
            View Status
          </button>
        </td>
      </tr>`
      )
      .join("");
    container.innerHTML = `
      <table class="table table-hover">
        <thead><tr>
          <th>Wave Name</th><th>Target System</th>
          <th>Planned Date</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  /**
   * Render the wave status detail panel into #waveStatusPanel.
   *
   * @param {object} statusData
   */
  function _renderWaveStatus(statusData) {
    const container = document.getElementById("waveStatusPanel");
    if (!container) return;
    const { wave, transports, total, status_counts, is_complete } = statusData;
    const statusBadge = is_complete
      ? '<span class="badge bg-success">Complete</span>'
      : '<span class="badge bg-warning text-dark">In Progress</span>';
    const rows = transports
      .map(
        (t) => `
      <tr>
        <td><code>${_escHtml(t.transport_number)}</code></td>
        <td>${_escHtml(t.transport_type)}</td>
        <td>${_escHtml(t.current_system)}</td>
        <td><span class="badge bg-secondary">${_escHtml(t.status)}</span></td>
        <td>${t.latest_import ? `${t.latest_import.status} @ ${t.latest_import.system}` : "—"}</td>
      </tr>`
      )
      .join("");
    container.innerHTML = `
      <div class="card mt-3">
        <div class="card-header d-flex justify-content-between align-items-center">
          <strong>${_escHtml(wave.name)} → ${_escHtml(wave.target_system)}</strong>
          ${statusBadge}
        </div>
        <div class="card-body">
          <p class="mb-1">Total transports: <strong>${total}</strong></p>
          <table class="table table-sm">
            <thead><tr>
              <th>Transport #</th><th>Type</th><th>Current System</th>
              <th>Status</th><th>Latest Import</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  }

  // ── Transport Request management ──────────────────────────────────────────

  /**
   * Load all transport requests and render into #transportList.
   *
   * @param {{ transport_type?, status?, wave_id? }?} filters
   */
  async function loadTransports(filters = {}) {
    try {
      const params = new URLSearchParams({
        tenant_id: _tenantId,
        project_id: _projectId,
        ...filters,
      });
      const res = await fetch(`/api/v1/transports/requests?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      _renderTransportList(data.items || []);
    } catch (err) {
      console.error("[TransportsView] loadTransports failed:", err);
    }
  }

  /**
   * Create a new transport request.
   *
   * @param {object} transportData  { transport_number, transport_type, ... }
   * @returns {Promise<object>} Created TransportRequest dict.
   */
  async function createTransport(transportData) {
    const res = await fetch("/api/v1/transports/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tenant_id: _tenantId,
        project_id: _projectId,
        ...transportData,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    const transport = await res.json();
    await loadTransports();
    return transport;
  }

  /**
   * Assign a backlog item to a transport request.
   *
   * @param {number} transportId
   * @param {number} backlogItemId
   * @returns {Promise<object>} Updated transport dict.
   */
  async function assignBacklogItem(transportId, backlogItemId) {
    const res = await fetch(
      `/api/v1/transports/requests/${transportId}/assign-backlog`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: _tenantId,
          project_id: _projectId,
          backlog_item_id: backlogItemId,
        }),
      }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Remove a backlog item link from a transport request.
   *
   * @param {number} transportId
   * @param {number} backlogItemId
   * @returns {Promise<object>} Updated transport dict.
   */
  async function removeBacklogItem(transportId, backlogItemId) {
    const res = await fetch(
      `/api/v1/transports/requests/${transportId}/assign-backlog/${backlogItemId}?tenant_id=${_tenantId}&project_id=${_projectId}`,
      { method: "DELETE" }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  /**
   * Record an STMS import result for a transport.
   *
   * @param {number} transportId
   * @param {string} system       DEV|QAS|PRE|PRD
   * @param {"imported"|"failed"} status
   * @param {number|null} returnCode  SAP STMS return code
   * @returns {Promise<object>} Updated transport dict.
   */
  async function recordImportResult(transportId, system, status, returnCode = null) {
    const res = await fetch(
      `/api/v1/transports/requests/${transportId}/import-result`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: _tenantId,
          project_id: _projectId,
          system,
          status,
          return_code: returnCode,
        }),
      }
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    const transport = await res.json();
    await loadTransports();
    return transport;
  }

  /**
   * Render the transport list into #transportList.
   *
   * @param {Array<object>} transports
   */
  function _renderTransportList(transports) {
    const container = document.getElementById("transportList");
    if (!container) return;
    if (!transports.length) {
      container.innerHTML = '<p class="text-muted">No transport requests found.</p>';
      return;
    }
    const rows = transports
      .map(
        (t) => `
      <tr data-transport-id="${t.id}">
        <td><code>${_escHtml(t.transport_number)}</code></td>
        <td>${_escHtml(t.transport_type)}</td>
        <td>${_escHtml(t.sap_module || "—")}</td>
        <td><span class="badge bg-primary">${_escHtml(t.current_system)}</span></td>
        <td><span class="badge bg-secondary">${_escHtml(t.status)}</span></td>
        <td>
          <button class="btn btn-sm btn-outline-secondary"
            onclick="TransportsView.openTransportDetail(${t.id})">
            Details
          </button>
        </td>
      </tr>`
      )
      .join("");
    container.innerHTML = `
      <table class="table table-hover">
        <thead><tr>
          <th>Transport #</th><th>Type</th><th>Module</th>
          <th>Current System</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  /**
   * Open detail panel for a specific transport request.
   *
   * @param {number} transportId
   */
  async function openTransportDetail(transportId) {
    _selectedTransportId = transportId;
    try {
      const res = await fetch(
        `/api/v1/transports/requests/${transportId}?tenant_id=${_tenantId}&project_id=${_projectId}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const transport = await res.json();
      _renderTransportDetail(transport);
    } catch (err) {
      console.error("[TransportsView] openTransportDetail failed:", err);
    }
  }

  /**
   * Render the transport detail panel into #transportDetailPanel.
   *
   * @param {object} transport
   */
  function _renderTransportDetail(transport) {
    const container = document.getElementById("transportDetailPanel");
    if (!container) return;
    const logRows = (transport.import_log || [])
      .map(
        (ev) => `
      <tr>
        <td>${_escHtml(ev.system)}</td>
        <td>${ev.imported_at ? ev.imported_at.replace("T", " ").slice(0, 19) : "—"}</td>
        <td><span class="badge ${ev.status === "imported" ? "bg-success" : "bg-danger"}">${ev.status}</span></td>
        <td>${ev.return_code != null ? ev.return_code : "—"}</td>
      </tr>`
      )
      .join("");
    const backlogList = (transport.backlog_item_ids || [])
      .map((id) => `<li>${id}</li>`)
      .join("");
    container.innerHTML = `
      <div class="card mt-3">
        <div class="card-header">
          <strong><code>${_escHtml(transport.transport_number)}</code></strong>
          — ${_escHtml(transport.transport_type)}
          <span class="badge bg-primary ms-2">${_escHtml(transport.current_system)}</span>
        </div>
        <div class="card-body">
          <p><strong>Description:</strong> ${_escHtml(transport.description || "—")}</p>
          <p><strong>SAP Module:</strong> ${_escHtml(transport.sap_module || "—")}</p>
          <p><strong>Status:</strong> ${_escHtml(transport.status)}</p>
          <h6 class="mt-3">Linked Backlog Items</h6>
          ${backlogList ? `<ul>${backlogList}</ul>` : '<p class="text-muted">None linked.</p>'}
          <h6 class="mt-3">Import Log</h6>
          ${
            logRows
              ? `<table class="table table-sm">
                  <thead><tr><th>System</th><th>Imported At</th><th>Status</th><th>RC</th></tr></thead>
                  <tbody>${logRows}</tbody>
                </table>`
              : '<p class="text-muted">No import events recorded.</p>'
          }
        </div>
      </div>`;
  }

  // ── Coverage analytics ────────────────────────────────────────────────────

  /**
   * Load coverage analytics and render into #coveragePanel.
   */
  async function loadCoverage() {
    try {
      const res = await fetch(
        `/api/v1/transports/coverage?tenant_id=${_tenantId}&project_id=${_projectId}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      _renderCoverage(data);
    } catch (err) {
      console.error("[TransportsView] loadCoverage failed:", err);
    }
  }

  /**
   * Render coverage analytics into #coveragePanel.
   *
   * @param {object} coverage
   */
  function _renderCoverage(coverage) {
    const container = document.getElementById("coveragePanel");
    if (!container) return;
    const pct = coverage.coverage_pct ?? 0;
    const barColor = pct >= 80 ? "bg-success" : pct >= 50 ? "bg-warning" : "bg-danger";
    container.innerHTML = `
      <div class="card">
        <div class="card-header">Transport Coverage</div>
        <div class="card-body">
          <div class="progress mb-2" style="height:20px;">
            <div class="progress-bar ${barColor}" style="width:${pct}%;">${pct}%</div>
          </div>
          <p class="mb-1">
            ${coverage.with_transport} / ${coverage.total_backlog_items} backlog items have a transport assigned.
          </p>
          <p class="text-muted mb-0">
            ${coverage.without_transport} items still need a transport.
          </p>
        </div>
      </div>`;
  }

  // ── Utilities ─────────────────────────────────────────────────────────────

  /**
   * Escape HTML to prevent XSS in dynamically inserted content.
   *
   * @param {string|null|undefined} str
   * @returns {string}
   */
  function _escHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ── Public API ────────────────────────────────────────────────────────────

  return {
    init,
    loadWaves,
    createWave,
    loadWaveStatus,
    loadTransports,
    createTransport,
    assignBacklogItem,
    removeBacklogItem,
    recordImportResult,
    openTransportDetail,
    loadCoverage,
  };
})();
