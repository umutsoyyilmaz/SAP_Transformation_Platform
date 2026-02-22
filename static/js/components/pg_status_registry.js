/* UI-S01-T02 — PGStatusRegistry: Central status → color map */
const PGStatusRegistry = (() => {
    /**
     * Merkezi statüs renk kaydı.
     * Her domain'in kendi statüsleri + genel statüsler burada.
     * Renk çiftleri: { bg, fg } — WCAG 4.5:1 kontrast karşılanmış.
     */
    const MAP = {
        // ── WRICEF / Backlog ──────────────────────────────
        new:         { bg: '#dbeafe', fg: '#1e40af' },
        design:      { bg: '#e0e7ff', fg: '#3730a3' },
        build:       { bg: '#fef3c7', fg: '#92400e' },
        test:        { bg: '#fce7f3', fg: '#9d174d' },
        deploy:      { bg: '#d1fae5', fg: '#065f46' },
        blocked:     { bg: '#fee2e2', fg: '#991b1b' },
        cancelled:   { bg: '#f1f5f9', fg: '#475569' },

        // ── Requirement lifecycle ─────────────────────────
        draft:       { bg: '#f1f5f9', fg: '#475569' },
        in_review:   { bg: '#fef9c3', fg: '#713f12' },
        approved:    { bg: '#dcfce7', fg: '#14532d' },
        implemented: { bg: '#dbeafe', fg: '#1e3a8a' },
        verified:    { bg: '#d1fae5', fg: '#064e3b' },

        // ── Test execution ────────────────────────────────
        pass:        { bg: '#dcfce7', fg: '#14532d' },
        fail:        { bg: '#fee2e2', fg: '#991b1b' },
        not_run:     { bg: '#f1f5f9', fg: '#475569' },
        deferred:    { bg: '#f3e8ff', fg: '#581c87' },
        skipped:     { bg: '#f1f5f9', fg: '#475569' },
        ready:       { bg: '#dbeafe', fg: '#1e3a8a' },
        deprecated:  { bg: '#fee2e2', fg: '#7f1d1d' },

        // ── Priority ──────────────────────────────────────
        critical:    { bg: '#fee2e2', fg: '#991b1b' },
        high:        { bg: '#ffedd5', fg: '#9a3412' },
        medium:      { bg: '#fef9c3', fg: '#713f12' },
        low:         { bg: '#f0fdf4', fg: '#14532d' },

        // ── Severity ──────────────────────────────────────
        s1:          { bg: '#fee2e2', fg: '#991b1b' },
        s2:          { bg: '#ffedd5', fg: '#9a3412' },
        s3:          { bg: '#dbeafe', fg: '#1e3a8a' },
        s4:          { bg: '#f1f5f9', fg: '#475569' },

        // ── RAID ──────────────────────────────────────────
        risk:        { bg: '#fee2e2', fg: '#991b1b' },
        assumption:  { bg: '#dbeafe', fg: '#1e3a8a' },
        issue:       { bg: '#ffedd5', fg: '#9a3412' },
        dependency:  { bg: '#f3e8ff', fg: '#581c87' },

        // ── General ───────────────────────────────────────
        active:      { bg: '#dcfce7', fg: '#14532d' },
        inactive:    { bg: '#f1f5f9', fg: '#475569' },
        open:        { bg: '#dbeafe', fg: '#1e3a8a' },
        closed:      { bg: '#f1f5f9', fg: '#475569' },
        pending:     { bg: '#fef9c3', fg: '#713f12' },
        completed:   { bg: '#dcfce7', fg: '#14532d' },
        in_progress: { bg: '#dbeafe', fg: '#1e3a8a' },
    };

    /** Statüse göre renk döndür. Bilinmeyen statüs → nötr gri. */
    function colors(status) {
        const key = (status || '').toLowerCase().replace(/[\s\-]/g, '_');
        return MAP[key] || { bg: '#f1f5f9', fg: '#475569' };
    }

    /** HTML badge string döndür. */
    function badge(status, opts) {
        opts = opts || {};
        const { bg, fg } = colors(status);
        const label = opts.label || status || 'unknown';
        const size  = opts.size === 'lg'
            ? 'font-size:13px;padding:3px 10px'
            : 'font-size:11px;padding:2px 8px';
        return `<span style="display:inline-block;${size};border-radius:4px;font-weight:600;background:${bg};color:${fg};white-space:nowrap">${_esc(label)}</span>`;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { colors, badge, MAP };
})();
