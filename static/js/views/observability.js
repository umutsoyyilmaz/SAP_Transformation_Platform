/**
 * F11 — Observability Dashboard view
 * Shows async tasks, cache stats, health checks, and metrics.
 */
const ObservabilityView = (function () {
  'use strict';

  let activeTab = 'health';
  let tasks = [];
  let cacheStats = {};
  let healthData = {};
  let metricsData = {};

  function init() {
    render();
    loadAll();
  }

  function render() {
    const c = document.getElementById('main-content');
    if (!c) return;
    c.innerHTML = `
      <div class="obs-container">
        <div class="obs-header">
          <h2><i class="fas fa-chart-bar"></i> Infrastructure & Observability</h2>
        </div>

        <div class="obs-tabs">
          <button class="tab-btn active" data-tab="health" onclick="ObservabilityView.switchTab('health')">
            <i class="fas fa-heartbeat"></i> Health
          </button>
          <button class="tab-btn" data-tab="tasks" onclick="ObservabilityView.switchTab('tasks')">
            <i class="fas fa-tasks"></i> Async Tasks
          </button>
          <button class="tab-btn" data-tab="cache" onclick="ObservabilityView.switchTab('cache')">
            <i class="fas fa-database"></i> Cache
          </button>
          <button class="tab-btn" data-tab="metrics" onclick="ObservabilityView.switchTab('metrics')">
            <i class="fas fa-tachometer-alt"></i> Metrics
          </button>
        </div>

        <div id="obs-tab-content"></div>
      </div>
    `;
  }

  async function loadAll() {
    await Promise.all([loadHealth(), loadTasks(), loadCache(), loadMetrics()]);
    renderTab();
  }

  async function loadHealth() {
    try {
      const r = await fetch('/api/v1/health/detailed');
      healthData = await r.json();
    } catch { healthData = {}; }
  }

  async function loadTasks() {
    try {
      const r = await fetch('/api/v1/tasks');
      const d = await r.json();
      tasks = d.items || [];
    } catch { tasks = []; }
  }

  async function loadCache() {
    try {
      const r = await fetch('/api/v1/cache/stats');
      cacheStats = await r.json();
    } catch { cacheStats = {}; }
  }

  async function loadMetrics() {
    try {
      const r = await fetch('/api/v1/metrics/summary');
      metricsData = await r.json();
    } catch { metricsData = {}; }
  }

  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.obs-tabs .tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    renderTab();
  }

  function renderTab() {
    const c = document.getElementById('obs-tab-content');
    if (!c) return;
    if (activeTab === 'health') renderHealthTab(c);
    else if (activeTab === 'tasks') renderTasksTab(c);
    else if (activeTab === 'cache') renderCacheTab(c);
    else renderMetricsTab(c);
  }

  function renderHealthTab(c) {
    const comps = healthData.components || {};
    let cards = Object.entries(comps).map(([name, info]) => `
      <div class="health-card health-${info.status}">
        <div class="health-card-icon">
          <i class="fas fa-${iconFor(name)}"></i>
        </div>
        <div class="health-card-info">
          <strong>${name}</strong>
          <span class="badge badge-${info.status === 'healthy' ? 'success' : 'danger'}">${info.status}</span>
          ${info.response_time_ms !== undefined ? `<span class="text-muted">${info.response_time_ms}ms</span>` : ''}
        </div>
      </div>`).join('');
    if (!cards) cards = '<p class="text-muted">No health data</p>';
    c.innerHTML = `
      <div class="health-panel">
        <div class="panel-toolbar">
          <span class="badge badge-${(healthData.status || 'unknown') === 'healthy' ? 'success' : 'danger'}">
            Overall: ${healthData.status || 'unknown'}
          </span>
          <button class="btn btn-sm btn-primary" onclick="ObservabilityView.runHealthCheck()">
            <i class="fas fa-sync"></i> Run Check
          </button>
        </div>
        <div class="health-grid">${cards}</div>
      </div>`;
  }

  function renderTasksTab(c) {
    let rows = tasks.map(t => `
      <tr>
        <td><code>${t.task_id.slice(0,8)}</code></td>
        <td>${t.task_type}</td>
        <td><span class="badge badge-${taskColor(t.status)}">${t.status}</span></td>
        <td>
          <div class="progress-bar-mini">
            <div class="progress-fill" style="width:${t.progress}%"></div>
          </div>
          <span class="text-muted">${t.progress}%</span>
        </td>
        <td>${new Date(t.created_at).toLocaleString()}</td>
      </tr>`).join('');
    if (!rows) rows = '<tr><td colspan="5" class="text-center text-muted">No async tasks</td></tr>';
    c.innerHTML = `
      <div class="tasks-panel">
        <table class="data-table">
          <thead><tr>
            <th>Task ID</th><th>Type</th><th>Status</th><th>Progress</th><th>Created</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function renderCacheTab(c) {
    const stats = cacheStats.stats || {};
    let rows = Object.entries(stats).map(([tier, s]) => `
      <tr>
        <td><strong>${tier}</strong></td>
        <td>${s.hit}</td>
        <td>${s.miss}</td>
        <td>${s.hit_rate}%</td>
        <td>${s.keys} keys</td>
      </tr>`).join('');
    if (!rows) rows = '<tr><td colspan="5" class="text-center text-muted">No cache data</td></tr>';
    c.innerHTML = `
      <div class="cache-panel">
        <table class="data-table">
          <thead><tr><th>Tier</th><th>Hits</th><th>Misses</th><th>Hit Rate</th><th>Keys</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function renderMetricsTab(c) {
    const tc = metricsData.tasks || {};
    const ca = metricsData.cache || {};
    c.innerHTML = `
      <div class="metrics-panel">
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-value">${tc.completed || 0}</div>
            <div class="metric-label">Tasks Completed</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${tc.running || 0}</div>
            <div class="metric-label">Tasks Running</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${tc.failed || 0}</div>
            <div class="metric-label">Tasks Failed</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${ca.hit_rate || 0}%</div>
            <div class="metric-label">Cache Hit Rate</div>
          </div>
        </div>
        <div class="rate-limits-info">
          <h4>Rate Limit Tiers</h4>
          ${Object.entries(metricsData.rate_limits || {}).map(([tier, info]) =>
            `<div class="rate-row"><strong>${tier}</strong><span>${info.limit}</span><span class="text-muted">${info.description}</span></div>`
          ).join('')}
        </div>
      </div>`;
  }

  function iconFor(name) {
    return { database: 'database', redis: 'server', celery: 'cogs', storage: 'hdd' }[name] || 'circle';
  }

  function taskColor(s) {
    return { pending: 'warning', running: 'info', completed: 'success', failed: 'danger', retrying: 'warning' }[s] || 'secondary';
  }

  async function runHealthCheck() {
    await fetch('/api/v1/health/check', { method: 'POST' });
    await loadHealth();
    renderTab();
  }

  return { init, switchTab, runHealthCheck };
})();
