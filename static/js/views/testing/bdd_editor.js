/* ================================================================
   F7 — BDD / Gherkin Editor View
   static/js/views/bdd_editor.js
   ================================================================ */
const BddEditorView = (function () {
  "use strict";

  let _currentTcId = null;
  let _bddSpec = null;

  /* ── public render ─────────────────────────────────────────── */
  function render() {
    const main = document.getElementById("main-content");
    if (!main) return;
    const programId = window.currentProgramId;
    if (!programId) {
      main.innerHTML = '<div class="f7-empty">Please select a program first.</div>';
      return;
    }
    main.innerHTML = `
      <div class="f7-layout">
        <div class="f7-sidebar">
          <h3>Test Cases</h3>
          <input type="text" id="f7-tc-search" class="f7-search"
                 placeholder="TC ara…" />
          <div id="f7-tc-list" class="f7-tc-list"></div>
        </div>
        <div class="f7-main">
          <div class="f7-tabs">
            <button class="f7-tab active" data-tab="gherkin">Gherkin Editor</button>
            <button class="f7-tab" data-tab="steps">Parsed Steps</button>
            <button class="f7-tab" data-tab="shared">Shared Steps</button>
          </div>
          <div id="f7-tab-content" class="f7-tab-content">
            <div class="f7-empty">Select a Test Case from the left panel.</div>
          </div>
        </div>
      </div>`;

    // Bind events
    document.getElementById("f7-tc-search")
      .addEventListener("input", _debounce(_loadTcList, 300));
    main.querySelectorAll(".f7-tab").forEach(btn => {
      btn.addEventListener("click", () => _switchTab(btn.dataset.tab));
    });
    _loadTcList();
  }

  /* ── Load test cases list ──────────────────────────────────── */
  async function _loadTcList() {
    const programId = window.currentProgramId;
    const search = (document.getElementById("f7-tc-search") || {}).value || "";
    const url = `/api/v1/programs/${programId}/testing/test-cases?per_page=100&search=${encodeURIComponent(search)}`;
    try {
      const resp = await fetch(url, { headers: { "X-User": "admin" } });
      const json = await resp.json();
      const list = document.getElementById("f7-tc-list");
      if (!list) return;
      const tcs = json.test_cases || json.items || [];
      list.innerHTML = tcs.map(tc => `
        <div class="f7-tc-item ${tc.id === _currentTcId ? 'active' : ''}"
             data-id="${tc.id}">
          <span class="f7-tc-code">${tc.code || ''}</span>
          <span class="f7-tc-title">${tc.title}</span>
        </div>`).join("");
      list.querySelectorAll(".f7-tc-item").forEach(el => {
        el.addEventListener("click", () => _selectTc(parseInt(el.dataset.id)));
      });
    } catch (e) {
      console.error("TC list load failed:", e);
    }
  }

  /* ── Select a TC ────────────────────────────────────────────── */
  async function _selectTc(tcId) {
    _currentTcId = tcId;
    // Highlight
    document.querySelectorAll(".f7-tc-item").forEach(el => {
      el.classList.toggle("active", parseInt(el.dataset.id) === tcId);
    });
    await _loadBdd();
    _switchTab("gherkin");
  }

  /* ── Load BDD spec ──────────────────────────────────────────── */
  async function _loadBdd() {
    if (!_currentTcId) return;
    try {
      const resp = await fetch(`/api/v1/testing/test-cases/${_currentTcId}/bdd`,
        { headers: { "X-User": "admin" } });
      const json = await resp.json();
      _bddSpec = json.bdd;
    } catch (e) {
      _bddSpec = null;
    }
  }

  /* ── Tab switch ─────────────────────────────────────────────── */
  function _switchTab(tab) {
    document.querySelectorAll(".f7-tab").forEach(b =>
      b.classList.toggle("active", b.dataset.tab === tab));
    const content = document.getElementById("f7-tab-content");
    if (!content) return;

    if (tab === "gherkin") _renderGherkin(content);
    else if (tab === "steps") _renderParsedSteps(content);
    else if (tab === "shared") _renderSharedSteps(content);
  }

  /* ── Gherkin editor ─────────────────────────────────────────── */
  function _renderGherkin(container) {
    if (!_currentTcId) {
      container.innerHTML = '<div class="f7-empty">Select a Test Case.</div>';
      return;
    }
    const feature = _bddSpec ? _bddSpec.feature_file : "";
    const lang = _bddSpec ? _bddSpec.language : "en";
    container.innerHTML = `
      <div class="f7-gherkin-editor">
        <div class="f7-gherkin-toolbar">
          <select id="f7-bdd-lang" class="f7-select">
            <option value="en" ${lang === 'en' ? 'selected' : ''}>English</option>
            <option value="de" ${lang === 'de' ? 'selected' : ''}>Deutsch</option>
            <option value="tr" ${lang === 'tr' ? 'selected' : ''}>Turkish</option>
          </select>
          <button id="f7-save-bdd" class="f7-btn f7-btn-primary">Save</button>
          <button id="f7-parse-bdd" class="f7-btn">Parse → Steps</button>
          ${_bddSpec ? '<button id="f7-delete-bdd" class="f7-btn f7-btn-danger">Delete</button>' : ''}
        </div>
        <textarea id="f7-feature-text" class="f7-gherkin-textarea"
                  placeholder="Feature: …\n  Scenario: …\n    Given …\n    When …\n    Then …"
                  spellcheck="false">${feature}</textarea>
        <div class="f7-gherkin-hints">
          <span class="f7-hint-keyword">Feature</span>
          <span class="f7-hint-keyword">Scenario</span>
          <span class="f7-hint-keyword">Given</span>
          <span class="f7-hint-keyword">When</span>
          <span class="f7-hint-keyword">Then</span>
          <span class="f7-hint-keyword">And</span>
          <span class="f7-hint-keyword">But</span>
        </div>
      </div>`;

    document.getElementById("f7-save-bdd").addEventListener("click", _saveBdd);
    document.getElementById("f7-parse-bdd").addEventListener("click",
      () => _switchTab("steps"));
    const delBtn = document.getElementById("f7-delete-bdd");
    if (delBtn) delBtn.addEventListener("click", _deleteBdd);
  }

  async function _saveBdd() {
    const text = document.getElementById("f7-feature-text").value;
    const lang = document.getElementById("f7-bdd-lang").value;
    const method = _bddSpec ? "PUT" : "POST";
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/bdd`,
        {
          method,
          headers: {
            "Content-Type": "application/json",
            "X-User": "admin",
          },
          body: JSON.stringify({ feature_file: text, language: lang }),
        }
      );
      const json = await resp.json();
      if (resp.ok) {
        _bddSpec = json.bdd;
        _showToast("BDD spec saved");
      } else {
        _showToast(json.error || "Error", true);
      }
    } catch (e) {
      _showToast("Save error", true);
    }
  }

  async function _deleteBdd() {
    if (!confirm("BDD spec will be deleted. Continue?")) return;
    try {
      await fetch(`/api/v1/testing/test-cases/${_currentTcId}/bdd`, {
        method: "DELETE",
        headers: { "X-User": "admin" },
      });
      _bddSpec = null;
      _switchTab("gherkin");
      _showToast("BDD spec deleted");
    } catch (e) {
      _showToast("Delete error", true);
    }
  }

  /* ── Parsed steps preview ───────────────────────────────────── */
  async function _renderParsedSteps(container) {
    if (!_currentTcId || !_bddSpec) {
      container.innerHTML = '<div class="f7-empty">Create a BDD spec first.</div>';
      return;
    }
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/bdd/parse`,
        { method: "POST", headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const steps = json.steps || [];
      container.innerHTML = `
        <div class="f7-parsed-steps">
          <h4>Parsed Steps (${steps.length})</h4>
          <table class="f7-step-table">
            <thead><tr><th>#</th><th>Keyword</th><th>Action</th></tr></thead>
            <tbody>
              ${steps.map(s => `
                <tr>
                  <td>${s.step_no}</td>
                  <td><span class="f7-keyword f7-kw-${s.keyword.toLowerCase()}">${s.keyword}</span></td>
                  <td>${s.action}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>`;
    } catch (e) {
      container.innerHTML = '<div class="f7-empty">Parse error.</div>';
    }
  }

  /* ── Shared steps tab ───────────────────────────────────────── */
  async function _renderSharedSteps(container) {
    const programId = window.currentProgramId;
    container.innerHTML = `
      <div class="f7-shared-steps">
        <div class="f7-shared-header">
          <h4>Shared Step Library</h4>
          <button id="f7-new-shared" class="f7-btn f7-btn-primary">+ New Shared Step</button>
        </div>
        <div id="f7-shared-list" class="f7-shared-list">Loading…</div>
        <div id="f7-step-refs" class="f7-step-refs">
          <h4>Shared Steps linked to this TC</h4>
          <div id="f7-ref-list"></div>
        </div>
      </div>`;

    document.getElementById("f7-new-shared")
      .addEventListener("click", _createSharedStep);

    // Load shared steps
    try {
      const resp = await fetch(
        `/api/v1/programs/${programId}/shared-steps?per_page=50`,
        { headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const items = json.shared_steps || [];
      const listEl = document.getElementById("f7-shared-list");
      listEl.innerHTML = items.map(s => `
        <div class="f7-shared-item" data-id="${s.id}">
          <div class="f7-shared-title">${s.title}</div>
          <div class="f7-shared-meta">
            ${(s.tags || []).map(t => `<span class="f7-tag">${t}</span>`).join("")}
            <span class="f7-usage">Usage: ${s.usage_count}</span>
          </div>
          <div class="f7-shared-actions">
            <button class="f7-btn-sm f7-insert-shared" data-id="${s.id}">Insert</button>
          </div>
        </div>`).join("") || "<div class='f7-empty'>No shared steps yet.</div>";

      listEl.querySelectorAll(".f7-insert-shared").forEach(btn => {
        btn.addEventListener("click", () => _insertSharedStep(parseInt(btn.dataset.id)));
      });
    } catch (e) {
      console.error(e);
    }

    // Load current refs
    await _loadStepRefs();
  }

  async function _loadStepRefs() {
    if (!_currentTcId) return;
    const refList = document.getElementById("f7-ref-list");
    if (!refList) return;
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/step-references`,
        { headers: { "X-User": "admin" } }
      );
      const json = await resp.json();
      const refs = json.step_references || [];
      refList.innerHTML = refs.map(r => `
        <div class="f7-ref-item">
          <span>Step ${r.step_no}: <strong>${r.shared_step_title || 'Shared #' + r.shared_step_id}</strong></span>
          <button class="f7-btn-sm f7-btn-danger f7-remove-ref" data-id="${r.id}">×</button>
        </div>`).join("") || "<div class='f7-empty'>No linked shared steps.</div>";

      refList.querySelectorAll(".f7-remove-ref").forEach(btn => {
        btn.addEventListener("click", () => _removeStepRef(parseInt(btn.dataset.id)));
      });
    } catch (e) {
      console.error(e);
    }
  }

  async function _insertSharedStep(sharedId) {
    if (!_currentTcId) { _showToast("Select a TC first", true); return; }
    try {
      const resp = await fetch(
        `/api/v1/testing/test-cases/${_currentTcId}/step-references`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-User": "admin" },
          body: JSON.stringify({ shared_step_id: sharedId }),
        }
      );
      if (resp.ok) {
        _showToast("Shared step added");
        await _loadStepRefs();
      }
    } catch (e) {
      _showToast("Add error", true);
    }
  }

  async function _removeStepRef(refId) {
    try {
      await fetch(`/api/v1/testing/step-references/${refId}`, {
        method: "DELETE",
        headers: { "X-User": "admin" },
      });
      _showToast("Reference removed");
      await _loadStepRefs();
    } catch (e) {
      _showToast("Delete error", true);
    }
  }

  async function _createSharedStep() {
    const title = prompt("Shared Step title:");
    if (!title) return;
    const programId = window.currentProgramId;
    try {
      const resp = await fetch(`/api/v1/programs/${programId}/shared-steps`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User": "admin" },
        body: JSON.stringify({ title, steps: [] }),
      });
      if (resp.ok) {
        _showToast("Shared step created");
        _switchTab("shared"); // reload
      }
    } catch (e) {
      _showToast("Creation error", true);
    }
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
