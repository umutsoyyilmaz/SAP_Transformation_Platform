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

    const DISCOVER_NAV_STATE_KEY = "pg.discoverWorkspace";

    /* ── module state ────────────────────────────────────────────────── */
    let programId = null;
    let currentWorkspace = "overview";
    let currentRoute = "discover";
    let rootEl = null;
    let landscapeFilters = { search: "", type: "", activity: "all" };
    let scopeFilters = { queue: "all", search: "" };

    /* ── constants ───────────────────────────────────────────────────── */
    const PROJECT_TYPES = ["greenfield", "brownfield", "bluefield", "selective_data_transition"];
    const SYSTEM_TYPES  = ["sap_erp", "s4hana", "non_sap", "middleware", "cloud", "legacy"];
    const SYSTEM_ROLES  = ["source", "target", "interface", "decommission", "keep"];
    const ENVIRONMENTS  = ["dev", "test", "q", "prod"];
    const COMPLEXITIES  = ["low", "medium", "high", "very_high"];
    const COMMON_MODULES = ["FI", "CO", "MM", "SD", "PP", "PM", "QM", "WM", "PS", "HR", "TR", "BC"];
    const WORKSPACES = [
        { id: "overview", step: "01", eyebrow: "Readiness", label: "Overview" },
        { id: "charter", step: "02", eyebrow: "Intent", label: "Project Charter" },
        { id: "landscape", step: "03", eyebrow: "Systems", label: "Landscape" },
        { id: "scope", step: "04", eyebrow: "Modules", label: "Scope" },
        { id: "timeline", step: "05", eyebrow: "Plan", label: "Timeline" },
        { id: "raci", step: "06", eyebrow: "Governance", label: "RACI" },
    ];

    /* Human-readable labels for raw enum values */
    const LABEL_MAP = {
        greenfield: "Greenfield", brownfield: "Brownfield",
        bluefield: "Bluefield", selective_data_transition: "Selective Data Transition",
        sap_erp: "SAP ERP", s4hana: "S/4HANA", non_sap: "Non-SAP",
        middleware: "Middleware", cloud: "Cloud", legacy: "Legacy",
        source: "Source", target: "Target", interface: "Interface",
        decommission: "Decommission", keep: "Keep",
        dev: "Development", test: "Test", q: "Quality", prod: "Production",
        low: "Low", medium: "Medium", high: "High", very_high: "Very High",
        draft: "Draft", in_review: "In Review",
        approved: "Approved", rejected: "Rejected",
    };
    function label(val) { return LABEL_MAP[val] ?? String(val ?? ""); }

    function _persistWorkspaceState(state = {}) {
        try {
            sessionStorage.setItem(DISCOVER_NAV_STATE_KEY, JSON.stringify(state));
        } catch {
            // Ignore storage failures; navigation still works.
        }
    }

    function _consumeWorkspaceState() {
        try {
            const raw = sessionStorage.getItem(DISCOVER_NAV_STATE_KEY);
            if (!raw) return null;
            sessionStorage.removeItem(DISCOVER_NAV_STATE_KEY);
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    function _routeForWorkspace(workspace) {
        if (workspace === "timeline") return "timeline";
        if (workspace === "raci") return "raci";
        return "discover";
    }

    function _workspaceMeta(workspace = currentWorkspace) {
        const map = {
            overview: {
                crumb: "Discover",
                lead: "Canonical cockpit for charter readiness, systems, scope, schedule, and governance alignment.",
            },
            charter: {
                crumb: "Project Charter",
                lead: "Capture the transformation intent, scope boundary, benefits, and approval readiness in one place.",
            },
            landscape: {
                crumb: "System Landscape",
                lead: "Track SAP and non-SAP systems in scope, their roles, and environment coverage across the program.",
            },
            scope: {
                crumb: "Scope Assessment",
                lead: "Assess module scope, complexity, and estimate coverage before Explore planning accelerates.",
            },
            timeline: {
                crumb: "Timeline",
                lead: "Review phase cadence, gate milestones, sprint pacing, and delay signals in the Discover cockpit.",
            },
            raci: {
                crumb: "RACI Matrix",
                lead: "Validate accountable ownership and delivery responsibility before the phase exits Discover.",
            },
        };
        return map[workspace] || map.overview;
    }

    function _renderWorkspaceNav() {
        const links = WORKSPACES.map((item) => {
            const active = item.id === currentWorkspace;
            return `<button type="button" class="explore-stage-link${active ? " explore-stage-link--active" : ""}" data-workspace="${item.id}" ${active ? 'aria-current="page"' : ""}>
                <span class="explore-stage-link__step">${esc(item.step)}</span>
                <span class="explore-stage-link__body">
                    <span class="explore-stage-link__eyebrow">${esc(item.eyebrow)}</span>
                    <span class="explore-stage-link__label">${esc(item.label)}</span>
                </span>
            </button>`;
        }).join("");
        return `<div class="explore-stage-nav discover-stage-nav" data-testid="discover-stage-nav">
            <div class="explore-stage-nav__items">${links}</div>
        </div>`;
    }

    function navigateWorkspace(workspace = "overview") {
        _persistWorkspaceState({ workspace });
        App.navigate(_routeForWorkspace(workspace));
    }

    /* ── entry point ─────────────────────────────────────────────────── */
    function render(container, opts = {}) {
        programId = (App.getActiveProgram() || {}).id;
        rootEl = container;
        currentRoute = opts.route || "discover";

        const navState = _consumeWorkspaceState();
        if (opts.workspace) currentWorkspace = opts.workspace;
        else if (navState?.workspace) currentWorkspace = navState.workspace;
        else if (currentRoute === "timeline") currentWorkspace = "timeline";
        else if (currentRoute === "raci") currentWorkspace = "raci";
        else if (currentWorkspace === "timeline" || currentWorkspace === "raci") currentWorkspace = "overview";

        if (!programId) {
            container.innerHTML = PGEmptyState.html({ icon: 'explore', title: 'No program selected', description: 'Select a program from the Programs view to access the Discover phase.' });
            return;
        }

        const meta = _workspaceMeta(currentWorkspace);
        const crumbs = [{ label: "Programs", onclick: 'App.navigate("programs")' }, { label: "Discover" }];
        if (currentWorkspace !== "overview") crumbs.push({ label: meta.crumb });

        container.innerHTML = `
            <div class="discover-shell" data-testid="discover-page" data-discover-workspace="${esc(currentWorkspace)}">
                <div class="pg-view-header">
                    ${PGBreadcrumb.html(crumbs)}
                    <div class="discover-shell__hero">
                        <div>
                            <h2 class="pg-view-title">Discover Phase</h2>
                            <p class="discover-shell__lead">${esc(meta.lead)}</p>
                        </div>
                        <div class="discover-shell__hero-actions">
                            <span class="badge badge-info" id="discoverGateBadge">Loading gate…</span>
                        </div>
                    </div>
                </div>
                <div id="discoverGateBanner" class="discover-gate-banner"></div>
                ${_renderWorkspaceNav()}
                <div id="discoverTabBody" class="discover-tab-body" data-testid="discover-workspace-body">
                    <div class="spinner-center"><div class="spinner"></div></div>
                </div>
            </div>`;

        container.querySelectorAll("[data-workspace]").forEach((btn) => {
            btn.addEventListener("click", () => {
                navigateWorkspace(btn.dataset.workspace);
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

            badge.textContent = data.gate_passed ? "Discover Ready" : "Discover Incomplete";
            badge.className   = `badge ${data.gate_passed ? "badge-success" : "badge-danger"}`;
            banner.classList.toggle("discover-gate-banner--passed", !!data.gate_passed);

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
        if (currentWorkspace === "overview") renderOverviewTab(body);
        else if (currentWorkspace === "charter") renderCharterTab(body);
        else if (currentWorkspace === "landscape") renderLandscapeTab(body);
        else if (currentWorkspace === "scope") renderScopeTab(body);
        else if (currentWorkspace === "timeline") TimelineView.render(body, { embedded: true });
        else if (currentWorkspace === "raci") RaciView.render(body, { embedded: true });
    }

    async function renderOverviewTab(container) {
        const workspace = currentWorkspace;
        const [gateResult, charterResult, landscapeResult, scopeResult, timelineResult, raciResult] = await Promise.allSettled([
            apiFetch("GET", `/programs/${programId}/discover/gate-status`),
            apiFetch("GET", `/programs/${programId}/discover/charter`).catch(() => null),
            apiFetch("GET", `/programs/${programId}/discover/landscape`),
            apiFetch("GET", `/programs/${programId}/discover/scope-assessment`),
            apiFetch("GET", `/programs/${programId}/timeline`).catch(() => null),
            apiFetch("GET", `/programs/${programId}/raci/validate`).catch(() => null),
        ]);
        if (workspace !== currentWorkspace) return;

        const gate = gateResult.status === "fulfilled" ? gateResult.value : { gate_passed: false, criteria: [] };
        const charter = charterResult.status === "fulfilled" ? charterResult.value : null;
        const landscapeItems = landscapeResult.status === "fulfilled" ? (landscapeResult.value.items || landscapeResult.value || []) : [];
        const scopeItems = scopeResult.status === "fulfilled" ? (scopeResult.value.items || scopeResult.value || []) : [];
        const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : null;
        const raci = raciResult.status === "fulfilled" ? raciResult.value : null;

        const inScope = scopeItems.filter((item) => item.is_in_scope);
        const highComplexity = inScope.filter((item) => ["high", "very_high"].includes(item.complexity));
        const delayedPhases = (timeline?.phases || []).filter((item) => item.color === "#ef4444");
        const nextMilestone = (timeline?.milestones || []).find((item) => item.status !== "completed");
        const noAccountable = raci?.activities_without_accountable?.length || 0;
        const noResponsible = raci?.activities_without_responsible?.length || 0;
        const systemsActive = landscapeItems.filter((item) => item.is_active !== false).length;
        const requirementsEstimate = inScope.reduce((sum, item) => sum + (Number(item.estimated_requirements) || 0), 0);
        const readinessScore = [
            charter?.status === "approved" ? 25 : 0,
            landscapeItems.length > 0 ? 20 : 0,
            inScope.length >= 3 ? 20 : 0,
            delayedPhases.length === 0 ? 15 : 0,
            noAccountable === 0 && noResponsible === 0 ? 20 : 0,
        ].reduce((sum, value) => sum + value, 0);

        const kpiCard = ({ value, label, sub = "", tone = "default" }) =>
            summaryMetric(value, label, tone, sub);

        const cards = [
            {
                workspace: "charter",
                eyebrow: "Readiness Gap",
                title: "Charter",
                copy: charter?.status === "approved"
                    ? "Charter is approved and locked for the phase exit."
                    : "Objective, scope, and approval are still the biggest gate dependency.",
                metric: charter?.status ? label(charter.status) : "Draft missing",
            },
            {
                workspace: "landscape",
                eyebrow: "System Coverage",
                title: "Landscape",
                copy: `${systemsActive} active systems tracked across SAP and non-SAP scope.`,
                metric: `${landscapeItems.length} systems`,
            },
            {
                workspace: "scope",
                eyebrow: "Assessment",
                title: "Scope Matrix",
                copy: `${highComplexity.length} modules are high complexity and need early Explore attention.`,
                metric: `${inScope.length} in scope`,
            },
            {
                workspace: "timeline",
                eyebrow: "Schedule Signal",
                title: "Timeline",
                copy: delayedPhases.length
                    ? `${delayedPhases.length} delayed phase signal${delayedPhases.length > 1 ? "s" : ""} detected.`
                    : "No delayed phases detected in the current plan.",
                metric: nextMilestone ? `Next gate: ${nextMilestone.date}` : "No open gate",
            },
            {
                workspace: "raci",
                eyebrow: "Ownership",
                title: "RACI Coverage",
                copy: noAccountable || noResponsible
                    ? `${noAccountable + noResponsible} activity assignment gaps need cleanup.`
                    : "Responsible and accountable coverage is complete.",
                metric: raci?.is_valid ? "Matrix valid" : "Needs review",
            },
        ];

        container.innerHTML = `
            <div class="discover-overview" data-testid="discover-overview-workspace">
                <div class="discover-summary-strip discover-overview__kpis">
                    ${kpiCard({ value: `${readinessScore}%`, label: "Discover Readiness", sub: gate.gate_passed ? "Gate criteria satisfied" : "Gate criteria still open", tone: readinessScore >= 80 ? "success" : readinessScore >= 50 ? "warning" : "default" })}
                    ${kpiCard({ value: charter?.status ? label(charter.status) : "Missing", label: "Charter", sub: charter?.target_go_live_date ? `Go-live ${charter.target_go_live_date}` : "Target date not set", tone: charter?.status === "approved" ? "success" : charter?.status === "in_review" ? "warning" : "info" })}
                    ${kpiCard({ value: landscapeItems.length, label: "Landscape Systems", sub: `${systemsActive} active / ${landscapeItems.length - systemsActive} inactive`, tone: landscapeItems.length ? "info" : "default" })}
                    ${kpiCard({ value: inScope.length, label: "In-Scope Modules", sub: `${requirementsEstimate} est. requirements`, tone: inScope.length ? "info" : "default" })}
                    ${kpiCard({ value: delayedPhases.length, label: "Delayed Phases", sub: nextMilestone ? `Next gate ${nextMilestone.name}` : "No upcoming milestone", tone: delayedPhases.length ? "warning" : "success" })}
                    ${kpiCard({ value: noAccountable + noResponsible, label: "RACI Gaps", sub: `${noAccountable} missing A / ${noResponsible} missing R`, tone: noAccountable + noResponsible ? "warning" : "success" })}
                </div>
                <div class="discover-overview__actions">
                    ${cards.map((card) => `
                        <button class="explore-spotlight-card" type="button" data-workspace-link="${card.workspace}">
                            <span class="explore-spotlight-card__eyebrow">${esc(card.eyebrow)}</span>
                            <span class="explore-spotlight-card__title">${esc(card.title)}</span>
                            <span class="explore-spotlight-card__copy">${esc(card.copy)}</span>
                            <span class="explore-spotlight-card__metric">${esc(card.metric)}</span>
                        </button>`).join("")}
                </div>
                <div class="discover-overview__board">
                    <div class="discover-overview__panel">
                        <div class="discover-overview__panel-title">Gate Criteria</div>
                        <div class="discover-overview__criteria">
                            ${(gate.criteria || []).map((item) => `
                                <div class="discover-overview__criterion ${item.passed ? "is-passed" : "is-open"}">
                                    <strong>${item.passed ? "Ready" : "Open"}</strong>
                                    <span>${esc(item.label)}</span>
                                    ${item.detail ? `<small>${esc(item.detail)}</small>` : ""}
                                </div>`).join("") || `<div class="discover-overview__criterion is-open"><span>No gate criteria available.</span></div>`}
                        </div>
                    </div>
                    <div class="discover-overview__panel">
                        <div class="discover-overview__panel-title">Focus Queues</div>
                        <div class="discover-overview__queue">
                            <button type="button" class="discover-overview__queue-item" data-workspace-link="charter">
                                <span>Approval & Intent</span>
                                <strong>${charter?.status === "approved" ? "Complete" : "Review charter"}</strong>
                            </button>
                            <button type="button" class="discover-overview__queue-item" data-workspace-link="scope">
                                <span>High Complexity Modules</span>
                                <strong>${highComplexity.length}</strong>
                            </button>
                            <button type="button" class="discover-overview__queue-item" data-workspace-link="timeline">
                                <span>Delayed Phases</span>
                                <strong>${delayedPhases.length}</strong>
                            </button>
                            <button type="button" class="discover-overview__queue-item" data-workspace-link="raci">
                                <span>Ownership Gaps</span>
                                <strong>${noAccountable + noResponsible}</strong>
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;

        container.querySelectorAll("[data-workspace-link]").forEach((btn) => {
            btn.addEventListener("click", () => navigateWorkspace(btn.dataset.workspaceLink));
        });
    }

    function summaryMetric(value, label, tone = "default", sub = "") {
        return `
            <div class="discover-summary-card discover-summary-card--${tone}">
                <div class="discover-summary-card__value">${esc(value)}</div>
                <div class="discover-summary-card__label">${esc(label)}</div>
                ${sub ? `<div class="discover-summary-card__sub">${esc(sub)}</div>` : ""}
            </div>`;
    }

    function workspaceErrorCard(title, message) {
        return `
            <div class="section-card discover-inline-error" data-testid="discover-workspace-error">
                <div class="section-card__body">
                    <div class="discover-inline-error__title">${esc(title)}</div>
                    <div class="discover-inline-error__copy">${esc(message)}</div>
                </div>
            </div>`;
    }

    function hydrateDiscoverDom(container) {
        if (!container) return;
        container.querySelectorAll(".charter-completion__fill[data-progress]").forEach((el) => {
            const pct = Number(el.dataset.progress || 0);
            el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
        });
    }

    function charterCompletion(charter = {}) {
        const checks = [
            !!charter.project_objective,
            !!charter.business_drivers,
            !!charter.expected_benefits,
            !!charter.in_scope_summary,
            !!charter.out_of_scope_summary,
            !!charter.affected_sap_modules,
            !!charter.target_go_live_date,
        ];
        const complete = checks.filter(Boolean).length;
        const percent = Math.round((complete / checks.length) * 100);
        return { complete, total: checks.length, percent };
    }

    function openConfirmModal({ title, message, confirmLabel = "Confirm", confirmVariant = "btn-primary", onConfirm }) {
        App.openModal(`
            <div class="modal-header">
                <h2>${esc(title)}</h2>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal-body">
                <p class="discover-modal-copy">${esc(message)}</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button type="button" class="btn ${confirmVariant}" id="discoverConfirmBtn">${esc(confirmLabel)}</button>
            </div>
        `);
        const btn = document.getElementById("discoverConfirmBtn");
        if (!btn) return;
        btn.addEventListener("click", async () => {
            btn.disabled = true;
            try {
                if (typeof onConfirm === "function") await onConfirm();
                App.closeModal();
            } catch (err) {
                btn.disabled = false;
                showToast(err.message || "Action failed", "error");
            }
        });
    }

    function openLandscapeFormModal(container, existing) {
        const isEdit = !!existing;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? "Edit System" : "Add System"}</h2>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <form id="discoverLandscapeForm">
                <div class="modal-body">
                    <div class="form-row">
                        <div class="form-group">
                            <label>System Name *</label>
                            <input type="text" name="system_name" value="${esc(existing?.system_name ?? "")}" required maxlength="100" />
                        </div>
                        <div class="form-group">
                            <label>System Type</label>
                            <select name="system_type">
                                ${SYSTEM_TYPES.map((t) => `<option value="${t}" ${existing?.system_type === t ? "selected" : ""}>${label(t)}</option>`).join("")}
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Role</label>
                            <select name="role">
                                ${SYSTEM_ROLES.map((r) => `<option value="${r}" ${existing?.role === r ? "selected" : ""}>${label(r)}</option>`).join("")}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Environment</label>
                            <select name="environment">
                                ${ENVIRONMENTS.map((e) => `<option value="${e}" ${existing?.environment === e ? "selected" : ""}>${label(e)}</option>`).join("")}
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Vendor</label>
                            <input type="text" name="vendor" value="${esc(existing?.vendor ?? "")}" maxlength="100" />
                        </div>
                        <div class="form-group">
                            <label>Version</label>
                            <input type="text" name="version" value="${esc(existing?.version ?? "")}" maxlength="50" />
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <input type="text" name="description" value="${esc(existing?.description ?? "")}" maxlength="500" />
                    </div>
                    <div class="form-group discover-checkbox-row">
                        <label><input type="checkbox" name="is_active" ${existing?.is_active !== false ? "checked" : ""} /> Active in current program scope</label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? "Update System" : "Add System"}</button>
                </div>
            </form>
        `);
        const form = document.getElementById("discoverLandscapeForm");
        if (!form) return;
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fd = new FormData(form);
            const payload = Object.fromEntries(fd.entries());
            payload.is_active = fd.has("is_active");
            ["vendor", "version", "description"].forEach((key) => {
                if (payload[key] === "") payload[key] = null;
            });
            try {
                if (isEdit) {
                    await apiFetch("PUT", `/programs/${programId}/discover/landscape/${existing.id}`, payload);
                } else {
                    await apiFetch("POST", `/programs/${programId}/discover/landscape`, payload);
                }
                App.closeModal();
                showToast(`System ${isEdit ? "updated" : "added"}`, "success");
                renderLandscapeTab(container);
                refreshGateBanner();
            } catch (err) {
                showToast("Save failed: " + err.message, "error");
            }
        });
    }

    function openCustomModuleModal(container) {
        App.openModal(`
            <div class="modal-header">
                <h2>Add Custom Module</h2>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal-body">
                <p class="discover-modal-copy">Add a non-standard SAP or adjacent capability module to the Discover scope matrix.</p>
                <div class="form-group">
                    <label>Module code</label>
                    <input type="text" id="discoverCustomModuleInput" class="discover-input--caps" placeholder="e.g. EWM" maxlength="10" />
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button type="button" class="btn btn-primary" id="discoverCustomModuleSave">Add Module</button>
            </div>
        `);
        const btn = document.getElementById("discoverCustomModuleSave");
        if (!btn) return;
        btn.addEventListener("click", async () => {
            const mod = (document.getElementById("discoverCustomModuleInput")?.value || "").trim().toUpperCase();
            if (!mod) return;
            btn.disabled = true;
            try {
                await apiFetch("POST", `/programs/${programId}/discover/scope-assessment`, { sap_module: mod, is_in_scope: true });
                App.closeModal();
                showToast(`${mod} added`, "success");
                renderScopeTab(container);
                refreshGateBanner();
            } catch (err) {
                btn.disabled = false;
                showToast("Failed: " + err.message, "error");
            }
        });
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
        const completion = charterCompletion(charter || {});
        const affectedModules = String(charter?.affected_sap_modules || "")
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);

        container.innerHTML = `
            <div data-testid="discover-charter-workspace">
            <div class="discover-summary-strip">
                ${summaryMetric(label(status), "Status", status === "approved" ? "success" : status === "in_review" ? "warning" : "default", status === "approved" ? "Ready for gate exit" : "Still editable")}
                ${summaryMetric(`${completion.percent}%`, "Completion", completion.percent >= 80 ? "success" : completion.percent >= 50 ? "warning" : "default", `${completion.complete}/${completion.total} key fields`)}
                ${summaryMetric(label(charter?.project_type || "greenfield"), "Project Type", "info")}
                ${summaryMetric(charter?.target_go_live_date?.slice(0, 10) || "TBD", "Target Go-Live", "default")}
                ${summaryMetric(charter?.estimated_duration_months || "—", "Duration", "default", charter?.estimated_duration_months ? "months" : "Not set")}
                ${summaryMetric(affectedModules.length, "Affected Modules", affectedModules.length ? "info" : "warning", affectedModules.slice(0, 3).join(", ") || "Not listed")}
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <div class="discover-workspace-heading">
                        <h3>Project Charter</h3>
                        <p class="discover-section-lead">Set the business intent, scope boundary, and delivery framing that everything else in Discover depends on.</p>
                    </div>
                    <span class="badge badge-${statusBadgeClass(status)}">${esc(label(status))}</span>
                    ${!isApproved
                        ? `<button class="btn btn-secondary btn-sm discover-header-action" id="charterApproveBtn">Submit for Approval</button>`
                        : ""}
                </div>
                <div class="charter-completion">
                    <span>${completion.complete} of ${completion.total} key charter signals captured</span>
                    <div class="charter-completion__bar">
                        <div class="charter-completion__fill ${completion.percent === 100 ? "charter-completion__fill--complete" : ""}" data-progress="${completion.percent}"></div>
                    </div>
                    <strong>${completion.percent}%</strong>
                </div>
                <form id="charterForm" class="discover-form ${isReadonly ? "readonly" : ""}">
                    <div class="discover-form-stack">
                        <section class="discover-form-section">
                            <div class="discover-form-section__title">Intent & Value</div>
                            <div class="form-grid-2">
                                <div class="form-group full-width">
                                    <label>Project Objective *</label>
                                    <textarea name="project_objective" rows="3" ${isReadonly ? "disabled" : ""} placeholder="What is the primary goal of this SAP transformation?">${esc(charter?.project_objective ?? "")}</textarea>
                                </div>
                                <div class="form-group">
                                    <label>Business Drivers</label>
                                    <textarea name="business_drivers" rows="3" ${isReadonly ? "disabled" : ""} placeholder="Why is this transformation needed now?">${esc(charter?.business_drivers ?? "")}</textarea>
                                </div>
                                <div class="form-group">
                                    <label>Expected Benefits</label>
                                    <textarea name="expected_benefits" rows="3" ${isReadonly ? "disabled" : ""} placeholder="Quantified / qualitative benefits">${esc(charter?.expected_benefits ?? "")}</textarea>
                                </div>
                                <div class="form-group full-width">
                                    <label>Key Risks</label>
                                    <textarea name="key_risks" rows="3" ${isReadonly ? "disabled" : ""} placeholder="Top 3–5 risks identified in discovery">${esc(charter?.key_risks ?? "")}</textarea>
                                </div>
                            </div>
                        </section>
                        <section class="discover-form-section">
                            <div class="discover-form-section__title">Scope Boundary</div>
                            <div class="form-grid-2">
                                <div class="form-group">
                                    <label>In-Scope Summary</label>
                                    <textarea name="in_scope_summary" rows="3" ${isReadonly ? "disabled" : ""}>${esc(charter?.in_scope_summary ?? "")}</textarea>
                                </div>
                                <div class="form-group">
                                    <label>Out-of-Scope Summary</label>
                                    <textarea name="out_of_scope_summary" rows="3" ${isReadonly ? "disabled" : ""}>${esc(charter?.out_of_scope_summary ?? "")}</textarea>
                                </div>
                                <div class="form-group">
                                    <label>Affected Countries <small>(comma-separated)</small></label>
                                    <input type="text" name="affected_countries" value="${esc(charter?.affected_countries ?? "")}" placeholder="DE, TR, US" ${isReadonly ? "disabled" : ""} />
                                </div>
                                <div class="form-group">
                                    <label>Affected SAP Modules <small>(comma-separated)</small></label>
                                    <input type="text" name="affected_sap_modules" value="${esc(charter?.affected_sap_modules ?? "")}" placeholder="FI, CO, MM, SD" ${isReadonly ? "disabled" : ""} />
                                </div>
                            </div>
                        </section>
                        <section class="discover-form-section">
                            <div class="discover-form-section__title">Delivery Framing</div>
                            <div class="form-grid-3">
                                <div class="form-group">
                                    <label>Project Type</label>
                                    <select name="project_type" ${isReadonly ? "disabled" : ""}>
                                        ${PROJECT_TYPES.map((t) => `<option value="${t}" ${charter?.project_type === t ? "selected" : ""}>${label(t)}</option>`).join("")}
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Target Go-Live Date</label>
                                    <input type="date" name="target_go_live_date" value="${esc(charter?.target_go_live_date?.slice(0, 10) ?? "")}" ${isReadonly ? "disabled" : ""} />
                                </div>
                                <div class="form-group">
                                    <label>Estimated Duration (months)</label>
                                    <input type="number" name="estimated_duration_months" min="1" max="120" value="${charter?.estimated_duration_months ?? ""}" ${isReadonly ? "disabled" : ""} />
                                </div>
                            </div>
                        </section>
                    </div>
                    ${!isReadonly
                        ? `<div class="form-actions">
                               <span class="discover-inline-note">Save as draft anytime, then submit once the charter is review-ready.</span>
                               <button type="submit" class="btn btn-primary">Save Charter</button>
                           </div>`
                        : `<div class="charter-approved-banner">
                               <span class="charter-approved-banner__icon">✅</span>
                               <span>Charter approved
                                   <span class="charter-approved-banner__meta">
                                       by ${esc(charter?.approved_by ?? "—")}
                                       &nbsp;·&nbsp;
                                       ${esc((charter?.approved_at ?? "").slice(0, 10) || "—")}
                                   </span>
                               </span>
                           </div>`}
                </form>
                ${charter?.approval_notes
                    ? `<div class="approval-notes"><strong>Approval notes:</strong> ${esc(charter.approval_notes)}</div>`
                    : ""}
            </div>
            </div>`;
        hydrateDiscoverDom(container);

        /* save handler */
        const form = qs("#charterForm", container);
        if (form && !isReadonly) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const payload = DiscoverCharterUI.collectPayload(form);
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
            approveBtn.addEventListener("click", () => {
                DiscoverCharterUI.openApprovalModal({
                    container,
                    charter,
                    programId,
                    saveDraft: (payload) => apiFetch("POST", `/programs/${programId}/discover/charter`, payload),
                    approveCharter: (payload) => apiFetch("POST", `/programs/${programId}/discover/charter/approve`, payload),
                    onApproved: async () => {
                        showToast("Charter approved successfully", "success");
                        await renderCharterTab(container);
                        await refreshGateBanner();
                    },
                    showToast,
                });
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
            container.innerHTML = workspaceErrorCard("Landscape unavailable", `Error loading landscape: ${err.message}`);
            return;
        }

        const search = (landscapeFilters.search || "").trim().toLowerCase();
        const filteredSystems = systems.filter((item) => {
            if (landscapeFilters.type && item.system_type !== landscapeFilters.type) return false;
            if (landscapeFilters.activity === "active" && item.is_active === false) return false;
            if (landscapeFilters.activity === "inactive" && item.is_active !== false) return false;
            if (search) {
                const haystack = [item.system_name, item.vendor, item.version, item.description].join(" ").toLowerCase();
                if (!haystack.includes(search)) return false;
            }
            return true;
        });
        const activeCount = systems.filter((item) => item.is_active !== false).length;
        const sapCoreCount = systems.filter((item) => ["sap_erp", "s4hana"].includes(item.system_type)).length;
        const nonSapCount = systems.filter((item) => !["sap_erp", "s4hana"].includes(item.system_type)).length;
        const targetCount = systems.filter((item) => item.role === "target").length;

        container.innerHTML = `
            <div data-testid="discover-landscape-workspace">
            <div class="discover-summary-strip">
                ${summaryMetric(systems.length, "Systems", "info", `${filteredSystems.length} visible`)}
                ${summaryMetric(activeCount, "Active", activeCount ? "success" : "warning", `${systems.length - activeCount} inactive`)}
                ${summaryMetric(sapCoreCount, "SAP Core", "info", "ERP / S/4HANA")}
                ${summaryMetric(nonSapCount, "Non-SAP", "default", "Cloud, legacy, middleware")}
                ${summaryMetric(targetCount, "Target Systems", targetCount ? "success" : "warning", "Transformation destination")}
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <div class="discover-workspace-heading">
                        <h3>System Landscape <span class="badge badge-secondary">${systems.length} system${systems.length !== 1 ? "s" : ""}</span></h3>
                        <p class="discover-section-lead">Track source, target, interface, and keep/decommission decisions before scope and integration detail expands.</p>
                    </div>
                    <button class="btn btn-primary btn-sm discover-header-action" id="addSystemBtn">+ Add System</button>
                </div>
                <div class="discover-toolbar">
                    <div class="discover-toolbar__group">
                        <input class="discover-toolbar__search" id="landscapeSearch" type="search" value="${esc(landscapeFilters.search)}" placeholder="Search systems, vendor, description…" />
                        <select id="landscapeTypeFilter">
                            <option value="">All types</option>
                            ${SYSTEM_TYPES.map((type) => `<option value="${type}" ${landscapeFilters.type === type ? "selected" : ""}>${label(type)}</option>`).join("")}
                        </select>
                        <select id="landscapeActivityFilter">
                            <option value="all" ${landscapeFilters.activity === "all" ? "selected" : ""}>All activity</option>
                            <option value="active" ${landscapeFilters.activity === "active" ? "selected" : ""}>Active only</option>
                            <option value="inactive" ${landscapeFilters.activity === "inactive" ? "selected" : ""}>Inactive only</option>
                        </select>
                    </div>
                    <div class="discover-toolbar__meta">${filteredSystems.length} visible</div>
                </div>
                ${systems.length === 0
                    ? `<div class="discover-empty">
                            <div class="discover-empty__icon">🖥️</div>
                            <p class="discover-empty__text">No systems added yet. Add your SAP and non-SAP systems to build the system landscape.</p>
                         </div>`
                    : filteredSystems.length === 0
                        ? `<div class="discover-empty discover-empty--compact">
                                <p class="discover-empty__text">No systems match the active filters.</p>
                           </div>`
                        : `<table class="data-table" id="landscapeTable">
                        <thead>
                            <tr>
                                <th>System Name</th><th>Type</th><th>Role</th>
                                <th>Vendor</th><th>Version</th><th>Environment</th>
                                <th>Active</th><th></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${filteredSystems.map(s => `
                            <tr data-id="${s.id}">
                                <td>${esc(s.system_name)}</td>
                                <td><span class="sys-type-badge sys-type-badge--${s.system_type ?? ''}">${esc(label(s.system_type ?? "—"))}</span></td>
                                <td>${esc(label(s.role) ?? "—")}</td>
                                <td>${esc(s.vendor ?? "—")}</td>
                                <td>${esc(s.version ?? "—")}</td>
                                <td>${esc(label(s.environment) ?? "—")}</td>
                                <td>${s.is_active ? "✅" : "—"}</td>
                                <td>
                                    <button class="btn btn-icon" data-action="edit-landscape" data-id="${s.id}">✏️</button>
                                    <button class="btn btn-icon btn-danger-icon" data-action="delete-landscape" data-id="${s.id}">🗑️</button>
                                </td>
                            </tr>`).join("")}
                        </tbody>
                    </table>`}
            </div>
            </div>`;

        qs("#landscapeSearch", container)?.addEventListener("input", (e) => {
            landscapeFilters.search = e.target.value;
            renderLandscapeTab(container);
        });
        qs("#landscapeTypeFilter", container)?.addEventListener("change", (e) => {
            landscapeFilters.type = e.target.value;
            renderLandscapeTab(container);
        });
        qs("#landscapeActivityFilter", container)?.addEventListener("change", (e) => {
            landscapeFilters.activity = e.target.value;
            renderLandscapeTab(container);
        });

        qs("#addSystemBtn", container).addEventListener("click", () => openLandscapeFormModal(container, null));

        container.querySelectorAll("[data-action='edit-landscape']").forEach(btn => {
            btn.addEventListener("click", () => {
                const sys = systems.find(s => s.id == btn.dataset.id);
                if (sys) openLandscapeFormModal(container, sys);
            });
        });

        container.querySelectorAll("[data-action='delete-landscape']").forEach(btn => {
            btn.addEventListener("click", () => {
                const sys = systems.find((item) => item.id == btn.dataset.id);
                openConfirmModal({
                    title: "Delete system",
                    message: `Remove ${sys?.system_name || "this system"} from the Discover landscape?`,
                    confirmLabel: "Delete System",
                    confirmVariant: "btn-danger",
                    onConfirm: async () => {
                        await apiFetch("DELETE", `/programs/${programId}/discover/landscape/${btn.dataset.id}`);
                        showToast("System removed", "success");
                        renderLandscapeTab(container);
                        refreshGateBanner();
                    },
                });
            });
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
            container.innerHTML = workspaceErrorCard("Scope matrix unavailable", err.message);
            return;
        }

        const byModule = {};
        assessments.forEach(a => { byModule[a.sap_module] = a; });

        const allModules = Array.from(
            new Set([...COMMON_MODULES, ...assessments.map(a => a.sap_module)])
        ).sort();
        const inScopeCount = assessments.filter((a) => a.is_in_scope).length;
        const highComplexityCount = assessments.filter((a) => a.is_in_scope && ["high", "very_high"].includes(a.complexity)).length;
        const missingEstimateCount = assessments.filter((a) => a.is_in_scope && (a.estimated_requirements == null || a.estimated_gaps == null)).length;
        const customModuleCount = assessments.filter((a) => !COMMON_MODULES.includes(a.sap_module)).length;
        const filteredModules = allModules.filter((mod) => {
            const assessment = byModule[mod];
            const q = (scopeFilters.search || "").trim().toLowerCase();
            if (q) {
                const haystack = [mod, assessment?.notes || "", label(assessment?.complexity || "")].join(" ").toLowerCase();
                if (!haystack.includes(q)) return false;
            }
            if (scopeFilters.queue === "inScope") return !!assessment?.is_in_scope;
            if (scopeFilters.queue === "highRisk") return !!assessment?.is_in_scope && ["high", "very_high"].includes(assessment?.complexity);
            if (scopeFilters.queue === "missingEstimates") return !!assessment?.is_in_scope && (assessment?.estimated_requirements == null || assessment?.estimated_gaps == null);
            if (scopeFilters.queue === "custom") return !COMMON_MODULES.includes(mod);
            return true;
        });

        container.innerHTML = `
            <div data-testid="discover-scope-workspace">
            <div class="discover-summary-strip">
                ${summaryMetric(inScopeCount, "In Scope", inScopeCount ? "success" : "warning", `${allModules.length} tracked modules`)}
                ${summaryMetric(highComplexityCount, "High Complexity", highComplexityCount ? "warning" : "success", "High / Very High")}
                ${summaryMetric(missingEstimateCount, "Missing Estimates", missingEstimateCount ? "warning" : "success", "Requirements or gaps unset")}
                ${summaryMetric(customModuleCount, "Custom Modules", customModuleCount ? "info" : "default", "Outside common baseline")}
            </div>
            <div class="section-card">
                <div class="section-card__header">
                    <div class="discover-workspace-heading">
                        <h3>Scope Assessment
                            <span class="badge badge-success">${inScopeCount} in scope</span>
                        </h3>
                        <p class="discover-section-lead">Use the matrix to flag what moves into Explore first, where estimation is still thin, and which modules are structurally risky.</p>
                    </div>
                    <button class="btn btn-secondary btn-sm discover-header-action" id="addModuleBtn">+ Add Custom Module</button>
                </div>
                <div class="discover-toolbar">
                    <div class="discover-toolbar__group">
                        <input class="discover-toolbar__search" id="scopeSearch" type="search" value="${esc(scopeFilters.search)}" placeholder="Search modules or notes…" />
                        <div class="discover-segmented">
                            <button type="button" class="discover-segmented__item ${scopeFilters.queue === "all" ? "is-active" : ""}" data-scope-queue="all">All</button>
                            <button type="button" class="discover-segmented__item ${scopeFilters.queue === "inScope" ? "is-active" : ""}" data-scope-queue="inScope">In Scope</button>
                            <button type="button" class="discover-segmented__item ${scopeFilters.queue === "highRisk" ? "is-active" : ""}" data-scope-queue="highRisk">High Complexity</button>
                            <button type="button" class="discover-segmented__item ${scopeFilters.queue === "missingEstimates" ? "is-active" : ""}" data-scope-queue="missingEstimates">Missing Estimates</button>
                            <button type="button" class="discover-segmented__item ${scopeFilters.queue === "custom" ? "is-active" : ""}" data-scope-queue="custom">Custom</button>
                        </div>
                    </div>
                    <div class="discover-toolbar__meta">${filteredModules.length} visible</div>
                </div>
                <p class="text-muted discover-section-help">
                    Toggle modules in or out of scope, set complexity and estimates, then save each row once you are comfortable with the assessment.
                </p>
                <table class="data-table scope-grid">
                    <thead>
                        <tr>
                            <th>Module</th><th>In Scope</th><th>Complexity</th>
                            <th>Est. Requirements</th><th>Est. Gaps</th><th>Notes</th><th></th>
                        </tr>
                    </thead>
                    <tbody id="scopeTableBody">
                        ${filteredModules.map(mod => {
                            const a = byModule[mod];
                            return `
                            <tr data-module="${mod}" data-id="${a?.id ?? ''}" class="${a?.is_in_scope ? 'is-in-scope' : ''}">
                                <td><strong>${esc(mod)}</strong></td>
                                <td class="scope-toggle-cell">
                                    <input type="checkbox" class="scope-inscope-chk"
                                        ${a?.is_in_scope ? "checked" : ""} />
                                </td>
                                <td>
                                    <select class="scope-complexity-sel" ${!a?.is_in_scope ? "disabled" : ""}>
                                        <option value="">—</option>
                                        ${COMPLEXITIES.map(c =>
                                            `<option value="${c}" ${a?.complexity === c ? "selected" : ""}>${label(c)}</option>`
                                        ).join("")}
                                    </select>
                                </td>
                                <td>
                                    <input type="number" class="scope-req-inp" min="0"
                                        value="${a?.estimated_requirements ?? ""}"
                                        ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <input type="number" class="scope-gap-inp" min="0"
                                        value="${a?.estimated_gaps ?? ""}"
                                        ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <input type="text" class="scope-notes-inp"
                                        value="${esc(a?.notes ?? "")}"
                                        ${!a?.is_in_scope ? "disabled" : ""} />
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-primary scope-save-btn">Save</button>
                                    ${a ? `<button class="btn btn-icon btn-danger-icon scope-del-btn" data-id="${a.id}">🗑️</button>` : ""}
                                </td>
                            </tr>`;
                        }).join("")}
                    </tbody>
                </table>
            </div>
            </div>`;

        qs("#scopeSearch", container)?.addEventListener("input", (e) => {
            scopeFilters.search = e.target.value;
            renderScopeTab(container);
        });
        container.querySelectorAll("[data-scope-queue]").forEach((btn) => {
            btn.addEventListener("click", () => {
                scopeFilters.queue = btn.dataset.scopeQueue;
                renderScopeTab(container);
            });
        });

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
            btn.addEventListener("click", () => {
                const row = btn.closest("tr");
                openConfirmModal({
                    title: "Remove scope assessment",
                    message: `Delete the assessment row for ${row?.dataset.module || "this module"}?`,
                    confirmLabel: "Remove Assessment",
                    confirmVariant: "btn-danger",
                    onConfirm: async () => {
                        await apiFetch("DELETE", `/programs/${programId}/discover/scope-assessment/${btn.dataset.id}`);
                        showToast("Removed", "success");
                        renderScopeTab(container);
                        refreshGateBanner();
                    },
                });
            });
        });

        /* add custom module */
        qs("#addModuleBtn", container).addEventListener("click", () => {
            openCustomModuleModal(container);
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

    function renderForTimelineRoute(container = document.getElementById("mainContent")) {
        render(container, { route: "timeline", workspace: "timeline" });
    }

    function renderForRaciRoute(container = document.getElementById("mainContent")) {
        render(container, { route: "raci", workspace: "raci" });
    }

    /* ── public API ──────────────────────────────────────────────────── */
    return {
        render,
        renderForTimelineRoute,
        renderForRaciRoute,
        navigateWorkspace,
    };
})();
