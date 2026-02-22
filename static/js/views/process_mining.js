/**
 * S8-01 FDD-I05 Phase B — Process Mining SPA view.
 *
 * 3-tab interface:
 *   Tab 1: Connection  — status indicator, test button, configure form
 *   Tab 2: Import Wizard — browse provider processes + checkbox import
 *   Tab 3: Imported Variants — table with conformance rate, Promote / Reject actions
 *
 * Public API (mounted as window.ProcessMiningView):
 *   init(container)         — boot the view inside `container` element
 *   testConnection()        — programmatic connection test trigger
 *   openConfigForm()        — programmatic open of the config form
 *   importSelected()        — trigger import of checked variants
 *   promoteVariant(id)      — promote a specific import record
 *   rejectVariant(id)       — reject a specific import record
 *
 * Called by integrations.js renderProcessMiningTab().
 * Reads tenant_id and project_id from window.App.state (set by app-shell).
 */
window.ProcessMiningView = (function () {
  "use strict";

  /* ── Constants ─────────────────────────────────────────────────────────── */
  const BASE = "/api/v1";
  const TABS = ["connection", "import", "variants"];
  const TAB_LABELS = {
    connection: "Bağlantı",
    import: "İçe Aktar",
    variants: "Varyantlar",
  };
  const PROVIDER_OPTIONS = [
    { value: "celonis", label: "Celonis" },
    { value: "signavio", label: "SAP Signavio" },
    { value: "uipath", label: "UiPath Process Mining" },
    { value: "sap_lama", label: "SAP LAMA" },
    { value: "custom", label: "Custom / Diğer" },
  ];

  /* ── Module state (reset on each init() call) ────────────────────────── */
  let _container = null;
  let _activeTab = "connection";
  let _tenantId = null;
  let _projectId = null;

  // Cached data
  let _connection = null;    // ProcessMiningConnection dict or null
  let _processes = [];       // list of provider processes
  let _variants = [];        // list of provider variants for selected process
  let _selectedProcessId = null;
  let _selectedVariantIds = new Set();
  let _imports = [];         // list of ProcessVariantImport records

  /* ── Utility ──────────────────────────────────────────────────────────── */

  function _tenantParams() {
    return _tenantId ? `?tenant_id=${_tenantId}` : "";
  }

  function _tenantBody(extra = {}) {
    return { tenant_id: _tenantId, ...extra };
  }

  async function _api(method, path, body = null) {
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    let json = null;
    try { json = await res.json(); } catch (_) {}
    return { ok: res.ok, status: res.status, data: json };
  }

  function _toast(msg, isError = false) {
    const el = document.createElement("div");
    el.style.cssText = `
      position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;
      padding:.75rem 1.25rem;border-radius:8px;font-size:.9rem;
      box-shadow:0 4px 12px rgba(0,0,0,.15);max-width:340px;
      background:${isError ? "#fee2e2" : "#d1fae5"};
      color:${isError ? "#991b1b" : "#065f46"};
    `;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  function _loading(text = "Yükleniyor…") {
    return `<div style="padding:2rem;text-align:center;color:#6b7280">
      <i class="fas fa-spinner fa-spin"></i> ${text}
    </div>`;
  }

  function _statusBadge(status) {
    const MAP = {
      active: ["#d1fae5", "#065f46", "check-circle", "Aktif"],
      testing: ["#dbeafe", "#1e40af", "sync fa-spin", "Test ediliyor…"],
      configured: ["#fef3c7", "#92400e", "cog", "Yapılandırıldı"],
      failed: ["#fee2e2", "#991b1b", "exclamation-circle", "Hata"],
      disabled: ["#f3f4f6", "#6b7280", "ban", "Devre Dışı"],
    };
    const [bg, clr, ico, label] = MAP[status] || MAP["configured"];
    return `<span style="background:${bg};color:${clr};padding:.25rem .6rem;
      border-radius:20px;font-size:.78rem;font-weight:600">
      <i class="fas fa-${ico}" style="margin-right:.3rem"></i>${label}
    </span>`;
  }

  /* ── Render skeleton ─────────────────────────────────────────────────── */

  function _renderShell() {
    _container.innerHTML = `
      <div style="padding:1.5rem">
        <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:1rem">
          <i class="fas fa-project-diagram" style="font-size:1.4rem;color:#8b5cf6"></i>
          <h3 style="margin:0;font-size:1.1rem;font-weight:600">Process Mining Entegrasyonu</h3>
        </div>

        <div id="pm-tabs" style="display:flex;gap:.5rem;border-bottom:2px solid #e5e7eb;margin-bottom:1.25rem">
          ${TABS.map(t => `
            <button id="pm-tab-${t}" onclick="window.ProcessMiningView._switchTab('${t}')"
              style="padding:.5rem 1rem;border:none;background:none;cursor:pointer;
                font-size:.88rem;font-weight:500;
                ${t === _activeTab ? "border-bottom:2px solid #8b5cf6;color:#8b5cf6;margin-bottom:-2px" : "color:#6b7280"}">
              ${TAB_LABELS[t]}
            </button>`).join("")}
        </div>

        <div id="pm-tab-content">${_loading()}</div>
      </div>`;
  }

  function _setTabActive(tabId) {
    TABS.forEach(t => {
      const btn = document.getElementById(`pm-tab-${t}`);
      if (!btn) return;
      if (t === tabId) {
        btn.style.borderBottom = "2px solid #8b5cf6";
        btn.style.color = "#8b5cf6";
        btn.style.marginBottom = "-2px";
      } else {
        btn.style.borderBottom = "none";
        btn.style.color = "#6b7280";
        btn.style.marginBottom = "0";
      }
    });
  }

  function _tabContent() {
    return document.getElementById("pm-tab-content");
  }

  function _switchTab(tabId) {
    _activeTab = tabId;
    _setTabActive(tabId);
    switch (tabId) {
      case "connection": _renderConnectionTab(); break;
      case "import":    _renderImportTab(); break;
      case "variants":  _renderVariantsTab(); break;
    }
  }

  /* ── Tab 1: Connection ─────────────────────────────────────────────────── */

  async function _renderConnectionTab() {
    const c = _tabContent();
    if (!c) return;
    c.innerHTML = _loading("Bağlantı bilgileri alınıyor…");

    const { ok, data } = await _api("GET", `${BASE}/integrations/process-mining${_tenantParams()}`);
    _connection = (ok && data) ? data.config : null;

    if (!_connection) {
      c.innerHTML = _renderConfigForm(null);
      return;
    }

    c.innerHTML = `
      <div style="display:grid;gap:1rem">
        <div style="background:#f9fafb;border-radius:8px;padding:1rem">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem">
            <strong style="font-size:.95rem">Bağlantı Durumu</strong>
            ${_statusBadge(_connection.status || "configured")}
          </div>
          <table style="font-size:.85rem;width:100%;border-collapse:collapse">
            <tr><td style="padding:.3rem .5rem;color:#6b7280;width:40%">Sağlayıcı</td>
                <td style="padding:.3rem .5rem;font-weight:500;text-transform:capitalize">${_connection.provider || "—"}</td></tr>
            <tr><td style="padding:.3rem .5rem;color:#6b7280">URL</td>
                <td style="padding:.3rem .5rem;word-break:break-all">${_connection.connection_url || "—"}</td></tr>
            <tr><td style="padding:.3rem .5rem;color:#6b7280">Durum</td>
                <td style="padding:.3rem .5rem">${_connection.status || "—"}</td></tr>
            <tr><td style="padding:.3rem .5rem;color:#6b7280">Son Test</td>
                <td style="padding:.3rem .5rem">${_connection.last_tested_at ? new Date(_connection.last_tested_at).toLocaleString("tr-TR") : "Henüz test edilmedi"}</td></tr>
            ${_connection.error_message ? `
            <tr><td style="padding:.3rem .5rem;color:#6b7280">Hata</td>
                <td style="padding:.3rem .5rem;color:#dc2626">${_connection.error_message}</td></tr>` : ""}
          </table>
        </div>

        <div style="display:flex;gap:.5rem;flex-wrap:wrap">
          <button onclick="window.ProcessMiningView.testConnection()"
            style="padding:.5rem 1rem;background:#8b5cf6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
            <i class="fas fa-plug"></i> Bağlantıyı Test Et
          </button>
          <button onclick="window.ProcessMiningView.openConfigForm()"
            style="padding:.5rem 1rem;background:#e5e7eb;color:#374151;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
            <i class="fas fa-cog"></i> Yapılandır
          </button>
          <button onclick="window.ProcessMiningView._deleteConnection()"
            style="padding:.5rem 1rem;background:#fee2e2;color:#dc2626;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
            <i class="fas fa-trash"></i> Sil
          </button>
        </div>
      </div>`;
  }

  function _renderConfigForm(existing) {
    const v = existing || {};
    const providerOpts = PROVIDER_OPTIONS.map(o =>
      `<option value="${o.value}" ${(v.provider || "celonis") === o.value ? "selected" : ""}>${o.label}</option>`
    ).join("");

    return `
      <form id="pm-config-form" onsubmit="window.ProcessMiningView._submitConfig(event)">
        <div style="display:grid;gap:.75rem">
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">Sağlayıcı *</label>
            <select id="pm-provider" name="provider" required
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
              ${providerOpts}
            </select>
          </div>
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">Bağlantı URL *</label>
            <input id="pm-url" type="url" name="connection_url" required maxlength="500"
              value="${v.connection_url || ""}"
              placeholder="https://tenant.celonis.cloud"
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
          </div>
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">API Key
              <span style="color:#6b7280;font-weight:400">(Celonis)</span></label>
            <input id="pm-apikey" type="password" name="api_key" maxlength="500"
              placeholder="Mevcut anahtarı korumak için boş bırakın"
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
          </div>
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">Client ID
              <span style="color:#6b7280;font-weight:400">(OAuth2 / Signavio)</span></label>
            <input id="pm-clientid" type="text" name="client_id" maxlength="200"
              value="${v.client_id || ""}"
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
          </div>
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">Client Secret
              <span style="color:#6b7280;font-weight:400">(OAuth2)</span></label>
            <input id="pm-secret" type="password" name="client_secret" maxlength="500"
              placeholder="Mevcut sırrı korumak için boş bırakın"
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
          </div>
          <div>
            <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">Token URL
              <span style="color:#6b7280;font-weight:400">(Signavio OAuth2)</span></label>
            <input id="pm-tokenurl" type="url" name="token_url" maxlength="500"
              value="${v.token_url || ""}"
              placeholder="https://signavio.example.com/oauth/token"
              style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.9rem">
          </div>
          <div style="display:flex;align-items:center;gap:.5rem">
            <input id="pm-enabled" type="checkbox" name="is_enabled" ${v.is_enabled ? "checked" : ""}
              style="width:1rem;height:1rem">
            <label for="pm-enabled" style="font-size:.88rem">Entegrasyonu Etkinleştir</label>
          </div>
          <div style="display:flex;gap:.5rem;margin-top:.25rem">
            <button type="submit"
              style="padding:.5rem 1.25rem;background:#8b5cf6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.88rem">
              <i class="fas fa-save"></i> Kaydet
            </button>
            ${existing ? `<button type="button" onclick="window.ProcessMiningView._renderConnectionTab()"
              style="padding:.5rem 1rem;background:#e5e7eb;color:#374151;border:none;border-radius:6px;cursor:pointer;font-size:.88rem">
              İptal
            </button>` : ""}
          </div>
        </div>
      </form>`;
  }

  async function _submitConfig(e) {
    e.preventDefault();
    const form = document.getElementById("pm-config-form");
    if (!form) return;

    const body = _tenantBody({
      provider: form.provider.value,
      connection_url: form.connection_url.value.trim(),
      client_id: form.client_id.value.trim() || undefined,
      client_secret: form.client_secret.value || undefined,
      api_key: form.api_key.value || undefined,
      token_url: form.token_url.value.trim() || undefined,
      is_enabled: form.is_enabled.checked,
    });

    const method = _connection ? "PUT" : "POST";
    const { ok, data } = await _api(method, `${BASE}/integrations/process-mining`, body);
    if (ok) {
      _connection = data;
      _toast("Bağlantı kaydedildi.");
      _renderConnectionTab();
    } else {
      _toast((data && data.error) || "Kayıt başarısız.", true);
    }
  }

  async function _deleteConnection() {
    if (!confirm("Bu bağlantıyı ve tüm içe aktarmaları silmek istiyor musunuz?")) return;
    const { ok } = await _api("DELETE", `${BASE}/integrations/process-mining${_tenantParams()}`);
    if (ok) {
      _connection = null;
      _toast("Bağlantı silindi.");
      _renderConnectionTab();
    } else {
      _toast("Silme işlemi başarısız.", true);
    }
  }

  /* ── Tab 2: Import Wizard ──────────────────────────────────────────────── */

  async function _renderImportTab() {
    const c = _tabContent();
    if (!c) return;
    c.innerHTML = _loading("Süreçler yükleniyor…");

    const { ok, data } = await _api("GET", `${BASE}/integrations/process-mining/processes${_tenantParams()}`);
    if (!ok || !data || !data.ok) {
      c.innerHTML = `<div style="padding:1.5rem;text-align:center;color:#dc2626">
        <i class="fas fa-exclamation-circle"></i>
        ${(data && data.error) || "Sağlayıcıdan süreçler alınamadı. Bağlantıyı kontrol edin."}
        <br><br>
        <button onclick="window.ProcessMiningView._switchTab('connection')"
          style="padding:.5rem 1rem;background:#e5e7eb;color:#374151;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
          Bağlantı Sekmesine Git
        </button>
      </div>`;
      return;
    }

    _processes = data.processes || [];
    _renderProcessList(c);
  }

  function _renderProcessList(c) {
    if (!_processes.length) {
      c.innerHTML = `<div style="padding:1.5rem;text-align:center;color:#6b7280">
        <i class="fas fa-inbox"></i> Sağlayıcıda hiç süreç bulunamadı.
      </div>`;
      return;
    }

    c.innerHTML = `
      <div style="display:grid;gap:1rem">
        <div>
          <p style="font-size:.88rem;color:#374151;margin:.5rem 0">
            Aşağıdan bir süreç seçin ve varyantlarını görüntüleyin.
          </p>
          <div style="display:grid;gap:.4rem;max-height:320px;overflow-y:auto;border:1px solid #e5e7eb;border-radius:8px;padding:.5rem">
            ${_processes.map(p => {
              const pid = p.id || p.variantId || "unknown";
              const name = p.name || p.processName || pid;
              return `<button onclick="window.ProcessMiningView._loadVariants('${pid}', this)"
                style="text-align:left;padding:.5rem .75rem;border:1px solid #e5e7eb;border-radius:6px;
                  background:#fff;cursor:pointer;font-size:.85rem;transition:background .15s"
                onmouseover="this.style.background='#f3f0ff'" onmouseout="this.style.background='#fff'">
                <i class="fas fa-sitemap" style="color:#8b5cf6;margin-right:.4rem"></i>
                ${name}
              </button>`;
            }).join("")}
          </div>
        </div>
        <div id="pm-variant-section"></div>
      </div>`;
  }

  async function _loadVariants(processId, btn) {
    _selectedProcessId = processId;
    _selectedVariantIds.clear();

    // Highlight active process button
    btn.closest("div").querySelectorAll("button").forEach(b => {
      b.style.background = "#fff";
      b.style.borderColor = "#e5e7eb";
    });
    btn.style.background = "#f3f0ff";
    btn.style.borderColor = "#8b5cf6";

    const section = document.getElementById("pm-variant-section");
    if (!section) return;
    section.innerHTML = _loading("Varyantlar yükleniyor…");

    const { ok, data } = await _api(
      "GET",
      `${BASE}/integrations/process-mining/processes/${encodeURIComponent(processId)}/variants${_tenantParams()}`
    );
    if (!ok || !data || !data.ok) {
      section.innerHTML = `<div style="color:#dc2626;font-size:.85rem;padding:.5rem">
        ${(data && data.error) || "Varyantlar alınamadı."}
      </div>`;
      return;
    }

    _variants = data.variants || [];
    _renderVariantCheckboxes(section);
  }

  function _renderVariantCheckboxes(section) {
    if (!_variants.length) {
      section.innerHTML = `<p style="color:#6b7280;font-size:.85rem;padding:.5rem">Bu süreç için varyant bulunamadı.</p>`;
      return;
    }

    section.innerHTML = `
      <div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">
          <strong style="font-size:.88rem">${_variants.length} varyant bulundu</strong>
          <label style="font-size:.82rem;color:#6b7280">
            <input type="checkbox" id="pm-select-all" onchange="window.ProcessMiningView._toggleAll(this)">
            Tümünü seç
          </label>
        </div>
        <div style="display:grid;gap:.3rem;max-height:260px;overflow-y:auto;border:1px solid #e5e7eb;border-radius:8px;padding:.5rem;margin-bottom:.75rem">
          ${_variants.map(v => {
            const vid = v.id || v.variantId || v.variant_id || "?";
            const name = v.name || v.processName || vid;
            const conformance = v.conformance != null ? `${Number(v.conformance).toFixed(1)}%` : "—";
            const count = v.caseCount || v.variant_count || "?";
            return `<label style="display:flex;align-items:center;gap:.5rem;padding:.3rem .4rem;border-radius:4px;cursor:pointer;font-size:.84rem"
              onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='transparent'">
              <input type="checkbox" value="${vid}" onchange="window.ProcessMiningView._toggleVariant('${vid}', this.checked)"
                style="flex-shrink:0">
              <span style="flex:1">${name}</span>
              <span style="color:#6b7280;font-size:.78rem">Uyum: ${conformance} | ${count} örnek</span>
            </label>`;
          }).join("")}
        </div>
        <button onclick="window.ProcessMiningView.importSelected()"
          style="padding:.5rem 1.25rem;background:#8b5cf6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.88rem">
          <i class="fas fa-download"></i> Seçilenleri İçe Aktar
        </button>
      </div>`;
  }

  function _toggleAll(checkbox) {
    const isChecked = checkbox.checked;
    _selectedVariantIds.clear();
    document.querySelectorAll("#pm-variant-section input[type=checkbox][value]").forEach(cb => {
      cb.checked = isChecked;
      if (isChecked) _selectedVariantIds.add(cb.value);
    });
  }

  function _toggleVariant(id, checked) {
    if (checked) _selectedVariantIds.add(id);
    else _selectedVariantIds.delete(id);

    // Update "select all" state
    const allCbs = document.querySelectorAll("#pm-variant-section input[type=checkbox][value]");
    const selectAll = document.getElementById("pm-select-all");
    if (selectAll && allCbs.length) {
      selectAll.checked = allCbs.length === _selectedVariantIds.size;
      selectAll.indeterminate = _selectedVariantIds.size > 0 && _selectedVariantIds.size < allCbs.length;
    }
  }

  /* ── Tab 3: Imported Variants ──────────────────────────────────────────── */

  async function _renderVariantsTab() {
    const c = _tabContent();
    if (!c) return;
    if (!_projectId) {
      c.innerHTML = `<div style="padding:1.5rem;color:#6b7280;text-align:center">
        <i class="fas fa-info-circle"></i>
        Bu sekmeyi kullanmak için bir proje bağlamında olmanız gerekiyor.
      </div>`;
      return;
    }

    c.innerHTML = _loading("İçe aktarmalar yükleniyor…");
    const { ok, data } = await _api(
      "GET",
      `${BASE}/projects/${_projectId}/process-mining/imports${_tenantParams()}`
    );
    if (!ok) {
      c.innerHTML = `<div style="padding:1rem;color:#dc2626">İçe aktarmalar alınamadı.</div>`;
      return;
    }

    _imports = (data && data.items) || [];
    _renderImportsTable(c);
  }

  function _renderImportsTable(c) {
    if (!_imports.length) {
      c.innerHTML = `<div style="padding:1.5rem;text-align:center;color:#6b7280">
        <i class="fas fa-inbox"></i> Henüz içe aktarma yok.
        <br><br>
        <button onclick="window.ProcessMiningView._switchTab('import')"
          style="padding:.5rem 1rem;background:#8b5cf6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.85rem">
          İçe Aktarma Sihirbazına Git
        </button>
      </div>`;
      return;
    }

    const STATUS_STYLES = {
      imported: ["#dbeafe", "#1e40af"],
      reviewed: ["#fef3c7", "#92400e"],
      promoted: ["#d1fae5", "#065f46"],
      rejected: ["#f3f4f6", "#6b7280"],
    };

    const rows = _imports.map(imp => {
      const [bg, clr] = STATUS_STYLES[imp.status] || STATUS_STYLES.imported;
      const conformance = imp.conformance_rate != null
        ? `${Number(imp.conformance_rate).toFixed(1)}%` : "—";
      const actions = imp.status === "imported" || imp.status === "reviewed"
        ? `<button onclick="window.ProcessMiningView._openPromoteModal(${imp.id})"
             style="padding:.25rem .5rem;background:#8b5cf6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:.78rem;margin-right:.25rem">
             <i class="fas fa-level-up-alt"></i> Promote
           </button>
           <button onclick="window.ProcessMiningView.rejectVariant(${imp.id})"
             style="padding:.25rem .5rem;background:#fee2e2;color:#dc2626;border:none;border-radius:4px;cursor:pointer;font-size:.78rem">
             <i class="fas fa-times"></i> Reject
           </button>`
        : `<span style="font-size:.78rem;color:#6b7280;font-style:italic">${imp.status}</span>`;

      return `<tr>
        <td style="padding:.4rem .6rem">${imp.id}</td>
        <td style="padding:.4rem .6rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${imp.process_name || "—"}</td>
        <td style="padding:.4rem .6rem;text-align:center">${imp.variant_count || "—"}</td>
        <td style="padding:.4rem .6rem;text-align:center">${conformance}</td>
        <td style="padding:.4rem .6rem;text-align:center">
          <span style="background:${bg};color:${clr};padding:.15rem .5rem;border-radius:12px;font-size:.75rem;font-weight:600">
            ${imp.status}
          </span>
        </td>
        <td style="padding:.4rem .6rem">${actions}</td>
      </tr>`;
    }).join("");

    c.innerHTML = `
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:.85rem">
          <thead>
            <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
              <th style="padding:.4rem .6rem;text-align:left">ID</th>
              <th style="padding:.4rem .6rem;text-align:left">Süreç Adı</th>
              <th style="padding:.4rem .6rem;text-align:center">Örnek</th>
              <th style="padding:.4rem .6rem;text-align:center">Uyum</th>
              <th style="padding:.4rem .6rem;text-align:center">Durum</th>
              <th style="padding:.4rem .6rem">İşlemler</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function _openPromoteModal(importId) {
    const imp = _imports.find(i => i.id === importId);
    if (!imp) return;

    const existing = document.getElementById("pm-promote-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "pm-promote-modal";
    modal.style.cssText = `
      position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:10000;
      display:flex;align-items:center;justify-content:center;`;
    modal.innerHTML = `
      <div style="background:#fff;border-radius:12px;padding:1.5rem;width:min(90vw,480px);box-shadow:0 20px 60px rgba(0,0,0,.2)">
        <h4 style="margin:0 0 1rem 0;font-size:1rem">Varyantı L4 Süreç Adımına Promote Et</h4>
        <p style="font-size:.85rem;color:#374151;margin-bottom:.75rem">
          Varyant: <strong>${imp.process_name || imp.id}</strong>
        </p>
        <div style="margin-bottom:.75rem">
          <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">
            L3 Üst Seviye UUID *
          </label>
          <input id="pm-parent-level-id" type="text" maxlength="36"
            placeholder="00000000-0000-0000-0000-000000000000"
            style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.88rem">
        </div>
        <div style="margin-bottom:1rem">
          <label style="display:block;font-size:.85rem;margin-bottom:.25rem;font-weight:500">
            Başlık <span style="font-weight:400;color:#6b7280">(isteğe bağlı)</span>
          </label>
          <input id="pm-promote-title" type="text" maxlength="255"
            value="${imp.process_name || ""}"
            style="width:100%;padding:.5rem;border:1px solid #d1d5db;border-radius:6px;font-size:.88rem">
        </div>
        <div style="display:flex;gap:.5rem">
          <button onclick="window.ProcessMiningView.promoteVariant(${importId})"
            style="padding:.5rem 1.25rem;background:#8b5cf6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.88rem">
            <i class="fas fa-level-up-alt"></i> Promote Et
          </button>
          <button onclick="document.getElementById('pm-promote-modal').remove()"
            style="padding:.5rem 1rem;background:#e5e7eb;color:#374151;border:none;border-radius:6px;cursor:pointer;font-size:.88rem">
            İptal
          </button>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }

  /* ── Public API ─────────────────────────────────────────────────────────── */

  async function testConnection() {
    _toast("Test başlatılıyor…");
    const { ok, data } = await _api("POST", `${BASE}/integrations/process-mining/test`, _tenantBody());
    if (data && data.ok) {
      _toast(`✓ ${data.message || "Bağlantı başarılı."}`);
    } else {
      _toast((data && data.message) || "Bağlantı testi başarısız.", true);
    }
    _renderConnectionTab();
  }

  function openConfigForm() {
    const c = _tabContent();
    if (c) c.innerHTML = _renderConfigForm(_connection);
  }

  async function importSelected() {
    if (!_selectedProcessId) {
      _toast("Lütfen önce bir süreç seçin.", true);
      return;
    }
    if (!_projectId) {
      _toast("Import işlemi için proje bağlamı gerekiyor.", true);
      return;
    }
    const selected = Array.from(_selectedVariantIds);

    const { ok, data } = await _api(
      "POST",
      `${BASE}/projects/${_projectId}/process-mining/import`,
      _tenantBody({
        process_id: _selectedProcessId,
        selected_variant_ids: selected.length ? selected : undefined,
      })
    );
    if (ok && data) {
      _toast(`${data.imported} varyant içe aktarıldı, ${data.skipped} atlandı.`);
      _selectedVariantIds.clear();
      _switchTab("variants");
    } else {
      _toast((data && data.error) || "İçe aktarma başarısız.", true);
    }
  }

  async function promoteVariant(importId) {
    const parentId = (document.getElementById("pm-parent-level-id") || {}).value || "";
    const title = (document.getElementById("pm-promote-title") || {}).value || "";
    if (!parentId.trim()) {
      _toast("Üst seviye UUID gerekli.", true);
      return;
    }
    if (!_projectId) { _toast("Proje bağlamı gerekli.", true); return; }

    const { ok, data } = await _api(
      "POST",
      `${BASE}/projects/${_projectId}/process-mining/imports/${importId}/promote`,
      _tenantBody({ parent_process_level_id: parentId.trim(), title: title.trim() || undefined })
    );
    document.getElementById("pm-promote-modal")?.remove();
    if (ok) {
      _toast("Varyant L4 süreç adımına promote edildi.");
      _renderVariantsTab();
    } else {
      _toast((data && data.error) || "Promote işlemi başarısız.", true);
    }
  }

  async function rejectVariant(importId) {
    if (!confirm("Bu varyantı reddetmek istiyor musunuz?")) return;
    if (!_projectId) { _toast("Proje bağlamı gerekli.", true); return; }

    const { ok, data } = await _api(
      "POST",
      `${BASE}/projects/${_projectId}/process-mining/imports/${importId}/reject`,
      _tenantBody()
    );
    if (ok) {
      _toast("Varyant reddedildi.");
      _renderVariantsTab();
    } else {
      _toast((data && data.error) || "Red işlemi başarısız.", true);
    }
  }

  /* ── init ───────────────────────────────────────────────────────────────── */

  function init(container) {
    _container = container;
    _activeTab = "connection";

    // Resolve tenant + project from app state if available
    const state = (window.App && window.App.state) || {};
    _tenantId = state.tenantId || state.tenant_id || null;
    _projectId = state.projectId || state.project_id || state.currentProjectId || null;

    _renderShell();
    _renderConnectionTab();
  }

  /* ── Expose public interface ─────────────────────────────────────────────── */
  return {
    init,
    testConnection,
    openConfigForm,
    importSelected,
    promoteVariant,
    rejectVariant,
    // Internal helpers exposed for inline onclick handlers
    _switchTab,
    _renderConnectionTab,
    _submitConfig,
    _deleteConnection,
    _loadVariants,
    _toggleAll,
    _toggleVariant,
    _openPromoteModal,
  };
})();
