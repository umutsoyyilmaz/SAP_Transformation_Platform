const DiscoverCharterUI = (() => {
    function _esc(value) {
        const el = document.createElement("div");
        el.textContent = value ?? "";
        return el.innerHTML;
    }

    function collectPayload(form) {
        const fd = new FormData(form);
        const payload = Object.fromEntries(fd.entries());
        [
            "key_risks",
            "in_scope_summary",
            "out_of_scope_summary",
            "business_drivers",
            "expected_benefits",
            "affected_countries",
            "affected_sap_modules",
            "target_go_live_date",
            "estimated_duration_months",
        ].forEach((key) => {
            if (payload[key] === "") payload[key] = null;
        });
        if (payload.estimated_duration_months !== null) {
            payload.estimated_duration_months = parseInt(payload.estimated_duration_months, 10);
        }
        return payload;
    }

    function openApprovalModal({
        container,
        charter,
        saveDraft,
        approveCharter,
        onApproved,
        showToast,
    }) {
        const form = container?.querySelector("#charterForm");
        App.openModal(`
            <div class="modal-header">
                <h2>Approve Project Charter</h2>
                <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal-body">
                <p class="discover-modal-copy">
                    This will lock the charter, mark the approval criterion as complete, and move Discover closer to gate exit.
                </p>
                <div class="form-group">
                    <label>Approval notes <small>(optional)</small></label>
                    <textarea id="discoverApprovalNotes" rows="4" placeholder="e.g. Reviewed in steering committee on ${new Date().toISOString().slice(0, 10)}"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button type="button" class="btn btn-primary" id="discoverApprovalConfirm">Approve Charter</button>
            </div>
        `);

        const confirmBtn = document.getElementById("discoverApprovalConfirm");
        if (!confirmBtn) return;

        confirmBtn.addEventListener("click", async () => {
            confirmBtn.disabled = true;
            const notes = (document.getElementById("discoverApprovalNotes")?.value || "").trim() || null;
            if (!charter && form) {
                try {
                    await saveDraft(collectPayload(form));
                } catch (err) {
                    confirmBtn.disabled = false;
                    showToast("Could not save charter before approval: " + err.message, "error");
                    return;
                }
            }

            const currentUser = (typeof Auth !== "undefined") ? Auth.getUser() : null;
            const approverId = currentUser?.id ?? null;
            try {
                await approveCharter({ approver_id: approverId, notes });
                App.closeModal();
                if (typeof onApproved === "function") await onApproved();
            } catch (err) {
                confirmBtn.disabled = false;
                showToast("Approval failed: " + err.message, "error");
            }
        });
    }

    return { collectPayload, openApprovalModal };
})();
