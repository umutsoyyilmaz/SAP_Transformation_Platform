/**
 * S3-01 — Discover Phase MVP
 *
 * Surfaces the three core Discover artefacts for a Program:
 *   Tab 1: Project Charter  — objective, drivers, benefits, go-live date, SAP modules
 *   Tab 2: System Landscape — SAP + non-SAP systems in scope
 *   Tab 3: Scope Assessment — per-module fit/gap complexity grid
 *
 * A gate-status banner above the tabs shows live criteria:
 *   ✅ Charter approved | ✅ ≥1 system in landscape | ✅ ≥3 modules assessed
 */
const DiscoverView = (() => {
    "use strict";

    const API_BASE = "/api/v1";

    /* ── tiny DOM helpers (same pattern as gate_criteria.js) ─────────── */
    function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
    function html(tag, attrs, children) {
        const el = document.createElement(tag);
        if (attrs) {
            Object.entries(attrs).forEach(([k, v]) => {
                if (k === "className") el.className = v;
                else if (k === "textContent") el.textContent = v;
                else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
                else el.setAttribute(k, v);
            });
        }
        if (typeof children === "string") el.textContent = children;
        else if (Array.isArray(children)) children.forEach(c => c && el.appendChild(c));
        return el;
    }
    function esc(s) {
        const d = document.createElement("div");
        d.textContent = s ?? "";
        return d.innerHTML;
    }

    async function apiFetch(method, path, body) {
        const opts = { method, headers: { "Content-Type": "application/json" } };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const res = await fetch(API_BASE + path, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || res.statusText);
        }
        if (res.status === 204) return null;
        return res.json();
    }

    /* ── module state ────────────────────────────────────────────────── */
    let programId = null;
    let currentTab = "charter";
    let rootEl = null;

    /* ── constants ───────────────────────────────────────────────────── */
    const PROJECT_TYPES = ["greenfield", "brownfield", "bluefield", "selective_dt"];
    const SYSTEM_TYPES  = ["sap_erp", "s4hana", "non_sap", "middleware", "cloud", "legacy"];
    const SYSTEM_ROLES  = ["source", "target", "interface", "decommission", "keep"];
    const ENVIRONMENTS  = ["dev", "test", "q", "prod"];
    const COMPLEXITIES  = ["low", "medium", "high", "very_high"];
    const COMMON_MODULES = ["FI", "CO", "MM", "SD", "PP", "PM", "QM", "WM", "PS", "HR", "TR", "BC"];

    /* ── entry point ─────────────────────────────────────────────────── */
    function render(container) {
        programId = (App.getActiveProgram() || {}).id;
        rootEl = container;

        if (!programId) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🔍</div>
                    <div class="empty-state__title">No program selected</div>
                    <p>Select a program from the Programs view to access the Discover phase.</p>
                </div>`;
            return;
        }

        container.innerHTML = `
            <div class="page-header">
                <h1>🔍 Discover Phase</h1>
                <span class="badge badge-info" id="discoverGateBadge">Loading gate…</span>
            </div>
            <div id="discoverGateBanner" class="discover-gate-banner"></div>
            <div class="discover-tabs">
                <button class="discover-tab active" data-tab="charter">📋 Project Charter</button>
                <button class="discover-tab" data-tab="landscape">🖥️ System Landscape</button>
                <button class="discover-tab" data-tab="scope">📊 Scope Assessment</button>
            </div>
            <div id="discoverTabBody" class="discover-tab-body">
                <div class="spinner-center"><div class="spinner"></div></div>
            </div>`;

        /* tab click handlers */
        container.querySelectorAll(".discover-tab").forEach(btn => {
            btn.addEventListener("click", () => {
                currentTab = btn.dataset.tab;
                container.querySelectorAll(".discover-tab").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                renderTabBody();
            });
        });

        refreshGateBanner();
        renderTabBody();
    }

    /* ── gate status banner ──────────────────────────────────────────── */
    async function refreshGateBanner() {
        try {
            const data = await apiFetch("GET", `/programs/${programId}/discover/gate-status`);
            const badge = qs("#discoverGateBadge", rootEl);
            const banner = qs("#discoverGateBanner", rootEl);
            if (!badge || !banner) return;

            badge.textContent = data.gate_passed ? "✅ Gate Passed" : "🔴 Gate Not Passed";
            badge.className   = `badge ${data.gate_passed ? "badge-success" : "badge-danger"}`;

            const rows = (data.criteria || []).map(c =>
                `<div class="gate-criterion ${c.passed ? "passed" : "failed"}">
                    ${c.passed ? "✅" : "❌"} <strong>${esc(c.label)}</strong>
                    ${c.detail ? `<span class="gate-detail"> — ${esc(c.detail)}</span>` : ""}
                </div>`
            ).join("");
            banner.innerHTML = `<div class="gate-criteria-row">${rows}</div>`;
        } catch {
            /* gate endpoint unavailable — silent fail, not blocking */
        }
    }

    /* ── tab dispatcher ──────────────────────────────────────────────── */
    function renderTabBody() {
        const body = qs("#discoverTabBody", rootEl);
        if (!body) return;
        body.innerHTML = '<div class="spinner-center"><div class="spinner"></div></div>';
        if (currentTab === "charter")   renderCharterTab(body);
        else if (currentTab === "landscape") renderLandscapeTab(body);
        else if (currentTab === "scope")    renderScopeTab(body);
    }

    /* ════════════════════════════════════════════════════════════════════
     * TAB 1 — PROJECT CHARTER
     * ════════════════════════════════════════════════════════════════════ */
    async function renderCharterTab(container) {
        let charter = null;
        try {
            charter = await apiFetch("GET", `/programs/${programId}/discover/charter`);
        } catch { /* 404 means not yet created — that's fine */ }

        const status      = charter?.status ?? "draft";
        const isApproved  = status === "approved";
        const isReadonly  = isApproved;

        container.innerHTML = `
            <div class="section-card">
                <div class="section-card__header">
                    <h3>Project Charter</h3>
                    <span class="badge badge-${statusBadgeClass(status)}">${esc(status.replace("_", " "))}</span>
                    ${!isApproved
                        ? `<button class="btn btn-secondary btn-sm" id="charterApproveBtn" style="margin-left:auto">
                               ✅ Submit for Approval
                           </button>`
                        : ""}
                </div>
                <form id="charterForm" class="discover-form ${isReadonly ? "readonly" : ""}">
                    <div class="form-grid-2">
                        <div class="form-group full-width">
                            <label>Project Objective *</label>
                            <textarea name="project_objective" rows="3" ${isReadonly ? "disabled" : ""}
                                placeholder="What is the primary goal of this SAP transformation?"
                            >${esc(charter?.project_objective ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Business Drivers</label>
                            <textarea name="business_drivers" rows="3" ${isReadonly ? "disabled" : ""}
                                placeholder="Why is this transformation needed now?"
                            >${esc(charter?.business_drivers ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Expected Benefits</label>
                            <textarea name="expected_benefits" rows="3" ${isReadonly ? "disabled" : ""}
                                placeholder="Quantified / qualitative benefits"
                            >${esc(charter?.expected_benefits ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Key Risks</label>
                            <textarea name="key_risks" rows="3" ${isReadonly ? "disabled" : ""}
                                placeholder="Top 3–5 risks identified in discovery"
                            >${esc(charter?.key_risks ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>In-Scope Summary</label>
                            <textarea name="in_scope_summary" rows="2" ${isReadonly ? "disabled" : ""}
                            >${esc(charter?.in_scope_summary ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Out-of-Scope Summary</label>
                            <textarea name="out_of_scope_summary" rows="2" ${isReadonly ? "disabled" : ""}
                            >${esc(charter?.out_of_scope_summary ?? "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Project Type</label>
                            <select name="project_type" ${isReadonly ? "disabled" : ""}>
                                ${PROJECT_TYPES.map(t =>
                                    `<option value="${t}" ${charter?.project_type === t ? "selected" : ""}>${t}</option>`
                                ).join("")}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Target Go-Live Date</label>
                            <input type="date" name="target_go_live_date"
                                value="${esc(charter?.target_go_live_date?.slice(0, 10) ?? "")}"
                                ${isReadonly ? "disabled" : ""} />
                        </div>
                        <div class="form-group">
                            <label>Estimated Duration (months)</label>
                            <input type="number" name="estimated_duration_months" min="1" max="120"
                                value="${charter?.estimated_duration_months ?? ""}"
                                ${isReadonly ? "disabled" : ""} />
                        </div>
                        <div class="form-group">
                            <label>Affected Countries <small>(comma-separated)</small></label>
                            <input type="text" name="affected_countries"
                                value="${esc(charter?.affected_countries ?? "")}"
                                placeholder="DE, TR, US"
                                ${isReadonly ? "disabled" : ""} />
                        </div>
                        <div class="form-group full-width">
                            <label>Affected SAP Modules <small>(comma-separated)</small></label>
                            <input type="text" name="affected_sap_modules"
                                value="${esc(charter?.affected_sap_modules ?? "")}"
                                placeholder="FI, CO, MM, SD"
                                ${isReadonly ? "disabled" : ""} />
                        </div>
                    </div>
                    ${!isReadonly
                        ? `<div class="form-actions">
                               <button type="submit" class="btn btn-primary">💾 Save Charter</button>
                           </div>`
                        : `<div class="form-actions">
                               <span class="text-muted">Approved by ${esc(charter?.approved_by ?? "—")}
                               on ${esc((charter?.approved_at ?? "").slice(0, 10) || "—")}</span>
                           </div>`}
                </form>
                ${charter?.approval_notes
                    ? `<div class="approval-notes"><strong>Approval notes:</strong> ${esc(charter.approval_notes)}</div>`
                    : ""}
            </div>`;

        /* save handler */
        const form = qs("#charterForm", container);
        if (form && !isReadonly) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const fd = new FormData(form);
                const payload = Object.fromEntries(fd.entries());
                // Convert empty strings to null for optional fields
                ["key_risks", "in_scope_summary", "out_of_scope_summary",
                 "business_drivers", "expected_benefits", "affected_countries",
                 "affected_sap_modules", "target_go_live_date"].forEach(k => {
                    if (payload[k] === "") payload[k] = null;
                });
                if (payload.estimated_duration_months)
                    payload.estimated_duration_months = parseInt(payload.estimated_duration_months, 10);
                try {
                    await apiFetch("POST", `/programs/${programId}/discover/charter`, payload);
                    showToast("Charter saved", "success");
                    renderCharterTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Save failed: " + err.message, "error");
                }
            });
        }

        /* approve button */
        const approveBtn = qs("#charterApproveBtn", container);
        if (approveBtn) {
            approveBtn.addEventListener("click", async () => {
                const notes = prompt("Approval notes (optional):");
                if (notes === null) return; /* cancelled */
                try {
                    await apiFetch("POST", `/programs/${programId}/discover/charter/approve`,
                        { approver_id: null, notes });
                    showToast("Charter submitted for approval", "success");
                    renderCharterTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Approval failed: " + err.message, "error");
                }
            });
        }
    }

    /* ════════════════════════════════════════════════════════════════════
     * TAB 2 — SYSTEM LANDSCAPE
     * ════════════════════════════════════════════════════════════════════ */
    async function renderLandscapeTab(container) {
        let systems = [];
        try {
            const data = await apiFetch("GET", `/programs/${programId}/discover/landscape`);
            systems = data.items ?? data ?? [];
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error loading landscape: ${esc(err.message)}</div>`;
            return;
        }

        container.innerHTML = `
            <div class="section-card">
                <div class="section-card__header">
                    <h3>System Landscape <span class="badge badge-secondary">${systems.length} system${systems.length !== 1 ? "s" : ""}</span></h3>
                    <button class="btn btn-primary btn-sm" id="addSystemBtn" style="margin-left:auto">+ Add System</button>
                </div>
                ${systems.length === 0
                    ? `<div class="empty-state"><p>No systems added yet. Add your SAP and non-SAP systems to define the landscape.</p></div>`
                    : `<table class="data-table" id="landscapeTable">
                        <thead>
                            <tr>
                                <th>System Name</th><th>Type</th><th>Role</th>
                                <th>Vendor</th><th>Version</th><th>Environment</th>
                                <th>Active</th><th></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${systems.map(s => `
                            <tr data-id="${s.id}">
                                <td>${esc(s.system_name)}</td>
                                <td><span class="badge badge-info">${esc(s.system_type ?? "—")}</span></td>
                                <td>${esc(s.role ?? "—")}</td>
                                <td>${esc(s.vendor ?? "—")}</td>
                                <td>${esc(s.version ?? "—")}</td>
                                <td>${esc(s.environment ?? "—")}</td>
                                <td>${s.is_active ? "✅" : "—"}</td>
                                <td>
                                    <button class="btn btn-icon" data-action="edit-landscape" data-id="${s.id}">✏️</button>
                                    <button class="btn btn-icon btn-danger-icon" data-action="delete-landscape" data-id="${s.id}">🗑️</button>
                                </td>
                            </tr>`).join("")}
                        </tbody>
                    </table>`}
                <div id="landscapeFormArea"></div>
            </div>`;

        qs("#addSystemBtn", container).addEventListener("click", () =>
            showLandscapeForm(qs("#landscapeFormArea", container), null)
        );

        container.querySelectorAll("[data-action='edit-landscape']").forEach(btn => {
            btn.addEventListener("click", () => {
                const sys = systems.find(s => s.id == btn.dataset.id);
                if (sys) showLandscapeForm(qs("#landscapeFormArea", container), sys);
            });
        });

        container.querySelectorAll("[data-action='delete-landscape']").forEach(btn => {
            btn.addEventListener("click", async () => {
                if (!confirm("Delete this system?")) return;
                try {
                    await apiFetch("DELETE", `/programs/${programId}/discover/landscape/${btn.dataset.id}`);
                    showToast("System removed", "success");
                    renderLandscapeTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Delete failed: " + err.message, "error");
                }
            });
        });
    }

    function showLandscapeForm(area, existing) {
        const isEdit = !!existing;
        area.innerHTML = `
            <form class="discover-inline-form" id="landscapeForm">
                <h4>${isEdit ? "Edit System" : "Add System"}</h4>
                <div class="form-grid-3">
                    <div class="form-group">
                        <label>System Name *</label>
                        <input type="text" name="system_name" value="${esc(existing?.system_name ?? "")}" required maxlength="100" />
                    </div>
                    <div class="form-group">
                        <label>System Type</label>
                        <select name="system_type">
                            ${SYSTEM_TYPES.map(t =>
                                `<option value="${t}" ${existing?.system_type === t ? "selected" : ""}>${t}</option>`
                            ).join("")}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Role</label>
                        <select name="role">
                            ${SYSTEM_ROLES.map(r =>
                                `<option value="${r}" ${existing?.role === r ? "selected" : ""}>${r}</option>`
                            ).join("")}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Vendor</label>
                        <input type="text" name="vendor" value="${esc(existing?.vendor ?? "")}" maxlength="100" />
                    </div>
                    <div class="form-group">
                        <label>Version</label>
                        <input type="text" name="version" value="${esc(existing?.version ?? "")}" maxlength="50" />
                    </div>
                    <div class="form-group">
                        <label>Environment</label>
                        <select name="environment">
                            ${ENVIRONMENTS.map(e =>
                                `<option value="${e}" ${existing?.environment === e ? "selected" : ""}>${e}</option>`
                            ).join("")}
                        </select>
                    </div>
                    <div class="form-group full-width">
                        <label>Description</label>
                        <input type="text" name="description" value="${esc(existing?.description ?? "")}" maxlength="500" />
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" name="is_active" ${existing?.is_active !== false ? "checked" : ""} /> Active</label>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">${isEdit ? "Update" : "Add"} System</button>
                    <button type="button" class="btn btn-secondary" id="cancelLandscapeForm">Cancel</button>
                </div>
            </form>`;

        qs("#cancelLandscapeForm", area).addEventListener("click", () => { area.innerHTML = ""; });

        qs("#landscapeForm", area).addEventListener("submit", async (e) => {
            e.preventDefault();
            const fd  = new FormData(e.target);
            const payload = Object.fromEntries(fd.entries());
            payload.is_active = fd.has("is_active");
            ["vendor", "version", "description"].forEach(k => {
                if (payload[k] === "") payload[k] = null;
            });
            try {
                if (isEdit) {
                    await apiFetch("PUT",
                        `/programs/${programId}/discover/landscape/${existing.id}`, payload);
                } else {
                    await apiFetch("POST",
                        `/programs/${programId}/discover/landscape`, payload);
                }
                showToast(`System ${isEdit ? "updated" : "added"}`, "success");
                renderLandscapeTab(qs("#discoverTabBody", rootEl));
                refreshGateBanner();
            } catch (err) {
                showToast("Save failed: " + err.message, "error");
            }
        });
    }

    /* ════════════════════════════════════════════════════════════════════
     * TAB 3 — SCOPE ASSESSMENT
     * ════════════════════════════════════════════════════════════════════ */
    async function renderScopeTab(container) {
        let assessments = [];
        try {
            const data = await apiFetch("GET", `/programs/${programId}/discover/scope-assessment`);
            assessments = data.items ?? data ?? [];
        } catch (err) {
            container.innerHTML = `<div class="alert alert-danger">Error: ${esc(err.message)}</div>`;
            return;
        }

        const byModule = {};
        assessments.forEach(a => { byModule[a.sap_module] = a; });

        const allModules = Array.from(
            new Set([...COMMON_MODULES, ...assessments.map(a => a.sap_module)])
        ).sort();

        container.innerHTML = `
            <div class="section-card">
                <div class="section-card__header">
                    <h3>Scope Assessment
                        <span class="badge badge-success">${assessments.filter(a => a.is_in_scope).length} in scope</span>
                    </h3>
                    <button class="btn btn-secondary btn-sm" id="addModuleBtn" style="margin-left:auto">+ Add Custom Module</button>
                </div>
                <p class="text-muted" style="margin:0 0 12px">
                    Toggle modules in/out of scope, set complexity and estimates.
                    Changes are saved immediately.
                </p>
                <table class="data-table scope-grid">
                    <thead>
                        <tr>
                            <th>Module</th><th>In Scope</th><th>Complexity</th>
                            <th>Est. Requirements</th><th>Est. Gaps</th><th>Notes</th><th></th>
                        </tr>
                    </thead>
                    <tbody id="scopeTableBody">
                        ${allModules.map(mod => {
                            const a = byModule[mod];
                            return `
                            <tr data-module="${mod}" data-id="${a?.id ?? ""}">
                                <td><strong>${esc(mod)}</strong></td>
                                <td class="scope-toggle-cell">
                                    <input type="checkbox" class="scope-inscope-chk"
                                        ${a?.is_in_scope ? "checked" : ""} />
                                </td>
                                <td>
                                    <select class="scope-complexity-sel" ${!a?.is_in_scope ? "disabled" : ""}>
                                        <option value="">—</option>
                                        ${COMPLEXITIES.map(c =>
                                            `<option value="${c}" ${a?.complexity === c ? "selected" : ""}>${c}</option>`
                                        ).join("")}
                                    </select>
                                </td>
                                <td>
                                    <input type="number" class="scope-req-inp" min="0"
                                        value="${a?.estimated_requirements ?? ""}"
                                        style="width:80px" ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <input type="number" class="scope-gap-inp" min="0"
                                        value="${a?.estimated_gaps ?? ""}"
                                        style="width:80px" ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <input type="text" class="scope-notes-inp"
                                        value="${esc(a?.notes ?? "")}"
                                        style="width:140px" ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-primary scope-save-btn">Save</button>
                                    ${a ? `<button class="btn btn-icon btn-danger-icon scope-del-btn" data-id="${a.id}">🗑️</button>` : ""}
                                </td>
                            </tr>`;
                        }).join("")}
                    </tbody>
                </table>
                <div id="addModuleArea"></div>
            </div>`;

        /* enable/disable row fields when toggling in-scope */
        container.querySelectorAll(".scope-inscope-chk").forEach(chk => {
            chk.addEventListener("change", () => {
                const row = chk.closest("tr");
                const dis = !chk.checked;
                row.querySelectorAll(".scope-complexity-sel, .scope-req-inp, .scope-gap-inp, .scope-notes-inp")
                    .forEach(el => { el.disabled = dis; });
            });
        });

        /* save per-row */
        container.querySelectorAll(".scope-save-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                const row     = btn.closest("tr");
                const mod     = row.dataset.module;
                const payload = {
                    is_in_scope:              row.querySelector(".scope-inscope-chk").checked,
                    complexity:               row.querySelector(".scope-complexity-sel").value || null,
                    estimated_requirements:   parseInt(row.querySelector(".scope-req-inp").value, 10) || null,
                    estimated_gaps:           parseInt(row.querySelector(".scope-gap-inp").value, 10) || null,
                    notes:                    row.querySelector(".scope-notes-inp").value || null,
                };
                try {
                    await apiFetch("POST",
                        `/programs/${programId}/discover/scope-assessment`,
                        Object.assign({ sap_module: mod }, payload)
                    );
                    showToast(`${mod} saved`, "success");
                    renderScopeTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Save failed: " + err.message, "error");
                }
            });
        });

        /* delete per-row */
        container.querySelectorAll(".scope-del-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                if (!confirm("Remove this module assessment?")) return;
                try {
                    await apiFetch("DELETE",
                        `/programs/${programId}/discover/scope-assessment/${btn.dataset.id}`);
                    showToast("Removed", "success");
                    renderScopeTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Delete failed: " + err.message, "error");
                }
            });
        });

        /* add custom module */
        qs("#addModuleBtn", container).addEventListener("click", () => {
            const area = qs("#addModuleArea", container);
            if (area.innerHTML) { area.innerHTML = ""; return; }
            area.innerHTML = `
                <div class="discover-inline-form" style="margin-top:12px;display:flex;gap:8px;align-items:center">
                    <input type="text" id="customModInput" placeholder="Module (e.g. EWM)" maxlength="10"
                        style="width:120px;text-transform:uppercase" />
                    <button class="btn btn-primary btn-sm" id="customModSaveBtn">Add</button>
                    <button class="btn btn-secondary btn-sm" id="customModCancelBtn">Cancel</button>
                </div>`;
            qs("#customModSaveBtn", area).addEventListener("click", async () => {
                const mod = qs("#customModInput", area).value.trim().toUpperCase();
                if (!mod) return;
                try {
                    await apiFetch("POST",
                        `/programs/${programId}/discover/scope-assessment`,
                        { sap_module: mod, is_in_scope: true }
                    );
                    showToast(`${mod} added`, "success");
                    renderScopeTab(container);
                    refreshGateBanner();
                } catch (err) {
                    showToast("Failed: " + err.message, "error");
                }
            });
            qs("#customModCancelBtn", area).addEventListener("click", () => { area.innerHTML = ""; });
        });
    }

    /* ── helpers ─────────────────────────────────────────────────────── */
    function statusBadgeClass(status) {
        return { approved: "success", in_review: "warning", rejected: "danger", draft: "secondary" }[status] ?? "secondary";
    }

    function showToast(msg, type) {
        /* Reuse the platform toast if available, else fallback */
        if (typeof App !== "undefined" && App.showToast) {
            App.showToast(msg, type);
            return;
        }
        const t = html("div", { className: `toast toast-${type}`, textContent: msg });
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    }

    /* ── public API ──────────────────────────────────────────────────── */
    return { render };
})();
