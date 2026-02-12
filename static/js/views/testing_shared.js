/**
 * SAP Transformation Management Platform
 * Testing Shared — common state & utilities for Test Planning, Execution,
 * and Defect Management modules.
 */

const TestingShared = (() => {
    let selectedProgramId = null;

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    function getProgram() {
        const prog = App.getActiveProgram();
        selectedProgramId = prog ? prog.id : null;
        return selectedProgramId;
    }

    function noProgramHtml(title) {
        return `
            <div class="page-header"><h1>${title}</h1></div>
            <div class="empty-state">
                <div class="empty-state__icon">📋</div>
                <div class="empty-state__title">No Program Selected</div>
                <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one.</p>
            </div>`;
    }

    return { esc, getProgram, noProgramHtml, get pid() { return selectedProgramId; } };
})();
