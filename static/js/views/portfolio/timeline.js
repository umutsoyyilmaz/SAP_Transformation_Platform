/**
 * Timeline View — S3-02 · FDD-F04: Project Timeline Visualization
 *
 * Renders a Gantt chart of SAP Activate phases + a sprint table for the
 * currently active program, using the frappe-gantt (MIT) library.
 *
 * Entry point: TimelineView.render(containerEl)
 */
const TimelineView = (() => {
    "use strict";

    let _lastContainer = null;
    let _lastOpts = {};
    let _programId = null;
    let _timelineData = null;
    let _milestoneFilters = { source: "all", status: "all", search: "" };
    const PLATFORM_PERMISSION_SOURCE = "platformPermissions";

    // ------------------------------------------------------------------
    // Local helpers
    // ------------------------------------------------------------------

    function escHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function apiFetch(url) {
        return fetch(url).then((r) => {
            if (!r.ok) return Promise.reject(new Error(`HTTP ${r.status}: ${url}`));
            return r.json();
        });
    }

    // ------------------------------------------------------------------
    // Color helpers — keep in sync with program_bp.py _PHASE_COLORS
    // ------------------------------------------------------------------
    const PHASE_COLORS = {
        discover: "#6366f1",
        prepare:  "#f59e0b",
        explore:  "#3b82f6",
        realize:  "#8b5cf6",
        deploy:   "#ef4444",
        run:      "#22c55e",
    };
    const COLOR_COMPLETED = "#9ca3af";
    const COLOR_DELAYED   = "#ef4444";
    const COLOR_DEFAULT   = "#6366f1";

    function phaseColor(phase) {
        if (phase.status === "completed" || phase.status === "skipped") return COLOR_COMPLETED;
        if (phase.color) return phase.color; // server already computed it
        return PHASE_COLORS[phase.sap_activate_phase] || COLOR_DEFAULT;
    }

    function phaseTone(phase) {
        if (phase.status === "completed" || phase.status === "skipped") return "completed";
        if (phase.color === COLOR_DELAYED) return "delayed";
        return phase.sap_activate_phase || "default";
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

    function statusBadge(status) {
        const map = {
            not_started: { cls: "secondary", label: "Not Started" },
            in_progress: { cls: "info",      label: "In Progress" },
            completed:   { cls: "success",   label: "Completed"   },
            skipped:     { cls: "secondary", label: "Skipped"     },
            planning:    { cls: "secondary", label: "Planning"    },
            active:      { cls: "info",      label: "Active"      },
            cancelled:   { cls: "danger",    label: "Cancelled"   },
        };
        const { cls, label } = map[status] || { cls: "secondary", label: status };
        return `<span class="badge badge-${cls}">${escHtml(label)}</span>`;
    }

    // Apply per-task colors to frappe-gantt SVG bars after render.
    // frappe-gantt places each task bar in a group with data-id matching the task id.
    function applyBarColors(ganttWrap, phaseTasks) {
        phaseTasks.forEach(({ id, color }) => {
            const group = ganttWrap.querySelector(`.bar-group[data-id="${CSS.escape(id)}"]`);
            if (!group) return;
            // Try multiple selectors used across frappe-gantt versions
            [".bar", ".bar-inner"].forEach((sel) => {
                const el = group.querySelector(sel);
                if (el) {
                    el.style.fill = color;
                    el.setAttribute("fill", color);
                }
            });
        });
    }

    // ------------------------------------------------------------------
    // Skeleton / loading state
    // ------------------------------------------------------------------
    function renderSkeleton(container, opts = {}) {
        if (opts.embedded) {
            container.innerHTML = `
                <div class="timeline-skeleton timeline-skeleton--hero skeleton"></div>
                <div class="timeline-skeleton timeline-skeleton--board skeleton"></div>
            `;
            return;
        }
        container.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Program Timeline' }])}
                <h2 class="pg-view-title">Program Timeline</h2>
            </div>
            <div class="timeline-skeleton timeline-skeleton--hero skeleton"></div>
            <div class="timeline-skeleton timeline-skeleton--board skeleton"></div>
        `;
    }

    // ------------------------------------------------------------------
    // Error state
    // ------------------------------------------------------------------
    function renderError(container, msg, opts = {}) {
        if (opts.embedded) {
            container.innerHTML = `<div class="section-card timeline-empty-card timeline-empty-card--error">${escHtml(msg)}</div>`;
            return;
        }
        container.innerHTML = PGEmptyState.html({ icon: 'warning', title: 'Timeline unavailable', description: escHtml(msg), action: { label: 'Retry', onclick: "TimelineView.render(document.getElementById('mainContent'))" } });
    }

    // ------------------------------------------------------------------
    // No-program guard
    // ------------------------------------------------------------------
    function renderNoProgram(container, opts = {}) {
        container.innerHTML = PGEmptyState.html({ icon: 'programs', title: 'No program selected', description: 'Select a program from the Programs list to view its timeline.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
    }

    function _activeProject() {
        return (typeof App !== "undefined" && App.getActiveProject) ? App.getActiveProject() : null;
    }

    function _reload() {
        if (_lastContainer) render(_lastContainer, _lastOpts);
    }

    function _milestoneTypeLabel(type) {
        const map = {
            gate: "Gate",
            program_milestone: "Milestone",
            milestone: "Milestone",
            checkpoint: "Checkpoint",
            go_live: "Go-Live",
            cutover: "Cutover",
            phase_end: "Phase End",
        };
        return map[type] || String(type || "Milestone").replace(/_/g, " ");
    }

    function _milestoneCanManage(item) {
        return item?.type === "program_milestone"
            && Number.isFinite(Number(item.record_id))
            && _canManageProgramMilestones();
    }

    function _canManageProgramMilestones() {
        return typeof RoleNav !== "undefined"
            && typeof RoleNav.canSyncInSource === "function"
            && RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, "programs.edit");
    }

    function _canDeleteProgramMilestones() {
        return typeof RoleNav !== "undefined"
            && typeof RoleNav.canSyncInSource === "function"
            && RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, "programs.delete");
    }

    async function _preloadMilestonePermissions() {
        if (typeof RoleNav === "undefined" || typeof RoleNav.preloadSource !== "function") {
            return null;
        }
        return RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE);
    }

    function _milestoneScopeLabel(item) {
        return item?.project_id ? "Project" : "Program";
    }

    function _findManagedMilestone(recordId) {
        const milestones = _timelineData?.milestones || [];
        return milestones.find((item) => Number(item.record_id) === Number(recordId) && _milestoneCanManage(item)) || null;
    }

    function _milestoneActionsHtml(item) {
        const canEdit = _milestoneCanManage(item);
        const canDelete = item?.type === "program_milestone"
            && Number.isFinite(Number(item.record_id))
            && _canDeleteProgramMilestones();
        if (!canEdit && !canDelete) {
            return `<span class="timeline-table__meta">Read only</span>`;
        }
        return `
            <div class="timeline-row-actions">
                ${canEdit ? `<button type="button" class="btn btn-secondary btn-sm" onclick="TimelineView.openMilestoneModal(${Number(item.record_id)})">Edit</button>` : ""}
                ${canDelete ? `<button type="button" class="btn btn-secondary btn-sm" onclick="TimelineView.deleteMilestone(${Number(item.record_id)})">Delete</button>` : ""}
            </div>
        `;
    }

    function _matchesMilestoneFilters(item) {
        if (_milestoneFilters.source === "gates" && item.type !== "gate") return false;
        if (_milestoneFilters.source === "manual" && item.type !== "program_milestone") return false;
        if (_milestoneFilters.status !== "all" && item.status !== _milestoneFilters.status) return false;
        const q = String(_milestoneFilters.search || "").trim().toLowerCase();
        if (q) {
            const haystack = [
                item.name,
                item.code,
                item.owner,
                _milestoneTypeLabel(item.milestone_type || item.type),
                _milestoneScopeLabel(item),
            ].filter(Boolean).join(" ").toLowerCase();
            if (!haystack.includes(q)) return false;
        }
        return true;
    }

    function _milestoneFilterToolbar(items) {
        const visible = items.length;
        return `
            <div class="discover-toolbar timeline-toolbar">
                <div class="discover-toolbar__group">
                    <input
                        type="search"
                        class="discover-toolbar__search"
                        placeholder="Search title, code, owner…"
                        value="${escHtml(_milestoneFilters.search)}"
                        oninput="TimelineView.setMilestoneFilter('search', this.value)"
                    />
                    <div class="discover-segmented">
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.source === "all" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('source', 'all')">All</button>
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.source === "gates" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('source', 'gates')">Gates</button>
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.source === "manual" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('source', 'manual')">Milestones</button>
                    </div>
                    <div class="discover-segmented">
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.status === "all" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('status', 'all')">All Statuses</button>
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.status === "planned" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('status', 'planned')">Planned</button>
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.status === "delayed" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('status', 'delayed')">Delayed</button>
                        <button type="button" class="discover-segmented__item ${_milestoneFilters.status === "completed" ? "is-active" : ""}" onclick="TimelineView.setMilestoneFilter('status', 'completed')">Completed</button>
                    </div>
                </div>
                <div class="discover-toolbar__meta">${visible} visible</div>
            </div>
        `;
    }

    function setMilestoneFilter(key, value) {
        _milestoneFilters[key] = value;
        _reload();
    }

    function openMilestoneModal(recordId = null) {
        if (!_canManageProgramMilestones()) {
            App.toast("You do not have permission to manage program milestones", "warning");
            return;
        }
        const current = recordId ? _findManagedMilestone(recordId) : null;
        const activeProject = _activeProject();
        const isProgramWide = !current?.project_id;
        const types = ["milestone", "checkpoint", "go_live", "cutover", "phase_end"];
        const statuses = ["planned", "in_progress", "completed", "delayed", "cancelled"];

        App.openModal(`
            <div class="modal timeline-milestone-modal" data-testid="timeline-milestone-modal">
                <div class="modal-header">
                    <h2>${current ? "Edit milestone" : "Create milestone"}</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                </div>
                <form onsubmit="event.preventDefault(); TimelineView.submitMilestoneForm(event, ${current ? Number(current.record_id) : 'null'})">
                    <div class="modal-body timeline-milestone-form">
                        <div class="form-group">
                            <label for="timelineMilestoneTitle">Title</label>
                            <input id="timelineMilestoneTitle" name="title" class="form-input" maxlength="300" required value="${escHtml(current?.name || "")}">
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="timelineMilestoneCode">Code</label>
                                <input id="timelineMilestoneCode" name="code" class="form-input" value="${escHtml(current?.code || "")}">
                            </div>
                            <div class="form-group">
                                <label for="timelineMilestoneType">Type</label>
                                <select id="timelineMilestoneType" name="milestone_type" class="form-input">
                                    ${types.map((type) => `<option value="${type}" ${String(current?.milestone_type || "milestone") === type ? "selected" : ""}>${escHtml(_milestoneTypeLabel(type))}</option>`).join("")}
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="timelineMilestonePlanned">Planned Date</label>
                                <input id="timelineMilestonePlanned" name="planned_date" type="date" class="form-input" value="${escHtml(current?.planned_date || current?.date || "")}">
                            </div>
                            <div class="form-group">
                                <label for="timelineMilestoneForecast">Forecast Date</label>
                                <input id="timelineMilestoneForecast" name="forecast_date" type="date" class="form-input" value="${escHtml(current?.forecast_date || "")}">
                            </div>
                            <div class="form-group">
                                <label for="timelineMilestoneActual">Actual Date</label>
                                <input id="timelineMilestoneActual" name="actual_date" type="date" class="form-input" value="${escHtml(current?.actual_date || "")}">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="timelineMilestoneStatus">Status</label>
                                <select id="timelineMilestoneStatus" name="status" class="form-input">
                                    ${statuses.map((status) => `<option value="${status}" ${String(current?.status || "planned") === status ? "selected" : ""}>${escHtml(status.replace(/_/g, " "))}</option>`).join("")}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="timelineMilestoneOwner">Owner</label>
                                <input id="timelineMilestoneOwner" name="owner" class="form-input" value="${escHtml(current?.owner || "")}">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="timelineMilestoneDescription">Description</label>
                            <textarea id="timelineMilestoneDescription" name="description" class="form-input" rows="3">${escHtml(current?.description || "")}</textarea>
                        </div>
                        <div class="form-group">
                            <label for="timelineMilestoneNotes">Notes</label>
                            <textarea id="timelineMilestoneNotes" name="notes" class="form-input" rows="3">${escHtml(current?.notes || "")}</textarea>
                        </div>
                        <div class="form-row timeline-milestone-form__meta">
                            <label class="timeline-milestone-check">
                                <input type="checkbox" name="is_critical_path" ${current?.is_critical_path ? "checked" : ""}>
                                <span>Critical path</span>
                            </label>
                            <label class="timeline-milestone-check">
                                <input type="checkbox" name="program_wide" ${isProgramWide ? "checked" : ""} ${activeProject ? "" : "disabled"}>
                                <span>${activeProject ? "Program-wide milestone" : "No active project context"}</span>
                            </label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">${current ? "Save Changes" : "Create Milestone"}</button>
                    </div>
                </form>
            </div>
        `);
    }

    async function submitMilestoneForm(event, recordId = null) {
        const form = event.target;
        const fd = new FormData(form);
        const activeProject = _activeProject();
        const payload = {
            title: String(fd.get("title") || "").trim(),
            code: String(fd.get("code") || "").trim() || null,
            description: String(fd.get("description") || "").trim() || null,
            notes: String(fd.get("notes") || "").trim() || null,
            milestone_type: fd.get("milestone_type") || "milestone",
            planned_date: fd.get("planned_date") || null,
            forecast_date: fd.get("forecast_date") || null,
            actual_date: fd.get("actual_date") || null,
            status: fd.get("status") || "planned",
            owner: String(fd.get("owner") || "").trim() || null,
            is_critical_path: fd.has("is_critical_path"),
            project_id: (fd.has("program_wide") || !activeProject) ? null : activeProject.id,
        };

        if (!payload.title) {
            App.toast("Milestone title is required", "warning");
            form.querySelector('[name="title"]')?.focus();
            return;
        }

        try {
            if (recordId) {
                await API.put(`/program-milestones/${recordId}`, payload);
                App.toast("Milestone updated", "success");
            } else {
                await API.post(`/programs/${_programId}/milestones`, payload);
                App.toast("Milestone created", "success");
            }
            App.closeModal();
            _reload();
        } catch (err) {
            App.toast(err.message || "Milestone save failed", "error");
        }
    }

    async function deleteMilestone(recordId) {
        if (!_canDeleteProgramMilestones()) {
            App.toast("You do not have permission to delete program milestones", "warning");
            return;
        }
        const milestone = _findManagedMilestone(recordId);
        const confirmed = await App.confirmDialog({
            title: "Delete milestone",
            message: `Delete ${milestone?.name || "this milestone"}?`,
            confirmLabel: "Delete",
            testId: "timeline-delete-milestone-modal",
            confirmTestId: "timeline-delete-milestone-submit",
            cancelTestId: "timeline-delete-milestone-cancel",
        });
        if (!confirmed) return;

        try {
            await API.delete(`/program-milestones/${recordId}`);
            App.toast("Milestone deleted", "success");
            _reload();
        } catch (err) {
            App.toast(err.message || "Milestone delete failed", "error");
        }
    }

    // ------------------------------------------------------------------
    // Main render
    // ------------------------------------------------------------------
    function render(container, opts = {}) {
        if (!container) return;
        _lastContainer = container;
        _lastOpts = opts;

        const _prog = typeof App !== 'undefined' && App.getActiveProgram && App.getActiveProgram();
        const programId = _prog && (_prog.id || _prog);
        _programId = programId || null;
        if (!programId) {
            renderNoProgram(container, opts);
            return;
        }

        renderSkeleton(container, opts);

        Promise.all([
            apiFetch(`/api/v1/programs/${programId}/timeline`),
            _preloadMilestonePermissions(),
        ])
            .then(([data]) => _renderTimeline(container, data, opts))
            .catch((err) => renderError(container, err.message || String(err), opts));
    }

    // ------------------------------------------------------------------
    // Full timeline render after data fetched
    // ------------------------------------------------------------------
    function _renderTimeline(container, data, opts = {}) {
        _timelineData = data;
        const { program, phases, sprints, milestones, today } = data;
        const visibleMilestones = milestones.filter(_matchesMilestoneFilters);

        const delayedPhases = phases.filter((p) => p.color === COLOR_DELAYED);
        const hasAnyDate    = phases.some((p) => p.start_date && p.end_date);
        const openMilestones = milestones.filter((item) => item.status !== "completed");
        const avgCompletion = phases.length
            ? Math.round(phases.reduce((sum, item) => sum + (item.completion_pct || 0), 0) / phases.length)
            : 0;
        const datedPhases = phases.filter((item) => item.start_date || item.end_date).length;

        const heroActions = opts.embedded
            ? `
                ${_canManageProgramMilestones() ? '<button class="pg-btn pg-btn--secondary pg-btn--sm" type="button" onclick="TimelineView.openMilestoneModal()">+ Milestone</button>' : '<span class="timeline-table__meta">Milestones are read only</span>'}
                <span class="timeline-meta-chip ${delayedPhases.length ? "timeline-meta-chip--danger" : "timeline-meta-chip--success"}">${delayedPhases.length ? `${delayedPhases.length} delayed` : "On track"}</span>
            `
            : `
                <span class="timeline-meta-chip">${escHtml(today)}</span>
                ${_canManageProgramMilestones() ? '<button class="pg-btn pg-btn--secondary pg-btn--sm" type="button" onclick="TimelineView.openMilestoneModal()">+ Milestone</button>' : '<span class="timeline-table__meta">Milestones are read only</span>'}
                <button class="btn btn-secondary btn-sm" onclick="App.navigate('programs')">Back to Programs</button>
            `;

        const summaryHtml = `
            <div class="timeline-hero">
                <div class="timeline-hero__body">
                    <div class="timeline-hero__eyebrow">Discover Schedule</div>
                    <div class="timeline-hero__title">${escHtml(program.name)} Timeline</div>
                    <p class="timeline-hero__copy">Track phase cadence, gate milestones, and sprint pacing without leaving the Discover cockpit.</p>
                </div>
                <div class="timeline-hero__meta">
                    ${program.start_date ? `<span class="timeline-meta-chip">Window ${escHtml(program.start_date)} → ${escHtml(program.end_date || "TBD")}</span>` : ""}
                    <span class="timeline-meta-chip">Today ${escHtml(today)}</span>
                    ${heroActions}
                </div>
            </div>
            <div class="discover-summary-strip timeline-summary-strip">
                ${metricCard({ value: `${avgCompletion}%`, label: "Average Completion", tone: avgCompletion >= 80 ? "success" : avgCompletion >= 50 ? "info" : "warning", sub: `${phases.length} phases tracked` })}
                ${metricCard({ value: delayedPhases.length, label: "Delayed Phases", tone: delayedPhases.length ? "warning" : "success", sub: delayedPhases.length ? "Needs replanning" : "No delay signal" })}
                ${metricCard({ value: openMilestones.length, label: "Open Gate Milestones", tone: openMilestones.length ? "info" : "default", sub: `${milestones.length} total milestones` })}
                ${metricCard({ value: sprints.length, label: "Sprints", tone: sprints.length ? "info" : "default", sub: sprints.length ? "Execution cadence defined" : "No sprint plan" })}
                ${metricCard({ value: `${datedPhases}/${phases.length}`, label: "Phases with Dates", tone: datedPhases === phases.length && phases.length ? "success" : "warning", sub: phases.length ? "Schedule completeness" : "No phases yet" })}
            </div>
        `;

        // ── Gantt section ────────────────────────────────────────────────
        let ganttHtml;
        if (!hasAnyDate) {
            ganttHtml = `
                <section class="section-card timeline-panel timeline-panel--gantt">
                    <div class="section-card__header">
                        <div class="discover-workspace-heading">
                            <h3>Phase Timeline</h3>
                            <p class="discover-section-lead">The Gantt canvas appears when phases have dated ranges.</p>
                        </div>
                    </div>
                    <div class="timeline-empty-card">
                        <div class="timeline-empty-card__icon">📅</div>
                        <div class="timeline-empty-card__title">No phase dates set yet</div>
                        <div class="timeline-empty-card__copy">
                        Add start and end dates to phases to see the Gantt chart.
                        </div>
                    </div>
                </section>
            `;
        } else {
            ganttHtml = `
                <section class="section-card timeline-panel timeline-panel--gantt">
                    <div class="section-card__header">
                        <div class="discover-workspace-heading">
                            <h3>Phase Timeline</h3>
                            <p class="discover-section-lead">Visualise current phase overlap, progress, and gate timing against today.</p>
                        </div>
                    </div>
                    <div class="timeline-gantt-card" id="timelineGanttCard">
                        <div id="timelineGantt" class="timeline-gantt-canvas"></div>
                    </div>
                </section>
            `;
        }

        // ── Phase table ──────────────────────────────────────────────────
        const phaseRowsHtml = phases
            .map(
                (p) => `
                <tr class="timeline-table__row">
                    <td class="timeline-phase-cell">
                        <span class="timeline-phase-swatch timeline-phase-swatch--${phaseTone(p)}"></span>
                        <span class="timeline-phase-name">${escHtml(p.name)}</span>
                    </td>
                    <td>${escHtml(p.start_date || "—")}</td>
                    <td>${escHtml(p.end_date || "—")}</td>
                    <td>${statusBadge(p.status)}</td>
                    <td class="timeline-progress-cell">
                        <div class="timeline-progress">
                            <div class="timeline-progress__track">
                                <div class="timeline-progress__fill timeline-progress__fill--${phaseTone(p)}" data-progress="${p.completion_pct || 0}"></div>
                            </div>
                            <span class="timeline-progress__value">${p.completion_pct || 0}%</span>
                        </div>
                    </td>
                    <td class="timeline-table__meta">${p.gates.length} gate${p.gates.length !== 1 ? "s" : ""}</td>
                </tr>
            `
            )
            .join("");

        const phaseTableHtml = `
            <section class="section-card timeline-panel">
                <div class="section-card__header">
                    <div class="discover-workspace-heading">
                        <h3>Phases (${phases.length})</h3>
                        <p class="discover-section-lead">Review duration, status, and gate density phase by phase.</p>
                    </div>
                </div>
                ${
                    phases.length
                        ? `<div class="timeline-table-wrap">
                            <table class="data-table timeline-table" aria-label="Program phases">
                                <thead>
                                    <tr>
                                        <th>Phase</th><th>Start</th><th>End</th>
                                        <th>Status</th><th class="timeline-table__progress-head">Progress</th><th>Gates</th>
                                    </tr>
                                </thead>
                                <tbody>${phaseRowsHtml}</tbody>
                            </table>
                          </div>`
                        : `<div class="timeline-empty-card"><div class="timeline-empty-card__copy">No phases defined yet.</div></div>`
                }
            </section>
        `;

        // ── Milestones / Gates ───────────────────────────────────────────
        const milestoneRowsHtml = visibleMilestones
            .map(
                (m) => `
                <tr>
                    <td class="timeline-milestone-cell">
                        <div class="timeline-milestone-cell__title">◆ ${escHtml(m.name)}</div>
                        <div class="timeline-milestone-cell__meta">
                            <span>${escHtml(_milestoneTypeLabel(m.milestone_type || m.type))}</span>
                            <span>•</span>
                            <span>${escHtml(_milestoneScopeLabel(m))}</span>
                        </div>
                    </td>
                    <td>${escHtml(m.date)}</td>
                    <td>${statusBadge(m.status)}</td>
                    <td>${_milestoneActionsHtml(m)}</td>
                </tr>
            `
            )
            .join("");

        const milestonesHtml = `<section class="section-card timeline-panel${milestones.length ? "" : " timeline-panel--compact"}">
            <div class="section-card__header">
                <div class="discover-workspace-heading">
                    <h3>Gate Milestones (${milestones.length})</h3>
                    <p class="discover-section-lead">${milestones.length ? "Upcoming steering and quality checkpoints in the schedule." : "No explicit milestones have been added yet."}</p>
                </div>
                ${_canManageProgramMilestones() ? '<button class="pg-btn pg-btn--secondary pg-btn--sm" type="button" onclick="TimelineView.openMilestoneModal()">+ New Milestone</button>' : '<span class="timeline-table__meta">Milestones are read only</span>'}
            </div>
            ${_milestoneFilterToolbar(visibleMilestones)}
            ${milestones.length
                ? `<div class="timeline-table-wrap">
                    <table class="data-table timeline-table" aria-label="Gate milestones">
                        <thead><tr><th>Milestone</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>${milestoneRowsHtml || `<tr><td colspan="4" class="timeline-table__empty">No milestones match the current filter.</td></tr>`}</tbody>
                    </table>
                </div>`
                : `<div class="timeline-empty-card timeline-empty-card--compact"><div class="timeline-empty-card__copy">Add milestone dates to track Discover exit checkpoints.</div></div>`
            }
           </section>`;

        // ── Sprint table ─────────────────────────────────────────────────
        const sprintRowsHtml = sprints
            .map(
                (s) => `
                <tr>
                    <td>${escHtml(s.name)}</td>
                    <td>${escHtml(s.start_date || "—")}</td>
                    <td>${escHtml(s.end_date || "—")}</td>
                    <td>${statusBadge(s.status)}</td>
                    <td>${s.capacity_points != null ? s.capacity_points : "—"}</td>
                    <td>${s.velocity != null ? s.velocity : "—"}</td>
                </tr>
            `
            )
            .join("");

        const sprintsHtml =
            sprints.length
                ? `<section class="section-card timeline-panel">
                    <div class="section-card__header">
                        <div class="discover-workspace-heading">
                            <h3>Sprints (${sprints.length})</h3>
                            <p class="discover-section-lead">Execution rhythm feeding the downstream delivery plan.</p>
                        </div>
                    </div>
                    <div class="timeline-table-wrap">
                        <table class="data-table timeline-table" aria-label="Program sprints">
                            <thead>
                                <tr>
                                    <th>Sprint</th><th>Start</th><th>End</th>
                                    <th>Status</th><th>Capacity (pts)</th><th>Velocity (pts)</th>
                                </tr>
                            </thead>
                            <tbody>${sprintRowsHtml}</tbody>
                        </table>
                    </div>
                   </section>`
                : `<section class="section-card timeline-panel timeline-panel--compact">
                    <div class="section-card__header">
                        <div class="discover-workspace-heading">
                            <h3>Sprints</h3>
                            <p class="discover-section-lead">No sprint plan is linked to this program yet.</p>
                        </div>
                    </div>
                    <div class="timeline-empty-card timeline-empty-card--compact"><div class="timeline-empty-card__copy">Sprint planning has not been defined.</div></div>
                   </section>`;

        // ── Assemble page ────────────────────────────────────────────────
        const contentHtml = `
            ${summaryHtml}
            ${ganttHtml}
            <div class="timeline-grid">
                ${phaseTableHtml}
                <div class="timeline-grid__stack">
                    ${milestonesHtml}
                    ${sprintsHtml}
                </div>
            </div>
        `;
        container.innerHTML = opts.embedded
            ? `
                <div class="discover-timeline-workspace timeline-shell timeline-shell--embedded" data-testid="discover-timeline-workspace">
                    ${contentHtml}
                </div>
            `
            : `
                <div class="timeline-shell timeline-shell--standalone" data-testid="timeline-page">
                    ${contentHtml}
                </div>
            `;
        hydrateTimelineDom(container);

        // ── Render frappe-gantt if dates exist and library loaded ────────
        if (hasAnyDate && typeof Gantt !== "undefined") {
            _renderGantt(phases, today);
        } else if (hasAnyDate) {
            // Library not loaded yet — ignore gracefully
            const ganttWrap = document.getElementById("timelineGantt");
            if (ganttWrap) {
                ganttWrap.innerHTML = `<div class="timeline-empty-card timeline-empty-card--compact"><div class="timeline-empty-card__copy">Gantt library not available — ensure frappe-gantt CDN is loaded.</div></div>`;
            }
        }
    }

    function hydrateTimelineDom(container) {
        container.querySelectorAll(".timeline-progress__fill").forEach((el) => {
            const pct = Number(el.dataset.progress || 0);
            el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
        });
    }

    // ------------------------------------------------------------------
    // frappe-gantt initialisation
    // ------------------------------------------------------------------
    function _renderGantt(phases, today) {
        const ganttWrap = document.getElementById("timelineGantt");
        if (!ganttWrap) return;

        // Build task list — skip phases missing both start/end dates.
        const phaseTasks = [];
        const phaseColors = [];

        // Use a safe fallback date so frappe-gantt doesn't crash.
        const fallbackStart = today;
        const fallbackEnd   = today;

        phases.forEach((p) => {
            if (!p.start_date && !p.end_date) return; // completely undated → skip

            const start = p.start_date || fallbackStart;
            // frappe-gantt requires end > start; add 1 day if equal.
            const end =
                p.end_date && p.end_date > start
                    ? p.end_date
                    : _addDays(start, 1);

            const taskId = `p${p.id}`;
            phaseTasks.push({
                id:           taskId,
                name:         p.name,
                start,
                end,
                progress:     p.completion_pct || 0,
                custom_class: `tl-phase tl-phase--${p.sap_activate_phase}${p.color === COLOR_DELAYED ? " tl-phase--delayed" : ""}`,
            });
            phaseColors.push({ id: taskId, color: p.color });
        });

        if (!phaseTasks.length) {
            ganttWrap.innerHTML = `<div class="timeline-empty-card timeline-empty-card--compact"><div class="timeline-empty-card__copy">No phases with date ranges to display.</div></div>`;
            return;
        }

        try {
            // Drag interaction is disabled (readonly timeline view).
            const gantt = new Gantt(ganttWrap, phaseTasks, {
                view_mode:          "Month",
                date_format:        "YYYY-MM-DD",
                column_width:       40,
                bar_height:         28,
                bar_corner_radius:  4,
                padding:            18,
                on_click:           () => {},   // intentionally no-op
                on_date_change:     () => {},   // drag disabled
                on_progress_change: () => {},   // drag disabled
            });

            // Apply brand colors after the SVG has been built.
            applyBarColors(ganttWrap, phaseColors);

            // Keep colors applied when user switches view mode via gantt controls.
            const observer = new MutationObserver(() => applyBarColors(ganttWrap, phaseColors));
            observer.observe(ganttWrap, { childList: true, subtree: true });

            // Store ref for potential cleanup.
            ganttWrap._gantt    = gantt;
            ganttWrap._observer = observer;
        } catch (err) {
            ganttWrap.innerHTML = `<div class="timeline-empty-card timeline-empty-card--error timeline-empty-card--compact"><div class="timeline-empty-card__copy">Gantt chart could not be rendered: ${escHtml(String(err.message || err))}</div></div>`;
        }
    }

    // ------------------------------------------------------------------
    // Date utility
    // ------------------------------------------------------------------
    function _addDays(isoDateStr, days) {
        const d = new Date(isoDateStr + "T00:00:00");
        d.setDate(d.getDate() + days);
        return d.toISOString().slice(0, 10);
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------
    return {
        render,
        openMilestoneModal,
        submitMilestoneForm,
        deleteMilestone,
        setMilestoneFilter,
    };
})();
