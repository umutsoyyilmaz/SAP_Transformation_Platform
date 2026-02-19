/**
 * F8 — Evidence Capture View
 * Evidence gallery, lightbox, upload simulation, step/execution linking
 */
var EvidenceCaptureView = (function () {
  "use strict";

  const API = "/api/v1";
  let currentExecutionId = null;
  let evidenceList = [];

  /* ── helpers ── */
  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return (ctx || document).querySelectorAll(sel); }
  function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API + url, opts).then(r => r.json());
  }
  function escHtml(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }
  function fmtDate(d) { return d ? new Date(d).toLocaleString() : "—"; }
  function fmtSize(bytes) {
    if (!bytes) return "0 B";
    const u = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < u.length - 1) { bytes /= 1024; i++; }
    return bytes.toFixed(i ? 1 : 0) + " " + u[i];
  }

  /* ── render ── */
  function render() {
    const root = $("#main-content") || document.body;
    root.innerHTML = `
      <div class="f8e-layout">
        <div class="f8e-toolbar">
          <h3>Kanıt Galerisi</h3>
          <div class="f8e-controls">
            <label>Execution ID:</label>
            <input type="number" id="f8e-exec-id" class="form-input f8e-id-input"
                   placeholder="Execution ID" value="${currentExecutionId || ""}">
            <button class="btn btn-primary btn-sm" id="f8e-load">Yükle</button>
            <button class="btn btn-success btn-sm" id="f8e-add">+ Kanıt Ekle</button>
          </div>
        </div>
        <div class="f8e-type-filter" id="f8e-type-filter">
          <button class="f8e-filter-btn active" data-type="">Tümü</button>
          <button class="f8e-filter-btn" data-type="screenshot">📷 Ekran Görüntüsü</button>
          <button class="f8e-filter-btn" data-type="video">🎥 Video</button>
          <button class="f8e-filter-btn" data-type="log">📄 Log</button>
          <button class="f8e-filter-btn" data-type="document">📑 Doküman</button>
        </div>
        <div class="f8e-gallery" id="f8e-gallery">
          <p class="f8e-empty">Execution ID seçip "Yükle" butonuna basın</p>
        </div>
      </div>`;

    $("#f8e-load").onclick = () => {
      const id = parseInt($("#f8e-exec-id").value);
      if (id) { currentExecutionId = id; loadEvidence(); }
    };
    $("#f8e-add").onclick = showAddModal;
    $$(".f8e-filter-btn").forEach(b => {
      b.onclick = () => {
        $$(".f8e-filter-btn").forEach(x => x.classList.remove("active"));
        b.classList.add("active");
        renderGallery(b.dataset.type);
      };
    });
  }

  /* ── load ── */
  function loadEvidence() {
    if (!currentExecutionId) return;
    api("GET", `/testing/executions/${currentExecutionId}/evidence`).then(d => {
      evidenceList = d.evidence || [];
      renderGallery("");
    });
  }

  /* ── gallery ── */
  function renderGallery(filterType) {
    const el = $("#f8e-gallery");
    let items = evidenceList;
    if (filterType) items = items.filter(e => e.evidence_type === filterType);

    if (!items.length) {
      el.innerHTML = '<p class="f8e-empty">Kanıt bulunamadı</p>';
      return;
    }
    el.innerHTML = items.map(ev => evidenceCard(ev)).join("");

    $$(".f8e-card", el).forEach(card => {
      card.onclick = () => openLightbox(+card.dataset.id);
    });
    $$(".f8e-card-primary", el).forEach(btn => {
      btn.onclick = e => { e.stopPropagation(); setPrimary(+btn.dataset.id); };
    });
    $$(".f8e-card-delete", el).forEach(btn => {
      btn.onclick = e => { e.stopPropagation(); deleteEvidence(+btn.dataset.id); };
    });
  }

  function evidenceCard(ev) {
    const icons = {
      screenshot: "📷", video: "🎥", log: "📄", document: "📑", other: "📎"
    };
    const icon = icons[ev.evidence_type] || "📎";
    return `
      <div class="f8e-card ${ev.is_primary ? 'f8e-primary' : ''}" data-id="${ev.id}">
        <div class="f8e-card-thumb">
          ${ev.thumbnail_path ? `<img src="${escHtml(ev.thumbnail_path)}" alt="">` :
            `<span class="f8e-card-icon">${icon}</span>`}
          ${ev.is_primary ? '<span class="f8e-star">★</span>' : ''}
        </div>
        <div class="f8e-card-info">
          <span class="f8e-card-name">${escHtml(ev.file_name || "Kanıt")}</span>
          <span class="f8e-card-meta">
            <span class="f8e-type-badge f8e-type-${ev.evidence_type}">${ev.evidence_type}</span>
            ${fmtSize(ev.file_size)}
          </span>
        </div>
        <div class="f8e-card-actions">
          <button class="f8e-card-primary" data-id="${ev.id}" title="Ana kanıt yap">★</button>
          <button class="f8e-card-delete" data-id="${ev.id}" title="Sil">×</button>
        </div>
      </div>`;
  }

  /* ── lightbox ── */
  function openLightbox(id) {
    const ev = evidenceList.find(e => e.id === id);
    if (!ev) return;
    const overlay = document.createElement("div");
    overlay.className = "f8e-lightbox";
    overlay.innerHTML = `
      <div class="f8e-lightbox-content">
        <button class="f8e-lightbox-close">×</button>
        <div class="f8e-lightbox-preview">
          ${ev.thumbnail_path || ev.file_path ?
            `<img src="${escHtml(ev.thumbnail_path || ev.file_path)}" alt="${escHtml(ev.file_name)}">` :
            `<div class="f8e-lightbox-placeholder">
              <span class="f8e-card-icon" style="font-size:4rem">${{screenshot:"📷",video:"🎥",log:"📄",document:"📑"}[ev.evidence_type]||"📎"}</span>
            </div>`}
        </div>
        <div class="f8e-lightbox-details">
          <h4>${escHtml(ev.file_name || "Kanıt")}</h4>
          <p><strong>Tür:</strong> ${ev.evidence_type}</p>
          <p><strong>Boyut:</strong> ${fmtSize(ev.file_size)}</p>
          <p><strong>MIME:</strong> ${escHtml(ev.mime_type)}</p>
          <p><strong>Yakalayan:</strong> ${escHtml(ev.captured_by)}</p>
          <p><strong>Tarih:</strong> ${fmtDate(ev.captured_at)}</p>
          ${ev.description ? `<p><strong>Açıklama:</strong> ${escHtml(ev.description)}</p>` : ""}
          <p><strong>Ana Kanıt:</strong> ${ev.is_primary ? "Evet ★" : "Hayır"}</p>
        </div>
        <div class="f8e-lightbox-nav">
          <button class="btn btn-outline btn-sm" id="f8e-lb-prev">◀ Önceki</button>
          <button class="btn btn-outline btn-sm" id="f8e-lb-next">Sonraki ▶</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector(".f8e-lightbox-close").onclick = () => overlay.remove();
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };

    const idx = evidenceList.findIndex(e => e.id === id);
    overlay.querySelector("#f8e-lb-prev").onclick = () => {
      overlay.remove();
      const prev = (idx - 1 + evidenceList.length) % evidenceList.length;
      openLightbox(evidenceList[prev].id);
    };
    overlay.querySelector("#f8e-lb-next").onclick = () => {
      overlay.remove();
      const next = (idx + 1) % evidenceList.length;
      openLightbox(evidenceList[next].id);
    };
  }

  /* ── actions ── */
  function setPrimary(id) {
    api("POST", `/evidence/${id}/set-primary`).then(() => loadEvidence());
  }

  function deleteEvidence(id) {
    if (!confirm("Kanıtı silmek istediğinize emin misiniz?")) return;
    api("DELETE", `/evidence/${id}`).then(() => loadEvidence());
  }

  /* ── add modal ── */
  function showAddModal() {
    if (!currentExecutionId) {
      alert("Önce Execution ID yükleyin");
      return;
    }
    const overlay = document.createElement("div");
    overlay.className = "f8e-modal-overlay";
    overlay.innerHTML = `
      <div class="f8e-modal">
        <h3>Kanıt Ekle</h3>
        <label>Kanıt Türü</label>
        <select id="f8em-type" class="form-select">
          <option value="screenshot">📷 Ekran Görüntüsü</option>
          <option value="video">🎥 Video</option>
          <option value="log">📄 Log</option>
          <option value="document">📑 Doküman</option>
          <option value="other">📎 Diğer</option>
        </select>
        <label>Dosya Adı</label>
        <input id="f8em-name" class="form-input" placeholder="screenshot_01.png">
        <label>Dosya Yolu / URL</label>
        <input id="f8em-path" class="form-input" placeholder="/storage/evidence/...">
        <label>Boyut (bytes)</label>
        <input id="f8em-size" type="number" class="form-input" value="0">
        <label>MIME Type</label>
        <input id="f8em-mime" class="form-input" placeholder="image/png">
        <label>Açıklama</label>
        <input id="f8em-desc" class="form-input" placeholder="Adım 3 sonrası ekran görüntüsü">
        <label><input type="checkbox" id="f8em-primary"> Ana Kanıt</label>
        <div class="f8e-modal-actions">
          <button class="btn btn-primary" id="f8em-save">Kaydet</button>
          <button class="btn btn-outline" id="f8em-cancel">İptal</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector("#f8em-save").onclick = () => {
      const data = {
        evidence_type: overlay.querySelector("#f8em-type").value,
        file_name: overlay.querySelector("#f8em-name").value.trim(),
        file_path: overlay.querySelector("#f8em-path").value.trim(),
        file_size: parseInt(overlay.querySelector("#f8em-size").value) || 0,
        mime_type: overlay.querySelector("#f8em-mime").value.trim(),
        description: overlay.querySelector("#f8em-desc").value.trim(),
        is_primary: overlay.querySelector("#f8em-primary").checked,
      };
      api("POST", `/testing/executions/${currentExecutionId}/evidence`, data).then(d => {
        if (d.evidence) {
          overlay.remove();
          loadEvidence();
        }
      });
    };
    overlay.querySelector("#f8em-cancel").onclick = () => overlay.remove();
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  }

  return { render };
})();
