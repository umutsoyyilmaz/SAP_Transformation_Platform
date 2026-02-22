/**
 * RACI Matrix View — S3-03 · FDD-F06: RACI Matrix UI
 *
 * Renders a spreadsheet-like RACI matrix for the active program.
 * Rows = activities (SAP Activate phases grouped), Columns = team members.
 * Cell click cycles through: R → A → C → I → (empty).
 *
 * Entry point: RaciView.render(containerEl)
 */
const RaciView = (() => {
    "use strict";

    // ------------------------------------------------------------------
    // Constants
    // ------------------------------------------------------------------

    /** RACI role cycle order: clicking an assigned cell advances to next role */
    const ROLE_CYCLE = ["R", "A", "C", "I", null];

    /** Display colors per RACI role */
    const ROLE_COLORS = {
        R: { bg: "#3b82f6", text: "#ffffff", label: "R" }, // Responsible — blue
        A: { bg: "#ef4444", text: "#ffffff", label: "A" }, // Accountable — red
        C: { bg: "#22c55e", text: "#ffffff", label: "C" }, // Consulted — green
        I: { bg: "#9ca3af", text: "#ffffff", label: "I" }, // Informed — gray
    };

    /** Human-readable role labels shown in the legend */
    const ROLE_LABELS = {
        R: "Responsible (Sorumlu)",
        A: "Accountable (Yetkili)",
        C: "Consulted (Danışılan)",
        I: "Informed (Bilgilendirilen)",
    };

    const SAP_PHASE_ORDER = ["discover", "prepare", "explore", "realize", "deploy", "run"];

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

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

    function nextRole(current) {
        const idx = ROLE_CYCLE.indexOf(current);
        return ROLE_CYCLE[(idx + 1) % ROLE_CYCLE.length];
    }

    // ------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------
    let _state = {
        programId: null,
        activities: [],
        teamMembers: [],
        matrix: {},       // {activityId_str: {memberId_str: role}}
        validation: {},
        filterPhase: "",
        filterWorkstream: "",
        loading: false,
    };

    // ------------------------------------------------------------------
    // API calls
    // ------------------------------------------------------------------

    function fetchMatrix(programId, phase, workstream) {
        let url = `/api/v1/programs/${programId}/raci`;
        const params = [];
        if (phase) params.push(`sap_phase=${encodeURIComponent(phase)}`);
        if (workstream) params.push(`workstream_id=${encodeURIComponent(workstream)}`);
        if (params.length) url += "?" + params.join("&");
        return apiFetch(url);
    }

    function putEntry(programId, activityId, memberId, role) {
        return apiFetch(`/api/v1/programs/${programId}/raci/entries`, {
            method: "PUT",
            body: JSON.stringify({
                activity_id: activityId,
                team_member_id: memberId,
                raci_role: role,
            }),
        });
    }

    function importTemplate(programId) {
        return apiFetch(`/api/v1/programs/${programId}/raci/import-template`, {
            method: "POST",
            body: JSON.stringify({}),
        });
    }

    // ------------------------------------------------------------------
    // Render functions
    // ------------------------------------------------------------------

    function renderValidationBanners(container, validation) {
        const { activities_without_accountable: noA, activities_without_responsible: noR } = validation;
        let html = "";
        if (noA && noA.length > 0) {
            html += `<div class="raci-warning raci-warning--yellow" title="${escHtml(noA.join(', '))}">
                ⚠ ${noA.length} aktivite için Accountable (A) atanmamış.
            </div>`;
        }
        if (noR && noR.length > 0) {
            html += `<div class="raci-warning raci-warning--red" title="${escHtml(noR.join(', '))}">
                ✗ ${noR.length} aktivite için Responsible (R) atanmamış.
            </div>`;
        }
        const banner = container.querySelector(".raci-validation-banners");
        if (banner) banner.innerHTML = html;
    }

    function renderMatrix(container) {
        const { activities, teamMembers, matrix, filterPhase } = _state;
        const tbody = container.querySelector(".raci-matrix-tbody");
        if (!tbody) return;

        // Group activities by SAP phase
        const byPhase = {};
        activities.forEach((act) => {
            const phase = act.sap_activate_phase || "other";
            if (!byPhase[phase]) byPhase[phase] = [];
            byPhase[phase].push(act);
        });

        const phaseOrder = [...SAP_PHASE_ORDER, "other"];
        let rowsHtml = "";

        phaseOrder.forEach((phase) => {
            const phaseActs = byPhase[phase];
            if (!phaseActs || phaseActs.length === 0) return;

            // Phase group header row
            rowsHtml += `<tr class="raci-phase-header">
                <td colspan="${teamMembers.length + 1}" class="raci-phase-label">
                    ${escHtml(phase.toUpperCase())}
                </td>
            </tr>`;

            phaseActs.forEach((act) => {
                const actId = String(act.id);
                rowsHtml += `<tr class="raci-row" data-activity-id="${act.id}">
                    <td class="raci-activity-name" title="${escHtml(act.category || "")}">${escHtml(act.name)}</td>`;

                teamMembers.forEach((mem) => {
                    const memId = String(mem.id);
                    const role = (matrix[actId] && matrix[actId][memId]) || null;
                    const color = role ? ROLE_COLORS[role] : null;
                    const cellStyle = color
                        ? `background:${color.bg};color:${color.text};cursor:pointer;`
                        : "cursor:pointer;";
                    const cellTitle = role ? `${ROLE_LABELS[role]}` : "Atanmadı — tıkla atamak için";
                    rowsHtml += `<td class="raci-cell"
                        data-activity-id="${act.id}"
                        data-member-id="${mem.id}"
                        data-role="${role || ""}"
                        style="${cellStyle}"
                        title="${escHtml(cellTitle)}">
                        ${role ? escHtml(role) : ""}
                    </td>`;
                });

                rowsHtml += `</tr>`;
            });
        });

        tbody.innerHTML = rowsHtml || '<tr><td colspan="99" class="raci-empty">Aktivite yok. "SAP Şablonunu Yükle" butonuna tıklayın.</td></tr>';

        // Attach click handlers to cells
        tbody.querySelectorAll(".raci-cell").forEach((cell) => {
            cell.addEventListener("click", onCellClick);
        });
    }

    function buildFilterOptions(phases) {
        let opts = '<option value="">Tüm Fazlar</option>';
        phases.forEach((p) => {
            opts += `<option value="${escHtml(p)}">${escHtml(p.toUpperCase())}</option>`;
        });
        return opts;
    }

    function buildHeaderRow(teamMembers) {
        let th = '<th class="raci-th-activity">Aktivite</th>';
        teamMembers.forEach((m) => {
            th += `<th class="raci-th-member" title="${escHtml(m.role || "")}">${escHtml(m.name)}<br><span class="raci-member-role">${escHtml(m.role || "")}</span></th>`;
        });
        return th;
    }

    function fullRender(container, data) {
        _state.activities = data.activities;
        _state.teamMembers = data.team_members;
        _state.matrix = data.matrix || {};
        _state.validation = data.validation || {};

        // Collect available phases from activities
        const phases = [...new Set(data.activities.map((a) => a.sap_activate_phase).filter(Boolean))]
            .sort((a, b) => SAP_PHASE_ORDER.indexOf(a) - SAP_PHASE_ORDER.indexOf(b));

        const phaseFilter = container.querySelector(".raci-filter-phase");
        if (phaseFilter) {
            const saved = phaseFilter.value;
            phaseFilter.innerHTML = buildFilterOptions(phases);
            phaseFilter.value = saved;
        }

        // Update header row
        const thead = container.querySelector(".raci-matrix-thead tr");
        if (thead) thead.innerHTML = buildHeaderRow(data.team_members);

        renderMatrix(container);
        renderValidationBanners(container, _state.validation);
    }

    // ------------------------------------------------------------------
    // Event handlers
    // ------------------------------------------------------------------

    function onCellClick(e) {
        const cell = e.currentTarget;
        const activityId = parseInt(cell.dataset.activityId, 10);
        const memberId = parseInt(cell.dataset.memberId, 10);
        const currentRole = cell.dataset.role || null;
        const newRole = nextRole(currentRole || null);

        // Optimistic UI update
        const color = newRole ? ROLE_COLORS[newRole] : null;
        cell.textContent = newRole || "";
        cell.dataset.role = newRole || "";
        cell.style.cssText = color
            ? `background:${color.bg};color:${color.text};cursor:pointer;`
            : "cursor:pointer;";

        // Persist to API
        putEntry(_state.programId, activityId, memberId, newRole).then((result) => {
            // Update local matrix state
            const aKey = String(activityId);
            const mKey = String(memberId);
            if (!_state.matrix[aKey]) _state.matrix[aKey] = {};
            if (newRole) {
                _state.matrix[aKey][mKey] = newRole;
            } else {
                delete _state.matrix[aKey][mKey];
            }
            // Re-validate banners
            fetchValidationBanners();
        }).catch((err) => {
            // Revert on error
            const revertColor = currentRole ? ROLE_COLORS[currentRole] : null;
            cell.textContent = currentRole || "";
            cell.dataset.role = currentRole || "";
            cell.style.cssText = revertColor
                ? `background:${revertColor.bg};color:${revertColor.text};cursor:pointer;`
                : "cursor:pointer;";
            alert(`Hata: ${err.message}`);
        });
    }

    function fetchValidationBanners() {
        const container = document.getElementById("mainContent");
        if (!container || !_state.programId) return;
        apiFetch(`/api/v1/programs/${_state.programId}/raci/validate`).then((v) => {
            _state.validation = v;
            renderValidationBanners(container, v);
        }).catch(() => {}); // non-fatal — banners just won't update
    }

    // ------------------------------------------------------------------
    // Public render entry point
    // ------------------------------------------------------------------

    function render(container) {
        if (!container) return;

        const _prog = typeof App !== "undefined" && App.getActiveProgram && App.getActiveProgram();
        const programId = _prog && (_prog.id || _prog);
        if (!programId) {
            container.innerHTML = `<div class="raci-no-program">
                <p>Lütfen önce bir program seçin.</p>
            </div>`;
            return;
        }

        _state.programId = typeof programId === "object" ? programId.id : programId;
        _state.loading = true;

        container.innerHTML = `
<div class="raci-view">
    <div class="raci-header">
        <h2 class="raci-title">RACI Matris</h2>
        <div class="raci-toolbar">
            <select class="raci-filter-phase" title="Faza göre filtrele">
                <option value="">Tüm Fazlar</option>
            </select>
            <button class="btn btn-secondary btn-sm raci-btn-import" type="button">
                📥 SAP Şablonunu Yükle
            </button>
            <button class="btn btn-secondary btn-sm raci-btn-refresh" type="button">
                🔄 Yenile
            </button>
        </div>
    </div>

    <div class="raci-legend">
        <span class="raci-legend-item" style="background:#3b82f6;color:#fff;">R</span> Responsible &nbsp;
        <span class="raci-legend-item" style="background:#ef4444;color:#fff;">A</span> Accountable &nbsp;
        <span class="raci-legend-item" style="background:#22c55e;color:#fff;">C</span> Consulted &nbsp;
        <span class="raci-legend-item" style="background:#9ca3af;color:#fff;">I</span> Informed &nbsp;
        <small style="color:#6b7280;">Hücreye tıklayarak rol atayın/değiştirin (R→A→C→I→Boş)</small>
    </div>

    <div class="raci-validation-banners"></div>

    <div class="raci-table-wrapper">
        <table class="raci-table">
            <thead class="raci-matrix-thead"><tr></tr></thead>
            <tbody class="raci-matrix-tbody">
                <tr><td colspan="99" class="raci-loading">Yükleniyor…</td></tr>
            </tbody>
        </table>
    </div>
</div>

<style>
.raci-view { padding: 1rem; }
.raci-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:.75rem; }
.raci-title { font-size:1.25rem; font-weight:600; margin:0; }
.raci-toolbar { display:flex; gap:.5rem; align-items:center; flex-wrap:wrap; }
.raci-filter-phase { padding:.25rem .5rem; border:1px solid #d1d5db; border-radius:.25rem; font-size:.875rem; }
.raci-legend { display:flex; align-items:center; gap:.25rem; margin-bottom:.5rem; font-size:.8rem; flex-wrap:wrap; }
.raci-legend-item { display:inline-block; padding:.1rem .4rem; border-radius:.25rem; font-weight:700; font-size:.85rem; }
.raci-validation-banners { margin-bottom:.5rem; }
.raci-warning { padding:.4rem .75rem; border-radius:.25rem; margin-bottom:.25rem; font-size:.85rem; }
.raci-warning--yellow { background:#fef9c3; color:#854d0e; border:1px solid #fde68a; }
.raci-warning--red { background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }
.raci-table-wrapper { overflow-x:auto; }
.raci-table { border-collapse:collapse; min-width:100%; font-size:.8rem; }
.raci-table th, .raci-table td { border:1px solid #e5e7eb; padding:.3rem .5rem; text-align:center; white-space:nowrap; }
.raci-th-activity { text-align:left; min-width:200px; max-width:260px; background:#f9fafb; }
.raci-th-member { background:#f9fafb; font-size:.75rem; max-width:90px; }
.raci-member-role { font-weight:400; color:#6b7280; font-size:.7rem; }
.raci-activity-name { text-align:left; max-width:260px; overflow:hidden; text-overflow:ellipsis; }
.raci-phase-header td { background:#e0e7ff; color:#3730a3; font-weight:700; font-size:.75rem; padding:.2rem .5rem; letter-spacing:.05em; text-align:left; }
.raci-cell { min-width:36px; font-weight:700; transition:opacity .1s; }
.raci-cell:hover { opacity:.8; }
.raci-loading, .raci-empty { color:#9ca3af; font-style:italic; padding:1rem; }
.raci-no-program { padding:2rem; text-align:center; color:#6b7280; }
.btn-sm { padding:.25rem .6rem; font-size:.8rem; }
</style>`;

        // Wire up filter
        const phaseSelect = container.querySelector(".raci-filter-phase");
        phaseSelect && phaseSelect.addEventListener("change", () => {
            _state.filterPhase = phaseSelect.value;
            fetchMatrix(_state.programId, _state.filterPhase, _state.filterWorkstream)
                .then((data) => fullRender(container, data))
                .catch((err) => {
                    container.querySelector(".raci-matrix-tbody").innerHTML =
                        `<tr><td colspan="99" style="color:red;padding:1rem;">Hata: ${escHtml(err.message)}</td></tr>`;
                });
        });

        // Wire up import button
        const importBtn = container.querySelector(".raci-btn-import");
        importBtn && importBtn.addEventListener("click", () => {
            importBtn.disabled = true;
            importBtn.textContent = "Yükleniyor…";
            importTemplate(_state.programId)
                .then((result) => {
                    if (result.created === 0) {
                        alert("Tüm SAP şablon aktiviteleri zaten mevcut.");
                    } else {
                        alert(`${result.created} aktivite eklendi.`);
                    }
                    return fetchMatrix(_state.programId, _state.filterPhase, _state.filterWorkstream);
                })
                .then((data) => fullRender(container, data))
                .catch((err) => alert(`Hata: ${err.message}`))
                .finally(() => {
                    importBtn.disabled = false;
                    importBtn.textContent = "📥 SAP Şablonunu Yükle";
                });
        });

        // Wire up refresh button
        const refreshBtn = container.querySelector(".raci-btn-refresh");
        refreshBtn && refreshBtn.addEventListener("click", () => load());

        function load() {
            fetchMatrix(_state.programId, _state.filterPhase, _state.filterWorkstream)
                .then((data) => fullRender(container, data))
                .catch((err) => {
                    container.querySelector(".raci-matrix-tbody").innerHTML =
                        `<tr><td colspan="99" style="color:red;padding:1rem;">Yüklenemedi: ${escHtml(err.message)}</td></tr>`;
                });
        }

        load();
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------
    return { render };
})();
