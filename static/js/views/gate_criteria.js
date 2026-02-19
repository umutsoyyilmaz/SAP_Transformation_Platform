/**
 * F12 — Entry/Exit Criteria Engine & Go/No-Go Scorecard
 *
 * Tabs: Gate Criteria | Evaluation | Scorecard
 */
(function () {
    "use strict";

    const API = "/api/v1";

    /* ── helpers ──────────────────────────────────────────── */
    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }
    function html(tag, attrs, children) {
        const el = document.createElement(tag);
        if (attrs) Object.entries(attrs).forEach(([k, v]) => {
            if (k === "className") el.className = v;
            else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
            else el.setAttribute(k, v);
        });
        if (typeof children === "string") el.textContent = children;
        else if (Array.isArray(children)) children.forEach(c => c && el.appendChild(c));
        return el;
    }

    async function api(method, path, body) {
        const opts = { method, headers: { "Content-Type": "application/json" } };
        if (body) opts.body = JSON.stringify(body);
        const r = await fetch(API + path, opts);
        return r.json();
    }

    /* ── state ────────────────────────────────────────────── */
    let currentTab = "criteria";
    let programId = null;

    /* ── render root ──────────────────────────────────────── */
    function render(container) {
        programId = window.__currentProgramId || 1;
        container.innerHTML = "";

        const header = html("div", { className: "gc-header" }, [
            html("h2", {}, "Entry / Exit Criteria & Go/No-Go"),
            html("div", { className: "gc-tabs" }, [
                tabBtn("criteria", "Gate Criteria"),
                tabBtn("evaluation", "Evaluation"),
                tabBtn("scorecard", "Scorecard"),
            ]),
        ]);
        container.appendChild(header);

        const body = html("div", { id: "gc-body", className: "gc-body" });
        container.appendChild(body);
        renderTab();
    }

    function tabBtn(id, label) {
        return html("button", {
            className: "gc-tab" + (currentTab === id ? " active" : ""),
            onClick: () => { currentTab = id; renderTab(); }
        }, label);
    }

    function renderTab() {
        const body = $("#gc-body");
        if (!body) return;
        body.innerHTML = '<div class="gc-loading">Loading…</div>';
        if (currentTab === "criteria") renderCriteria(body);
        else if (currentTab === "evaluation") renderEvaluation(body);
        else if (currentTab === "scorecard") renderScorecard(body);
    }

    /* ── 1. Gate Criteria tab ─────────────────────────────── */
    async function renderCriteria(container) {
        const data = await api("GET", `/programs/${programId}/gate-criteria`);
        container.innerHTML = "";

        const toolbar = html("div", { className: "gc-toolbar" }, [
            html("button", { className: "btn btn-primary", onClick: () => showCriteriaModal() }, "+ New Criterion"),
        ]);
        container.appendChild(toolbar);

        if (!data.items || data.items.length === 0) {
            container.appendChild(html("p", { className: "gc-empty" }, "No gate criteria defined. Create one to get started."));
            return;
        }

        const table = html("table", { className: "gc-table" });
        const thead = html("thead", {}, [
            html("tr", {}, [
                html("th", {}, "Name"),
                html("th", {}, "Gate Type"),
                html("th", {}, "Criteria"),
                html("th", {}, "Condition"),
                html("th", {}, "Blocking"),
                html("th", {}, "Active"),
                html("th", {}, "Actions"),
            ])
        ]);
        table.appendChild(thead);

        const tbody = html("tbody");
        data.items.forEach(c => {
            tbody.appendChild(html("tr", {}, [
                html("td", {}, c.name),
                html("td", {}, html("span", { className: "gc-badge gc-badge--" + c.gate_type }, c.gate_type.replace("_", " "))),
                html("td", {}, c.criteria_type),
                html("td", {}, `${c.operator} ${c.threshold}`),
                html("td", {}, c.is_blocking ? "🔒 Yes" : "⚠️ No"),
                html("td", {}, c.is_active ? "✅" : "❌"),
                html("td", {}, [
                    html("button", { className: "btn btn-sm", onClick: () => showCriteriaModal(c) }, "Edit"),
                    html("button", { className: "btn btn-sm btn-danger", onClick: () => deleteCriteria(c.id) }, "Del"),
                ]),
            ]));
        });
        table.appendChild(tbody);
        container.appendChild(table);
    }

    async function showCriteriaModal(existing) {
        const isEdit = !!existing;
        const modal = html("div", { className: "gc-modal-overlay", onClick: (e) => { if (e.target === modal) modal.remove(); } });
        const form = html("div", { className: "gc-modal" });
        form.innerHTML = `
            <h3>${isEdit ? "Edit" : "New"} Gate Criterion</h3>
            <label>Name<input id="gc-name" value="${existing?.name || ""}" maxlength="100"></label>
            <label>Gate Type
                <select id="gc-gate-type">
                    <option value="cycle_exit" ${existing?.gate_type === "cycle_exit" ? "selected" : ""}>Cycle Exit</option>
                    <option value="plan_exit" ${existing?.gate_type === "plan_exit" ? "selected" : ""}>Plan Exit</option>
                    <option value="release_gate" ${existing?.gate_type === "release_gate" ? "selected" : ""}>Release Gate</option>
                </select>
            </label>
            <label>Criteria Type
                <select id="gc-criteria-type">
                    <option value="pass_rate" ${existing?.criteria_type === "pass_rate" ? "selected" : ""}>Pass Rate</option>
                    <option value="defect_count" ${existing?.criteria_type === "defect_count" ? "selected" : ""}>Defect Count</option>
                    <option value="coverage" ${existing?.criteria_type === "coverage" ? "selected" : ""}>Coverage</option>
                    <option value="execution_complete" ${existing?.criteria_type === "execution_complete" ? "selected" : ""}>Execution Complete</option>
                    <option value="approval_complete" ${existing?.criteria_type === "approval_complete" ? "selected" : ""}>Approval Complete</option>
                    <option value="sla_compliance" ${existing?.criteria_type === "sla_compliance" ? "selected" : ""}>SLA Compliance</option>
                    <option value="custom" ${existing?.criteria_type === "custom" ? "selected" : ""}>Custom</option>
                </select>
            </label>
            <label>Operator
                <select id="gc-operator">
                    <option value=">=" ${existing?.operator === ">=" ? "selected" : ""}>>=</option>
                    <option value="<=" ${existing?.operator === "<=" ? "selected" : ""}><=</option>
                    <option value="==" ${existing?.operator === "==" ? "selected" : ""}>=</option>
                    <option value=">" ${existing?.operator === ">" ? "selected" : ""}>></option>
                    <option value="<" ${existing?.operator === "<" ? "selected" : ""}><</option>
                </select>
            </label>
            <label>Threshold<input id="gc-threshold" value="${existing?.threshold || "0"}" maxlength="50"></label>
            <label><input type="checkbox" id="gc-blocking" ${existing?.is_blocking !== false ? "checked" : ""}> Blocking</label>
            <label><input type="checkbox" id="gc-active" ${existing?.is_active !== false ? "checked" : ""}> Active</label>
            <div class="gc-modal-actions">
                <button class="btn btn-primary" id="gc-save">Save</button>
                <button class="btn" id="gc-cancel">Cancel</button>
            </div>`;
        modal.appendChild(form);
        document.body.appendChild(modal);

        $("#gc-cancel", form).onclick = () => modal.remove();
        $("#gc-save", form).onclick = async () => {
            const payload = {
                name: $("#gc-name", form).value,
                gate_type: $("#gc-gate-type", form).value,
                criteria_type: $("#gc-criteria-type", form).value,
                operator: $("#gc-operator", form).value,
                threshold: $("#gc-threshold", form).value,
                is_blocking: $("#gc-blocking", form).checked,
                is_active: $("#gc-active", form).checked,
            };
            if (isEdit) {
                await api("PUT", `/gate-criteria/${existing.id}`, payload);
            } else {
                await api("POST", `/programs/${programId}/gate-criteria`, payload);
            }
            modal.remove();
            renderTab();
        };
    }

    async function deleteCriteria(id) {
        if (!confirm("Delete this criterion and all its evaluations?")) return;
        await api("DELETE", `/gate-criteria/${id}`);
        renderTab();
    }

    /* ── 2. Evaluation tab ────────────────────────────────── */
    async function renderEvaluation(container) {
        container.innerHTML = "";

        const panel = html("div", { className: "gc-eval-panel" });
        panel.innerHTML = `
            <h3>Run Gate Evaluation</h3>
            <div class="gc-eval-form">
                <label>Gate Type
                    <select id="gc-eval-gate">
                        <option value="cycle_exit">Cycle Exit</option>
                        <option value="plan_exit">Plan Exit</option>
                        <option value="release_gate">Release Gate</option>
                    </select>
                </label>
                <label>Entity ID<input id="gc-eval-eid" type="number" value="1" min="1"></label>
                <button class="btn btn-primary" id="gc-eval-run">Evaluate Now</button>
            </div>
            <div id="gc-eval-results"></div>`;
        container.appendChild(panel);

        $("#gc-eval-run", panel).onclick = async () => {
            const gateType = $("#gc-eval-gate", panel).value;
            const eid = parseInt($("#gc-eval-eid", panel).value, 10);
            let result;
            if (gateType === "cycle_exit") {
                result = await api("POST", `/testing/cycles/${eid}/evaluate-exit`, { program_id: programId });
            } else if (gateType === "plan_exit") {
                result = await api("POST", `/testing/plans/${eid}/evaluate-exit`, { program_id: programId });
            } else {
                result = await api("POST", `/programs/${programId}/evaluate-release`, { entity_id: eid });
            }
            showEvalResults(result);
        };
    }

    function showEvalResults(result) {
        const box = $("#gc-eval-results");
        if (!box) return;
        box.innerHTML = "";

        const statusClass = result.can_proceed ? (result.all_passed ? "go" : "warning") : "blocked";
        const banner = html("div", { className: "gc-result-banner gc-result--" + statusClass }, [
            html("span", { className: "gc-result-icon" }, result.can_proceed ? (result.all_passed ? "✅" : "⚠️") : "🚫"),
            html("span", {}, result.summary || "Evaluation complete"),
        ]);
        box.appendChild(banner);

        if (result.results && result.results.length) {
            const table = html("table", { className: "gc-table gc-result-table" });
            const thead = html("thead", {}, [
                html("tr", {}, [
                    html("th", {}, "Criterion"),
                    html("th", {}, "Type"),
                    html("th", {}, "Condition"),
                    html("th", {}, "Actual"),
                    html("th", {}, "Result"),
                    html("th", {}, "Blocking"),
                ])
            ]);
            table.appendChild(thead);

            const tbody = html("tbody");
            result.results.forEach(r => {
                tbody.appendChild(html("tr", { className: r.is_passed ? "" : "gc-row-fail" }, [
                    html("td", {}, r.criteria_name),
                    html("td", {}, r.criteria_type),
                    html("td", {}, r.threshold),
                    html("td", {}, String(r.actual)),
                    html("td", {}, r.is_passed ? "✅ PASS" : "❌ FAIL"),
                    html("td", {}, r.is_blocking ? "🔒" : "—"),
                ]));
            });
            table.appendChild(tbody);
            box.appendChild(table);
        }
    }

    /* ── 3. Scorecard tab ─────────────────────────────────── */
    async function renderScorecard(container) {
        container.innerHTML = "";

        const panel = html("div", { className: "gc-score-panel" });
        panel.innerHTML = `
            <h3>Go / No-Go Scorecard</h3>
            <div class="gc-score-form">
                <label>Entity Type
                    <select id="gc-sc-type">
                        <option value="test_cycle">Test Cycle</option>
                        <option value="test_plan">Test Plan</option>
                        <option value="release">Release</option>
                    </select>
                </label>
                <label>Entity ID<input id="gc-sc-eid" type="number" value="1" min="1"></label>
                <button class="btn btn-primary" id="gc-sc-load">Load Scorecard</button>
            </div>
            <div id="gc-sc-results"></div>`;
        container.appendChild(panel);

        $("#gc-sc-load", panel).onclick = async () => {
            const etype = $("#gc-sc-type", panel).value;
            const eid = parseInt($("#gc-sc-eid", panel).value, 10);
            const data = await api("GET", `/gate-scorecard/${etype}/${eid}`);
            showScorecard(data);
        };
    }

    function showScorecard(data) {
        const box = $("#gc-sc-results");
        if (!box) return;
        box.innerHTML = "";

        if (data.status === "not_evaluated") {
            box.appendChild(html("p", { className: "gc-empty" }, "No evaluations found. Run an evaluation first."));
            return;
        }

        const statusMap = { go: "GO ✅", warning: "WARNING ⚠️", blocked: "NO-GO 🚫" };
        const banner = html("div", { className: "gc-scorecard-banner gc-sc--" + data.status }, [
            html("h2", {}, statusMap[data.status] || data.status),
            html("p", {}, `${data.passed_count}/${data.total_count} criteria passed`),
        ]);
        box.appendChild(banner);

        if (data.criteria && data.criteria.length) {
            const list = html("div", { className: "gc-scorecard-list" });
            data.criteria.forEach(c => {
                list.appendChild(html("div", { className: "gc-sc-item " + (c.is_passed ? "gc-sc-pass" : "gc-sc-fail") }, [
                    html("div", { className: "gc-sc-indicator" }, c.is_passed ? "✅" : "❌"),
                    html("div", { className: "gc-sc-details" }, [
                        html("strong", {}, c.criteria_name),
                        html("span", {}, ` (${c.criteria_type}) — Actual: ${c.actual_value}`),
                        c.notes ? html("small", {}, c.notes) : null,
                    ]),
                    html("div", { className: "gc-sc-blocking" }, c.is_blocking ? "🔒 Blocking" : ""),
                ]));
            });
            box.appendChild(list);
        }
    }

    /* ── expose ───────────────────────────────────────────── */
    window.GateCriteriaView = { render };
})();
