/**
 * SAP Transformation Platform — WR-3.4
 * Demo Flow Controller
 *
 * Manages the seamless 3-step demo flow:
 *   Step 1: Workshop Detail — review decisions
 *   Step 2: Requirements Hub — see generated requirements
 *   Step 3: Convert — convert approved requirements to WRICEF/Config
 *
 * Provides:
 *   - Breadcrumb navigation bar
 *   - Step context (which workshop we came from)
 *   - "Next Step" / "Previous Step" buttons
 *   - Auto-transition helpers
 *
 * Usage:
 *   DemoFlow.start(workshopId);      // enters step 1
 *   DemoFlow.breadcrumbHTML();        // returns breadcrumb bar HTML
 *   DemoFlow.nextStep();              // advances to next step
 *   DemoFlow.isActive();              // true when demo flow is running
 */
const DemoFlow = (() => {
    'use strict';

    const STORAGE_KEY = 'sap_demo_flow';

    const STEPS = [
        { key: 'workshop-detail', label: 'Workshop Review', icon: '📋', view: 'explore-workshop-detail' },
        { key: 'requirements',    label: 'Requirements',    icon: '📝', view: 'explore-requirements' },
        { key: 'convert',         label: 'Convert & Trace', icon: '🔄', view: 'explore-requirements' },
    ];

    // ── State ───────────────────────────────────────────────────────

    function _getState() {
        try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null'); } catch { return null; }
    }

    function _setState(state) {
        if (state) {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } else {
            sessionStorage.removeItem(STORAGE_KEY);
        }
    }

    function isActive() {
        return !!_getState();
    }

    function currentStep() {
        const s = _getState();
        return s ? s.step : -1;
    }

    function getWorkshopId() {
        const s = _getState();
        return s ? s.workshopId : null;
    }

    // ── Flow control ────────────────────────────────────────────────

    /**
     * Start the demo flow at Step 1 (Workshop Detail).
     * @param {string|number} workshopId
     */
    function start(workshopId) {
        _setState({ step: 0, workshopId: String(workshopId) });
        // Set the workshop for workshop detail view
        localStorage.setItem('exp_selected_workshop', workshopId);
        App.navigate('explore-workshop-detail');
    }

    function nextStep() {
        const s = _getState();
        if (!s) return;
        const next = s.step + 1;
        if (next >= STEPS.length) {
            // Flow complete
            finish();
            App.toast('Demo flow completed! 🎉', 'success');
            return;
        }
        s.step = next;
        _setState(s);
        App.navigate(STEPS[next].view);
    }

    function prevStep() {
        const s = _getState();
        if (!s || s.step <= 0) return;
        s.step -= 1;
        _setState(s);
        if (s.step === 0) {
            localStorage.setItem('exp_selected_workshop', s.workshopId);
        }
        App.navigate(STEPS[s.step].view);
    }

    function goToStep(idx) {
        const s = _getState();
        if (!s || idx < 0 || idx >= STEPS.length) return;
        s.step = idx;
        _setState(s);
        if (idx === 0) {
            localStorage.setItem('exp_selected_workshop', s.workshopId);
        }
        App.navigate(STEPS[idx].view);
    }

    function finish() {
        _setState(null);
    }

    // ── UI components ───────────────────────────────────────────────

    /**
     * Returns the breadcrumb HTML bar for the current demo flow state.
     * Should be injected at the top of each view when DemoFlow.isActive().
     */
    function breadcrumbHTML() {
        const s = _getState();
        if (!s) return '';

        const steps = STEPS.map((step, idx) => {
            let cls = 'demo-crumb';
            if (idx < s.step) cls += ' demo-crumb--done';
            else if (idx === s.step) cls += ' demo-crumb--active';
            const clickable = idx <= s.step ? `onclick="DemoFlow.goToStep(${idx})"` : '';
            return `<div class="${cls}" ${clickable}>
                <span class="demo-crumb__icon">${step.icon}</span>
                <span class="demo-crumb__label">${step.label}</span>
                <span class="demo-crumb__num">${idx + 1}</span>
            </div>`;
        }).join('<span class="demo-crumb__arrow">→</span>');

        return `
            <div class="demo-flow-bar">
                <div class="demo-flow-bar__crumbs">${steps}</div>
                <div class="demo-flow-bar__actions">
                    ${s.step > 0 ? '<button class="btn btn-secondary btn-sm" onclick="DemoFlow.prevStep()">← Previous</button>' : ''}
                    ${s.step < STEPS.length - 1
                        ? '<button class="btn btn-primary btn-sm" onclick="DemoFlow.nextStep()">Next Step →</button>'
                        : '<button class="btn btn-primary btn-sm" onclick="DemoFlow.finish(); App.toast(\'Demo complete!\', \'success\'); App.navigate(\'executive-cockpit\')">✓ Finish Demo</button>'}
                    <button class="btn btn-sm" onclick="DemoFlow.finish(); App.toast('Demo flow ended', 'info')" title="Exit demo flow" style="color:var(--sap-text-secondary)">✕</button>
                </div>
            </div>`;
    }

    /**
     * Returns a "Start Demo Flow" button for workshop lists.
     * @param {string|number} workshopId
     */
    function startButton(workshopId) {
        return `<button class="btn btn-primary btn-sm" onclick="DemoFlow.start('${workshopId}')" title="Start guided demo flow from this workshop">
            🎬 Demo Flow
        </button>`;
    }

    return {
        start, nextStep, prevStep, goToStep, finish,
        isActive, currentStep, getWorkshopId,
        breadcrumbHTML, startButton,
    };
})();
