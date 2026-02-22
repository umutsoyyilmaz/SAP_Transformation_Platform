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
        return PGEmptyState.html({ icon: 'test', title: title || 'No Program Selected', description: 'Select a program to continue.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
    }

    return { esc, getProgram, noProgramHtml, get pid() { return selectedProgramId; } };
})();
