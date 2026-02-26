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
    function renderSkeleton(container) {
        container.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Program Timeline' }])}
                <h2 class="pg-view-title">Program Timeline</h2>
            </div>
            <div class="skeleton" style="height:48px;margin-bottom:12px;border-radius:8px"></div>
            <div class="skeleton" style="height:320px;border-radius:8px"></div>
        `;
    }

    // ------------------------------------------------------------------
    // Error state
    // ------------------------------------------------------------------
    function renderError(container, msg) {
        container.innerHTML = PGEmptyState.html({ icon: 'warning', title: 'Timeline unavailable', description: escHtml(msg), action: { label: 'Retry', onclick: "TimelineView.render(document.getElementById('mainContent'))" } });
    }

    // ------------------------------------------------------------------
    // No-program guard
    // ------------------------------------------------------------------
    function renderNoProgram(container) {
        container.innerHTML = PGEmptyState.html({ icon: 'programs', title: 'No program selected', description: 'Select a program from the Programs list to view its timeline.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
    }

    // ------------------------------------------------------------------
    // Main render
    // ------------------------------------------------------------------
    function render(container) {
        if (!container) return;

        const _prog = typeof App !== 'undefined' && App.getActiveProgram && App.getActiveProgram();
        const programId = _prog && (_prog.id || _prog);
        if (!programId) {
            renderNoProgram(container);
            return;
        }

        renderSkeleton(container);

        apiFetch(`/api/v1/programs/${programId}/timeline`)
            .then((data) => _renderTimeline(container, data))
            .catch((err) => renderError(container, err.message || String(err)));
    }

    // ------------------------------------------------------------------
    // Full timeline render after data fetched
    // ------------------------------------------------------------------
    function _renderTimeline(container, data) {
        const { program, phases, sprints, milestones, today } = data;

        const delayedPhases = phases.filter((p) => p.color === COLOR_DELAYED);
        const hasAnyDate    = phases.some((p) => p.start_date && p.end_date);

        // ── Summary bar ─────────────────────────────────────────────────
        const summaryHtml = `
            <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px">
                <div style="font-size:22px;font-weight:700">${escHtml(program.name)} — Timeline</div>
                ${
                    program.start_date
                        ? `<span style="color:var(--sap-text-secondary);font-size:13px">
                            📅 ${escHtml(program.start_date)} → ${escHtml(program.end_date || "TBD")}
                           </span>`
                        : ""
                }
                ${
                    delayedPhases.length
                        ? `<span class="badge badge-danger">⚠ ${delayedPhases.length} phase${delayedPhases.length > 1 ? "s" : ""} delayed</span>`
                        : ""
                }
                <span style="margin-left:auto;color:var(--sap-text-secondary);font-size:13px">Today: ${escHtml(today)}</span>
                <button class="btn btn-secondary btn-sm" onclick="App.navigate('programs')">← Back to Programs</button>
            </div>
        `;

        // ── Gantt section ────────────────────────────────────────────────
        let ganttHtml;
        if (!hasAnyDate) {
            ganttHtml = `
                <div class="card" style="padding:24px;text-align:center;color:var(--sap-text-secondary)">
                    <div style="font-size:32px;margin-bottom:8px">📅</div>
                    <div style="font-weight:600">No phase dates set yet</div>
                    <div style="font-size:13px;margin-top:4px">
                        Add start and end dates to phases to see the Gantt chart.
                    </div>
                </div>
            `;
        } else {
            ganttHtml = `
                <div class="card" style="overflow-x:auto;padding:0" id="timelineGanttCard">
                    <div id="timelineGantt" style="min-width:600px;padding:16px 0"></div>
                </div>
            `;
        }

        // ── Phase table ──────────────────────────────────────────────────
        const phaseRowsHtml = phases
            .map(
                (p) => `
                <tr>
                    <td>
                        <span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:${escHtml(p.color)};margin-right:6px;vertical-align:middle"></span>
                        ${escHtml(p.name)}
                    </td>
                    <td>${escHtml(p.start_date || "—")}</td>
                    <td>${escHtml(p.end_date || "—")}</td>
                    <td>${statusBadge(p.status)}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px">
                            <div style="flex:1;background:var(--bg-secondary,#f1f5f9);border-radius:4px;height:8px;min-width:60px">
                                <div style="width:${p.completion_pct || 0}%;background:${escHtml(p.color)};height:8px;border-radius:4px"></div>
                            </div>
                            <span style="font-size:12px;color:var(--sap-text-secondary)">${p.completion_pct || 0}%</span>
                        </div>
                    </td>
                    <td style="font-size:12px;color:var(--sap-text-secondary)">${p.gates.length} gate${p.gates.length !== 1 ? "s" : ""}</td>
                </tr>
            `
            )
            .join("");

        const phaseTableHtml = `
            <div class="card" style="margin-top:16px">
                <div style="font-weight:600;margin-bottom:12px">Phases (${phases.length})</div>
                ${
                    phases.length
                        ? `<table class="data-table" aria-label="Program phases" style="font-size:13px">
                            <thead>
                                <tr>
                                    <th>Phase</th><th>Start</th><th>End</th>
                                    <th>Status</th><th style="min-width:120px">Progress</th><th>Gates</th>
                                </tr>
                            </thead>
                            <tbody>${phaseRowsHtml}</tbody>
                          </table>`
                        : `<div style="color:var(--sap-text-secondary);text-align:center;padding:24px">No phases defined yet.</div>`
                }
            </div>
        `;

        // ── Milestones / Gates ───────────────────────────────────────────
        const milestoneRowsHtml = milestones
            .map(
                (m) => `
                <tr>
                    <td>◆ ${escHtml(m.name)}</td>
                    <td>${escHtml(m.date)}</td>
                    <td>${statusBadge(m.status)}</td>
                </tr>
            `
            )
            .join("");

        const milestonesHtml =
            milestones.length
                ? `<div class="card" style="margin-top:16px">
                    <div style="font-weight:600;margin-bottom:12px">Gate Milestones (${milestones.length})</div>
                    <table class="data-table" aria-label="Gate milestones" style="font-size:13px">
                        <thead><tr><th>Gate</th><th>Planned Date</th><th>Status</th></tr></thead>
                        <tbody>${milestoneRowsHtml}</tbody>
                    </table>
                   </div>`
                : "";

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
                ? `<div class="card" style="margin-top:16px">
                    <div style="font-weight:600;margin-bottom:12px">Sprints (${sprints.length})</div>
                    <table class="data-table" aria-label="Program sprints" style="font-size:13px">
                        <thead>
                            <tr>
                                <th>Sprint</th><th>Start</th><th>End</th>
                                <th>Status</th><th>Capacity (pts)</th><th>Velocity (pts)</th>
                            </tr>
                        </thead>
                        <tbody>${sprintRowsHtml}</tbody>
                    </table>
                   </div>`
                : "";

        // ── Assemble page ────────────────────────────────────────────────
        container.innerHTML = `
            <div style="padding:16px 24px;max-width:1400px">
                ${summaryHtml}
                ${ganttHtml}
                ${phaseTableHtml}
                ${milestonesHtml}
                ${sprintsHtml}
            </div>
        `;

        // ── Render frappe-gantt if dates exist and library loaded ────────
        if (hasAnyDate && typeof Gantt !== "undefined") {
            _renderGantt(phases, today);
        } else if (hasAnyDate) {
            // Library not loaded yet — ignore gracefully
            const ganttWrap = document.getElementById("timelineGantt");
            if (ganttWrap) {
                ganttWrap.innerHTML = `<div style="padding:16px;color:var(--sap-text-secondary);text-align:center;font-size:13px">
                    Gantt library not available — ensure frappe-gantt CDN is loaded.
                </div>`;
            }
        }
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
            ganttWrap.innerHTML = `<div style="padding:16px;color:var(--sap-text-secondary);text-align:center">
                No phases with date ranges to display.
            </div>`;
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
            ganttWrap.innerHTML = `<div style="padding:16px;color:var(--sap-text-secondary);text-align:center;font-size:13px">
                Gantt chart could not be rendered: ${escHtml(String(err.message || err))}
            </div>`;
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
    return { render };
})();
