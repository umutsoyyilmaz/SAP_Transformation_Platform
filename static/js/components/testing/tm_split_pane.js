var TMSplitPane = (() => {
    function mount(container, options) {
        if (!container) return;
        const {
            leftHtml = '',
            rightHtml = '',
            leftWidth = 260,
            minLeft = 180,
            maxLeft = 520,
        } = options || {};

        container.innerHTML = `
            <div class="tm-split" id="tmSplitRoot" style="grid-template-columns:${leftWidth}px 6px 1fr">
                <div class="tm-split__left" id="tmSplitLeft">${leftHtml}</div>
                <div class="tm-split__divider" id="tmSplitDivider"></div>
                <div class="tm-split__right" id="tmSplitRight">${rightHtml}</div>
            </div>
        `;

        const root = container.querySelector('#tmSplitRoot');
        const divider = container.querySelector('#tmSplitDivider');
        let dragging = false;

        divider.addEventListener('mousedown', () => { dragging = true; });
        document.addEventListener('mouseup', () => { dragging = false; });
        document.addEventListener('mousemove', (e) => {
            if (!dragging || !root) return;
            const rect = root.getBoundingClientRect();
            let next = e.clientX - rect.left;
            if (next < minLeft) next = minLeft;
            if (next > maxLeft) next = maxLeft;
            root.style.gridTemplateColumns = `${next}px 6px 1fr`;
        });
    }

    return { mount };
})();
