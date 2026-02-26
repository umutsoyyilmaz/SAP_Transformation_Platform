/**
 * F8 — Exploratory Testing View
 * Session timer, real-time notes, quick defect creation
 */
var ExploratoryView = (function () {
  "use strict";

  const API = "/api/v1";
  let currentProgramId = null;
  let currentSession = null;
  let timerInterval = null;
  let timerSeconds = 0;

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
  function fmtDuration(min) { return min != null ? `${min} min` : "—"; }

  /* ── render ── */
  function render() {
    currentProgramId = window.currentProgramId || 1;
    const root = $("#main-content") || document.body;
    root.innerHTML = `
      <div class="f8-layout">
        <div class="f8-sidebar" id="f8-session-list"></div>
        <div class="f8-main">
          <div class="f8-toolbar">
            <button class="btn btn-primary" id="f8-new-session">+ New Session</button>
            <select id="f8-status-filter" class="form-select f8-filter">
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <div id="f8-detail" class="f8-detail">
            <p class="f8-empty">Select a session or create a new one</p>
          </div>
        </div>
      </div>`;

    $("#f8-new-session").onclick = showCreateModal;
    $("#f8-status-filter").onchange = () => loadSessions();
    loadSessions();
  }

  /* ── session list ── */
  function loadSessions() {
    const status = $("#f8-status-filter")?.value || "";
    const qs = status ? `?status=${status}` : "";
    api("GET", `/programs/${currentProgramId}/exploratory-sessions${qs}`)
      .then(d => renderSessionList(d.sessions || []));
  }

  function renderSessionList(sessions) {
    const el = $("#f8-session-list");
    if (!sessions.length) {
      el.innerHTML = '<p class="f8-empty-sidebar">No sessions</p>';
      return;
    }
    el.innerHTML = sessions.map(s => `
      <div class="f8-session-card ${currentSession?.id === s.id ? 'active' : ''}"
           data-id="${s.id}">
        <div class="f8-session-charter">${escHtml(s.charter)}</div>
        <div class="f8-session-meta">
          <span class="f8-status-badge f8-status-${s.status}">${s.status}</span>
          <span>${escHtml(s.tester_name || "")}</span>
        </div>
      </div>`).join("");

    $$(".f8-session-card", el).forEach(card => {
      card.onclick = () => loadSession(+card.dataset.id);
    });
  }

  /* ── session detail ── */
  function loadSession(id) {
    api("GET", `/exploratory-sessions/${id}?include_notes=true`).then(d => {
      currentSession = d.session;
      renderDetail();
      loadSessions(); // highlight active
    });
  }

  function renderDetail() {
    const s = currentSession;
    if (!s) return;
    const el = $("#f8-detail");
    el.innerHTML = `
      <div class="f8-session-header">
        <h3>${escHtml(s.charter)}</h3>
        <div class="f8-actions">
          ${s.status === "draft" || s.status === "paused" ?
            `<button class="btn btn-success btn-sm" id="f8-start">▶ Start</button>` : ""}
          ${s.status === "active" ?
            `<button class="btn btn-warning btn-sm" id="f8-pause">⏸ Pause</button>` : ""}
          ${s.status === "active" || s.status === "paused" ?
            `<button class="btn btn-danger btn-sm" id="f8-complete">⏹ Stop</button>` : ""}
          <button class="btn btn-outline btn-sm" id="f8-edit-session">✏️</button>
          <button class="btn btn-outline btn-sm f8-del" id="f8-delete-session">🗑️</button>
        </div>
      </div>
      <div class="f8-timer-row">
        <div class="f8-timer" id="f8-timer">00:00:00</div>
        <div class="f8-meta-grid">
          <span>Scope: ${escHtml(s.scope)}</span>
          <span>Time Box: ${s.time_box || 60} min</span>
          <span>Environment: ${escHtml(s.environment)}</span>
          <span>Tester: ${escHtml(s.tester_name)}</span>
          ${s.actual_duration != null ? `<span>Actual Duration: ${fmtDuration(s.actual_duration)}</span>` : ""}
        </div>
      </div>
      <div class="f8-tabs">
        <button class="f8-tab active" data-tab="notes">Notes</button>
        <button class="f8-tab" data-tab="summary">Summary</button>
      </div>
      <div class="f8-tab-content" id="f8-tab-content"></div>`;

    // timer controls
    const startBtn = $("#f8-start");
    const pauseBtn = $("#f8-pause");
    const completeBtn = $("#f8-complete");
    if (startBtn) startBtn.onclick = () => sessionAction("start");
    if (pauseBtn) pauseBtn.onclick = () => sessionAction("pause");
    if (completeBtn) completeBtn.onclick = () => sessionAction("complete");
    $("#f8-edit-session").onclick = showEditModal;
    $("#f8-delete-session").onclick = deleteSession;

    // tabs
    $$(".f8-tab", el).forEach(t => {
      t.onclick = () => {
        $$(".f8-tab", el).forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        renderTab(t.dataset.tab);
      };
    });

    // start timer if active
    updateTimer(s);
    renderTab("notes");
  }

  /* ── timer ── */
  function updateTimer(s) {
    clearInterval(timerInterval);
    if (s.status === "active" && s.started_at) {
      const start = new Date(s.started_at).getTime();
      timerInterval = setInterval(() => {
        timerSeconds = Math.floor((Date.now() - start) / 1000);
        const hh = String(Math.floor(timerSeconds / 3600)).padStart(2, "0");
        const mm = String(Math.floor((timerSeconds % 3600) / 60)).padStart(2, "0");
        const ss = String(timerSeconds % 60).padStart(2, "0");
        const el = $("#f8-timer");
        if (el) el.textContent = `${hh}:${mm}:${ss}`;
      }, 1000);
    }
  }

  /* ── session actions ── */
  function sessionAction(action) {
    api("POST", `/exploratory-sessions/${currentSession.id}/${action}`).then(d => {
      if (d.session) {
        currentSession = d.session;
        renderDetail();
        loadSessions();
      }
    });
  }

  function deleteSession() {
    if (!confirm("Are you sure you want to delete this session?")) return;
    api("DELETE", `/exploratory-sessions/${currentSession.id}`).then(() => {
      currentSession = null;
      $("#f8-detail").innerHTML = '<p class="f8-empty">Select a session or create a new one</p>';
      loadSessions();
    });
  }

  /* ── tabs ── */
  function renderTab(tab) {
    const el = $("#f8-tab-content");
    if (tab === "notes") renderNotesTab(el);
    else renderSummaryTab(el);
  }

  function renderNotesTab(el) {
    const s = currentSession;
    const notes = s.session_notes || [];
    el.innerHTML = `
      <div class="f8-note-input">
        <select id="f8-note-type" class="form-select f8-note-type-sel">
          <option value="observation">🔍 Observation</option>
          <option value="bug">🐛 Bug</option>
          <option value="question">❓ Question</option>
          <option value="idea">💡 Idea</option>
        </select>
        <input type="text" id="f8-note-text" class="form-input f8-note-field"
               placeholder="Add note… (press Enter to save)">
        <button class="btn btn-primary btn-sm" id="f8-add-note">Add</button>
      </div>
      <div class="f8-notes-list" id="f8-notes-list">
        ${notes.length ? notes.map(n => noteCard(n)).join("") :
          '<p class="f8-empty">No notes yet</p>'}
      </div>`;

    $("#f8-add-note").onclick = addNote;
    $("#f8-note-text").onkeydown = e => { if (e.key === "Enter") addNote(); };
    $$(".f8-note-delete", el).forEach(btn => {
      btn.onclick = () => deleteNote(+btn.dataset.id);
    });
  }

  function noteCard(n) {
    const icons = { observation: "🔍", bug: "🐛", question: "❓", idea: "💡" };
    return `
      <div class="f8-note-card f8-note-${n.note_type}">
        <span class="f8-note-icon">${icons[n.note_type] || "📝"}</span>
        <span class="f8-note-content">${escHtml(n.content)}</span>
        <span class="f8-note-time">${fmtDate(n.timestamp)}</span>
        <button class="f8-note-delete" data-id="${n.id}">×</button>
      </div>`;
  }

  function addNote() {
    const content = $("#f8-note-text")?.value?.trim();
    if (!content) return;
    const note_type = $("#f8-note-type")?.value || "observation";
    api("POST", `/exploratory-sessions/${currentSession.id}/notes`, { content, note_type })
      .then(d => {
        if (d.note) {
          currentSession.session_notes = currentSession.session_notes || [];
          currentSession.session_notes.push(d.note);
          renderTab("notes");
        }
      });
  }

  function deleteNote(nid) {
    api("DELETE", `/exploratory-notes/${nid}`).then(() => {
      currentSession.session_notes = (currentSession.session_notes || []).filter(n => n.id !== nid);
      renderTab("notes");
    });
  }

  function renderSummaryTab(el) {
    const s = currentSession;
    const notes = s.session_notes || [];
    const bugs = notes.filter(n => n.note_type === "bug").length;
    const observations = notes.filter(n => n.note_type === "observation").length;
    const questions = notes.filter(n => n.note_type === "question").length;
    const ideas = notes.filter(n => n.note_type === "idea").length;
    el.innerHTML = `
      <div class="f8-summary">
        <div class="f8-summary-stat"><span>🐛</span><strong>${bugs}</strong> Bugs</div>
        <div class="f8-summary-stat"><span>🔍</span><strong>${observations}</strong> Observations</div>
        <div class="f8-summary-stat"><span>❓</span><strong>${questions}</strong> Questions</div>
        <div class="f8-summary-stat"><span>💡</span><strong>${ideas}</strong> Ideas</div>
      </div>
      <div class="f8-summary-detail">
        <p><strong>Start:</strong> ${fmtDate(s.started_at)}</p>
        <p><strong>End:</strong> ${fmtDate(s.ended_at)}</p>
        <p><strong>Duration:</strong> ${fmtDuration(s.actual_duration)}</p>
        <p><strong>Status:</strong> ${s.status}</p>
        <p><strong>Notes:</strong> ${escHtml(s.notes)}</p>
      </div>`;
  }

  /* ── create / edit modals ── */
  function showCreateModal() {
    showModal("New Exploratory Session", {}, data => {
      api("POST", `/programs/${currentProgramId}/exploratory-sessions`, data).then(d => {
        if (d.session) {
          currentSession = d.session;
          loadSessions();
          renderDetail();
          closeModal();
        }
      });
    });
  }

  function showEditModal() {
    showModal("Edit Session", currentSession, data => {
      api("PUT", `/exploratory-sessions/${currentSession.id}`, data).then(d => {
        if (d.session) {
          currentSession = d.session;
          renderDetail();
          loadSessions();
          closeModal();
        }
      });
    });
  }

  function showModal(title, defaults, onSave) {
    let overlay = document.createElement("div");
    overlay.className = "f8-modal-overlay";
    overlay.innerHTML = `
      <div class="f8-modal">
        <h3>${title}</h3>
        <label>Charter (Purpose) *</label>
        <input id="f8m-charter" class="form-input" value="${escHtml(defaults.charter || "")}">
        <label>Scope</label>
        <input id="f8m-scope" class="form-input" value="${escHtml(defaults.scope || "")}">
        <label>Time Box (min)</label>
        <input id="f8m-timebox" type="number" class="form-input" value="${defaults.time_box || 60}">
        <label>Tester</label>
        <input id="f8m-tester" class="form-input" value="${escHtml(defaults.tester_name || "")}">
        <label>Environment</label>
        <input id="f8m-env" class="form-input" value="${escHtml(defaults.environment || "")}">
        <div class="f8-modal-actions">
          <button class="btn btn-primary" id="f8m-save">Save</button>
          <button class="btn btn-outline" id="f8m-cancel">Cancel</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    $("#f8m-save").onclick = () => {
      const charter = $("#f8m-charter").value.trim();
      if (!charter) return;
      onSave({
        charter,
        scope: $("#f8m-scope").value.trim(),
        time_box: parseInt($("#f8m-timebox").value) || 60,
        tester_name: $("#f8m-tester").value.trim(),
        environment: $("#f8m-env").value.trim(),
      });
    };
    $("#f8m-cancel").onclick = closeModal;
    overlay.onclick = e => { if (e.target === overlay) closeModal(); };
  }

  function closeModal() {
    const m = $(".f8-modal-overlay");
    if (m) m.remove();
  }

  return { render };
})();
