/**
 * RACI Matrix View — S3-03 · FDD-F06: RACI Matrix UI
 *
 * Refactored to align with the Discover cockpit shell.
 * Removes JS-injected CSS and browser-native alerts while preserving
 * the spreadsheet-style click-to-cycle interaction.
 */
const RaciView = (() => {
    "use strict";

    const ROLE_CYCLE = ["R", "A", "C", "I", null];
    const ROLE_LABELS = {
        R: "Responsible",
        A: "Accountable",
        C: "Consulted",
        I: "Informed",
    };
    const SAP_PHASE_ORDER = ["discover", "prepare", "explore", "realize", "deploy", "run"];

    let _state = {
        programId: null,
        projectId: null,
        container: null,
        activities: [],
        teamMembers: [],
        matrix: {},
        validation: {},
        filterPhase: "",
        filterWorkstream: "",
        loading: false,
    };

    function _activeProjectId() {
        if (typeof App === "undefined" || typeof App.getActiveProject !== "function") return null;
        return App.getActiveProject()?.id || null;
    }

    function escHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function apiFetch(url, opts = {}) {
        return fetch(url, { headers: { "Content-Type": "application/json" }, ...opts })
            .then((r) => {
                if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.error || `HTTP ${r.status}`)));
                return r.json();
            });
    }

    function toast(message, type = "info") {
        if (typeof App !== "undefined" && typeof App.toast === "function") {
            App.toast(message, type);
            return;
        }
        if (typeof App !== "undefined" && typeof App.showToast === "function") {
            App.showToast(message, type);
            return;
        }
        console[type === "error" ? "error" : "log"](message);
    }

    function nextRole(current) {
        const idx = ROLE_CYCLE.indexOf(current);
        return ROLE_CYCLE[(idx + 1) % ROLE_CYCLE.length];
    }

    function fetchMatrix(programId, phase, workstream, projectId) {
        let url = `/api/v1/programs/${programId}/raci`;
        const params = [];
        if (phase) params.push(`sap_phase=${encodeURIComponent(phase)}`);
        if (workstream) params.push(`workstream_id=${encodeURIComponent(workstream)}`);
        if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
        if (params.length) url += "?" + params.join("&");
        return apiFetch(url);
    }

    function putEntry(programId, activityId, memberId, role, projectId) {
        return apiFetch(`/api/v1/programs/${programId}/raci/entries`, {
            method: "PUT",
            body: JSON.stringify({
                activity_id: activityId,
                team_member_id: memberId,
                raci_role: role,
                project_id: projectId,
            }),
        });
    }

    function importTemplate(programId, projectId) {
        return apiFetch(`/api/v1/programs/${programId}/raci/import-template`, {
            method: "POST",
            body: JSON.stringify(projectId ? { project_id: projectId } : {}),
        });
    }

    function metricCard({ value, label, sub = "", tone = "default" }) {
        return `
            <div class="discover-summary-card discover-summary-card--${tone}">
                <div class="discover-summary-card__value">${escHtml(value)}</div>
                <div class="discover-summary-card__label">${escHtml(label)}</div>
                ${sub ? `<div class="discover-summary-card__sub">${escHtml(sub)}</div>` : ""}
            </div>
        `;
    }

    function roleClass(role) {
        return role ? `raci-cell--${String(role).toLowerCase()}` : "raci-cell--empty";
    }

    function applyCellState(cell, role) {
        cell.textContent = role || "";
        cell.dataset.role = role || "";
        cell.classList.remove("raci-cell--r", "raci-cell--a", "raci-cell--c", "raci-cell--i", "raci-cell--empty");
        cell.classList.add(roleClass(role));
        cell.title = role ? ROLE_LABELS[role] : "Not assigned — click to assign";
    }

    function buildFilterOptions(phases) {
        let opts = '<option value="">All Phases</option>';
        phases.forEach((phase) => {
            opts += `<option value="${escHtml(phase)}">${escHtml(phase.toUpperCase())}</option>`;
        });
        return opts;
    }

    function buildHeaderRow(teamMembers) {
        let th = '<th class="raci-th-activity">Activity</th>';
        teamMembers.forEach((member) => {
            th += `<th class="raci-th-member" title="${escHtml(member.role || "")}">
                <span class="raci-th-member__name">${escHtml(member.name)}</span>
                <span class="raci-member-role">${escHtml(member.role || "")}</span>
            </th>`;
        });
        return th;
    }

    function renderSummary(container) {
        const phases = [...new Set(_state.activities.map((item) => item.sap_activate_phase).filter(Boolean))];
        const noA = _state.validation.activities_without_accountable?.length || 0;
        const noR = _state.validation.activities_without_responsible?.length || 0;
        const invalidCount = noA + noR;
        const summary = container.querySelector(".raci-summary-strip");
        if (!summary) return;
        summary.innerHTML = `
            ${metricCard({ value: _state.activities.length, label: "Activities", tone: _state.activities.length ? "info" : "default", sub: `${phases.length} phases represented` })}
            ${metricCard({ value: _state.teamMembers.length, label: "Team Members", tone: _state.teamMembers.length ? "info" : "default", sub: "Matrix columns" })}
            ${metricCard({ value: noA, label: "Missing Accountable", tone: noA ? "warning" : "success", sub: "Activities without A" })}
            ${metricCard({ value: noR, label: "Missing Responsible", tone: noR ? "warning" : "success", sub: "Activities without R" })}
            ${metricCard({ value: _state.validation.is_valid ? "Valid" : "Needs Review", label: "Matrix Status", tone: _state.validation.is_valid ? "success" : "warning", sub: invalidCount ? `${invalidCount} assignment gaps open` : "No coverage gaps" })}
        `;
    }

    function renderValidationBanners(container, validation) {
        const noA = validation.activities_without_accountable || [];
        const noR = validation.activities_without_responsible || [];
        const banner = container.querySelector(".raci-validation-banners");
        if (!banner) return;
        const rows = [];
        if (noA.length) {
            rows.push(`<div class="raci-warning raci-warning--yellow" title="${escHtml(noA.join(", "))}">
                <strong>${noA.length}</strong>
                <span>activities without Accountable (A) coverage.</span>
            </div>`);
        }
        if (noR.length) {
            rows.push(`<div class="raci-warning raci-warning--red" title="${escHtml(noR.join(", "))}">
                <strong>${noR.length}</strong>
                <span>activities without Responsible (R) coverage.</span>
            </div>`);
        }
        banner.innerHTML = rows.join("") || `<div class="raci-warning raci-warning--green"><strong>Valid</strong><span>All activities have accountable and responsible coverage.</span></div>`;
    }

    function renderMatrix(container) {
        const tbody = container.querySelector(".raci-matrix-tbody");
        if (!tbody) return;

        const byPhase = {};
        _state.activities.forEach((activity) => {
            const phase = activity.sap_activate_phase || "other";
            if (!byPhase[phase]) byPhase[phase] = [];
            byPhase[phase].push(activity);
        });

        const phaseOrder = [...SAP_PHASE_ORDER, "other"];
        let rowsHtml = "";

        phaseOrder.forEach((phase) => {
            const phaseActs = byPhase[phase];
            if (!phaseActs || !phaseActs.length) return;
            phaseActs.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));

            rowsHtml += `<tr class="raci-phase-header">
                <td colspan="${_state.teamMembers.length + 1}" class="raci-phase-label">${escHtml(phase.toUpperCase())}</td>
            </tr>`;

            phaseActs.forEach((activity) => {
                const activityId = String(activity.id);
                rowsHtml += `<tr class="raci-row" data-activity-id="${activity.id}">
                    <td class="raci-activity-name" title="${escHtml(activity.category || "")}">${escHtml(activity.name)}</td>`;
                _state.teamMembers.forEach((member) => {
                    const memberId = String(member.id);
                    const role = (_state.matrix[activityId] && _state.matrix[activityId][memberId]) || null;
                    rowsHtml += `<td class="raci-cell ${roleClass(role)}"
                        data-activity-id="${activity.id}"
                        data-member-id="${member.id}"
                        data-role="${role || ""}"
                        title="${escHtml(role ? ROLE_LABELS[role] : "Not assigned — click to assign")}">
                        ${role ? escHtml(role) : ""}
                    </td>`;
                });
                rowsHtml += "</tr>";
            });
        });

        tbody.innerHTML = rowsHtml || '<tr><td colspan="99" class="raci-empty">No activities yet. Load the SAP template to seed the matrix.</td></tr>';
        tbody.querySelectorAll(".raci-cell").forEach((cell) => cell.addEventListener("click", onCellClick));

        const meta = container.querySelector(".raci-toolbar__meta");
        if (meta) {
            meta.textContent = `${_state.activities.length} activities • ${_state.teamMembers.length} team members`;
        }
    }

    function fullRender(container, data) {
        _state.activities = data.activities || [];
        _state.teamMembers = data.team_members || [];
        _state.matrix = data.matrix || {};
        _state.validation = data.validation || {};

        const phases = [...new Set(_state.activities.map((item) => item.sap_activate_phase).filter(Boolean))]
            .sort((a, b) => SAP_PHASE_ORDER.indexOf(a) - SAP_PHASE_ORDER.indexOf(b));
        const phaseFilter = container.querySelector(".raci-filter-phase");
        if (phaseFilter) {
            const saved = _state.filterPhase || "";
            phaseFilter.innerHTML = buildFilterOptions(phases);
            phaseFilter.value = saved;
        }

        const thead = container.querySelector(".raci-matrix-thead tr");
        if (thead) thead.innerHTML = buildHeaderRow(_state.teamMembers);

        renderSummary(container);
        renderMatrix(container);
        renderValidationBanners(container, _state.validation);
    }

    function renderLoadError(container, message) {
        const tbody = container.querySelector(".raci-matrix-tbody");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="99" class="raci-table__error">${escHtml(message)}</td></tr>`;
        }
        const meta = container.querySelector(".raci-toolbar__meta");
        if (meta) meta.textContent = "Matrix unavailable";
        toast(message, "error");
    }

    function fetchValidationBanners(container = _state.container) {
        if (!container || !_state.programId) return;
        const params = new URLSearchParams();
        if (_state.projectId) params.set("project_id", String(_state.projectId));
        const url = params.toString()
            ? `/api/v1/programs/${_state.programId}/raci/validate?${params.toString()}`
            : `/api/v1/programs/${_state.programId}/raci/validate`;
        apiFetch(url)
            .then((validation) => {
                _state.validation = validation;
                renderSummary(container);
                renderValidationBanners(container, validation);
            })
            .catch(() => {});
    }

    function onCellClick(event) {
        const cell = event.currentTarget;
        const activityId = parseInt(cell.dataset.activityId, 10);
        const memberId = parseInt(cell.dataset.memberId, 10);
        const currentRole = cell.dataset.role || null;
        const newRole = nextRole(currentRole || null);

        applyCellState(cell, newRole);

        putEntry(_state.programId, activityId, memberId, newRole, _state.projectId)
            .then(() => {
                const aKey = String(activityId);
                const mKey = String(memberId);
                if (!_state.matrix[aKey]) _state.matrix[aKey] = {};
                if (newRole) _state.matrix[aKey][mKey] = newRole;
                else delete _state.matrix[aKey][mKey];
                fetchValidationBanners();
            })
            .catch((err) => {
                applyCellState(cell, currentRole);
                toast(`RACI update failed: ${err.message}`, "error");
            });
    }

    function buildShell(container, opts = {}) {
        const shellClass = `raci-workspace${opts.embedded ? " raci-workspace--embedded" : ""}`;
        const testId = opts.embedded ? "discover-raci-workspace" : "raci-page";
        container.innerHTML = `
            <div class="${shellClass}" data-testid="${testId}">
                <div class="raci-hero">
                    <div class="raci-hero__body">
                        <div class="raci-hero__eyebrow">Discover Governance</div>
                        <div class="raci-hero__title">RACI Matrix</div>
                        <p class="raci-hero__copy">Validate ownership before Discover exits, and keep the responsibility grid editable inside the cockpit.</p>
                    </div>
                    <div class="raci-hero__meta">
                        <span class="timeline-meta-chip">Click cells to cycle R → A → C → I → Empty</span>
                    </div>
                </div>
                <div class="discover-summary-strip raci-summary-strip">
                    ${metricCard({ value: "—", label: "Activities" })}
                    ${metricCard({ value: "—", label: "Team Members" })}
                    ${metricCard({ value: "—", label: "Missing Accountable" })}
                    ${metricCard({ value: "—", label: "Missing Responsible" })}
                    ${metricCard({ value: "—", label: "Matrix Status" })}
                </div>
                <section class="section-card">
                    <div class="section-card__header">
                        <div class="discover-workspace-heading">
                            <h3>Responsibility Grid</h3>
                            <p class="discover-section-lead">Load SAP template activities, filter by phase, and tighten accountable ownership before Explore expands the delivery team.</p>
                        </div>
                        <div class="raci-header-actions">
                            <button class="btn btn-secondary btn-sm raci-btn-import" type="button">Load SAP Template</button>
                            <button class="btn btn-secondary btn-sm raci-btn-refresh" type="button">Refresh</button>
                        </div>
                    </div>
                    <div class="discover-toolbar">
                        <div class="discover-toolbar__group">
                            <select class="raci-filter-phase" title="Filter by phase">
                                <option value="">All Phases</option>
                            </select>
                        </div>
                        <div class="discover-toolbar__meta raci-toolbar__meta">Loading matrix…</div>
                    </div>
                    <div class="raci-legend">
                        <span class="raci-legend-item raci-legend-item--r">R</span><span class="raci-legend-label">Responsible</span>
                        <span class="raci-legend-item raci-legend-item--a">A</span><span class="raci-legend-label">Accountable</span>
                        <span class="raci-legend-item raci-legend-item--c">C</span><span class="raci-legend-label">Consulted</span>
                        <span class="raci-legend-item raci-legend-item--i">I</span><span class="raci-legend-label">Informed</span>
                    </div>
                    <div class="raci-validation-banners"></div>
                    <div class="raci-table-wrapper">
                        <table class="raci-table" aria-label="RACI matrix">
                            <thead class="raci-matrix-thead"><tr></tr></thead>
                            <tbody class="raci-matrix-tbody">
                                <tr><td colspan="99" class="raci-loading">Loading…</td></tr>
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>
        `;
    }

    function render(container, opts = {}) {
        if (!container) return;

        const activeProgram = typeof App !== "undefined" && App.getActiveProgram && App.getActiveProgram();
        const activeProject = typeof App !== "undefined" && App.getActiveProject && App.getActiveProject();
        const programId = activeProgram && (activeProgram.id || activeProgram);
        if (!programId) {
            container.innerHTML = PGEmptyState.html({
                icon: "teams",
                title: "No program selected",
                description: "Select a program first to work on the Discover RACI matrix.",
                action: { label: "Go to Programs", onclick: "App.navigate('programs')" },
            });
            return;
        }

        _state.programId = typeof programId === "object" ? programId.id : programId;
        _state.projectId = activeProject?.id || null;
        _state.container = container;
        buildShell(container, opts);

        const heroMeta = container.querySelector(".raci-hero__meta");
        if (heroMeta && _state.projectId) {
            heroMeta.innerHTML = `
                <span class="timeline-meta-chip">Project scoped: ${escHtml(activeProject?.name || "Selected project")}</span>
                <span class="timeline-meta-chip">Click cells to cycle R → A → C → I → Empty</span>
            `;
        }

        const phaseSelect = container.querySelector(".raci-filter-phase");
        if (phaseSelect) {
            phaseSelect.addEventListener("change", () => {
                _state.filterPhase = phaseSelect.value;
                load(container);
            });
        }

        const importBtn = container.querySelector(".raci-btn-import");
        if (importBtn) {
            importBtn.addEventListener("click", () => {
                importBtn.disabled = true;
                importBtn.textContent = "Loading…";
                importTemplate(_state.programId, _state.projectId)
                    .then((result) => {
                        if (result.created === 0) toast("All SAP template activities already exist.", "info");
                        else toast(`${result.created} activities added.`, "success");
                        return fetchMatrix(_state.programId, _state.filterPhase, _state.filterWorkstream, _state.projectId);
                    })
                    .then((data) => fullRender(container, data))
                    .catch((err) => toast(`RACI import failed: ${err.message}`, "error"))
                    .finally(() => {
                        importBtn.disabled = false;
                        importBtn.textContent = "Load SAP Template";
                    });
            });
        }

        const refreshBtn = container.querySelector(".raci-btn-refresh");
        if (refreshBtn) refreshBtn.addEventListener("click", () => load(container));

        load(container);
    }

    function load(container = _state.container) {
        _state.projectId = _activeProjectId();
        fetchMatrix(_state.programId, _state.filterPhase, _state.filterWorkstream, _state.projectId)
            .then((data) => fullRender(container, data))
            .catch((err) => renderLoadError(container, `Failed to load RACI matrix: ${err.message}`));
    }

    return { render };
})();
