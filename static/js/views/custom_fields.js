/**
 * F9 — Custom Fields & Layout Engine View
 * Field definition CRUD, entity value management, layout config editor
 */
var CustomFieldsView = (function () {
  "use strict";

  const API = "/api/v1";
  let currentProgramId = null;
  let currentEntityType = "test_case";
  let fields = [];
  let layouts = [];

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $$(sel, ctx) { return (ctx || document).querySelectorAll(sel); }
  function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API + url, opts).then(r => r.json());
  }
  function escHtml(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }

  const FIELD_TYPES = [
    { value: "text", label: "Metin" },
    { value: "textarea", label: "Uzun Metin" },
    { value: "number", label: "Sayı" },
    { value: "date", label: "Tarih" },
    { value: "select", label: "Seçim" },
    { value: "multiselect", label: "Çoklu Seçim" },
    { value: "checkbox", label: "Onay Kutusu" },
    { value: "url", label: "URL" },
  ];

  const ENTITY_TYPES = [
    { value: "test_case", label: "Test Case" },
    { value: "defect", label: "Defect" },
    { value: "test_plan", label: "Test Plan" },
    { value: "test_cycle", label: "Test Cycle" },
  ];

  function render() {
    currentProgramId = window.currentProgramId || 1;
    const root = $("#main-content") || document.body;
    root.innerHTML = `
      <div class="f9-layout">
        <div class="f9-toolbar">
          <h3>Özel Alanlar & Layout Engine</h3>
          <select id="f9-entity-type" class="form-select f9-entity-sel">
            ${ENTITY_TYPES.map(t => `<option value="${t.value}" ${t.value === currentEntityType ? 'selected' : ''}>${t.label}</option>`).join("")}
          </select>
          <button class="btn btn-primary btn-sm" id="f9-add-field">+ Alan Ekle</button>
        </div>
        <div class="f9-tabs">
          <button class="f9-tab active" data-tab="fields">Alanlar</button>
          <button class="f9-tab" data-tab="layouts">Layout'lar</button>
        </div>
        <div id="f9-content" class="f9-content"></div>
      </div>`;

    $("#f9-entity-type").onchange = e => {
      currentEntityType = e.target.value;
      loadFields();
      loadLayouts();
    };
    $("#f9-add-field").onclick = showFieldModal;
    $$(".f9-tab").forEach(t => {
      t.onclick = () => {
        $$(".f9-tab").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        renderTab(t.dataset.tab);
      };
    });
    loadFields();
    loadLayouts();
  }

  function loadFields() {
    api("GET", `/programs/${currentProgramId}/custom-fields?entity_type=${currentEntityType}&per_page=200`)
      .then(d => { fields = d.fields || []; renderTab("fields"); });
  }

  function loadLayouts() {
    api("GET", `/programs/${currentProgramId}/layouts?entity_type=${currentEntityType}&per_page=50`)
      .then(d => { layouts = d.layouts || []; });
  }

  function renderTab(tab) {
    const el = $("#f9-content");
    if (tab === "fields") renderFieldsTab(el);
    else renderLayoutsTab(el);
  }

  /* ── Fields tab ── */
  function renderFieldsTab(el) {
    if (!fields.length) {
      el.innerHTML = '<p class="f9-empty">Bu varlık türü için alan tanımlanmamış</p>';
      return;
    }
    el.innerHTML = `
      <table class="f9-field-table">
        <thead><tr>
          <th>Sıra</th><th>Alan Adı</th><th>Etiket</th><th>Tür</th>
          <th>Zorunlu</th><th>Filtrelenebilir</th><th>İşlemler</th>
        </tr></thead>
        <tbody>
          ${fields.map(f => `
            <tr>
              <td>${f.sort_order}</td>
              <td><code>${escHtml(f.field_name)}</code></td>
              <td>${escHtml(f.field_label)}</td>
              <td><span class="f9-type-badge">${f.field_type}</span></td>
              <td>${f.is_required ? '✅' : '—'}</td>
              <td>${f.is_filterable ? '✅' : '—'}</td>
              <td>
                <button class="btn btn-outline btn-xs f9-edit-field" data-id="${f.id}">✏️</button>
                <button class="btn btn-outline btn-xs f9-del-field" data-id="${f.id}">🗑️</button>
              </td>
            </tr>`).join("")}
        </tbody>
      </table>`;

    $$(".f9-edit-field", el).forEach(b => {
      b.onclick = () => {
        const f = fields.find(x => x.id === +b.dataset.id);
        if (f) showFieldModal(f);
      };
    });
    $$(".f9-del-field", el).forEach(b => {
      b.onclick = () => deleteField(+b.dataset.id);
    });
  }

  function deleteField(id) {
    if (!confirm("Alan silinsin mi?")) return;
    api("DELETE", `/custom-fields/${id}`).then(() => loadFields());
  }

  function showFieldModal(existing) {
    const isEdit = existing && existing.id;
    const overlay = document.createElement("div");
    overlay.className = "f9-modal-overlay";
    overlay.innerHTML = `
      <div class="f9-modal">
        <h3>${isEdit ? 'Alan Düzenle' : 'Yeni Alan'}</h3>
        <label>Alan Adı *</label>
        <input id="f9m-name" class="form-input" value="${escHtml(existing?.field_name || "")}">
        <label>Etiket</label>
        <input id="f9m-label" class="form-input" value="${escHtml(existing?.field_label || "")}">
        <label>Tür</label>
        <select id="f9m-type" class="form-select">
          ${FIELD_TYPES.map(t => `<option value="${t.value}" ${(existing?.field_type || 'text') === t.value ? 'selected' : ''}>${t.label}</option>`).join("")}
        </select>
        <label>Sıra</label>
        <input id="f9m-order" type="number" class="form-input" value="${existing?.sort_order || 0}">
        <label>Varsayılan Değer</label>
        <input id="f9m-default" class="form-input" value="${escHtml(existing?.default_value || "")}">
        <label>Açıklama</label>
        <input id="f9m-desc" class="form-input" value="${escHtml(existing?.description || "")}">
        <label><input type="checkbox" id="f9m-required" ${existing?.is_required ? 'checked' : ''}> Zorunlu</label>
        <label><input type="checkbox" id="f9m-filterable" ${existing?.is_filterable !== false ? 'checked' : ''}> Filtrelenebilir</label>
        <div class="f9-modal-actions">
          <button class="btn btn-primary" id="f9m-save">Kaydet</button>
          <button class="btn btn-outline" id="f9m-cancel">İptal</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector("#f9m-save").onclick = () => {
      const data = {
        field_name: overlay.querySelector("#f9m-name").value.trim(),
        field_label: overlay.querySelector("#f9m-label").value.trim(),
        field_type: overlay.querySelector("#f9m-type").value,
        sort_order: parseInt(overlay.querySelector("#f9m-order").value) || 0,
        default_value: overlay.querySelector("#f9m-default").value.trim(),
        description: overlay.querySelector("#f9m-desc").value.trim(),
        is_required: overlay.querySelector("#f9m-required").checked,
        is_filterable: overlay.querySelector("#f9m-filterable").checked,
        entity_type: currentEntityType,
      };
      if (!data.field_name) return;
      const promise = isEdit
        ? api("PUT", `/custom-fields/${existing.id}`, data)
        : api("POST", `/programs/${currentProgramId}/custom-fields`, data);
      promise.then(d => {
        if (d.field) { overlay.remove(); loadFields(); }
      });
    };
    overlay.querySelector("#f9m-cancel").onclick = () => overlay.remove();
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  }

  /* ── Layouts tab ── */
  function renderLayoutsTab(el) {
    el.innerHTML = `
      <div class="f9-layout-toolbar">
        <button class="btn btn-primary btn-sm" id="f9-add-layout">+ Layout Ekle</button>
      </div>
      <div class="f9-layout-list">
        ${layouts.length ? layouts.map(l => `
          <div class="f9-layout-card ${l.is_default ? 'f9-default' : ''}">
            <div class="f9-layout-header">
              <span class="f9-layout-name">${escHtml(l.name)}</span>
              ${l.is_default ? '<span class="f9-default-badge">Varsayılan</span>' : ''}
            </div>
            <div class="f9-layout-meta">
              ${l.entity_type} · ${(l.sections || []).length} bölüm · ${escHtml(l.created_by)}
            </div>
            <div class="f9-layout-actions">
              ${!l.is_default ? `<button class="btn btn-outline btn-xs f9-set-default" data-id="${l.id}">★ Varsayılan Yap</button>` : ''}
              <button class="btn btn-outline btn-xs f9-edit-layout" data-id="${l.id}">✏️</button>
              <button class="btn btn-outline btn-xs f9-del-layout" data-id="${l.id}">🗑️</button>
            </div>
          </div>`).join("") : '<p class="f9-empty">Layout tanımlanmamış</p>'}
      </div>`;

    $("#f9-add-layout").onclick = () => showLayoutModal();
    $$(".f9-set-default", el).forEach(b => {
      b.onclick = () => api("POST", `/layouts/${b.dataset.id}/set-default`).then(() => { loadLayouts(); setTimeout(() => renderTab("layouts"), 200); });
    });
    $$(".f9-edit-layout", el).forEach(b => {
      b.onclick = () => {
        const l = layouts.find(x => x.id === +b.dataset.id);
        if (l) showLayoutModal(l);
      };
    });
    $$(".f9-del-layout", el).forEach(b => {
      b.onclick = () => {
        if (!confirm("Layout silinsin mi?")) return;
        api("DELETE", `/layouts/${b.dataset.id}`).then(() => { loadLayouts(); setTimeout(() => renderTab("layouts"), 200); });
      };
    });
  }

  function showLayoutModal(existing) {
    const isEdit = existing && existing.id;
    const overlay = document.createElement("div");
    overlay.className = "f9-modal-overlay";
    overlay.innerHTML = `
      <div class="f9-modal">
        <h3>${isEdit ? 'Layout Düzenle' : 'Yeni Layout'}</h3>
        <label>Ad *</label>
        <input id="f9l-name" class="form-input" value="${escHtml(existing?.name || "")}">
        <label>Bölümler (JSON)</label>
        <textarea id="f9l-sections" class="form-input f9-json-area" rows="8">${escHtml(JSON.stringify(existing?.sections || [], null, 2))}</textarea>
        <label><input type="checkbox" id="f9l-default" ${existing?.is_default ? 'checked' : ''}> Varsayılan Layout</label>
        <div class="f9-modal-actions">
          <button class="btn btn-primary" id="f9l-save">Kaydet</button>
          <button class="btn btn-outline" id="f9l-cancel">İptal</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector("#f9l-save").onclick = () => {
      const name = overlay.querySelector("#f9l-name").value.trim();
      if (!name) return;
      let sections;
      try { sections = JSON.parse(overlay.querySelector("#f9l-sections").value); }
      catch { sections = []; }
      const data = {
        name,
        entity_type: currentEntityType,
        sections,
        is_default: overlay.querySelector("#f9l-default").checked,
      };
      const promise = isEdit
        ? api("PUT", `/layouts/${existing.id}`, data)
        : api("POST", `/programs/${currentProgramId}/layouts`, data);
      promise.then(d => {
        if (d.layout) { overlay.remove(); loadLayouts(); setTimeout(() => renderTab("layouts"), 200); }
      });
    };
    overlay.querySelector("#f9l-cancel").onclick = () => overlay.remove();
    overlay.onclick = e => { if (e.target === overlay) overlay.remove(); };
  }

  return { render };
})();
