/* ================================================================
   F7 — Data-Driven / Parametric Testing View
   static/js/views/data_driven.js
   ================================================================ */
const DataDrivenView = (function () {
  "use strict";

  let _currentTcId = null;
  let _activeTab = "parameters";

  /* ── public render ─────────────────────────────────────────── */
  function render() {
    const main = document.getElementById("main-content");
    if (!main) return;
    const programId = window.currentProgramId;
    if (!programId) {
      main.innerHTML = '<div class="f7-empty">Lütfen önce bir program seçin.</div>';
      return;
    }
    main.innerHTML = `
      <div class="f7-layout">
        <div class="f7-sidebar">
          <h3>Test Cases</h3>
          <input type="text" id="f7dd-tc-search" class="f7-search"
                 placeholder="TC ara…" />
          <div id="f7dd-tc-list" class="f7-tc-list"></div>
        </div>
        <div class="f7-main">
          <div class="f7-tabs">
            <button class="f7-tab active" data-tab="parameters">Parameters</button>
            <button class="f7-tab" data-tab="bindings">Data Bindings</button>
            <button class="f7-tab" data-tab="iterations">Iterations</button>
            <button class="f7-tab" data-tab="templates">Suite Templates</button>
          </div>
          <div id="f7dd-tab-content" class="f7-tab-content">
            <div class="f7-empty">Sol panelden bir Test Case seçin.</div>
          </div>
        </div>
      </div>`;

    document.getElementById("f7dd-tc-search")
      .addEventListener("input", _debounce(_loadTcList, 300));
    main.querySelectorAll(".f7-tab").forEach(btn => {
      btn.addEventListener("click", () => _switchTab(btn.dataset.tab));
    });
    _loadTcList();
  }

  /* ── Load TC list ──────────────────────────────────────────── */
  async function _loadTcList() {
    const programId = window.currentProgramId;
    const search = (document.getElementById("f7dd-tc-search") || {}).value || "";
    try {
      const resp = await fetch(
        `/api/v1/programs/${programId}/testing/test-cases?per_page=100&search=${encodeURIComponent(search)}`,
        { headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const list = document.getElementById("f7dd-tc-list");
      if (!list) return;
      const tcs = json.test_cases || json.items || [];
      list.innerHTML = tcs.map(tc => `
        <div class="f7-tc-item ${tc.id === _currentTcId ? 'active' : ''}"
             data-id="${tc.id}">
          <span class="f7-tc-code">${tc.code || ''}</span>
          <span class="f7-tc-title">${tc.title}</span>
        </div>`).join("");
      list.querySelectorAll(".f7-tc-item").forEach(el => {
        el.addEventListener("click", () => {
          _currentTcId = parseInt(el.dataset.id);
          document.querySelectorAll(".f7-tc-item").forEach(x =>
            x.classList.toggle("active", parseInt(x.dataset.id) === _currentTcId));
          _switchTab(_activeTab);
        });
      });
    } catch (e) { console.error(e); }
  }

  /* ── Tab switch ─────────────────────────────────────────────── */
  function _switchTab(tab) {
    _activeTab = tab;
    document.querySelectorAll(".f7-tab").forEach(b =>
      b.classList.toggle("active", b.dataset.tab === tab));
    const c = document.getElementById("f7dd-tab-content");
    if (!c) return;
    if (tab === "parameters") _renderParameters(c);
    else if (tab === "bindings") _renderBindings(c);
    else if (tab === "iterations") _renderIterations(c);
    else if (tab === "templates") _renderTemplates(c);
  }

  /* ── Parameters ─────────────────────────────────────────────── */
  async function _renderParameters(container) {
    if (!_currentTcId) {
      container.innerHTML = '<div class="f7-empty">TC seçin.</div>';
      return;
    }
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/parameters`,
        { headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const params = json.parameters || [];
      container.innerHTML = `
        <div class="f7-params">
          <div class="f7-params-header">
            <h4>Parameters (${params.length})</h4>
            <button id="f7dd-add-param" class="f7-btn f7-btn-primary">+ Parametre Ekle</button>
          </div>
          <table class="f7-param-table">
            <thead><tr><th>Ad</th><th>Tip</th><th>Kaynak</th><th>Değerler</th><th></th></tr></thead>
            <tbody>
              ${params.map(p => `
                <tr>
                  <td><code>{{${p.name}}}</code></td>
                  <td>${p.data_type}</td>
                  <td>${p.source}</td>
                  <td>${(p.values || []).slice(0, 3).join(", ")}${p.values && p.values.length > 3 ? '…' : ''}</td>
                  <td>
                    <button class="f7-btn-sm f7-btn-danger f7-del-param" data-id="${p.id}">×</button>
                  </td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>`;
      document.getElementById("f7dd-add-param")
        .addEventListener("click", _addParameter);
      container.querySelectorAll(".f7-del-param").forEach(btn => {
        btn.addEventListener("click", () => _deleteParameter(parseInt(btn.dataset.id)));
      });
    } catch (e) {
      container.innerHTML = '<div class="f7-empty">Yükleme hatası.</div>';
    }
  }

  async function _addParameter() {
    const name = prompt("Parametre adı (ör: customer_id):");
    if (!name) return;
    const valuesStr = prompt("Değerler (virgülle ayır):", "");
    const values = valuesStr ? valuesStr.split(",").map(v => v.trim()) : [];
    await fetch(`/api/v1/testing/test-cases/${_currentTcId}/parameters`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User": "admin" },
      body: JSON.stringify({ name, values, data_type: "string", source: "manual" }),
    });
    _switchTab("parameters");
  }

  async function _deleteParameter(pid) {
    await fetch(`/api/v1/testing/parameters/${pid}`, {
      method: "DELETE",
      headers: { "X-User": "admin" },
    });
    _switchTab("parameters");
  }

  /* ── Data Bindings ──────────────────────────────────────────── */
  async function _renderBindings(container) {
    if (!_currentTcId) {
      container.innerHTML = '<div class="f7-empty">TC seçin.</div>';
      return;
    }
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/data-bindings`,
        { headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const bindings = json.data_bindings || [];
      container.innerHTML = `
        <div class="f7-bindings">
          <div class="f7-params-header">
            <h4>Data Bindings (${bindings.length})</h4>
            <button id="f7dd-add-binding" class="f7-btn f7-btn-primary">+ Binding Ekle</button>
          </div>
          <div class="f7-binding-list">
            ${bindings.map(b => `
              <div class="f7-binding-card">
                <div class="f7-binding-info">
                  <strong>DataSet #${b.data_set_id}</strong>
                  <span class="f7-badge">${b.iteration_mode}</span>
                  ${b.max_iterations ? `<span class="f7-badge">max: ${b.max_iterations}</span>` : ''}
                </div>
                <div class="f7-binding-mapping">
                  ${Object.entries(b.parameter_mapping || {}).map(([k, v]) =>
                    `<div class="f7-map-row"><code>${k}</code> → <code>${v}</code></div>`
                  ).join("")}
                </div>
                <button class="f7-btn-sm f7-btn-danger f7-del-binding" data-id="${b.id}">Sil</button>
              </div>`).join("") || '<div class="f7-empty">Binding yok.</div>'}
          </div>
        </div>`;
      document.getElementById("f7dd-add-binding")
        .addEventListener("click", _addBinding);
      container.querySelectorAll(".f7-del-binding").forEach(btn => {
        btn.addEventListener("click", () => _deleteBinding(parseInt(btn.dataset.id)));
      });
    } catch (e) {
      container.innerHTML = '<div class="f7-empty">Yükleme hatası.</div>';
    }
  }

  async function _addBinding() {
    const dsId = prompt("DataSet ID:");
    if (!dsId) return;
    await fetch(`/api/v1/testing/test-cases/${_currentTcId}/data-bindings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User": "admin" },
      body: JSON.stringify({
        data_set_id: parseInt(dsId),
        parameter_mapping: {},
        iteration_mode: "all",
      }),
    });
    _switchTab("bindings");
  }

  async function _deleteBinding(bid) {
    await fetch(`/api/v1/testing/data-bindings/${bid}`, {
      method: "DELETE",
      headers: { "X-User": "admin" },
    });
    _switchTab("bindings");
  }

  /* ── Iterations ─────────────────────────────────────────────── */
  async function _renderIterations(container) {
    container.innerHTML = `
      <div class="f7-iterations">
        <div class="f7-params-header">
          <h4>Execution Iterations</h4>
          <div>
            <input type="number" id="f7dd-exec-id" class="f7-input"
                   placeholder="Execution ID" style="width:140px" />
            <button id="f7dd-load-iter" class="f7-btn">Yükle</button>
            <button id="f7dd-gen-iter" class="f7-btn f7-btn-primary">Auto-Generate</button>
          </div>
        </div>
        <div id="f7dd-iter-list"></div>
      </div>`;
    document.getElementById("f7dd-load-iter")
      .addEventListener("click", _loadIterations);
    document.getElementById("f7dd-gen-iter")
      .addEventListener("click", _generateIterations);
  }

  async function _loadIterations() {
    const eid = document.getElementById("f7dd-exec-id").value;
    if (!eid) return;
    const list = document.getElementById("f7dd-iter-list");
    try {
      const resp = await fetch(`/api/v1/testing/executions/${eid}/iterations`,
        { headers: { "X-User": "admin" } });
      const json = await resp.json();
      const iters = json.iterations || [];
      list.innerHTML = `
        <table class="f7-param-table">
          <thead><tr><th>#</th><th>Parameters</th><th>Result</th><th></th></tr></thead>
          <tbody>
            ${iters.map(i => `
              <tr>
                <td>${i.iteration_no}</td>
                <td><code>${JSON.stringify(i.parameters || {})}</code></td>
                <td><span class="f7-result f7-result-${i.result}">${i.result}</span></td>
                <td>
                  <select class="f7-select f7-iter-result" data-id="${i.id}">
                    <option value="not_run" ${i.result === 'not_run' ? 'selected' : ''}>Not Run</option>
                    <option value="pass" ${i.result === 'pass' ? 'selected' : ''}>Pass</option>
                    <option value="fail" ${i.result === 'fail' ? 'selected' : ''}>Fail</option>
                    <option value="blocked" ${i.result === 'blocked' ? 'selected' : ''}>Blocked</option>
                  </select>
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
        <div class="f7-iter-summary">
          Toplam: ${iters.length} |
          Pass: ${iters.filter(i => i.result === 'pass').length} |
          Fail: ${iters.filter(i => i.result === 'fail').length} |
          Blocked: ${iters.filter(i => i.result === 'blocked').length}
        </div>`;
      list.querySelectorAll(".f7-iter-result").forEach(sel => {
        sel.addEventListener("change", () => _updateIterResult(
          parseInt(sel.dataset.id), sel.value));
      });
    } catch (e) {
      list.innerHTML = '<div class="f7-empty">Yükleme hatası.</div>';
    }
  }

  async function _updateIterResult(iid, result) {
    await fetch(`/api/v1/testing/iterations/${iid}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-User": "admin" },
      body: JSON.stringify({ result }),
    });
  }

  async function _generateIterations() {
    const eid = document.getElementById("f7dd-exec-id").value;
    if (!eid) return;
    try {
      const resp = await fetch(
        `/api/v1/testing/executions/${eid}/iterations/generate`,
        { method: "POST", headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      if (resp.ok) {
        _showToast(`${json.count} iteration oluşturuldu`);
        _loadIterations();
      } else {
        _showToast(json.error || "Hata", true);
      }
    } catch (e) {
      _showToast("Generate hatası", true);
    }
  }

  /* ── Suite Templates ────────────────────────────────────────── */
  async function _renderTemplates(container) {
    try {
      const resp = await fetch(`/api/v1/suite-templates?per_page=50`,
        { headers: { "X-User": "admin" } });
      const json = await resp.json();
      const templates = json.suite_templates || [];
      container.innerHTML = `
        <div class="f7-templates">
          <div class="f7-params-header">
            <h4>Suite Templates (${templates.length})</h4>
            <button id="f7dd-add-tmpl" class="f7-btn f7-btn-primary">+ Yeni Template</button>
          </div>
          <div class="f7-template-list">
            ${templates.map(t => `
              <div class="f7-template-card">
                <div class="f7-template-info">
                  <strong>${t.name}</strong>
                  <span class="f7-badge">${t.category}</span>
                  <span class="f7-usage">Kullanım: ${t.usage_count}</span>
                </div>
                <p>${t.description || ''}</p>
                <div class="f7-template-actions">
                  <button class="f7-btn-sm f7-apply-tmpl" data-id="${t.id}">Apply to Program</button>
                  <button class="f7-btn-sm f7-btn-danger f7-del-tmpl" data-id="${t.id}">Sil</button>
                </div>
              </div>`).join("") || '<div class="f7-empty">Template yok.</div>'}
          </div>
        </div>`;
      document.getElementById("f7dd-add-tmpl")
        .addEventListener("click", _addTemplate);
      container.querySelectorAll(".f7-apply-tmpl").forEach(btn => {
        btn.addEventListener("click", () => _applyTemplate(parseInt(btn.dataset.id)));
      });
      container.querySelectorAll(".f7-del-tmpl").forEach(btn => {
        btn.addEventListener("click", () => _deleteTemplate(parseInt(btn.dataset.id)));
      });
    } catch (e) {
      container.innerHTML = '<div class="f7-empty">Yükleme hatası.</div>';
    }
  }

  async function _addTemplate() {
    const name = prompt("Template adı:");
    if (!name) return;
    const category = prompt("Kategori (regression/smoke/integration):", "regression");
    await fetch(`/api/v1/suite-templates`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User": "admin" },
      body: JSON.stringify({ name, category: category || "regression", tc_criteria: {} }),
    });
    _switchTab("templates");
  }

  async function _applyTemplate(tid) {
    const programId = window.currentProgramId;
    if (!programId) { _showToast("Program seçin", true); return; }
    const resp = await fetch(
      `/api/v1/suite-templates/${tid}/apply/${programId}`,
      { method: "POST", headers: { "X-User": "admin" } }
    );
    const json = await resp.json();
    if (resp.ok) {
      _showToast(`Suite oluşturuldu: ${json.test_case_count} TC eklendi`);
    } else {
      _showToast(json.error || "Hata", true);
    }
  }

  async function _deleteTemplate(tid) {
    if (!confirm("Template silinecek?")) return;
    await fetch(`/api/v1/suite-templates/${tid}`, {
      method: "DELETE",
      headers: { "X-User": "admin" },
    });
    _switchTab("templates");
  }

  /* ── Helpers ────────────────────────────────────────────────── */
  function _debounce(fn, ms) {
    let t;
    return function (...args) { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function _showToast(msg, isError) {
    let toast = document.getElementById("f7-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "f7-toast";
      toast.className = "f7-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.className = "f7-toast" + (isError ? " f7-toast-error" : "");
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
  }

  return { render };
})();
