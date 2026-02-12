/**
 * SAP Transformation Platform — Global Error Handler
 * Sprint 24: Catches uncaught errors and unhandled promise rejections.
 */

(function () {
    'use strict';

    // ── Uncaught JS errors ─────────────────────────────────────────────
    window.onerror = function (message, source, lineno, colno, error) {
        _reportError('js_error', {
            message: String(message),
            source: source || '',
            line: lineno,
            col: colno,
            stack: error && error.stack ? error.stack.slice(0, 500) : '',
        });
        return false; // allow default browser error handling
    };

    // ── Unhandled promise rejections ───────────────────────────────────
    window.addEventListener('unhandledrejection', function (event) {
        const reason = event.reason;
        const message = reason instanceof Error
            ? reason.message
            : String(reason || 'Unknown promise rejection');

        _reportError('promise_rejection', {
            message: message,
            stack: reason && reason.stack ? reason.stack.slice(0, 500) : '',
        });
    });

    // ── Report handler ─────────────────────────────────────────────────
    function _reportError(type, details) {
        // Show toast notification if App is available
        if (typeof App !== 'undefined' && typeof App.toast === 'function') {
            App.toast(details.message || 'An unexpected error occurred', 'error');
        }

        // Log to console in development
        console.error(`[ErrorHandler] ${type}:`, details.message, details);

        // Optionally send to server (best-effort, fire-and-forget)
        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon('/api/v1/health', JSON.stringify({
                    type: 'client_error',
                    error_type: type,
                    message: details.message,
                    url: window.location.href,
                    timestamp: new Date().toISOString(),
                }));
            }
        } catch (_) {
            // silently ignore — error reporting must never throw
        }
    }
})();
