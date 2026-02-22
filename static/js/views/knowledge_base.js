/**
 * Knowledge Base View (FDD-I04 / S6-01)
 *
 * Search, browse, create and upvote Lessons Learned across the tenant's
 * project portfolio. Public lessons from other tenants surface anonymised.
 *
 * API base: /api/v1/kb
 */

const KnowledgeBaseView = (() => {
  "use strict";

  // ── State ────────────────────────────────────────────────────────────────

  let _tenantId = null;
  let _currentFilters = { q: "", module: "", phase: "", category: "" };
  let _currentPage = 1;
  let _totalLessons = 0;
  const _perPage = 20;

  // ── Constants ────────────────────────────────────────────────────────────

  const _CATEGORIES = [
    { value: "what_went_well",    label: "✅ What Went Well" },
    { value: "what_went_wrong",   label: "❌ What Went Wrong" },
    { value: "improve_next_time", label: "🔄 Improve Next Time" },
    { value: "risk_realized",     label: "⚠️ Risk Realized" },
    { value: "best_practice",     label: "⭐ Best Practice" },
  ];

  const _PHASES = ["discover", "prepare", "explore", "realize", "deploy", "run"];

  const _IMPACTS = ["high", "medium", "low"];

  // ── Initialise ───────────────────────────────────────────────────────────

  /**
   * Initialise the KB view.
   * Called by the SPA router when navigating to /knowledge-base.
   *
   * @param {number|null} tenantId  — passed from App context
   */
  function init(tenantId) {
    _tenantId = tenantId || window.currentTenantId || null;
    _currentPage = 1;
    _currentFilters = { q: "", module: "", phase: "", category: "" };
    _render();
    loadSummary();
    loadLessons();
  }

  // ── Render shell ─────────────────────────────────────────────────────────

  function _render() {
    const container = document.getElementById("main-content") || document.getElementById("mainContent");
    if (!container) return;

    container.innerHTML = `
<div id="kb-view" class="kb-view">
  <!-- Header -->
  <div class="kb-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;">
    <div>
      <h2 style="margin:0;font-size:1.4rem;">📚 Knowledge Base</h2>
      <p style="margin:0.25rem 0 0;color:var(--text-secondary,#666);font-size:0.85rem;">
        Lessons learned from across all projects
      </p>
    </div>
    <button id="kb-add-btn" class="btn btn-primary btn-sm" onclick="KnowledgeBaseView.openAddForm()">
      + Add Lesson
    </button>
  </div>

  <!-- Summary chips -->
  <div id="kb-summary" style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1.5rem;"></div>

  <!-- Filter bar -->
  <div class="kb-filters" style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:1rem;align-items:center;">
    <input id="kb-search" type="text" placeholder="🔍 Search lessons..." class="form-control form-control-sm"
           style="width:220px;" oninput="KnowledgeBaseView.onSearchInput(this.value)" />
    <select id="kb-filter-module" class="form-select form-select-sm" style="width:120px;"
            onchange="KnowledgeBaseView.onFilterChange()">
      <option value="">All Modules</option>
      ${["FI","CO","MM","SD","PP","PM","QM","HR","BASIS","ABAP","PI"].map(m => `<option value="${m}">${m}</option>`).join("")}
    </select>
    <select id="kb-filter-phase" class="form-select form-select-sm" style="width:130px;"
            onchange="KnowledgeBaseView.onFilterChange()">
      <option value="">All Phases</option>
      ${_PHASES.map(p => `<option value="${p}">${_capitalize(p)}</option>`).join("")}
    </select>
    <select id="kb-filter-category" class="form-select form-select-sm" style="width:175px;"
            onchange="KnowledgeBaseView.onFilterChange()">
      <option value="">All Categories</option>
      ${_CATEGORIES.map(c => `<option value="${c.value}">${c.label}</option>`).join("")}
    </select>
    <button class="btn btn-outline-secondary btn-sm" onclick="KnowledgeBaseView.clearFilters()">Clear</button>
  </div>

  <!-- Lesson list -->
  <div id="kb-lesson-list" class="kb-lesson-list">
    <p class="text-muted" style="padding:1rem;">Loading…</p>
  </div>

  <!-- Pagination -->
  <div id="kb-pagination" style="margin-top:1rem;display:flex;gap:0.5rem;align-items:center;"></div>
</div>

<!-- Add/Edit Modal -->
<div id="kb-modal-overlay" class="modal-overlay" style="display:none;" onclick="KnowledgeBaseView.closeForm()">
  <div class="modal-box" style="max-width:600px;max-height:90vh;overflow-y:auto;"
       onclick="event.stopPropagation()">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
      <h3 id="kb-modal-title" style="margin:0;">Add Lesson</h3>
      <button class="btn btn-sm btn-outline-secondary" onclick="KnowledgeBaseView.closeForm()">✕</button>
    </div>
    <form id="kb-lesson-form" onsubmit="KnowledgeBaseView.submitForm(event)">
      <input type="hidden" id="kb-form-id" value="" />

      <div class="mb-3">
        <label class="form-label">Title *</label>
        <input id="kb-form-title" class="form-control" maxlength="255" required />
      </div>
      <div class="row mb-3">
        <div class="col">
          <label class="form-label">Category *</label>
          <select id="kb-form-category" class="form-select" required>
            ${_CATEGORIES.map(c => `<option value="${c.value}">${c.label}</option>`).join("")}
          </select>
        </div>
        <div class="col">
          <label class="form-label">Impact</label>
          <select id="kb-form-impact" class="form-select">
            <option value="">— None —</option>
            ${_IMPACTS.map(i => `<option value="${i}">${_capitalize(i)}</option>`).join("")}
          </select>
        </div>
      </div>
      <div class="row mb-3">
        <div class="col">
          <label class="form-label">SAP Module</label>
          <input id="kb-form-module" class="form-control" maxlength="10" placeholder="FI, MM, SD…" />
        </div>
        <div class="col">
          <label class="form-label">SAP Activate Phase</label>
          <select id="kb-form-phase" class="form-select">
            <option value="">— None —</option>
            ${_PHASES.map(p => `<option value="${p}">${_capitalize(p)}</option>`).join("")}
          </select>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea id="kb-form-description" class="form-control" rows="3"></textarea>
      </div>
      <div class="mb-3">
        <label class="form-label">Recommendation (for next project)</label>
        <textarea id="kb-form-recommendation" class="form-control" rows="2"></textarea>
      </div>
      <div class="mb-3">
        <label class="form-label">Tags <small class="text-muted">(comma-separated)</small></label>
        <input id="kb-form-tags" class="form-control" maxlength="500" placeholder="data-migration, interface, authorization" />
      </div>
      <div class="mb-3 form-check">
        <input type="checkbox" class="form-check-input" id="kb-form-public" />
        <label class="form-check-label" for="kb-form-public">
          Make public <small class="text-muted">(visible to all tenants — sensitive details will be masked)</small>
        </label>
      </div>
      <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
        <button type="button" class="btn btn-outline-secondary" onclick="KnowledgeBaseView.closeForm()">Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>
  </div>
</div>
`;
  }

  // ── Summary chips ─────────────────────────────────────────────────────

  async function loadSummary() {
    try {
      const res = await fetch("/api/v1/kb/summary");
      if (!res.ok) return;
      const s = await res.json();
      const el = document.getElementById("kb-summary");
      if (!el) return;

      const chips = [
        { label: `${s.total} Total`, cls: "primary" },
        { label: `${s.public_count} Public`, cls: "success" },
        ...Object.entries(s.by_category || {}).map(([k, n]) => ({
          label: `${_labelForCategory(k)}: ${n}`,
          cls: "secondary",
        })),
      ];

      el.innerHTML = chips
        .map(
          (c) => `<span class="badge bg-${c.cls}" style="font-size:0.8rem;padding:0.4em 0.7em;">${_esc(c.label)}</span>`
        )
        .join("");
    } catch (err) {
      console.warn("[KnowledgeBaseView] loadSummary failed:", err);
    }
  }

  // ── Lesson list ──────────────────────────────────────────────────────────

  async function loadLessons() {
    const params = new URLSearchParams({
      page: _currentPage,
      per_page: _perPage,
    });
    if (_currentFilters.q)        params.set("q",        _currentFilters.q);
    if (_currentFilters.module)   params.set("module",   _currentFilters.module);
    if (_currentFilters.phase)    params.set("phase",    _currentFilters.phase);
    if (_currentFilters.category) params.set("category", _currentFilters.category);

    try {
      const res = await fetch(`/api/v1/kb/lessons?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      _totalLessons = data.total || 0;
      _renderLessonList(data.items || []);
      _renderPagination();
    } catch (err) {
      console.error("[KnowledgeBaseView] loadLessons failed:", err);
      const el = document.getElementById("kb-lesson-list");
      if (el) el.innerHTML = `<p class="text-danger">Failed to load lessons. ${_esc(err.message)}</p>`;
    }
  }

  function _renderLessonList(lessons) {
    const el = document.getElementById("kb-lesson-list");
    if (!el) return;

    if (!lessons.length) {
      el.innerHTML = `<p class="text-muted" style="padding:1rem 0;">No lessons found. Be the first to add one!</p>`;
      return;
    }

    el.innerHTML = lessons.map(_renderLessonCard).join("");
  }

  function _renderLessonCard(lesson) {
    const catLabel = _labelForCategory(lesson.category);
    const catBadgeColor = _categoryColor(lesson.category);
    const phaseBadge = lesson.sap_activate_phase
      ? `<span class="badge bg-info text-dark me-1" style="font-size:0.72rem;">${_esc(lesson.sap_activate_phase)}</span>`
      : "";
    const moduleBadge = lesson.sap_module
      ? `<span class="badge bg-secondary me-1" style="font-size:0.72rem;">${_esc(lesson.sap_module)}</span>`
      : "";
    const impactBadge = lesson.impact
      ? `<span class="badge bg-${lesson.impact === "high" ? "danger" : lesson.impact === "medium" ? "warning text-dark" : "light text-dark"} me-1" style="font-size:0.72rem;">${_capitalize(lesson.impact)}</span>`
      : "";
    const publicBadge = lesson.is_public
      ? `<span class="badge bg-success me-1" style="font-size:0.72rem;">🌐 Public</span>`
      : "";
    const tagBadges = (lesson.tags || "").split(",").filter(Boolean).slice(0, 5)
      .map(t => `<span class="badge bg-light text-dark border me-1" style="font-size:0.7rem;">${_esc(t.trim())}</span>`)
      .join("");

    return `
<div class="kb-card" data-id="${lesson.id}"
     style="border:1px solid var(--border-color,#dee2e6);border-radius:8px;padding:1rem;margin-bottom:0.75rem;background:var(--bg-card,#fff);">
  <div style="display:flex;align-items:flex-start;gap:0.75rem;">
    <!-- Upvote -->
    <div style="text-align:center;min-width:44px;">
      <button class="btn btn-sm btn-outline-secondary" style="padding:0.25rem 0.5rem;"
              onclick="KnowledgeBaseView.upvote(${lesson.id}, this)" title="Upvote">
        ▲
      </button>
      <div style="font-size:0.9rem;font-weight:600;margin-top:2px;">${lesson.upvote_count || 0}</div>
    </div>
    <!-- Content -->
    <div style="flex:1;">
      <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;flex-wrap:wrap;">
        <span class="badge bg-${catBadgeColor}" style="font-size:0.75rem;">${_esc(catLabel)}</span>
        ${phaseBadge}${moduleBadge}${impactBadge}${publicBadge}
      </div>
      <h6 style="margin:0 0 0.35rem;font-size:0.95rem;">${_esc(lesson.title)}</h6>
      ${lesson.description ? `<p style="margin:0 0 0.35rem;font-size:0.83rem;color:var(--text-secondary,#555);">${_esc(lesson.description.slice(0, 200))}${lesson.description.length > 200 ? "…" : ""}</p>` : ""}
      ${lesson.recommendation ? `<p style="margin:0 0 0.35rem;font-size:0.83rem;"><strong>💡 Rec:</strong> ${_esc(lesson.recommendation.slice(0, 150))}${lesson.recommendation.length > 150 ? "…" : ""}</p>` : ""}
      ${tagBadges ? `<div style="margin-top:0.3rem;">${tagBadges}</div>` : ""}
    </div>
    <!-- Actions -->
    ${lesson.tenant_id !== null ? `
    <div style="display:flex;flex-direction:column;gap:0.25rem;">
      <button class="btn btn-xs btn-outline-secondary" style="padding:0.2rem 0.5rem;font-size:0.75rem;"
              onclick="KnowledgeBaseView.openEditForm(${lesson.id})">Edit</button>
      <button class="btn btn-xs btn-outline-danger" style="padding:0.2rem 0.5rem;font-size:0.75rem;"
              onclick="KnowledgeBaseView.deleteLesson(${lesson.id})">Del</button>
    </div>` : ""}
  </div>
</div>`;
  }

  function _renderPagination() {
    const el = document.getElementById("kb-pagination");
    if (!el) return;
    const totalPages = Math.ceil(_totalLessons / _perPage);
    if (totalPages <= 1) { el.innerHTML = ""; return; }

    el.innerHTML = `
      <button class="btn btn-sm btn-outline-secondary" ${_currentPage <= 1 ? "disabled" : ""}
              onclick="KnowledgeBaseView.goToPage(${_currentPage - 1})">‹ Prev</button>
      <span style="align-self:center;font-size:0.85rem;">Page ${_currentPage} / ${totalPages} (${_totalLessons} total)</span>
      <button class="btn btn-sm btn-outline-secondary" ${_currentPage >= totalPages ? "disabled" : ""}
              onclick="KnowledgeBaseView.goToPage(${_currentPage + 1})">Next ›</button>
    `;
  }

  // ── Filters ───────────────────────────────────────────────────────────────

  let _searchDebounceTimer = null;

  function onSearchInput(val) {
    clearTimeout(_searchDebounceTimer);
    _searchDebounceTimer = setTimeout(() => {
      _currentFilters.q = val;
      _currentPage = 1;
      loadLessons();
    }, 350);
  }

  function onFilterChange() {
    _currentFilters.module   = document.getElementById("kb-filter-module")?.value || "";
    _currentFilters.phase    = document.getElementById("kb-filter-phase")?.value || "";
    _currentFilters.category = document.getElementById("kb-filter-category")?.value || "";
    _currentPage = 1;
    loadLessons();
  }

  function clearFilters() {
    _currentFilters = { q: "", module: "", phase: "", category: "" };
    _currentPage = 1;
    const search = document.getElementById("kb-search");
    if (search) search.value = "";
    const mod  = document.getElementById("kb-filter-module");
    const ph   = document.getElementById("kb-filter-phase");
    const cat  = document.getElementById("kb-filter-category");
    if (mod) mod.value = "";
    if (ph)  ph.value  = "";
    if (cat) cat.value = "";
    loadLessons();
  }

  function goToPage(page) {
    _currentPage = page;
    loadLessons();
  }

  // ── Add / Edit form ───────────────────────────────────────────────────────

  function openAddForm() {
    document.getElementById("kb-modal-title").textContent = "Add Lesson";
    document.getElementById("kb-form-id").value = "";
    document.getElementById("kb-lesson-form").reset();
    document.getElementById("kb-modal-overlay").style.display = "flex";
  }

  async function openEditForm(lessonId) {
    try {
      const res = await fetch(`/api/v1/kb/lessons/${lessonId}`);
      if (!res.ok) { alert("Could not load lesson"); return; }
      const l = await res.json();

      document.getElementById("kb-modal-title").textContent = "Edit Lesson";
      document.getElementById("kb-form-id").value          = l.id;
      document.getElementById("kb-form-title").value       = l.title || "";
      document.getElementById("kb-form-category").value    = l.category || "what_went_well";
      document.getElementById("kb-form-impact").value      = l.impact || "";
      document.getElementById("kb-form-module").value      = l.sap_module || "";
      document.getElementById("kb-form-phase").value       = l.sap_activate_phase || "";
      document.getElementById("kb-form-description").value = l.description || "";
      document.getElementById("kb-form-recommendation").value = l.recommendation || "";
      document.getElementById("kb-form-tags").value        = l.tags || "";
      document.getElementById("kb-form-public").checked    = !!l.is_public;

      document.getElementById("kb-modal-overlay").style.display = "flex";
    } catch (err) {
      console.error("[KnowledgeBaseView] openEditForm error:", err);
    }
  }

  function closeForm() {
    document.getElementById("kb-modal-overlay").style.display = "none";
  }

  async function submitForm(event) {
    event.preventDefault();
    const id = document.getElementById("kb-form-id").value;
    const payload = {
      title:              document.getElementById("kb-form-title").value.trim(),
      category:           document.getElementById("kb-form-category").value,
      impact:             document.getElementById("kb-form-impact").value || null,
      sap_module:         document.getElementById("kb-form-module").value.trim() || null,
      sap_activate_phase: document.getElementById("kb-form-phase").value || null,
      description:        document.getElementById("kb-form-description").value.trim() || null,
      recommendation:     document.getElementById("kb-form-recommendation").value.trim() || null,
      tags:               document.getElementById("kb-form-tags").value.trim() || null,
      is_public:          document.getElementById("kb-form-public").checked,
    };

    const url    = id ? `/api/v1/kb/lessons/${id}` : "/api/v1/kb/lessons";
    const method = id ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Error: ${err.error || res.status}`);
        return;
      }
      closeForm();
      loadLessons();
      loadSummary();
    } catch (err) {
      console.error("[KnowledgeBaseView] submitForm error:", err);
    }
  }

  // ── Upvote ────────────────────────────────────────────────────────────────

  async function upvote(lessonId, btn) {
    try {
      const res = await fetch(`/api/v1/kb/lessons/${lessonId}/upvote`, { method: "POST" });
      if (res.status === 409) { alert("You have already upvoted this lesson."); return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Update the count in the card
      const card = btn.closest(".kb-card");
      if (card) {
        const countEl = btn.nextElementSibling;
        if (countEl) countEl.textContent = data.upvote_count;
        btn.disabled = true;
        btn.title = "Already upvoted";
      }
    } catch (err) {
      console.error("[KnowledgeBaseView] upvote failed:", err);
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────

  async function deleteLesson(lessonId) {
    if (!confirm("Delete this lesson? This cannot be undone.")) return;
    try {
      const res = await fetch(`/api/v1/kb/lessons/${lessonId}`, { method: "DELETE" });
      if (!res.ok) { alert("Could not delete lesson"); return; }
      loadLessons();
      loadSummary();
    } catch (err) {
      console.error("[KnowledgeBaseView] deleteLesson error:", err);
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function _esc(str) {
    const d = document.createElement("div");
    d.textContent = str ?? "";
    return d.innerHTML;
  }

  function _capitalize(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : "";
  }

  function _labelForCategory(cat) {
    return (_CATEGORIES.find((c) => c.value === cat) || { label: cat }).label;
  }

  function _categoryColor(cat) {
    const map = {
      what_went_well: "success",
      what_went_wrong: "danger",
      improve_next_time: "warning text-dark",
      risk_realized: "orange",
      best_practice: "primary",
    };
    return map[cat] || "secondary";
  }

  // ── Public API ────────────────────────────────────────────────────────────

  return {
    init,
    loadLessons,
    loadSummary,
    openAddForm,
    openEditForm,
    closeForm,
    submitForm,
    upvote,
    deleteLesson,
    onSearchInput,
    onFilterChange,
    clearFilters,
    goToPage,
  };
})();
