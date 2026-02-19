/**
 * F10 — Integrations & Webhooks view
 * Manages Jira connections, automation import jobs, and webhook subscriptions.
 */
const IntegrationsView = (function () {
  'use strict';

  let currentProgramId = null;
  let webhooks = [];
  let automationJobs = [];
  let jiraIntegration = null;
  let activeTab = 'jira';

  /* ── public ──────────────────────────────────────────── */
  function init(programId) {
    currentProgramId = programId;
    render();
    loadAll();
  }

  function render() {
    const container = document.getElementById('main-content');
    if (!container) return;
    container.innerHTML = `
      <div class="integrations-container">
        <div class="integrations-header">
          <h2><i class="fas fa-plug"></i> Integrations & Webhooks</h2>
          <div class="integrations-actions">
            <button class="btn btn-sm btn-outline" onclick="IntegrationsView.openApiSpec()">
              <i class="fas fa-file-code"></i> OpenAPI Spec
            </button>
          </div>
        </div>

        <div class="integrations-tabs">
          <button class="tab-btn active" data-tab="jira" onclick="IntegrationsView.switchTab('jira')">
            <i class="fab fa-jira"></i> Jira
          </button>
          <button class="tab-btn" data-tab="automation" onclick="IntegrationsView.switchTab('automation')">
            <i class="fas fa-robot"></i> Automation Import
          </button>
          <button class="tab-btn" data-tab="webhooks" onclick="IntegrationsView.switchTab('webhooks')">
            <i class="fas fa-satellite-dish"></i> Webhooks
          </button>
        </div>

        <div id="integrations-tab-content"></div>
      </div>

      <!-- Create/Edit Webhook Modal -->
      <div class="modal-overlay" id="webhook-modal" style="display:none">
        <div class="modal" style="max-width:520px">
          <div class="modal-header">
            <h3 id="webhook-modal-title">New Webhook</h3>
            <button class="modal-close" onclick="IntegrationsView.closeModal('webhook-modal')">&times;</button>
          </div>
          <div class="modal-body">
            <input type="hidden" id="wh-edit-id" />
            <div class="form-group">
              <label>Name</label>
              <input type="text" id="wh-name" class="form-control" placeholder="My Webhook" />
            </div>
            <div class="form-group">
              <label>URL *</label>
              <input type="url" id="wh-url" class="form-control" placeholder="https://example.com/hook" />
            </div>
            <div class="form-group">
              <label>Secret (HMAC)</label>
              <input type="text" id="wh-secret" class="form-control" placeholder="optional signing secret" />
            </div>
            <div class="form-group">
              <label>Events</label>
              <div id="wh-events-list" class="checkbox-grid"></div>
            </div>
            <div class="form-group">
              <label><input type="checkbox" id="wh-active" checked /> Active</label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="IntegrationsView.closeModal('webhook-modal')">Cancel</button>
            <button class="btn btn-primary" onclick="IntegrationsView.saveWebhook()">Save</button>
          </div>
        </div>
      </div>

      <!-- Jira Connect Modal -->
      <div class="modal-overlay" id="jira-modal" style="display:none">
        <div class="modal" style="max-width:480px">
          <div class="modal-header">
            <h3>Connect Jira</h3>
            <button class="modal-close" onclick="IntegrationsView.closeModal('jira-modal')">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Jira URL *</label>
              <input type="url" id="jira-url" class="form-control" placeholder="https://company.atlassian.net" />
            </div>
            <div class="form-group">
              <label>Project Key *</label>
              <input type="text" id="jira-project-key" class="form-control" placeholder="PROJ" />
            </div>
            <div class="form-group">
              <label>Auth Type</label>
              <select id="jira-auth-type" class="form-control">
                <option value="api_token">API Token</option>
                <option value="oauth2">OAuth 2.0</option>
                <option value="basic">Basic Auth</option>
              </select>
            </div>
            <div class="form-group">
              <label>Credentials</label>
              <input type="password" id="jira-credentials" class="form-control" placeholder="API token or password" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="IntegrationsView.closeModal('jira-modal')">Cancel</button>
            <button class="btn btn-primary" onclick="IntegrationsView.saveJira()">Connect</button>
          </div>
        </div>
      </div>

      <!-- Automation Import Modal -->
      <div class="modal-overlay" id="import-modal" style="display:none">
        <div class="modal" style="max-width:480px">
          <div class="modal-header">
            <h3>Import Automation Results</h3>
            <button class="modal-close" onclick="IntegrationsView.closeModal('import-modal')">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Source</label>
              <select id="import-source" class="form-control">
                <option value="jenkins">Jenkins</option>
                <option value="github_actions">GitHub Actions</option>
                <option value="azure_devops">Azure DevOps</option>
                <option value="gitlab">GitLab CI</option>
                <option value="manual">Manual Upload</option>
              </select>
            </div>
            <div class="form-group">
              <label>Build ID</label>
              <input type="text" id="import-build-id" class="form-control" placeholder="build-123" />
            </div>
            <div class="form-group">
              <label>Result Format</label>
              <select id="import-entity-type" class="form-control">
                <option value="junit">JUnit XML</option>
                <option value="testng">TestNG XML</option>
                <option value="cucumber">Cucumber JSON</option>
                <option value="robot">Robot Framework</option>
                <option value="csv">CSV</option>
              </select>
            </div>
            <div class="form-group">
              <label>File Path / URL</label>
              <input type="text" id="import-file-path" class="form-control" placeholder="/reports/results.xml" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="IntegrationsView.closeModal('import-modal')">Cancel</button>
            <button class="btn btn-primary" onclick="IntegrationsView.submitImport()">Import</button>
          </div>
        </div>
      </div>
    `;
  }

  /* ── data loading ────────────────────────────────────── */
  async function loadAll() {
    await Promise.all([loadJira(), loadAutomationJobs(), loadWebhooks()]);
    renderTab();
  }

  async function loadJira() {
    try {
      const r = await fetch(`/api/v1/programs/${currentProgramId}/jira-integration`);
      jiraIntegration = r.ok ? await r.json() : null;
    } catch { jiraIntegration = null; }
  }

  async function loadAutomationJobs() {
    try {
      const r = await fetch(`/api/v1/programs/${currentProgramId}/automation-jobs`);
      const d = await r.json();
      automationJobs = d.items || [];
    } catch { automationJobs = []; }
  }

  async function loadWebhooks() {
    try {
      const r = await fetch(`/api/v1/programs/${currentProgramId}/webhooks`);
      const d = await r.json();
      webhooks = d.items || [];
    } catch { webhooks = []; }
  }

  /* ── tabs ────────────────────────────────────────────── */
  function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.integrations-tabs .tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    renderTab();
  }

  function renderTab() {
    const c = document.getElementById('integrations-tab-content');
    if (!c) return;
    if (activeTab === 'jira') renderJiraTab(c);
    else if (activeTab === 'automation') renderAutomationTab(c);
    else renderWebhooksTab(c);
  }

  /* ── Jira tab ────────────────────────────────────────── */
  function renderJiraTab(c) {
    if (!jiraIntegration) {
      c.innerHTML = `
        <div class="integration-empty">
          <i class="fab fa-jira fa-3x"></i>
          <p>No Jira integration configured</p>
          <button class="btn btn-primary" onclick="IntegrationsView.showJiraModal()">
            <i class="fas fa-link"></i> Connect Jira
          </button>
        </div>`;
      return;
    }
    const ji = jiraIntegration;
    c.innerHTML = `
      <div class="jira-card">
        <div class="jira-card-header">
          <div>
            <h3><i class="fab fa-jira"></i> ${ji.project_key}</h3>
            <span class="text-muted">${ji.jira_url}</span>
          </div>
          <span class="badge badge-${ji.is_active ? 'success' : 'secondary'}">
            ${ji.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div class="jira-card-body">
          <div class="jira-stat"><strong>Auth</strong><span>${ji.auth_type}</span></div>
          <div class="jira-stat"><strong>Sync Status</strong>
            <span class="badge badge-info">${ji.sync_status || 'idle'}</span>
          </div>
          <div class="jira-stat"><strong>Last Sync</strong>
            <span>${ji.last_sync_at ? new Date(ji.last_sync_at).toLocaleString() : 'Never'}</span>
          </div>
        </div>
        <div class="jira-card-footer">
          <button class="btn btn-sm btn-primary" onclick="IntegrationsView.syncJira(${ji.id})">
            <i class="fas fa-sync"></i> Sync Now
          </button>
          <button class="btn btn-sm btn-danger" onclick="IntegrationsView.deleteJira(${ji.id})">
            <i class="fas fa-trash"></i> Disconnect
          </button>
        </div>
      </div>`;
  }

  /* ── automation tab ──────────────────────────────────── */
  function renderAutomationTab(c) {
    let rows = automationJobs.map(j => `
      <tr>
        <td><code>${j.request_id.slice(0, 8)}</code></td>
        <td>${j.source}</td>
        <td>${j.build_id || '—'}</td>
        <td>${j.entity_type}</td>
        <td><span class="badge badge-${statusColor(j.status)}">${j.status}</span></td>
        <td>${new Date(j.created_at).toLocaleString()}</td>
      </tr>`).join('');
    if (!rows) rows = '<tr><td colspan="6" class="text-center text-muted">No import jobs yet</td></tr>';
    c.innerHTML = `
      <div class="automation-panel">
        <div class="panel-toolbar">
          <button class="btn btn-primary btn-sm" onclick="IntegrationsView.showImportModal()">
            <i class="fas fa-upload"></i> Import Results
          </button>
        </div>
        <table class="data-table">
          <thead><tr>
            <th>Request ID</th><th>Source</th><th>Build</th>
            <th>Format</th><th>Status</th><th>Created</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  /* ── webhooks tab ────────────────────────────────────── */
  function renderWebhooksTab(c) {
    let cards = webhooks.map(w => `
      <div class="webhook-card">
        <div class="webhook-card-header">
          <strong>${w.name || 'Unnamed'}</strong>
          <span class="badge badge-${w.is_active ? 'success' : 'secondary'}">
            ${w.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <div class="webhook-card-body">
          <div><i class="fas fa-link"></i> <code>${w.url}</code></div>
          <div class="webhook-events">
            ${(w.events || []).map(e => `<span class="tag">${e}</span>`).join('')}
          </div>
        </div>
        <div class="webhook-card-footer">
          <button class="btn btn-xs btn-outline" onclick="IntegrationsView.testWebhook(${w.id})">
            <i class="fas fa-paper-plane"></i> Test
          </button>
          <button class="btn btn-xs btn-outline" onclick="IntegrationsView.editWebhook(${w.id})">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-xs btn-danger" onclick="IntegrationsView.deleteWebhook(${w.id})">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>`).join('');
    if (!cards) cards = '<p class="text-center text-muted">No webhooks configured</p>';
    c.innerHTML = `
      <div class="webhooks-panel">
        <div class="panel-toolbar">
          <button class="btn btn-primary btn-sm" onclick="IntegrationsView.showWebhookModal()">
            <i class="fas fa-plus"></i> New Webhook
          </button>
        </div>
        <div class="webhooks-grid">${cards}</div>
      </div>`;
  }

  /* ── helpers ─────────────────────────────────────────── */
  function statusColor(s) {
    return { queued: 'warning', processing: 'info', completed: 'success', failed: 'danger' }[s] || 'secondary';
  }

  function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.style.display = 'none';
  }

  /* Jira modal */
  function showJiraModal() {
    document.getElementById('jira-url').value = '';
    document.getElementById('jira-project-key').value = '';
    document.getElementById('jira-auth-type').value = 'api_token';
    document.getElementById('jira-credentials').value = '';
    document.getElementById('jira-modal').style.display = 'flex';
  }

  async function saveJira() {
    const body = {
      jira_url: document.getElementById('jira-url').value,
      project_key: document.getElementById('jira-project-key').value,
      auth_type: document.getElementById('jira-auth-type').value,
      credentials: document.getElementById('jira-credentials').value,
    };
    await fetch(`/api/v1/programs/${currentProgramId}/jira-integration`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    closeModal('jira-modal');
    await loadJira();
    renderTab();
  }

  async function syncJira(id) {
    await fetch(`/api/v1/jira-integrations/${id}/sync`, { method: 'POST' });
    await loadJira();
    renderTab();
  }

  async function deleteJira(id) {
    if (!confirm('Disconnect Jira integration?')) return;
    await fetch(`/api/v1/jira-integrations/${id}`, { method: 'DELETE' });
    jiraIntegration = null;
    renderTab();
  }

  /* Webhook modal */
  const EVENT_TYPES = [
    'defect.created','defect.status_changed','execution.completed',
    'test_case.approved','test_case.created','test_case.updated',
    'cycle.completed','plan.completed','import.completed'
  ];

  function showWebhookModal(editId) {
    document.getElementById('wh-edit-id').value = editId || '';
    document.getElementById('wh-name').value = '';
    document.getElementById('wh-url').value = '';
    document.getElementById('wh-secret').value = '';
    document.getElementById('wh-active').checked = true;
    document.getElementById('webhook-modal-title').textContent = editId ? 'Edit Webhook' : 'New Webhook';

    const el = document.getElementById('wh-events-list');
    el.innerHTML = EVENT_TYPES.map(e => `
      <label class="checkbox-label"><input type="checkbox" value="${e}" /> ${e}</label>
    `).join('');

    if (editId) {
      const w = webhooks.find(x => x.id === editId);
      if (w) {
        document.getElementById('wh-name').value = w.name || '';
        document.getElementById('wh-url').value = w.url || '';
        document.getElementById('wh-active').checked = w.is_active;
        (w.events || []).forEach(ev => {
          const cb = el.querySelector(`input[value="${ev}"]`);
          if (cb) cb.checked = true;
        });
      }
    }
    document.getElementById('webhook-modal').style.display = 'flex';
  }

  function editWebhook(id) { showWebhookModal(id); }

  async function saveWebhook() {
    const editId = document.getElementById('wh-edit-id').value;
    const events = Array.from(document.querySelectorAll('#wh-events-list input:checked')).map(cb => cb.value);
    const body = {
      name: document.getElementById('wh-name').value,
      url: document.getElementById('wh-url').value,
      secret: document.getElementById('wh-secret').value,
      events,
      is_active: document.getElementById('wh-active').checked,
    };
    const url = editId ? `/api/v1/webhooks/${editId}` : `/api/v1/programs/${currentProgramId}/webhooks`;
    await fetch(url, {
      method: editId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    closeModal('webhook-modal');
    await loadWebhooks();
    renderTab();
  }

  async function testWebhook(id) {
    const r = await fetch(`/api/v1/webhooks/${id}/test`, { method: 'POST' });
    if (r.ok) alert('Ping delivered successfully!');
    else alert('Webhook test failed');
  }

  async function deleteWebhook(id) {
    if (!confirm('Delete this webhook?')) return;
    await fetch(`/api/v1/webhooks/${id}`, { method: 'DELETE' });
    await loadWebhooks();
    renderTab();
  }

  /* Import modal */
  function showImportModal() {
    document.getElementById('import-source').value = 'jenkins';
    document.getElementById('import-build-id').value = '';
    document.getElementById('import-entity-type').value = 'junit';
    document.getElementById('import-file-path').value = '';
    document.getElementById('import-modal').style.display = 'flex';
  }

  async function submitImport() {
    const body = {
      program_id: currentProgramId,
      source: document.getElementById('import-source').value,
      build_id: document.getElementById('import-build-id').value,
      entity_type: document.getElementById('import-entity-type').value,
      file_path: document.getElementById('import-file-path').value,
    };
    await fetch('/api/v1/integrations/automation/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    closeModal('import-modal');
    await loadAutomationJobs();
    renderTab();
  }

  function openApiSpec() {
    window.open('/api/v1/openapi.json', '_blank');
  }

  return {
    init, switchTab, closeModal,
    showJiraModal, saveJira, syncJira, deleteJira,
    showWebhookModal, editWebhook, saveWebhook, testWebhook, deleteWebhook,
    showImportModal, submitImport, openApiSpec,
  };
})();
