/* Shared markdown rendering/export helper for lightweight document previews. */

window.PGMarkdown = (() => {
    function escHtml(value) {
        const el = document.createElement('span');
        el.textContent = value || '';
        return el.innerHTML;
    }

    function renderInline(text) {
        let html = escHtml(text || '');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        return html;
    }

    function isTableSeparator(line) {
        return /^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$/.test((line || '').trim());
    }

    function parseTableRow(line) {
        return (line || '')
            .trim()
            .replace(/^\|/, '')
            .replace(/\|$/, '')
            .split('|')
            .map((cell) => renderInline(cell.trim()));
    }

    function render(content) {
        if (!content) return '';

        const lines = String(content).replace(/\r\n/g, '\n').split('\n');
        const html = [];
        let paragraph = [];
        let listType = null;
        let listItems = [];

        function flushParagraph() {
            if (!paragraph.length) return;
            html.push(`<p>${paragraph.map((line) => renderInline(line)).join('<br>')}</p>`);
            paragraph = [];
        }

        function flushList() {
            if (!listItems.length) return;
            const items = listItems.map((item) => `<li>${renderInline(item)}</li>`).join('');
            html.push(listType === 'ol' ? `<ol>${items}</ol>` : `<ul>${items}</ul>`);
            listType = null;
            listItems = [];
        }

        for (let index = 0; index < lines.length; index += 1) {
            const rawLine = lines[index];
            const line = rawLine.trim();

            if (!line) {
                flushParagraph();
                flushList();
                continue;
            }

            const nextLine = lines[index + 1] || '';
            if (rawLine.includes('|') && isTableSeparator(nextLine)) {
                flushParagraph();
                flushList();

                const headerCells = parseTableRow(rawLine);
                const rows = [];
                index += 2;
                while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
                    rows.push(parseTableRow(lines[index]));
                    index += 1;
                }
                index -= 1;

                html.push(`
                    <div class="backlog-spec-table-wrap pg-markdown-table-wrap">
                        <table>
                            <thead><tr>${headerCells.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead>
                            <tbody>${rows.map((cells) => `<tr>${cells.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
                        </table>
                    </div>
                `);
                continue;
            }

            if (/^#{1,6}\s+/.test(line)) {
                flushParagraph();
                flushList();
                const level = Math.min(6, line.match(/^#+/)[0].length);
                const text = line.replace(/^#{1,6}\s+/, '');
                html.push(`<h${level}>${renderInline(text)}</h${level}>`);
                continue;
            }

            if (/^---+$/.test(line)) {
                flushParagraph();
                flushList();
                html.push('<hr>');
                continue;
            }

            if (/^>\s?/.test(line)) {
                flushParagraph();
                flushList();
                html.push(`<blockquote>${renderInline(line.replace(/^>\s?/, ''))}</blockquote>`);
                continue;
            }

            if (/^[-*]\s+/.test(line)) {
                flushParagraph();
                if (listType && listType !== 'ul') flushList();
                listType = 'ul';
                listItems.push(line.replace(/^[-*]\s+/, ''));
                continue;
            }

            if (/^\d+\.\s+/.test(line)) {
                flushParagraph();
                if (listType && listType !== 'ol') flushList();
                listType = 'ol';
                listItems.push(line.replace(/^\d+\.\s+/, ''));
                continue;
            }

            if (listType) flushList();
            paragraph.push(line);
        }

        flushParagraph();
        flushList();
        return html.join('');
    }

    function buildDocumentHtml({ title, subtitle, content, metadata = [], variant = 'fs', autoPrint = false }) {
        const rendered = render(content || '');
        const isTechnical = variant === 'ts';
        const theme = isTechnical
            ? {
                ink: '#21303f',
                inkSoft: '#5d6f80',
                title: '#20384f',
                accent: '#2e6a78',
                line: '#d9e4e8',
                fill: '#f3f8f8',
                fillStrong: '#e7f0f1',
                border: '#d3e0e3',
                tableHead: '#ebf4f5',
                blockquote: '#7fa9b4',
                blockquoteText: '#35535d',
            }
            : {
                ink: '#223244',
                inkSoft: '#5e7286',
                title: '#12324f',
                accent: '#1e5a88',
                line: '#d9e5f0',
                fill: '#f4f8fb',
                fillStrong: '#eaf1f7',
                border: '#d6e2ec',
                tableHead: '#eef5fb',
                blockquote: '#8fb4d8',
                blockquoteText: '#38546f',
            };
        const docKicker = isTechnical ? 'SAP Technical Specification' : 'SAP Functional Specification';
        const metadataHtml = (metadata || [])
            .filter((item) => item && item.label && item.value !== undefined && item.value !== null && String(item.value).trim())
            .map((item) => `
                <div class="doc-meta__item">
                    <div class="doc-meta__label">${escHtml(item.label)}</div>
                    <div class="doc-meta__value">${escHtml(String(item.value))}</div>
                </div>
            `)
            .join('');
        const printScript = autoPrint ? 'window.addEventListener("load", () => setTimeout(() => window.print(), 180));' : '';
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${escHtml(title || 'Document')}</title>
    <style>
        :root {
            --doc-ink: ${theme.ink};
            --doc-ink-soft: ${theme.inkSoft};
            --doc-title: ${theme.title};
            --doc-accent: ${theme.accent};
            --doc-line: ${theme.line};
            --doc-fill: ${theme.fill};
            --doc-fill-strong: ${theme.fillStrong};
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: linear-gradient(180deg, #edf3f8 0%, #e4edf5 100%);
            color: var(--doc-ink);
            font-family: "Aptos", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }
        .doc-shell {
            max-width: 1120px;
            margin: 28px auto;
            padding: 0 20px;
        }
        .doc-page {
            background: #fff;
            border: 1px solid ${theme.border};
            border-radius: 22px;
            box-shadow: 0 20px 50px rgba(16, 42, 68, 0.12);
            overflow: hidden;
        }
        .doc-toolbar {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            padding: 14px 18px;
            border-bottom: 1px solid var(--doc-line);
            background: rgba(255, 255, 255, 0.92);
        }
        .doc-toolbar__button {
            border: 1px solid var(--doc-line);
            background: #fff;
            color: var(--doc-title);
            border-radius: 999px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.02em;
            cursor: pointer;
        }
        .doc-header {
            padding: 34px 40px 24px;
            border-bottom: 1px solid var(--doc-line);
            background:
                linear-gradient(180deg, rgba(242, 248, 253, 0.98) 0%, rgba(255, 255, 255, 1) 78%),
                radial-gradient(circle at top right, rgba(30, 90, 136, 0.08), transparent 38%);
        }
        .doc-kicker {
            margin: 0 0 8px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--doc-accent);
        }
        .doc-header h1 {
            margin: 0;
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 32px;
            font-weight: 700;
            line-height: 1.15;
            color: var(--doc-title);
        }
        .doc-header p {
            margin: 10px 0 0;
            color: var(--doc-ink-soft);
            font-size: 14px;
        }
        .doc-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            padding: 18px 40px 22px;
            border-bottom: 1px solid var(--doc-line);
            background: var(--doc-fill);
        }
        .doc-meta__item {
            padding: 12px 14px;
            border: 1px solid var(--doc-line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.88);
            min-height: 72px;
        }
        .doc-meta__label {
            margin-bottom: 6px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--doc-ink-soft);
        }
        .doc-meta__value {
            font-size: 15px;
            font-weight: 600;
            color: var(--doc-title);
            word-break: break-word;
        }
        .doc-body {
            padding: 30px 40px 40px;
            line-height: 1.72;
            font-size: 14px;
        }
        .doc-body h1,
        .doc-body h2,
        .doc-body h3,
        .doc-body h4,
        .doc-body h5,
        .doc-body h6 {
            color: var(--doc-title);
            line-height: 1.22;
            page-break-after: avoid;
        }
        .doc-body h1 {
            margin: 0 0 18px;
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 1.85rem;
        }
        .doc-body h2 {
            margin: 28px 0 14px;
            font-size: 1.3rem;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--doc-line);
        }
        .doc-body h3 {
            margin: 22px 0 10px;
            font-size: 1.08rem;
        }
        .doc-body p,
        .doc-body ul,
        .doc-body ol,
        .doc-body blockquote {
            margin: 0 0 14px;
        }
        .doc-body ul,
        .doc-body ol {
            padding-left: 24px;
        }
        .doc-body li + li {
            margin-top: 6px;
        }
        .doc-body strong {
            color: #173a5b;
        }
        .doc-body hr {
            border: 0;
            border-top: 1px solid var(--doc-line);
            margin: 22px 0;
        }
        .doc-body blockquote {
            padding: 14px 16px;
            border-left: 4px solid ${theme.blockquote};
            background: #f5f9fd;
            color: ${theme.blockquoteText};
            border-radius: 0 12px 12px 0;
        }
        .doc-body code {
            padding: 2px 6px;
            border-radius: 6px;
            background: var(--doc-fill-strong);
            color: #0c4a6e;
            font-size: 0.92em;
        }
        .doc-body table {
            width: 100%;
            border-collapse: collapse;
            min-width: 420px;
            font-size: 13.5px;
        }
        .doc-body thead {
            background: ${theme.tableHead};
        }
        .doc-body th,
        .doc-body td {
            padding: 11px 12px;
            text-align: left;
            vertical-align: top;
            border-bottom: 1px solid #e4edf6;
        }
        .doc-body th {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #36526c;
        }
        .doc-body tbody tr:nth-child(even) {
            background: #fbfdff;
        }
        .pg-markdown-table-wrap {
            overflow-x: auto;
            border: 1px solid #dbe7f2;
            border-radius: 14px;
            margin: 14px 0 20px;
            break-inside: avoid;
        }
        @page {
            size: A4;
            margin: 15mm 12mm 16mm;
        }
        @media (max-width: 720px) {
            .doc-shell {
                padding: 0 10px;
            }
            .doc-header,
            .doc-meta,
            .doc-body {
                padding-left: 18px;
                padding-right: 18px;
            }
        }
        @media print {
            body {
                background: #fff;
            }
            .doc-toolbar {
                display: none;
            }
            .doc-shell {
                margin: 0;
                padding: 0;
                max-width: none;
            }
            .doc-page {
                border: 0;
                border-radius: 0;
                box-shadow: none;
            }
            .doc-header {
                padding-top: 10mm;
            }
            .pg-markdown-table-wrap {
                overflow: visible;
            }
        }
    </style>
</head>
<body>
    <div class="doc-shell">
        <article class="doc-page">
            <div class="doc-toolbar">
                <button class="doc-toolbar__button" type="button" onclick="window.print()">Print / Save PDF</button>
                <button class="doc-toolbar__button" type="button" onclick="window.close()">Close</button>
            </div>
            <header class="doc-header">
                <p class="doc-kicker">${escHtml(docKicker)}</p>
                <h1>${escHtml(title || 'Document')}</h1>
                ${subtitle ? `<p>${escHtml(subtitle)}</p>` : ''}
            </header>
            ${metadataHtml ? `<section class="doc-meta">${metadataHtml}</section>` : ''}
            <section class="doc-body">${rendered}</section>
        </article>
    </div>
    <script>${printScript}</script>
</body>
</html>`;
    }

    return {
        escHtml,
        renderInline,
        render,
        buildDocumentHtml,
    };
})();
