// One Take Studio — everything you see in the browser.
"use strict";

const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = t => { t = Math.max(0, t || 0); const m = Math.floor(t / 60), s = Math.floor(t % 60); return `${m}:${String(s).padStart(2, "0")}`; };
const clone = o => JSON.parse(JSON.stringify(o));
const media = rel => "/media/" + rel.split("/").map(encodeURIComponent).join("/");
const W = 1080, H = 1920;

const S = {
  name: null, p: null, rev: 0, settings: null, claude: false,
  lookbook: null, library: null,
  segs: [], T: 0, groups: [], style: null, spans: [],
  outT: 0, playing: false, curSeg: null, curWord: -1,
  sel: null, tab: "cut", hist: [], fut: [], saveTimer: null, saving: false, dirty: false,
  sprites: {}, spriteLoading: {}, jobs: {}, reqStatus: {}, selOv: null, zoom: 1, faceCard: false,
};

const v = $("#v"), bv = $("#bv"), music = $("#music"), fc = $("#fc"), fctx = fc.getContext("2d");

// ------------------------------------------------------------------ api
async function api(path, body, method) {
  const opt = body === undefined ? {} : { method: method || "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if (r.status === 409) { const e = new Error("conflict"); e.conflict = true; throw e; }
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

function toast(msg, actionLabel, action, ms = 5000) {
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span>${esc(msg)}</span>` + (actionLabel ? `<button>${esc(actionLabel)}</button>` : "");
  if (actionLabel) el.querySelector("button").onclick = () => { action(); el.remove(); };
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), actionLabel ? ms * 2 : ms);
}

function openModal(html, onMount) {
  $("#claudeTray").hidden = true;
  $("#mbody").innerHTML = html;
  $("#modal").hidden = false;
  onMount && onMount($("#mbody"));
}
function closeModal() { $("#modal").hidden = true; $("#mbody").innerHTML = ""; clearInterval(S.spriteAnim); }
$("#modal").addEventListener("click", e => { if (e.target.id === "modal" || e.target.classList.contains("mclose")) closeModal(); });

// ------------------------------------------------------------------ load
// Navigation: your reels list is the page "before" every reel, so the browser's Back button
// (and the ← All reels button) always returns to it instead of leaving the studio.
function openReel(name) { location.hash = name; }
function goHome() { if (history.state?.reel && history.length > 1) history.back(); else location.hash = ""; }
window.addEventListener("hashchange", async () => { if (S.dirty) await save(); location.reload(); });

async function boot() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h && h !== "newreel" && !history.state) {  // opened straight into a reel: put the list behind it
    history.replaceState({ home: 1 }, "", location.pathname);
    history.pushState({ reel: 1 }, "", "#" + h);
  } else if (h && !history.state?.reel) {
    history.replaceState({ reel: 1 }, "", location.href);
  }
  const st = await api("/api/status");
  S.settings = st.settings; S.claude = st.claude; S.stock = st.stock;
  const name = decodeURIComponent(location.hash.slice(1));
  if (!name || name === "newreel") return home();
  await loadProject(name);
  setInterval(poll, 2500);
}

// While a new reel is being edited, update just the % (redrawing the whole page made it flicker)
let nrTimer = 0;
function nrText(nr) {
  const mins = Math.max(0, Math.round((nr.now - nr.started) / 60));
  const left = nr.left == null ? "" : nr.left < 90 ? "almost done · " : `about ${Math.round(nr.left / 60)} min left · `;
  return `<b>${esc(nr.label || "Getting started")}</b> · ${left}started ${mins} min ago. This page updates by itself.`;
}
const STEP_NAMES = { start: "starting", join: "joining", transcribe: "captions", analyze: "face check", cut: "Claude's cut",
  style: "Claude's styling", sfx: "sound effects", check: "checks", render: "rendering" };
function tookText(nr) {  // "12 min: joining 2 min, captions 4 min, …" so you can see what's slow
  const m = s => s >= 90 ? `${Math.round(s / 60)} min` : `${Math.round(s)} s`;
  return `${m(nr.ended - nr.started)}: ` + Object.entries(nr.times).filter(([, v]) => v >= 1).map(([k, v]) => `${STEP_NAMES[k] || k} ${m(v)}`).join(", ");
}
async function tickNewReel() {
  if (!document.body.classList.contains("home") || !$("#nrPct")) return;  // you've opened a reel: stop
  const nr = await api("/api/newreel").catch(() => null);
  if (!nr) { nrTimer = setTimeout(tickNewReel, 5000); return; }
  if (nr.status !== "running") return home();  // finished or failed: show the result
  $("#nrPct").textContent = `${nr.pct ?? 0}%`;
  $("#nrBar").style.width = `${nr.pct ?? 0}%`;
  $("#nrText").innerHTML = nrText(nr);
  nrTimer = setTimeout(tickNewReel, 5000);
}

async function home() {
  document.body.classList.add("home");
  $("#previewCol").hidden = true; $("#bottom").hidden = true; $("#tabs").hidden = true;
  $("#main").style.gridTemplateColumns = "1fr";
  const list = await api("/api/projects");
  const nr = await api("/api/newreel").catch(() => ({ status: "none" }));
  const banner = {
    running: `<div class="card"><div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">
        <h3 style="margin:0">✳ Editing your new reel…</h3><b id="nrPct" style="font-size:26px;color:var(--accent)">${nr.pct ?? 0}%</b></div>
      <div class="progress"><i id="nrBar" style="width:${nr.pct ?? 0}%;transition:width 1s"></i></div>
      <div class="muted" id="nrText">${nrText(nr)}</div></div>`,
    noclips: `<div class="card"><h3 style="margin-top:0">No video found</h3>
      <div class="muted">Put your video in <b>Linux files → Claude → onetake → drop-in-order</b>, then click <b>One Take – New reel</b> again.</div></div>`,
    done: `<div class="card"><h3 style="margin-top:0">✓ Your new reel is ready</h3>
      <div class="muted" style="white-space:pre-wrap">${esc((nr.log || "").trim().split("\n\n").pop().slice(-700))}</div>
      ${nr.times && nr.started ? `<div class="muted" style="margin-top:6px;font-size:12px">⏱ Took ${tookText(nr)}</div>` : ""}
      ${list.length ? `<button class="primary" style="margin-top:10px" onclick="openReel('${list[0].name}')">Open it</button>` : ""}</div>`,
    failed: `<div class="card"><h3 style="margin-top:0">${nr.stuck ? "The edit stopped partway" : "Claude couldn't finish the edit"}</h3>
      <div class="muted" style="white-space:pre-wrap">${nr.stuck
        ? "It stopped before it finished, probably because the Chromebook went to sleep or Linux restarted. Your video is safe."
        : esc((nr.log || "").slice(-800))}</div>
      ${nr.waiting ? `<button class="primary" id="nrRetry" style="margin-top:10px">↻ Try again with the same video</button>`
        : `<div class="muted">Send the video again, or open the Terminal and type <b>~/Claude/onetake/new-reel.sh</b> to watch it work.</div>`}</div>`,
  }[(nr.status === "running" || (nr.now - (nr.ended || nr.started || 0)) < 6 * 3600) ? nr.status : "none"] || "";
  // fetched BEFORE the setTimeouts below: they bind buttons once the page is drawn, and an await in between
  // made them run first (Delete, Try again and the phone card did nothing)
  const st = await api("/api/status").catch(() => ({}));
  clearTimeout(nrTimer);
  if (nr.status === "running") nrTimer = setTimeout(tickNewReel, 5000);
  setTimeout(() => { const r = $("#nrRetry"); if (r) r.onclick = async () => {
    r.disabled = true;
    try { await api("/api/new-reel-start", { auto_render: !!nr.auto_render }); home(); } catch (e) { toast(e.message); r.disabled = false; }
  }; }, 0);
  setTimeout(bindDropzone, 0);
  setTimeout(drawPhoneCard, 0);
  setTimeout(() => document.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
    if (!confirm(`Delete “${b.dataset.title}”? Its edits and exports will be gone for good. Download the MP4 first if you want to keep it.`)) return;
    await api(`/api/project/${b.dataset.del}/delete`, {});
    toast("Reel deleted."); home();
  }), 0);
  const busy = nr.status === "running";
  const diskNote = st.disk_free_mb != null && st.disk_free_mb < 4000
    ? `<div class="card" style="background:var(--hl)"><b>Only ${gb(st.disk_free_mb)} free on this computer.</b>
       <div class="muted">A new reel needs about 4 GB while it's being made. Save finished reels to your phone, then press <b>🧹 Free up</b> on them below.</div></div>` : "";
  setTimeout(() => document.querySelectorAll("[data-free]").forEach(b => b.onclick = () => freeSpace(b.dataset.free, b.dataset.title, +b.dataset.mb)), 0);
  $("#panel").innerHTML = `<div class="projlist">${banner}
    ${busy ? "" : `<label class="dropzone" id="dropzone">
      <input type="file" id="dropFile" accept="video/*,.mov,.mp4,.m4v" multiple hidden>
      <div class="dz-icon">⬆</div>
      <b>Drop your video here to start a new reel</b>
      <div class="muted">or click to choose it, or paste it with <b>Ctrl + V</b>. Several clips? Drop them all; they're joined in name order.</div>
      <div id="dzProg" hidden><div class="progress"><i id="dzBar"></i></div><small id="dzMsg"></small></div>
    </label>`}
    <div id="phoneCard"></div>
    <h1>Your reels</h1>
    ${diskNote}
    ${list.length ? list.map(p => p.archived
      ? `<div class="card row"><div style="flex:1"><b>${esc(p.title)}</b><br><small>✓ Saved to your phone · space freed on this computer</small></div>
      <button class="ghost" data-del="${p.name}" data-title="${esc(p.title)}" title="Delete this reel">🗑 Delete</button></div>`
      : `<div class="card row"><div style="flex:1"><b>${esc(p.title)}</b><br><small>${fmt(p.duration)} filmed · ${p.render === "done" ? "rendered" : "in progress"}${p.mb ? ` · uses ${gb(p.mb)}` : ""}</small></div>
      ${p.render === "done" && p.mb > 50 ? `<button class="ghost" data-free="${p.name}" data-title="${esc(p.title)}" data-mb="${p.mb}" title="Once the finished video is on your phone, delete its clips and footage here">🧹 Free up ${gb(p.mb)}</button>` : ""}
      <button class="ghost" data-del="${p.name}" data-title="${esc(p.title)}" title="Delete this reel">🗑 Delete</button>
      <button class="primary" onclick="openReel('${p.name}')">Open</button></div>`).join("") : `<div class="card muted">No projects yet.</div>`}</div>`;
}

function gb(mb) { return mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb} MB`; }
async function freeSpace(name, title, mb) {
  if (!confirm(`Is “${title}” saved on your phone?\n\nThis deletes its clips, footage and rendered videos from this computer (about ${gb(mb)}). `
    + `The finished video on your phone isn't touched. You won't be able to edit or re-render this reel here afterwards.`)) return;
  try {
    const r = await api(`/api/project/${name}/free-space`, {});
    if (r.error) return toast(r.error);
    toast(`Freed ${gb(r.freed_mb)}. ${gb(r.disk_free_mb)} free now.`);
  } catch (e) { toast(e.message); }
  home();
}

// ---------- phone uploads (Google Drive "One Take/Inbox")
async function drawPhoneCard() {
  const box = $("#phoneCard"); if (!box) return;
  let st; try { st = await api("/api/inbox"); } catch { return; }
  const ps = await api("/api/status").catch(() => ({}));
  const link = ps.phone_link || {};
  const linkHtml = link.url
    ? `<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:8px">
        <img src="/api/phone-qr.png?u=${encodeURIComponent(link.url)}" alt="" width="132" height="132" style="border-radius:10px;background:#fff" onerror="this.remove()">
        <div class="muted" style="flex:1;min-width:220px;line-height:1.6"><b>Point your phone's camera at the code</b>, or open this link on your phone:<br>
        <b style="word-break:break-all;user-select:all">${esc(link.url)}/phone</b> (upload a video)<br>
        Full studio on your phone (edit, Finish, your reels): <b style="word-break:break-all;user-select:all">${esc(link.url)}</b><br>
        ${ps.phone_pin_off ? `No PIN needed: anyone with the link can open your phone page.` : `Then enter PIN <b style="font-size:18px;letter-spacing:.15em">${esc(ps.phone_pin)}</b> (once per phone).`} Works on Wi-Fi or mobile data.
        <br><small>${link.permanent ? "<b>This link never changes.</b> Open it on your phone, then browser menu → <b>Add to Home screen</b>: One Take becomes an app icon. It works whenever this Chromebook is on."
          : "The link changes when the studio restarts, so scan the new code then. Want one that never changes (an app icon on your phone)? Ask Claude: <b>set up my permanent phone link</b>."}</small></div></div>`
    : link.state === "error"
      ? `<div class="muted" style="margin-top:6px">⚠ ${esc(link.error)}<br>Check this Chromebook is online, then turn this off and on again.</div>`
      : `<div class="muted" style="margin-top:6px">✳ Making your private phone link… (the first time takes a minute)</div>`;
  if (ps.phone_access && !link.url && link.state !== "error") setTimeout(drawPhoneCard, 3000);
  const direct = ps.phone_access
    ? `<div class="card" style="background:var(--hl)"><b>📲 Send from your phone's gallery is on</b>${linkHtml}
        <button class="ghost" id="phoneOff" style="margin-top:6px">Turn off</button>
        <button class="ghost" id="pinToggle" style="margin-top:6px">${ps.phone_pin_off ? "Ask for a PIN again" : "Don't ask for a PIN"}</button></div>`
    : `<div class="card"><b>📲 Send videos from your phone's gallery</b>
        <div class="muted" style="margin-top:4px">Pick a video on your phone, it's edited here, and you download the finished reel on your phone.
        Uses a private link protected by a PIN, so it works on Wi-Fi or mobile data.</div>
        <button class="primary" id="phoneOn" style="margin-top:8px">Turn on</button></div>`;
  setTimeout(() => {
    const on = $("#phoneOn"), off = $("#phoneOff");
    if (on) on.onclick = async () => { await api("/api/phone-access", { on: true }); drawPhoneCard(); };
    if (off) off.onclick = async () => { await api("/api/phone-access", { on: false }); drawPhoneCard(); };
    const pt = $("#pinToggle");
    if (pt) pt.onclick = async () => { await api("/api/phone-pin", { on: !!ps.phone_pin_off }); drawPhoneCard(); };
  }, 0);
  if (st.connected) {
    const last = st.status === "ready" ? `Last one: <b>${esc(st.last || "")}</b> is ready in Drive → One Take → Ready.`
      : st.status === "editing" ? `Editing <b>${esc(st.last || "")}</b> from your phone now…` : "";
    box.innerHTML = direct + `<div class="card"><b>📱 Phone uploads are on</b>
      <div class="muted" style="margin-top:4px">On your phone: film, then <b>Share → Drive → One Take → Inbox</b>. It's edited here in your style,
      and the finished reel appears in <b>Drive → One Take → Ready</b>, ready to post or open in CapCut. ${last}</div></div>`;
  } else {
    box.innerHTML = direct + `<details class="card"><summary><b>📱 Upload from anywhere with Google Drive</b> <small class="muted">(one-time setup)</small></summary>
      <ol class="muted" style="margin:8px 0 0;padding-left:18px;line-height:1.6">
        <li>On this Chromebook, open the <b>Files</b> app, right-click <b>Google Drive</b> → <b>Share with Linux</b>.</li>
        <li>Restart the studio. It creates <b>One Take → Inbox</b> and <b>Ready</b> folders in your Drive.</li>
        <li>On your phone: film, then <b>Share → Drive → One Take → Inbox</b>. The finished reel shows up in <b>Ready</b>.</li>
      </ol><small class="muted">Your Chromebook does the editing, so it needs to be on with the studio running. Videos wait in the Inbox until it is.</small></details>`;
  }
}

// ---------- new reel by drag & drop / paste
function uploadOne(file, index, onProgress) {
  return new Promise((res, rej) => {
    const x = new XMLHttpRequest();
    x.open("POST", `/api/new-reel-file?name=${encodeURIComponent(file.name || "clip.mp4")}&index=${index}`);
    x.upload.onprogress = e => e.lengthComputable && onProgress(e.loaded / e.total);
    x.onload = () => { let j = {}; try { j = JSON.parse(x.responseText); } catch {} x.status < 300 ? res(j) : rej(new Error(j.error || x.statusText)); };
    x.onerror = () => rej(new Error("The upload stopped. Is the studio still running?"));
    x.send(file);
  });
}
async function startNewReel(files) {
  const vids = [...files].filter(f => (f.type || "").startsWith("video/") || /\.(mp4|mov|m4v|mkv|webm|avi)$/i.test(f.name || ""));
  if (!vids.length) return toast("That isn't a video. Drop an .mp4 or .mov file.");
  if (S.uploading) return;
  S.uploading = true;
  const prog = $("#dzProg"), bar = $("#dzBar"), msg = $("#dzMsg");
  if (prog) prog.hidden = false;
  const total = vids.reduce((a, f) => a + f.size, 0); let done = 0;
  try {
    for (let k = 0; k < vids.length; k++) {
      await uploadOne(vids[k], k + 1, p => {
        const pct = Math.round(((done + vids[k].size * p) / total) * 100);
        if (bar) bar.style.width = pct + "%"; if (msg) msg.textContent = `Adding your video… ${pct}%`;
      });
      done += vids[k].size;
    }
    if (msg) msg.textContent = "Starting the edit…";
    await api("/api/new-reel-start", {});
    toast("Got it! Your new reel is being edited.");
    home();
  } catch (e) { toast(e.message); if (prog) prog.hidden = true; }
  finally { S.uploading = false; }
}
function bindDropzone() {
  const dz = $("#dropzone"); if (!dz) return;
  $("#dropFile").onchange = e => startNewReel(e.target.files);
  if (window.__dzBound) return;
  window.__dzBound = true;
  const onHome = () => !S.name && !!$("#dropzone");
  ["dragenter", "dragover"].forEach(ev => document.addEventListener(ev, e => {
    if (!onHome()) return; e.preventDefault(); $("#dropzone")?.classList.add("over");
  }));
  document.addEventListener("dragleave", e => { if (!e.relatedTarget) $("#dropzone")?.classList.remove("over"); });
  document.addEventListener("drop", e => {
    if (!onHome()) return; e.preventDefault(); $("#dropzone")?.classList.remove("over");
    startNewReel(e.dataTransfer.files);
  });
  document.addEventListener("paste", e => {
    if (!onHome() || e.target.matches?.("input, textarea")) return;
    const files = e.clipboardData?.files;
    if (files && files.length) { e.preventDefault(); startNewReel(files); }
    else toast("Nothing to paste. Copy the video in the Files app (Ctrl + C) first, then paste here.");
  });
}

async function loadProject(name) {
  S.name = name;
  const [p, lb, lib] = await Promise.all([api(`/api/project/${name}`), api("/api/lookbook"), api("/api/library")]);
  if (p.archived) {  // its footage was cleared after it was saved to the phone: nothing to edit here
    toast("This reel was saved to your phone and cleared from this computer to free space, so it can't be edited here.");
    S.name = null; location.hash = ""; return;
  }
  S.lookbook = lb; S.library = lib;
  setProject(p);
  v.src = media(p._proxy || p.source);  // the light preview copy when there is one (renders use the full video)
  v.muted = +(p.voice_volume ?? 1) === 0;
  $("#ptitle").textContent = p.title;
  $("#homeBtn").hidden = false;
  document.title = `${p.title} · One Take Studio`;
  for (const r of p.requests || []) S.reqStatus[r.id] = r.status;
  setTab(localStorage.getItem("cc_tab_" + name) || "cut");
  updateMusic(); applyFilter();
  fitStage();
  requestAnimationFrame(tick);
}

function setProject(p) {
  S.p = p; S.rev = p.rev || 0;
  p.overlays ||= []; p.broll ||= []; p.faces ||= { detected: [], covers: [] }; p.faces.covers ||= [];
  p.requests ||= []; p.frames ||= []; p.exports ||= {}; p.sound ||= { src: null, volume: .12, offset: 0 };
  recompute();
}

function recompute() {
  const p = S.p;
  S.segs = applyTimeEdits(buildSegments(p.words, p.duration, S.settings), p.words, p.time_cuts, p.splits, p.time_keeps);
  S.T = totalLen(S.segs);
  S.style = Object.assign({}, S.lookbook.captions.find(c => c.id === p.caption_style) || S.lookbook.captions[0]);
  if (p.caption_y != null) S.style.y = +p.caption_y;
  S.groups = p.captions === false ? [] : captionGroups(p.words, S.segs, S.style);
  S.spans = p.overlays.map(ov => [ov, overlaySpan(p, p.words, S.segs, ov)]).filter(x => x[1]);
  S.bspans = p.broll.map(b => [b, rangeOut(p.words, S.segs, b.w0, b.w1)]).filter(x => x[1]);
  S.outT = Math.min(S.outT, S.T);
  S.lastCapKey = null; S._fxt = null;
  drawTimeline();
}

// ------------------------------------------------------------------ edits, undo, save
function mutate(fn, { render = true } = {}) {
  S.hist.push(JSON.stringify(S.p)); if (S.hist.length > 80) S.hist.shift();
  S.fut = [];
  fn(S.p);
  S.p.edit_rev = (S.p.edit_rev || 0) + 1;
  recompute();
  if (render) renderPanel();
  scheduleSave();
}
function undo() { if (!S.hist.length) return; S.fut.push(JSON.stringify(S.p)); const keep = S.rev; S.p = JSON.parse(S.hist.pop()); S.p.rev = keep; setProject(S.p); renderPanel(); scheduleSave(); }
function redo() { if (!S.fut.length) return; S.hist.push(JSON.stringify(S.p)); const keep = S.rev; S.p = JSON.parse(S.fut.pop()); S.p.rev = keep; setProject(S.p); renderPanel(); scheduleSave(); }

function scheduleSave() { S.dirty = true; clearTimeout(S.saveTimer); S.saveTimer = setTimeout(save, 600); }
async function save() {
  if (S.saving) return scheduleSave();
  S.saving = true;
  try {
    const r = await api(`/api/project/${S.name}`, { project: S.p, rev: S.rev }, "PUT");
    S.rev = S.p.rev = r.rev; S.dirty = false;
  } catch (e) {
    if (e.conflict) { toast("Claude changed this project at the same time — loaded the latest version."); await reload(); }
    else toast("Couldn't save: " + e.message);
  } finally { S.saving = false; }
}
async function reload() { setProject(await api(`/api/project/${S.name}`)); S.dirty = false; renderPanel(); }

async function poll() {
  if (!S.name) return;
  let r;
  try { r = await api(`/api/project/${S.name}/rev`); } catch { return; }
  const prevJobs = S.jobs; S.jobs = r.jobs || {};
  for (const [k, j] of Object.entries(S.jobs)) {
    const was = prevJobs[k]?.status;
    if (was === "running" && j.status === "done") jobDone(k, j);
    if (was === "running" && j.status === "error") toast(`${k} failed: ${j.error}`);
  }
  updateNextBtn();
  for (const q of r.requests) {
    if (S.reqStatus[q.id] && S.reqStatus[q.id] !== q.status && (q.status === "done" || q.status === "failed")) requestFinished(q);
    S.reqStatus[q.id] = q.status;
  }
  if (r.rev !== S.rev && !S.dirty && !S.saving) { await reload(); }
  else if (Object.values(S.jobs).some(j => j.status === "running")) renderJobsOnly();
  renderTray(r.requests);
}

function jobDone(kind, j) {
  const msg = { capcut_project: "Your CapCut project is ready.", storyboard: "Storyboard ready.", render: "Your reel is rendered!", capcut: "CapCut pack is ready.", carousel: "Carousel ready.", story: "Story ready.", trials: "Trial reels are ready.", faces: `Found ${j.result} face(s).` }[kind] || `${kind} done`;
  toast(msg);
  reload();
}

// ------------------------------------------------------------------ tabs + panel
const TABS = ["cut", "visuals", "sound", "finish"];
function setTab(t) {
  S.tab = t; localStorage.setItem("cc_tab_" + S.name, t);
  document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
  const i = TABS.indexOf(t);
  updateNextBtn();
  renderPanel();
}
function updateNextBtn() {  // while the reel renders, the button shows how far along it is
  const i = TABS.indexOf(S.tab), j = S.jobs?.render, b = $("#nextBtn");
  if (j?.status === "running") { b.textContent = `Rendering… ${Math.round((j.progress || 0) * 100)}%`; b.disabled = true; return; }
  b.disabled = false;
  b.textContent = i < 3 ? `Next: ${TABS[i + 1][0].toUpperCase() + TABS[i + 1].slice(1)} ›` : "Lock in my looks";
}
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => setTab(b.dataset.tab));
$("#nextBtn").onclick = () => { const i = TABS.indexOf(S.tab); if (i < 3) setTab(TABS[i + 1]); else lockIn(); };

function renderPanel() {
  if (!S.p) return;
  const scroll = $("#panel").scrollTop;
  ({ cut: renderCut, visuals: renderVisuals, sound: renderSound, finish: renderFinish })[S.tab]();
  $("#panel").scrollTop = scroll;
  S.curWord = -1;
}

function linesOf(p) {
  const out = [];
  p.words.forEach((w, i) => {
    let l = out[out.length - 1];
    if (!l || l.id !== w.l) { l = { id: w.l, w0: i, w1: i }; out.push(l); }
    l.w1 = i;
  });
  for (const l of out) {
    l.cut = true;
    for (let i = l.w0; i <= l.w1; i++) if (!p.words[i].cut) { l.cut = false; break; }
    l.text = p.words.slice(l.w0, l.w1 + 1).map(w => w.t).join(" ");
  }
  return out;
}

function selText() { if (!S.sel) return ""; return S.p.words.slice(S.sel.a, S.sel.b + 1).map(w => w.t).join(" "); }

function wordsHTML(l, mode) {
  const p = S.p; let h = "";
  for (let i = l.w0; i <= l.w1; i++) {
    const w = p.words[i];
    if (mode === "visuals" && w.cut) continue;
    const cls = ["w"];
    if (w.cut) cls.push("cut");
    if (w.why === "filler") cls.push("filler");
    if (w.hl) cls.push("hlw");
    if (S.sel && i >= S.sel.a && i <= S.sel.b) cls.push("sel");
    h += `<span class="${cls.join(" ")}" data-i="${i}">${esc(w.t)}</span> `;
  }
  return h;
}

function lineTime(l) { const r = rangeOut(S.p.words, S.segs, l.w0, l.w1); return r ? fmt(r[0]) : "cut"; }

function selTool(mode) {
  if (!S.sel) return "";
  const p = S.p, cut = p.words.slice(S.sel.a, S.sel.b + 1).every(w => w.cut);
  const t = `“${esc(selText())}”`;
  if (mode === "cut") return `<div class="seltool"><span>${t}</span>
    ${cut ? `<button data-a="restore">↺ Bring back</button>` : `<button data-a="cut">✂ Cut</button>`}
    <button data-a="fix">✎ Fix text</button><button data-a="clear">✕</button></div>`;
  const hl = p.words.slice(S.sel.a, S.sel.b + 1).some(w => w.hl);
  return `<div class="seltool"><span>${t}</span>
    <button data-a="fix">✎ Fix text</button><button data-a="hl">${hl ? "Remove highlight" : "★ Highlight"}</button>
    <button data-a="cbreak" title="Start a new caption at this word">${p.words[S.sel.a].cbreak ? "Join captions" : "T Captions here"}</button>
    <button data-a="splitline" title="Start a new line at this word">⫶ Split line here</button><button data-a="note">✎ Add a note</button>
    <button data-a="look">✦ Add a look</button><button data-a="media">🖼 Add media</button>
    <button data-a="broll">🎬 Cut away</button><button data-a="punch">${(p.camera?.punches || []).includes(S.sel.a) ? "Remove punch-in" : "⤢ Punch in"}</button>
    <button data-a="ask">✳ Ask Claude</button><button data-a="clear">✕</button></div>`;
}

function bindLines(root) {
  root.querySelectorAll(".w").forEach(el => el.onclick = e => {
    const i = +el.dataset.i;
    // the list re-renders on every click, so spot a double-click ourselves
    const dbl = S.lastClick && S.lastClick.i === i && performance.now() - S.lastClick.t < 450;
    S.lastClick = { i, t: performance.now() };
    if (e.shiftKey && S.sel) S.sel = { a: Math.min(S.sel.a, i), b: Math.max(S.sel.b, i) };
    else S.sel = { a: i, b: i };
    seekWord(i);
    renderPanel();
    if (dbl && !e.shiftKey) fixTextModal();
  });
  root.querySelectorAll(".seltool button").forEach(b => b.onclick = () => selAction(b.dataset.a));
}

function selAction(a) {
  const { a: x, b: y } = S.sel || {};
  if (a === "clear") { S.sel = null; return renderPanel(); }
  if (a === "cut" || a === "restore") mutate(p => { for (let i = x; i <= y; i++) { p.words[i].cut = a === "cut"; if (a === "cut") p.words[i].why = "you"; } });
  if (a === "fix") return fixTextModal();
  if (a === "cbreak") return mutate(p => { p.words[x].cbreak = !p.words[x].cbreak; });
  if (a === "note") return askClaudeModal("e.g. make this word pop bigger, or add a 🔥 here");
  if (a === "splitline") return mutate(p => {
    const l = linesOf(p).find(l => l.w0 <= x && x <= l.w1); if (!l || x === l.w0) return;
    p.words.forEach((w, j) => { if (w.l > l.id) w.l += 1; else if (w.l === l.id && j >= x) w.l = l.id + 1; });
  });
  if (a === "punch") return mutate(p => {
    p.camera = p.camera || {};
    const ps = new Set(p.camera.punches || []);
    ps.has(x) ? ps.delete(x) : ps.add(x);
    p.camera.punches = [...ps].sort((m, n) => m - n);
  });
  if (a === "hl") mutate(p => { const on = !p.words.slice(x, y + 1).some(w => w.hl); for (let i = x; i <= y; i++) p.words[i].hl = on; });
  if (a === "look") addLookModal();
  if (a === "media") addMediaModal("gifs");
  if (a === "broll") addMediaModal("broll");
  if (a === "ask") askClaudeModal();
}

// ---------- fixing words the transcript got wrong
function replaceWords(p, a, b, text) {
  // Replace words a..b with the words in `text`, sharing out their timing, and keep every
  // overlay/cut-away anchored to the right words.
  const olds = p.words.slice(a, b + 1);
  const parts = text.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return;
  const s0 = olds[0].s, e0 = olds[olds.length - 1].e, step = (e0 - s0) / parts.length;
  const fresh = parts.map((t, k) => ({
    t, s: +(s0 + k * step).toFixed(3), e: +(s0 + (k + 1) * step).toFixed(3), l: olds[0].l,
    ...(olds.every(w => w.cut) ? { cut: true, why: olds[0].why } : {}),
    ...(olds.some(w => w.hl) ? { hl: true } : {}),
  }));
  p.words.splice(a, b - a + 1, ...fresh);
  const d = fresh.length - olds.length, last = a + fresh.length - 1;
  const shift = i => i > b ? i + d : Math.min(i, last);
  for (const o of [...p.overlays, ...p.broll, ...(p.requests || [])]) {
    if (o.w0 != null) o.w0 = shift(o.w0);
    if (o.w1 != null) o.w1 = shift(o.w1);
  }
  S.sel = { a, b: last };
}

function fixTextModal() {
  if (!S.sel) return;
  const { a, b } = S.sel;
  openModal(`<h1>Fix the text</h1><div class="muted">Type what you actually said. This changes the captions; the video stays the same.</div>
    <input id="fixT" style="width:100%;font-size:18px;margin-top:12px" value="${esc(selText())}">
    <div class="row" style="margin-top:12px"><span style="flex:1"></span><button id="fixCancel">Cancel</button><button class="primary" id="fixOk">Save</button></div>`, root => {
    const inp = root.querySelector("#fixT");
    inp.focus(); inp.select();
    const ok = () => { const v = inp.value.trim(); if (v && v !== selText()) mutate(p => replaceWords(p, a, b, v)); closeModal(); };
    root.querySelector("#fixOk").onclick = ok;
    root.querySelector("#fixCancel").onclick = closeModal;
    inp.onkeydown = e => { if (e.key === "Enter") ok(); };
  });
}

// ---------- CUT
function renderCut() {
  const p = S.p, ls = linesOf(p);
  const changes = p.words.filter(w => w.cut && w.why !== "filler" && w.why !== "retake").length;
  const ec = (p.engine_cuts || []);
  let h = `<div class="intro"><h1>Your cut</h1>
    <div class="muted">Tap a word to jump there. Select words (shift-click to extend) to cut them, and tap a struck word to bring it back.
    Double-click a word to fix a typo in the captions.
    Trim on the timeline below like CapCut: drag a clip's edge, cut before/after the playhead, and zoom in for precision.</div>
    <div class="row" style="margin-top:6px"><small>${changes ? changes + " word(s) changed by you" : "No changes yet"} · ${fmt(S.T / (p.speed || 1))} long (from ${fmt(p.duration)})</small>
    <span style="flex:1"></span><small>Speed</small>${[1, 1.1, 1.15, 1.2, 1.25].map(v => `<button class="chip ${(p.speed || 1) === v ? "on" : ""}" data-speed="${v}">${v}×</button>`).join("")}</div></div>`;
  h += selTool("cut");
  h += `<div class="lines">`;
  // fully-cut lines stay where they were, folded into "› N lines the engine cut" (open one to bring a line back)
  const engineOf = id => ec.find(c => c.line === id);
  for (let k = 0; k < ls.length; k++) {
    const l = ls[k];
    if (l.cut) {
      let j = k; while (j + 1 < ls.length && ls[j + 1].cut) j++;
      const grp = ls.slice(k, j + 1), key = grp[0].id;
      const byEngine = grp.every(g => engineOf(g.id) || p.words.slice(g.w0, g.w1 + 1).every(w => w.why === "filler" || w.why === "retake"));
      const open = S.openCut?.[key];
      h += `<div class="cutgrp ${open ? "open" : ""}"><button class="cutfold" data-fold="${key}">${open ? "⌄" : "›"} ${grp.length} line${grp.length > 1 ? "s" : ""} ${byEngine ? "the engine cut" : "you cut"}</button>`;
      if (open) for (const g of grp) {
        const e = engineOf(g.id), kept = e && ls.find(x => x.id === e.kept && !x.cut);
        h += `<div class="line lcut" data-l="${g.id}"><div class="ln">${String(g.id + 1).padStart(2, "0")}<small>${e ? esc(e.reason) : "cut"}</small></div>
          <div class="words">${wordsHTML(g, "cut")}</div>
          <div class="lact" style="opacity:1"><button data-restore-line="${g.id}">↺ Bring back</button>
          ${kept ? `<button data-swap="${g.id}" data-kept="${e.kept}" title="Use this take and cut the one the engine kept">Use this take</button>` : ""}
          <button data-cnote="${g.id}">✎ Add a note</button></div></div>`;
      }
      h += `</div>`;
      k = j;
      continue;
    }
    h += `<div class="line" data-l="${l.id}"><div class="ln">${String(l.id + 1).padStart(2, "0")}<small>${lineTime(l)}</small></div>
      <div class="words">${wordsHTML(l, "cut")}</div>
      <div class="lact"><button data-cut-line="${l.id}">✂ Cut line</button></div></div>`;
  }
  h += `</div>`;
  $("#panel").innerHTML = h;
  bindLines($("#panel"));
  $("#panel").querySelectorAll("[data-speed]").forEach(b => b.onclick = () => { mutate(p => p.speed = +b.dataset.speed); applySpeed(); });
  $("#panel").querySelectorAll("[data-fold]").forEach(b => b.onclick = () => { S.openCut ||= {}; S.openCut[b.dataset.fold] = !S.openCut[b.dataset.fold]; renderPanel(); });
  $("#panel").querySelectorAll("[data-cnote]").forEach(b => b.onclick = () => {
    const l = linesOf(S.p).find(x => x.id === +b.dataset.cnote); S.sel = { a: l.w0, b: l.w1 };
    askClaudeModal("e.g. keep only the second half of this line, or bring it back but cut the “um”");
  });
  const setLine = (id, cut) => mutate(p => { const l = linesOf(p).find(x => x.id === id); for (let i = l.w0; i <= l.w1; i++) { p.words[i].cut = cut; if (cut) p.words[i].why = "you"; } });
  $("#panel").querySelectorAll("[data-cut-line]").forEach(b => b.onclick = () => setLine(+b.dataset.cutLine, true));
  $("#panel").querySelectorAll("[data-restore-line],[data-bring]").forEach(b => b.onclick = () => setLine(+(b.dataset.restoreLine ?? b.dataset.bring), false));
  $("#panel").querySelectorAll("[data-swap]").forEach(b => b.onclick = () => mutate(p => {
    const ls2 = linesOf(p), a = ls2.find(x => x.id === +b.dataset.swap), k = ls2.find(x => x.id === +b.dataset.kept);
    for (let i = a.w0; i <= a.w1; i++) p.words[i].cut = false;
    for (let i = k.w0; i <= k.w1; i++) { p.words[i].cut = true; p.words[i].why = "retake"; }
    const e = p.engine_cuts.find(x => x.line === a.id); if (e) { e.line = k.id; e.kept = a.id; e.text = k.text; e.reason = "other take"; }
  }));
}

// ---------- VISUALS
const ovName = ov => ov.kind === "look" ? (lookMeta(ov.look)?.name || ov.look) + (ov.role === "hook" ? " (hook)" : "")
  : ov.kind === "emoji" ? "Emoji" : (ov.src || "").split("/").pop();
const lookMeta = id => S.lookbook.looks.find(l => l.id === id);
function ovThumb(ov) {
  if (ov.kind === "emoji") return `<img src="/assets/emoji/${ov.emoji}.png">`;
  if (ov.kind === "look") return `<span class="thumb">✦</span>`;
  return `<img src="${media(ov.src)}">`;
}

function renderVisuals() {
  const p = S.p, ls = linesOf(p).filter(l => !l.cut);
  const opts = S.lookbook.captions.map(c => `<option value="${c.id}" ${c.id === p.caption_style ? "selected" : ""}>${esc(c.name)}</option>`).join("");
  let h = `<div class="intro"><h1>Your visuals</h1><div class="muted">Every look and caption is live — nothing is rendered until you lock it in.
    Tap a word to jump there; select words to highlight them or add a look, media or a cut-away. Drag stickers around on the preview.</div></div>
    <div class="chips">
      <label class="chip">Captions <select id="capStyle">${opts}</select></label>
      <button class="chip ${p.captions === false ? "" : "on"}" id="capToggle">${p.captions === false ? "Captions off" : "Captions on"}</button>
      ${p.burned_captions ? `<button class="chip ${p.burned_captions.remove ? "on" : ""}" id="burnToggle" title="Captions that were already in your video">${p.burned_captions.remove ? "Video's own captions: removed" : "Video's own captions: kept"}</button>` : ""}
      <label class="chip">Height <input type="range" id="capY" min="0.15" max="0.9" step="0.01" value="${S.style.y ?? 0.7}" style="width:90px"></label>
      <label class="chip">Filter <select id="filterSel">${(S.lookbook.filters || []).map(x => `<option value="${x.id}" ${x.id === (p.filter || "none") ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select></label>
      <button class="chip" id="lookbookBtn">📖 Lookbook</button>
      <button class="chip" id="addLookBtn">✦ Add a look</button>
      <button class="chip" id="addMediaBtn">🖼 Add media</button>
      <button class="chip ${S.faceCard ? "on" : ""}" id="faceBtn">🙂 Cover a face ${p.faces.covers.length ? `(${p.faces.covers.length})` : ""}</button>
      <button class="chip" id="brollBtn">🎬 Cut-away clip</button>
      <button class="chip ${p.camera?.push_in ? "on" : ""}" id="pushBtn" title="Slow zoom toward you during the hook">⤢ Hook push-in ${p.camera?.push_in ? "on" : "off"}</button>
    </div>`;
  h += selTool("visuals");
  if (S.faceCard) h += faceCardHTML();
  h += `<div class="lines">`;
  for (const l of ls) {
    const ovs = p.overlays.filter(o => o.role === "hook" ? l === ls[0] : o.w0 >= l.w0 && o.w0 <= l.w1);
    const bs = p.broll.filter(b => b.w0 >= l.w0 && b.w0 <= l.w1);
    h += `<div class="line" data-l="${l.id}"><div class="ln">${String(l.id + 1).padStart(2, "0")}<small>${lineTime(l)}</small></div>
      <div class="words">${wordsHTML(l, "visuals")}</div><div class="ochips">
      ${ovs.map(o => `<button class="ochip ${S.selOv === o.id ? "on" : ""}" data-ov="${o.id}">${ovThumb(o)}<span>${esc(ovName(o))}</span></button>`).join("")}
      ${bs.map(b => `<button class="ochip" data-br="${b.id}"><span class="thumb">${b.layout === "split" ? "◫" : "🎬"}</span><span>${esc(b.src ? b.src.split("/").pop() : "white panel")}${b.layout === "split" ? " (split)" : ""}</span></button>`).join("")}
      </div></div>`;
  }
  h += `</div>`;
  $("#panel").innerHTML = h;
  bindLines($("#panel"));
  $("#capStyle").onchange = e => mutate(p => p.caption_style = e.target.value);
  $("#capToggle").onclick = () => mutate(p => p.captions = p.captions === false);
  const bt = $("#burnToggle"); if (bt) bt.onclick = () => mutate(p => p.burned_captions.remove = !p.burned_captions.remove);
  $("#capY").oninput = e => { S.style.y = +e.target.value; S.lastCapKey = null; };
  $("#capY").onchange = e => mutate(p => p.caption_y = +e.target.value, { render: false });
  $("#lookbookBtn").onclick = lookbookModal;
  $("#filterSel").onchange = e => { S.noFilter = false; mutate(p => p.filter = e.target.value, { render: false }); applyFilter(); };
  $("#addLookBtn").onclick = addLookModal;
  $("#addMediaBtn").onclick = () => addMediaModal("gifs");
  $("#brollBtn").onclick = () => addMediaModal("broll");
  $("#faceBtn").onclick = () => { S.faceCard = !S.faceCard; renderPanel(); };
  $("#pushBtn").onclick = () => mutate(p => { p.camera = p.camera || {}; p.camera.push_in = p.camera.push_in ? 0 : 7; });
  $("#panel").querySelectorAll("[data-ov]").forEach(b => b.onclick = () => overlayEditor(b.dataset.ov));
  $("#panel").querySelectorAll("[data-br]").forEach(b => b.onclick = () => brollEditor(b.dataset.br));
  if (S.faceCard) bindFaceCard();
}

// target range for new things: the selection, else the line under the playhead
function target() {
  const p = S.p;
  if (S.sel) {
    let { a, b } = S.sel;
    if (a === b) { const l = linesOf(p).find(l => l.w0 <= a && a <= l.w1); b = l.w1; }
    return { w0: a, w1: b, text: p.words.slice(S.sel.a, S.sel.b + 1).map(w => w.t).join(" ") };
  }
  const i = Math.max(0, S.curWord);
  const l = linesOf(p).find(l => l.w0 <= i && i <= l.w1) || linesOf(p)[0];
  return { w0: l.w0, w1: l.w1, text: l.text };
}

function addOverlay(ov) {
  const t = target();
  const full = Object.assign({ id: "o" + Date.now().toString(36), w0: t.w0, w1: t.w1, x: 0.5, y: 0.36, scale: 0.45, anim_in: "snap", anim_out: "none", min_dur: 1.2 }, ov);
  mutate(p => p.overlays.push(full));
  S.selOv = full.id;
  if (S.p.sfx_on !== false && (S.p.sfx || []).length)  // give the new look its sound too
    save().then(() => api(`/api/project/${S.name}/sfx-auto`, { replace: false })).then(reload).catch(() => {});
  seekWord(full.w0);
  closeModal();
  toast("Added. Tap it to adjust timing, position or animation.");
}

function lookParams(look, text) {
  const meta = lookMeta(look); const params = {};
  if (meta && meta.params) {
    if ("text" in meta.params) params.text = text;
    if ("title" in meta.params) params.title = text;
  }
  return params;
}

function lookbookModal() {
  const lb = S.lookbook, p = S.p;
  const capTiles = lb.captions.map(c => `<div class="tile ${c.id === p.caption_style ? "on" : ""}" data-cap="${c.id}">
    ${captionTile(c)}${esc(c.name)}</div>`).join("");
  const hooks = lb.looks.filter(l => l.group === "hook");
  const hookText = (p.overlays.find(o => o.role === "hook")?.params?.text) || linesOf(p).find(l => !l.cut)?.text || "Your hook";
  const saved = lb.saved || [];
  openModal(`<h1>Your lookbook</h1><div class="muted">Your saved styles. The more you save, the more Claude learns your look.</div>
    <h3>Caption styles</h3><div class="grid">${capTiles}</div>
    <h3>Hooks</h3><div class="grid frames">${hooks.map(l => `<div class="tile" data-hook="${l.id}">${onFrame(l.id, { text: hookText }, 0.8)}${esc(l.name)}</div>`).join("")}
      ${saved.filter(s => s.group === "hook").map(s => `<div class="tile" data-hooksaved="${s.id}">${onFrame(s.look, Object.assign({}, s.params, { text: hookText }), 0.8)}${esc(s.name)}</div>`).join("")}</div>
    <h3>Saved looks</h3><div class="grid frames">${saved.filter(s => s.group !== "hook").map(s => `<div class="tile" data-saved="${s.id}">${onFrame(s.look, s.params, timeOfWord(Math.max(0, S.curWord)))}${esc(s.name)}</div>`).join("") || `<small class="muted">Nothing saved yet — open any look on your reel and press “Save to lookbook”.</small>`}</div>
    <h3>Reference reels</h3>
    <div class="muted">Reels you love. Claude studies each one frame by frame (cuts, captions, graphics, sound, pace) and adds its style to your rulebook, so it guides your edits.</div>
    <label class="dropzone" id="refDrop" style="margin:8px 0;padding:14px"><b>＋ Add a reference reel</b> <small class="muted">(drop a video here or click)</small>
      <input type="file" id="refFile" accept="video/*" multiple hidden></label>
    <div id="refList">${refListHTML()}</div>`,
    root => {
      root.querySelectorAll("[data-cap]").forEach(t => t.onclick = () => { mutate(p => p.caption_style = t.dataset.cap); closeModal(); });
      const setHook = (look, params) => mutate(p => {
        let hk = p.overlays.find(o => o.role === "hook");
        const text = hk?.params?.text || linesOf(p).find(l => !l.cut)?.text || "";
        if (!hk) { hk = { id: "o" + Date.now().toString(36), kind: "look", role: "hook", w0: 0, w1: 0, x: .5, y: .2, scale: 1, anim_in: "pop", anim_out: "fade" }; p.overlays.push(hk); }
        hk.look = look; hk.params = Object.assign({}, params, { text });
      });
      root.querySelectorAll("[data-hook]").forEach(t => t.onclick = () => { setHook(t.dataset.hook, {}); closeModal(); });
      root.querySelectorAll("[data-hooksaved]").forEach(t => t.onclick = () => { const s = saved.find(x => x.id === t.dataset.hooksaved); setHook(s.look, s.params); closeModal(); });
      root.querySelectorAll("[data-saved]").forEach(t => t.onclick = () => { const s = saved.find(x => x.id === t.dataset.saved); addOverlay({ kind: "look", look: s.look, params: Object.assign({}, s.params, lookParams(s.look, target().text)), scale: s.scale ?? 1, y: s.y ?? .4, anim_in: s.anim_in ?? "pop", anim_out: s.anim_out ?? "fade" }); });
      mountSprites(root, true);
      bindRefs(root);
    });
}

// ---------- reference reels (Lookbook): videos that guide the edits
function refListHTML() {
  const refs = S.library.references || [];
  if (!refs.length) return `<small class="muted">No reference reels yet.</small>`;
  return refs.map((r, k) => {
    const job = (S.p.requests || []).find(q => q.kind === "reference" && q.src === r.path && q.status === "running");
    const st = r.guide ? "✓ learned: it's in your style guide" : job ? "Claude is studying it…" : r.studied ? "measured, not written up yet" : "not studied yet";
    return `<div class="card row" style="gap:10px;align-items:center">${r.sheet ? `<img src="${media(r.sheet)}" style="height:54px;border-radius:6px">` : `<span style="font-size:28px">🎬</span>`}
      <div style="flex:1"><b>${esc(r.name)}</b><br><small class="muted">${st}</small></div>
      <input placeholder="What do you like about it? (optional)" data-refnote="${k}" style="flex:1.3">
      <button class="primary" data-refstudy="${k}" ${job ? "disabled" : ""}>${r.guide ? "Study again" : "Study it"}</button></div>`;
  }).join("");
}
function bindRefs(root) {
  const inp = root.querySelector("#refFile"), dz = root.querySelector("#refDrop");
  if (!inp) return;
  const up = async files => {
    for (const f of files) {
      if (!f.type.startsWith("video/")) continue;
      toast(`Uploading ${f.name}…`);
      await fetch(`/api/upload?kind=references&name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
    }
    S.library = await api("/api/library");
    root.querySelector("#refList").innerHTML = refListHTML(); bindRefs(root);
  };
  inp.onchange = () => up([...inp.files]);
  dz.ondragover = e => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = e => { e.preventDefault(); dz.classList.remove("over"); up([...e.dataTransfer.files]); };
  root.querySelectorAll("[data-refstudy]").forEach(b => b.onclick = () => {
    const r = S.library.references[+b.dataset.refstudy], note = root.querySelector(`[data-refnote="${b.dataset.refstudy}"]`).value;
    sendRequest({ kind: "reference", src: r.path, text: note || "" }, "Claude is studying your reference reel. It'll ping you when it's learned the style.");
  });
}

function captionTile(c) {  // the caption style on your frame, with your words
  const i = Math.max(0, S.curWord), l = linesOf(S.p).find(l => l.w0 <= i && i <= l.w1) || linesOf(S.p)[0];
  const ws = S.p.words.slice(l.w0, l.w1 + 1).filter(w => !w.cut).slice(0, c.mode === "single" ? 1 : Math.min(3, c.max_words || 3));
  const k = 130 / 1080, st = Object.assign({}, c, { size: c.size * k * 1.15, _base: c.size * 2.4, stroke_w: (c.stroke_w || 0) });
  const html = ws.map((w, n) => wordSpan(w, n === 0, st, caseText(w.t, st))).join(" ");
  const box = c.box ? `background:${c.box.length === 9 ? hexA(c.box) : c.box};border-radius:4px;padding:0 4px;` : "";
  return `<div class="sprbox frame" style="background-image:url('${thumbUrl(timeOfWord(l.w0))}')"><div class="capline" style="top:${(c.y ?? .7) * 100}%;left:${(c.x ?? .5) * 100}%;${box}">${html}</div></div>`;
}

function captionDemo(c) {
  const st = Object.assign({}, c, { size: 26, _base: c.size });
  const words = [{ t: "this" }, { t: "is" }, { t: "huge", hl: true }];
  return `<div style="text-align:center">${words.map((w, k) => wordSpan(w, k === 1, st, caseText(w.t, st))).join(" ")}</div>`;
}

function wordSpan(w, active, st, text) {
  const emph = !!w.hl;
  const font = emph ? (st.emph_font || st.font) : st.font;
  const size = st.size * (emph ? (st.emph_scale || 1) : 1);
  const color = emph ? (st.emph_color || st.color) : active ? (st.active_color || st.color) : st.color;
  const sw = st.stroke_w || 0;
  let css = `font-family:'${font}';font-size:${size}px;color:${color};`;
  if (sw) css += `-webkit-text-stroke:${sw * 2 * (st.size / (st._base || st.size))}px ${st.stroke_color || "#000"};`;
  if (st.shadow) css += `text-shadow:0 ${size * .06}px ${size * .08}px rgba(0,0,0,.6);`;
  if (active && st.active_box && !emph) css += `background:${st.active_box};border-radius:${size * .2}px;box-shadow:0 0 0 ${size * .16}px ${st.active_box};`;
  return `<span class="cw" style="${css}">${esc(text)}</span>`;
}

function addLookModal() {
  const t = target();
  const lk = S.lookbook.looks.filter(l => !l.error);
  openModal(`<h1>Add a look</h1><div class="muted">At: “${esc(t.text)}”</div>
    <div class="muted" style="font-size:12px;margin-top:6px">Shown on your own video, at the size and height it will really be. Hover to play.</div>
    <div class="grid frames" style="margin-top:8px">${lk.map(l => `<div class="tile" data-look="${l.id}">${onFrame(l.id, lookParams(l.id, t.text), timeOfWord(t.w0))}<b>${esc(l.name)}</b><small>${esc(l.description || "")}</small></div>`).join("")}</div>
    <h3>Don't see one you like? Describe it to Claude</h3>
    <div class="muted">Show or tell Claude what you're picturing. You'll get three options to choose from.</div>
    <textarea id="lookAsk" placeholder="e.g. a count-up to 800+ people in my community, in my colors"></textarea>
    <div class="row" style="margin-top:8px">${micBtn("lookAsk")}<span style="flex:1"></span><button class="primary" id="lookSend">✳ Send to Claude</button></div>`,
    root => {
      root.querySelectorAll("[data-look]").forEach(el => el.onclick = () => {
        const id = el.dataset.look;
        addOverlay({ kind: "look", look: id, params: lookParams(id, t.text), scale: 1, y: lookY(id), min_dur: 2 });
      });
      bindMic(root);
      $("#lookSend").onclick = () => sendRequest({ kind: "look", text: $("#lookAsk").value, w0: t.w0, w1: t.w1, words: t.text });
      mountSprites(root, true);
    });
}

function addMediaModal(tab) {
  const lib = S.library;
  const t = target();
  const tabs = { gifs: "GIFs", images: "Images", emoji: "Emoji", broll: "Videos (cut-away)" };
  const body = () => {
    if (tab === "emoji") return `<div class="emojis">${S.lookbook.emoji.map(c => `<img src="/assets/emoji/${c}.png" data-emoji="${c}">`).join("")}</div>`;
    const items = lib[tab] || [];
    if (!items.length) return `<div class="card muted">Nothing here yet. Upload from your computer below, or drop files in <b>library/${tab}</b>.</div>`;
    const favs = new Set(lib.favorites || []);
    const sorted = items.slice().sort((a, b) => (favs.has(b.path) ? 1 : 0) - (favs.has(a.path) ? 1 : 0));
    const fstar = f => `<button class="favstar ${favs.has(f.path) ? "on" : ""}" data-fav="${esc(f.path)}" title="Keep in my favorites">${favs.has(f.path) ? "★" : "☆"}</button>`;
    return `<div class="grid">${sorted.map(f => tab === "broll"
      ? `<div class="tile fav" data-src="${esc(f.path)}">${fstar(f)}<video src="${media(f.path)}#t=1" muted preload="metadata"></video>${esc(f.name)}</div>`
      : `<div class="tile fav" data-src="${esc(f.path)}">${fstar(f)}<img src="${media(f.path)}" loading="lazy">${esc(f.name)}</div>`).join("")}</div>`;
  };
  const draw = () => openModal(`<h1>${tab === "broll" ? "Cut away to a clip" : "Add an image, GIF or emoji"}</h1>
    <div class="muted">At: “${esc(t.text)}”${tab === "broll" ? " — Claude's engine watches the clip and picks the best moment; you can adjust it after." : ""}</div>
    <div class="mtabs">${Object.entries(tabs).map(([k, n]) => `<button class="chip ${k === tab ? "on" : ""}" data-tab2="${k}">${n}</button>`).join("")}</div>
    ${body()}
    ${tab === "broll" ? brollFinderHTML() : ""}
    ${tab !== "emoji" ? `<div class="row" style="margin-top:12px"><label class="chip">⬆ Upload from computer <input type="file" id="upl" multiple hidden></label></div>` : ""}
    ${tab !== "broll" ? `<h3>Want it to do something? Tell Claude</h3><div class="row"><select id="ain">${animOpts("snap")}</select><small>in,</small><select id="aout">${animOpts("none")}</select><small>out</small></div>` : ""}`,
    root => {
      root.querySelectorAll("[data-tab2]").forEach(b => b.onclick = () => { tab = b.dataset.tab2; draw(); });
      const ai = () => root.querySelector("#ain")?.value || "pop", ao = () => root.querySelector("#aout")?.value || "fade";
      root.querySelectorAll("[data-emoji]").forEach(el => el.onclick = () => addOverlay({ kind: "emoji", emoji: el.dataset.emoji, scale: 0.2, anim_in: ai(), anim_out: ao() }));
      root.querySelectorAll("[data-fav]").forEach(el => el.onclick = async e => {
        e.stopPropagation();
        const on = !(lib.favorites || []).includes(el.dataset.fav);
        lib.favorites = (await api("/api/favorite", { path: el.dataset.fav, on })).favorites; draw();
      });
      root.querySelectorAll("[data-src]").forEach(el => el.onclick = async () => {
        if (tab === "broll") return addBroll(el.dataset.src, t);
        addOverlay({ kind: tab === "gifs" ? "gif" : "image", src: el.dataset.src, anim_in: ai(), anim_out: ao() });
      });
      bindBrollFinder(root, draw);
      const up = root.querySelector("#upl");
      if (up) up.onchange = async () => {
        for (const f of up.files) await fetch(`/api/upload?kind=${tab}&name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
        S.library = await api("/api/library"); draw();
      };
    });
  draw();
}

// ---------- free stock B-roll (Pixabay)
function brollFinderHTML() {
  if (!S.stock) return `<div class="card" style="margin-top:12px"><b>Find free B-roll</b>
    <div class="muted" style="font-size:13px;margin:4px 0 8px">Free stock clips from Pixabay, allowed in your reels. Sign up free at <b>pixabay.com</b>, open
    <b>pixabay.com/api/docs</b>, and copy the green key next to "key". Paste it here once; it stays on this computer.</div>
    <div class="row"><input id="pxKey" placeholder="Paste your Pixabay API key" style="flex:1"><button class="primary" id="pxSave">Save</button></div></div>`;
  const job = S.brollJob;
  return `<div class="card" style="margin-top:12px"><b>Find free B-roll</b>
    <div class="row" style="margin-top:8px"><input id="pxQ" placeholder="e.g. credit card debt, stock market crash, paying bills" style="flex:1">
    <button class="primary" id="pxGo">Search</button></div>
    <div class="row" style="margin-top:8px"><button id="pxStarter">⬇ Get the finance starter pack (~30 clips)</button>
    <small class="muted">Clips from Pixabay · free to use</small></div>
    ${job?.status === "running" ? `<div class="progress"><i style="width:${Math.max(5, job.progress * 100)}%"></i></div><small>Downloading clips…</small>` : ""}
    ${job?.status === "error" ? `<small style="color:var(--warn)">${esc(job.error)}</small>` : ""}</div>`;
}
function bindBrollFinder(root, redraw) {
  const save = root.querySelector("#pxSave");
  if (save) save.onclick = async () => {
    const k = root.querySelector("#pxKey").value.trim(); if (!k) return;
    await api("/api/stock-key", { key: k }); S.stock = true; toast("Pixabay key saved."); redraw();
  };
  const go = async starter => {
    const q = root.querySelector("#pxQ")?.value.trim();
    if (!starter && !q) return toast("Type what you're looking for.");
    S.brollJob = await api("/api/broll-find", starter ? { starter: true } : { query: q, n: 5 });
    if (S.brollJob.need_key) { S.stock = false; return redraw(); }
    redraw();
    const tick = async () => {
      S.brollJob = await api("/api/broll-job");
      if (S.brollJob.status === "running") return setTimeout(tick, 1500);
      S.library = await api("/api/library");
      if (S.brollJob.status === "done") toast(`Added ${S.brollJob.result.length} clip(s) to your library.`);
      if (!$("#modal").hidden) redraw();
    };
    setTimeout(tick, 1500);
  };
  const g = root.querySelector("#pxGo"); if (g) g.onclick = () => go(false);
  const q = root.querySelector("#pxQ"); if (q) q.onkeydown = e => { if (e.key === "Enter") go(false); };
  const st = root.querySelector("#pxStarter"); if (st) st.onclick = () => go(true);
}

const ANIMS = ["snap", "none", "pop", "fade", "rise", "fade-quick", "slide-up", "slide-down", "slide-left", "slide-right", "spin", "zoom"];
const animOpts = cur => ANIMS.map(a => `<option ${a === cur ? "selected" : ""}>${a}</option>`).join("");

async function addBroll(src, t) {
  closeModal();
  const sp = rangeOut(S.p.words, S.segs, t.w0, t.w1);
  const dur = sp ? sp[1] - sp[0] : 3;
  toast("Watching the clip to find the best moment…");
  const r = await api(`/api/project/${S.name}/broll-moment`, { src, dur });
  const b = { id: "b" + Date.now().toString(36), src, w0: t.w0, w1: t.w1, clip_start: r.clip_start };
  mutate(p => p.broll.push(b));
  seekWord(t.w0);
  toast(`Cut-away added from ${r.clip_start.toFixed(1)}s of the clip.`, "Adjust", () => brollEditor(b.id));
}

function brollEditor(id) {
  const orig = S.p.broll.find(x => x.id === id);
  if (!orig) return;
  const b = JSON.parse(JSON.stringify(orig));  // edit a copy; Apply saves it
  const isVid = b.src && !/\.(png|jpe?g|webp|gif)$/i.test(b.src);
  const kept = i => !S.p.words[i]?.cut;
  const step = (i, d) => { let j = i + d; while (j >= 0 && j < S.p.words.length && !kept(j)) j += d; return j >= 0 && j < S.p.words.length ? j : i; };
  const span = () => rangeOut(S.p.words, S.segs, b.w0, b.w1) || [0, 0];
  openModal(`<div class="muted" style="font-size:11px;letter-spacing:.08em">CUT-AWAY · YOUR VOICE KEEPS GOING</div>
    <h1>${esc(b.src ? b.src.split("/").pop() : "Plain panel " + (b.color || "#FFFFFF"))}</h1>
    <div class="row" style="align-items:flex-start;gap:16px;margin-top:10px">
      ${isVid ? `<video id="bprev" src="${media(b.src)}" style="width:150px;border-radius:10px" muted playsinline></video>` : b.src ? `<img src="${media(b.src)}" style="width:150px;border-radius:10px">` : ""}
      <div style="flex:1" class="kv">
        ${isVid ? `<label>Which moment plays</label><div><div class="row"><input id="bcs" type="range" min="0" max="60" step="0.1" value="${b.clip_start || 0}" style="flex:1"></div>
          <small id="bcsv" class="muted"></small> <button class="ghost" id="bpick">✦ Engine's pick</button></div>` : ""}
        <label>When it's on screen</label><div><b id="bwhen"></b><div class="muted" id="bwords" style="font-size:12px"></div></div>
        <label>Starts</label><div class="row"><button data-mv="s-">A word earlier</button><button data-mv="s+">A word later</button></div>
        <label>Ends</label><div class="row"><button data-mv="e-">A word earlier</button><button data-mv="e+">A word later</button></div>
        ${isVid ? `<label>Its sound</label><div class="row"><button class="chip" data-au="muted">Muted</button><button class="chip" data-au="under">On, under my voice</button></div>` : ""}
        <label>Comes in</label><div class="row"><button class="chip" data-tr="cut">Cut</button><button class="chip" data-tr="fade">Fade</button></div>
        <label>Layout</label><div class="row"><button class="chip" data-lay="full">Full screen</button><button class="chip" data-lay="split">Split: clip on top, you below</button><button class="chip" data-lay="card">Card over you (blurred)</button></div>
      </div></div>
    <div class="row" style="margin-top:16px"><button id="bdel">Remove</button><span style="flex:1"></span><button id="bcancel">Cancel</button><button class="primary" id="bok">Apply</button></div>`,
    root => {
      const pv = root.querySelector("#bprev"), cs = root.querySelector("#bcs");
      const refresh = () => {
        const [a, z] = span(), dur = z - a;
        root.querySelector("#bwhen").textContent = `${fmt(a)} · ${dur.toFixed(1)}s`;
        root.querySelector("#bwords").textContent = "“" + S.p.words.slice(b.w0, b.w1 + 1).filter((w, k) => kept(b.w0 + k)).map(w => w.t).join(" ") + "”";
        if (cs) {
          const total = pv && pv.duration ? pv.duration : 0;
          root.querySelector("#bcsv").textContent = total ? `${(+cs.value).toFixed(1)}s to ${(+cs.value + dur).toFixed(1)}s of your ${total.toFixed(1)}s clip` : `from ${(+cs.value).toFixed(1)}s`;
        }
        root.querySelectorAll("[data-au]").forEach(x => x.classList.toggle("on", (b.audio || "muted") === x.dataset.au));
        root.querySelectorAll("[data-tr]").forEach(x => x.classList.toggle("on", (b.trans || "cut") === x.dataset.tr));
        root.querySelectorAll("[data-lay]").forEach(x => x.classList.toggle("on", (b.layout || "full") === x.dataset.lay));
      };
      if (pv) pv.onloadedmetadata = () => { cs.max = Math.max(0, pv.duration - 0.3).toFixed(1); pv.currentTime = b.clip_start || 0; refresh(); };
      if (cs) cs.oninput = () => { b.clip_start = +cs.value; if (pv) pv.currentTime = b.clip_start; refresh(); };
      const pk = root.querySelector("#bpick");
      if (pk) pk.onclick = async () => {
        const [a, z] = span();
        pk.textContent = "Watching the clip…";
        const r = await api(`/api/project/${S.name}/broll-moment`, { src: b.src, dur: z - a });
        b.clip_start = r.clip_start; cs.value = r.clip_start; if (pv) pv.currentTime = r.clip_start; pk.textContent = "✦ Engine's pick"; refresh();
      };
      root.querySelectorAll("[data-mv]").forEach(x => x.onclick = () => {
        const m = x.dataset.mv;
        if (m === "s-") b.w0 = step(b.w0, -1);
        if (m === "s+" && step(b.w0, 1) <= b.w1) b.w0 = step(b.w0, 1);
        if (m === "e-" && step(b.w1, -1) >= b.w0) b.w1 = step(b.w1, -1);
        if (m === "e+") b.w1 = step(b.w1, 1);
        refresh();
      });
      root.querySelectorAll("[data-au]").forEach(x => x.onclick = () => { b.audio = x.dataset.au; refresh(); });
      root.querySelectorAll("[data-tr]").forEach(x => x.onclick = () => { b.trans = x.dataset.tr; refresh(); });
      root.querySelectorAll("[data-lay]").forEach(x => x.onclick = () => { b.layout = x.dataset.lay; refresh(); });
      root.querySelector("#bdel").onclick = () => { mutate(p => p.broll = p.broll.filter(x => x.id !== id)); closeModal(); };
      root.querySelector("#bcancel").onclick = closeModal;
      root.querySelector("#bok").onclick = () => { mutate(p => { const i = p.broll.findIndex(x => x.id === id); p.broll[i] = b; }); closeModal(); seekWord(b.w0); };
      refresh();
    });
}

function overlayEditor(id) {
  const ov = S.p.overlays.find(o => o.id === id);
  if (!ov) return;
  S.selOv = id;
  const meta = ov.kind === "look" ? lookMeta(ov.look) : null;
  const endOpts = S.p.words.map((w, i) => i >= ov.w0 && i <= ov.w0 + 80 && !w.cut ? `<option value="${i}" ${i === ov.w1 ? "selected" : ""}>${esc(w.t)}</option>` : "").join("");
  const params = Object.assign({}, meta?.params || {}, ov.params || {});
  const paramRows = meta ? Object.entries(params).map(([k, val]) => `<label>${esc(k)}</label>` + (typeof val === "boolean"
    ? `<input type="checkbox" data-pk="${k}" ${val ? "checked" : ""}>`
    : `<input data-pk="${k}" data-num="${typeof val === "number"}" value="${esc(val)}">`)).join("") : "";
  openModal(`<h1>${esc(ovName(ov))}</h1>
    <div class="kv">
      ${ov.role === "hook" ? `<label>Shows</label><div>for the first <input id="hdur" type="number" step="0.5" min="1" max="10" value="${S.p.hook_duration || 3}" style="width:70px"> seconds</div>`
      : `<label>Ends at word</label><select id="oend">${endOpts}</select>`}
      <label>Position</label><div class="row"><button data-pos="0.18">Top</button><button data-pos="0.4">Middle</button><button data-pos="0.55">Lower</button><small>or drag it on the preview</small></div>
      <label>Size</label><input id="osc" type="range" min="0.05" max="${ov.kind === "look" ? 2 : 1}" step="0.01" value="${ov.scale ?? 0.45}">
      <label>Animate in</label><select id="oin">${animOpts(ov.anim_in ?? "pop")}</select>
      <label>Animate out</label><select id="oout">${animOpts(ov.anim_out ?? "fade")}</select>
      <label>Background</label><label class="row"><input type="checkbox" id="odim" ${ov.dim ? "checked" : ""}> dim it so this reads (receipt stacks)</label>
      <label>Movement</label><label class="row"><input type="checkbox" id="opush" ${ov.push ? "checked" : ""}> slow push-in while it's on screen</label>
      ${paramRows}
    </div>
    <h3>Want something different? Tell Claude</h3>
    <textarea id="onote" placeholder="e.g. slide in from the left, then spin out when I say “insane”">${esc(ov.note || "")}</textarea>
    <div class="row" style="margin-top:10px">${micBtn("onote")}<button id="osend">✳ Send to Claude</button>
      ${ov.kind !== "look" ? `<button id="oswap">⇄ Swap</button>` : `<button id="osave">☆ Save to lookbook</button>`}
      <span style="flex:1"></span><button id="odel">Remove</button><button class="primary" id="ook">Done</button></div>`,
    root => {
      bindMic(root);
      const apply = () => mutate(p => {
        const o = p.overlays.find(o => o.id === id);
        if (root.querySelector("#oend")) o.w1 = +root.querySelector("#oend").value;
        if (root.querySelector("#hdur")) p.hook_duration = +root.querySelector("#hdur").value;
        o.scale = +root.querySelector("#osc").value;
        o.anim_in = root.querySelector("#oin").value; o.anim_out = root.querySelector("#oout").value;
        o.dim = root.querySelector("#odim").checked ? 0.5 : 0; o.push = root.querySelector("#opush").checked;
        o.note = root.querySelector("#onote").value;
        if (meta) { o.params = o.params || {}; root.querySelectorAll("[data-pk]").forEach(inp => { o.params[inp.dataset.pk] = inp.type === "checkbox" ? inp.checked : inp.dataset.num === "true" ? +inp.value : inp.value; }); }
      }, { render: false });
      root.querySelectorAll("input,select").forEach(el => el.onchange = apply);
      root.querySelector("#osc").oninput = e => { ov.scale = +e.target.value; };
      root.querySelectorAll("[data-pos]").forEach(b => b.onclick = () => mutate(p => p.overlays.find(o => o.id === id).y = +b.dataset.pos, { render: false }));
      root.querySelector("#odel").onclick = () => { mutate(p => p.overlays = p.overlays.filter(o => o.id !== id)); closeModal(); };
      root.querySelector("#ook").onclick = () => { apply(); closeModal(); renderPanel(); };
      root.querySelector("#osend").onclick = () => { apply(); sendRequest({ kind: "edit", overlay: id, text: root.querySelector("#onote").value, w0: ov.w0, w1: ov.w1 }); };
      const sw = root.querySelector("#oswap"); if (sw) sw.onclick = () => { closeModal(); swapMedia(id); };
      const sv = root.querySelector("#osave"); if (sv) sv.onclick = async () => {
        const name = prompt("Name this look", ovName(ov)); if (!name) return;
        const entry = { id: "s" + Date.now().toString(36), name, look: ov.look, params: Object.assign({}, ov.params), scale: ov.scale, y: ov.y, anim_in: ov.anim_in, anim_out: ov.anim_out, group: ov.role === "hook" ? "hook" : "look" };
        if (entry.params.text && ov.role !== "hook") delete entry.params.text;
        await api(`/api/project/${S.name}/save-look`, entry);
        S.lookbook = await api("/api/lookbook");
        toast("Saved to your lookbook.");
      };
      seekWord(ov.role === "hook" ? 0 : ov.w0, ov.role === "hook");
    });
}

function swapMedia(id) {
  const ov = S.p.overlays.find(o => o.id === id);
  const tab = ov.kind === "emoji" ? "emoji" : ov.kind === "gif" ? "gifs" : "images";
  const items = tab === "emoji" ? S.lookbook.emoji.map(c => ({ emoji: c })) : S.library[tab];
  openModal(`<h1>Swap</h1><div class="grid">${items.map((f, k) => `<div class="tile" data-k="${k}">${f.emoji ? `<img src="/assets/emoji/${f.emoji}.png">` : `<img src="${media(f.path)}">`}</div>`).join("")}</div>`,
    root => root.querySelectorAll("[data-k]").forEach(el => el.onclick = () => {
      const f = items[+el.dataset.k];
      mutate(p => { const o = p.overlays.find(o => o.id === id); if (f.emoji) o.emoji = f.emoji; else o.src = f.path; });
      closeModal();
    }));
}

// ---------- faces
function faceCardHTML() {
  const f = S.p.faces, job = S.jobs.faces;
  let h = `<div class="card"><h3 style="margin-top:0">Cover a face</h3>`;
  if (job?.status === "running") return h + `<div class="muted">Finding faces…</div><div class="progress"><i style="width:${job.progress * 100}%"></i></div></div>`;
  if (!f.detected.length) return h + `<div class="muted">Find every face in the reel, then pick which one to cover — it follows them across the video.</div>
    <button class="primary" id="findFaces" style="margin-top:8px">Find faces</button></div>`;
  const cur = S.faceSel || f.detected[0].id;
  const cov = f.covers.find(c => c.face === cur);
  h += `<div class="muted">Which face should be covered?</div><div class="facepick" style="margin:10px 0">${f.detected.map(d => `<div class="face ${d.id === cur ? "on" : ""}" data-face="${d.id}"><img src="${media(d.thumb)}">${esc(d.name)}${f.covers.some(c => c.face === d.id) ? " ✓" : ""}</div>`).join("")}</div>
    <div class="muted">Cover with</div><div class="row" style="margin:6px 0">
      <button class="chip ${cov?.style === "blur" ? "on" : ""}" data-cs="blur">Blur</button>
      <button class="chip ${cov?.style === "pixelate" ? "on" : ""}" data-cs="pixelate">Pixelate</button>
      <button class="chip ${cov?.style === "image" ? "on" : ""}" data-cs="image">Your image</button>
      ${cov ? `<button class="chip" data-cs="none">Remove cover</button>` : ""}</div>
    <div class="emojis">${S.lookbook.emoji.map(c => `<img src="/assets/emoji/${c}.png" data-ce="${c}" class="${cov?.style === "emoji" && cov.emoji === c ? "on" : ""}">`).join("")}</div>
    ${cov ? `<div class="row" style="margin-top:10px"><small>Size</small><input type="range" id="cscale" min="0.8" max="2.5" step="0.05" value="${cov.scale || 1.3}"></div>` : ""}
    ${cov && f.detected.length > 1 ? `<div class="row" style="margin-top:8px"><button id="everyFace">Use on every face</button></div>` : ""}
    ${faceChecks()}
    <div class="row" style="margin-top:8px"><button id="refind">Find faces again</button><small class="muted">Check the preview — it tracks them across the video.</small></div></div>`;
  return h;
}
function faceChecks() {
  // moments where a covered face was turned away / out of view, so the cover held its last spot
  const f = S.p.faces, out = [];
  for (const c of f.covers) {
    const d = f.detected.find(d => d.id === c.face); if (!d) continue;
    const tr = d.track;
    for (let k = 1; k < tr.length; k++) {
      if (tr[k][0] - tr[k - 1][0] > 0.7) {
        const o = srcToOut(S.segs, tr[k - 1][0] + 0.3);
        if (o != null) out.push(o);
      }
    }
  }
  const uniq = [...new Set(out.map(t => Math.round(t * 2) / 2))].sort((a, b) => a - b).slice(0, 12);
  if (!uniq.length) return "";
  return `<div style="margin-top:10px"><b style="font-size:13px">Check these moments</b>
    <div class="muted" style="font-size:12px">A face turned away or left the frame here, so the cover held its spot. Tap to look.</div>
    <div class="row" style="margin-top:6px">${uniq.map(t => `<button class="chip" data-fjump="${t}">▶ ${fmt(t)}</button>`).join("")}</div></div>`;
}
function bindFaceCard() {
  const r = $("#panel");
  r.querySelectorAll("[data-fjump]").forEach(b => b.onclick = () => seek(+b.dataset.fjump));
  const ev = r.querySelector("#everyFace");
  if (ev) ev.onclick = () => mutate(p => {
    const c = p.faces.covers.find(c => c.face === (S.faceSel || p.faces.detected[0].id));
    p.faces.covers = p.faces.detected.map(d => Object.assign({}, c, { face: d.id }));
  });
  const ff = r.querySelector("#findFaces") || r.querySelector("#refind");
  if (ff) ff.onclick = async () => { S.jobs.faces = await api(`/api/project/${S.name}/faces`, {}); renderPanel(); };
  const cur = () => S.faceSel || S.p.faces.detected[0]?.id;
  r.querySelectorAll("[data-face]").forEach(el => el.onclick = () => { S.faceSel = el.dataset.face; renderPanel(); });
  const setCover = upd => mutate(p => {
    p.faces.covers = p.faces.covers.filter(c => c.face !== cur());
    if (upd) p.faces.covers.push(Object.assign({ face: cur(), scale: 1.3 }, upd));
  });
  r.querySelectorAll("[data-ce]").forEach(el => el.onclick = () => setCover({ style: "emoji", emoji: el.dataset.ce }));
  r.querySelectorAll("[data-cs]").forEach(el => el.onclick = () => {
    const s = el.dataset.cs;
    if (s === "none") return setCover(null);
    if (s === "image") {
      const imgs = S.library.images;
      if (!imgs.length) return toast("Add a picture to library/images (or upload one in Add media) first.");
      return openModal(`<h1>Cover with an image</h1><div class="grid">${imgs.map((f, k) => `<div class="tile" data-k="${k}"><img src="${media(f.path)}">${esc(f.name)}</div>`).join("")}</div>`,
        root => root.querySelectorAll("[data-k]").forEach(t => t.onclick = () => { setCover({ style: "image", image: imgs[+t.dataset.k].path }); closeModal(); }));
    }
    setCover({ style: s });
  });
  const sc = r.querySelector("#cscale");
  if (sc) sc.onchange = () => mutate(p => { const c = p.faces.covers.find(c => c.face === cur()); if (c) c.scale = +sc.value; }, { render: false });
}

// ---------- SOUND
function renderSound() {
  const p = S.p, snds = S.library.sounds, cur = p.sound.src;
  p.sfx ||= [];
  const fxLib = S.library.sfx || [];
  const fxName = src => (fxLib.find(x => x.path === src) || {}).name || (src || "").split("/").pop();
  const ls = linesOf(p).filter(l => !l.cut);
  const lineFor = fx => { const w = sfxLine(fx); if (w == null) return null; return ls.find(l => l.w0 <= w && w <= l.w1) || ls.find(l => l.w0 >= w) || ls[ls.length - 1]; };
  const byLine = new Map();
  for (const fx of p.sfx) { const l = lineFor(fx); if (!l) continue; if (!byLine.has(l.id)) byLine.set(l.id, []); byLine.get(l.id).push(fx); }
  const fxTime = fx => { const t = sfxTimes().get(fx.id); return t == null ? "" : fmt(t) + "." + String(Math.floor((t % 1) * 10)); };
  let h = `<div class="intro"><h1>Your sound</h1><div class="muted">Every moment that moves has a sound, timed to its motion. Play one, nudge it, or swap it. Then pick the music bed underneath.</div></div>
    <div class="card"><div class="row"><b style="flex:1">Sound FX</b>
      <label class="row"><input type="checkbox" id="fxOn" ${p.sfx_on === false ? "" : "checked"}> on</label></div>
      <div class="row" style="margin-top:8px"><small>Effects volume</small><input type="range" id="fxVol" min="0" max="1.2" step="0.05" value="${p.sfx_volume ?? 0.6}" style="flex:1">
      <button id="fxAuto">✳ ${p.sfx.length ? "Redo sounds for every look" : "Add sounds for every look"}</button></div>
      ${p.sfx.length ? "" : `<div class="muted" style="margin-top:6px">No sound effects yet. Tap the button and every card, sticker, cut-away and punch-in gets a matching sound.</div>`}</div>
    <div class="lines">`;
  for (const l of ls) {
    const fxs = (byLine.get(l.id) || []).slice().sort((a, b) => (sfxTimes().get(a.id) ?? 0) - (sfxTimes().get(b.id) ?? 0));
    h += `<div class="line" data-l="${l.id}"><div class="ln">${String(l.id + 1).padStart(2, "0")}<small>${lineTime(l)}</small></div>
      <div><div class="words">${wordsHTML(l, "visuals")}</div>
      ${fxs.map(fx => `<div class="fxrow ${fx.muted ? "muted-fx" : ""}" data-fx="${fx.id}">
        <small class="fxt">${fxTime(fx)}</small><span class="fxn">${esc(fxName(fx.src))}</span><small class="muted">${fx.auto ? "Matched to the motion" : "Added by you"}</small>
        <span style="flex:1"></span>
        <button data-fxa="play" title="Play">▶</button><button data-fxa="swap">⇄ Swap</button>
        <button data-fxa="earlier" title="0.1 s earlier">‹</button><button data-fxa="later" title="0.1 s later">›</button>
        <button data-fxa="mute" title="${fx.muted ? "Unmute" : "Mute"}" class="${fx.muted ? "on" : ""}">${fx.muted ? "🔇" : "🔈"}</button>
        <button data-fxa="del" title="Delete">🗑</button></div>`).join("")}
      <div class="row" style="margin-top:4px"><button class="ghost" data-fxadd="${l.w0}">＋ Add a sound</button><button class="ghost" data-fxnote="${l.id}">✳ Note for Claude</button></div></div><div></div></div>`;
  }
  h += `</div>
    <div class="intro" style="margin-top:22px"><h1 style="font-size:20px">Music bed</h1><div class="muted">Built-in tracks, sounds you've downloaded, or tracks from your music subscription. Drop them in <b>library/sounds</b> or upload here.</div></div>
    <div class="card kv"><label>Volume</label><input type="range" id="vol" min="0" max="0.6" step="0.01" value="${p.sound.volume ?? .12}">
    <label>Start the song at</label><div class="row"><input type="number" id="off" min="0" step="0.5" value="${p.sound.offset || 0}" style="width:80px"><small>seconds into the track</small></div></div>
    <div class="lines"><div class="sound ${!cur ? "on" : ""}"><span>🔇</span><b>No music</b><button data-use="">${!cur ? "Using" : "Use"}</button></div>
    ${snds.map(s => `<div class="sound ${s.path === cur ? "on" : ""}"><button data-play="${esc(s.path)}">▶</button><b>${esc(s.name)}</b><button data-use="${esc(s.path)}">${s.path === cur ? "Using" : "Swap to this"}</button></div>`).join("")}</div>
    <div class="row" style="margin-top:12px"><label class="chip">⬆ Upload music <input type="file" id="supl" accept="audio/*" multiple hidden></label>
      <label class="chip">⬆ Upload a sound effect <input type="file" id="fxupl" accept="audio/*" multiple hidden></label></div>`;
  $("#panel").innerHTML = h;
  bindLines($("#panel"));
  const pa = S.prevAudio || (S.prevAudio = new Audio());
  const playSrc = src => { pa.pause(); pa.src = media(src); pa.currentTime = 0; pa.play().catch(() => {}); };
  $("#panel").querySelectorAll("[data-play]").forEach(b => b.onclick = () => {
    if (pa.dataset.src === b.dataset.play && !pa.paused) { pa.pause(); b.textContent = "▶"; return; }
    pa.src = media(b.dataset.play); pa.dataset.src = b.dataset.play; pa.play(); b.textContent = "❚❚";
  });
  $("#panel").querySelectorAll("[data-use]").forEach(b => b.onclick = () => { pa.pause(); mutate(p => p.sound.src = b.dataset.use || null); updateMusic(); });
  $("#vol").oninput = e => { S.p.sound.volume = +e.target.value; music.volume = Math.min(1, S.p.sound.volume * 2.5); };
  $("#vol").onchange = e => mutate(p => p.sound.volume = +e.target.value, { render: false });
  $("#off").onchange = e => mutate(p => p.sound.offset = +e.target.value, { render: false });
  $("#fxOn").onchange = e => mutate(p => p.sfx_on = e.target.checked);
  $("#fxVol").onchange = e => mutate(p => p.sfx_volume = +e.target.value, { render: false });
  $("#fxAuto").onclick = async () => {
    if (S.dirty) await save();
    const r = await api(`/api/project/${S.name}/sfx-auto`, { replace: true });
    await reload(); toast(`${r.sfx.length} sounds placed, each timed to its motion.`);
  };
  const upl = async (inp, kind) => {
    for (const f of inp.files) await fetch(`/api/upload?kind=${kind}&name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
    S.library = await api("/api/library"); renderPanel();
  };
  $("#supl").onchange = e => upl(e.target, "sounds");
  $("#fxupl").onchange = e => upl(e.target, "sfx");
  $("#panel").querySelectorAll(".fxrow").forEach(row => {
    const id = row.dataset.fx;
    row.querySelectorAll("[data-fxa]").forEach(btn => btn.onclick = () => {
      const a = btn.dataset.fxa, fx = S.p.sfx.find(x => x.id === id);
      if (a === "play") return playSrc(fx.src);
      if (a === "swap") return sfxPicker(src => mutate(p => { const x = p.sfx.find(x => x.id === id); x.src = src; x.auto = false; }), fx.src);
      mutate(p => {
        const x = p.sfx.find(x => x.id === id);
        if (a === "earlier") { x.offset = +((x.offset || 0) - 0.1).toFixed(2); x.auto = false; }
        if (a === "later") { x.offset = +((x.offset || 0) + 0.1).toFixed(2); x.auto = false; }
        if (a === "mute") x.muted = !x.muted;
        if (a === "del") p.sfx = p.sfx.filter(y => y.id !== id);
      });
    });
  });
  $("#panel").querySelectorAll("[data-fxadd]").forEach(b => b.onclick = () => {
    const w = +b.dataset.fxadd;
    const at = S.curWord >= 0 && linesOf(S.p).find(l => l.w0 === w && l.w0 <= S.curWord && S.curWord <= l.w1) ? S.curWord : w;
    sfxPicker(src => mutate(p => p.sfx.push({ id: "s" + Date.now().toString(36), src, anchor: { w: at }, offset: 0, volume: 0.45, muted: false, auto: false })));
  });
  $("#panel").querySelectorAll("[data-fxnote]").forEach(b => b.onclick = () => {
    const l = linesOf(S.p).find(l => l.id === +b.dataset.fxnote);
    S.sel = { a: l.w0, b: l.w1 }; askClaudeModal("e.g. add a whoosh when I say “one-on-one”, or make the pop softer");
  });
}

function sfxLine(fx) {
  const a = fx.anchor || {};
  if (a.ov) { const o = S.p.overlays.find(o => o.id === a.ov); return o ? (o.role === "hook" ? 0 : o.w0) : null; }
  if (a.broll) { const b = S.p.broll.find(b => b.id === a.broll); return b ? b.w0 : null; }
  if (a.fx) { const f = (S.p.fx || []).find(f => f.id === a.fx); return f ? f.w : null; }
  return a.w ?? null;
}
function sfxTimes() {  // mirror of engine/sfx.py times()
  if (S._fxt && S._fxtRev === S.segs) return S._fxt;
  const m = new Map(), p = S.p;
  for (const fx of p.sfx || []) {
    const a = fx.anchor || {}; let t = null;
    if (a.ov) { const hit = S.spans.find(([o]) => o.id === a.ov); t = hit ? hit[1][0] : null; }
    else if (a.broll) { const hit = (S.bspans || []).find(([b]) => b.id === a.broll); t = hit ? hit[1][0] : null; }
    else if (a.fx) { const f = (p.fx || []).find(f => f.id === a.fx); const o = f ? wordOut(p.words, S.segs, f.w) : null; t = o ? o[0] : null; }
    else if (a.w != null) { const o = wordOut(p.words, S.segs, a.w); t = o ? o[0] : null; }
    if (t != null) m.set(fx.id, Math.max(0, t + (+fx.offset || 0)));
  }
  S._fxt = m; S._fxtRev = S.segs; return m;
}
function sfxPicker(onPick, current) {
  const all = S.library.sfx || [];
  const pa = S.prevAudio || (S.prevAudio = new Audio());
  const draw = q => {
    const list = all.filter(x => !q || (x.name + " " + x.tags).toLowerCase().includes(q.toLowerCase()));
    return list.map((x, k) => `<div class="sound ${x.path === current ? "on" : ""}"><button data-p="${k}">▶</button>
      <div><b>${esc(x.name)}</b><br><small class="muted">${esc(x.source)} · ${x.dur}s</small></div><button data-u="${k}">${x.path === current ? "Using" : "Use"}</button></div>`).join("") || `<div class="muted" style="padding:12px">No sounds match.</div>`;
  };
  openModal(`<h1>Find a sound</h1><input id="fxq" placeholder="Search: whoosh, pop, click, money…" style="width:100%;margin:8px 0">
    <div class="lines" id="fxlist">${draw("")}</div>
    <div class="muted" style="margin-top:10px;font-size:12px">Add your own effects (or ones from your sound subscription) to <b>library/sfx</b>; they show up first.</div>`, root => {
    const bind = list => {
      const items = all.filter(x => !root.querySelector("#fxq").value || (x.name + " " + x.tags).toLowerCase().includes(root.querySelector("#fxq").value.toLowerCase()));
      root.querySelectorAll("[data-p]").forEach(b => b.onclick = () => { pa.pause(); pa.src = media(items[+b.dataset.p].path); pa.play().catch(() => {}); });
      root.querySelectorAll("[data-u]").forEach(b => b.onclick = () => { pa.pause(); onPick(items[+b.dataset.u].path); closeModal(); });
    };
    root.querySelector("#fxq").oninput = e => { root.querySelector("#fxlist").innerHTML = draw(e.target.value); bind(); };
    bind();
    root.querySelector("#fxq").focus();
  });
}

// live preview: fire each sound effect as the playhead passes it
const fxPool = {};
function playSfxBetween(t0, t1) {
  if (S.p.sfx_on === false || !(S.p.sfx || []).length || t1 <= t0 || t1 - t0 > 0.5) return;
  const vol = +(S.p.sfx_volume ?? 0.6);
  for (const fx of S.p.sfx) {
    if (fx.muted) continue;
    const t = sfxTimes().get(fx.id);
    if (t == null || t < t0 || t >= t1) continue;
    const a = new Audio(media(fx.src));
    a.volume = Math.max(0, Math.min(1, (+fx.volume || 0.4) * vol * 1.6));
    a.play().catch(() => {});
  }
}

function updateMusic() {
  const src = S.p.sound.src;
  if (!src) { music.removeAttribute("src"); music.load(); return; }
  if (music.dataset.src !== src) { music.src = media(src); music.dataset.src = src; }
  music.volume = Math.min(1, (S.p.sound.volume ?? .12) * 2.5);
}

// ---------- FINISH
function stale() { const r = S.p.render || {}; return r.status === "done" && (r.edit_rev ?? -1) !== (S.p.edit_rev || 0); }
function jobBar(kind) { const j = S.jobs[kind]; return j?.status === "running" ? `<div class="progress"><i style="width:${(j.progress * 100).toFixed(0)}%"></i></div><small>Working… ${(j.progress * 100).toFixed(0)}%</small>` : ""; }

function renderFinish() {
  const p = S.p, r = p.render || {}, ex = p.exports || {};
  const done = r.status === "done";
  let h = `<div class="intro"><h1>Finish</h1><div class="muted">Lock in your looks to render the reel. Then turn it into more: frames, a carousel, a story and trial reels.</div></div>
  <div class="card"><h3 style="margin-top:0">1 · Your reel</h3>
    ${!done ? `<div class="muted">Nothing is rendered yet — everything so far has been a live preview.</div>` : ""}
    ${stale() ? `<div class="muted">You've made changes since the last render.</div>` : ""}
    <div class="row" style="margin:8px 0"><button class="primary" id="lock">${done ? "Render again" : "🔒 Lock in my looks"}</button></div>${jobBar("render")}
    <div id="edgeCard"></div>
    ${done ? `<video class="finalv" controls src="${media(r.file)}?v=${p.edit_rev || 0}-${p.rev}"></video>
      <div class="row" style="margin-top:10px"><a download href="${media(r.file)}"><button>⬇ Download MP4</button></a>
      ${r.phone ? `<a download href="${media(r.phone)}"><button title="A small copy to check on your phone like a viewer would">📱 Phone copy</button></a>` : ""}
      ${ex.cover ? `<a download href="${media(ex.cover)}"><button>⬇ Cover</button></a>` : ""}
      </div>` : ""}
  </div>
  <div class="card"><h3 style="margin-top:0">Send to CapCut</h3>
    <div class="muted">A CapCut project you keep editing: your cut on the original footage (drag any clip edge to bring a cut back),
    every look on its own track, captions as editable CapCut text, and every sound as its own clip.</div>
    <div class="row" style="margin-top:8px"><button class="primary" id="ccProj">✂ Send to CapCut</button>
      <button id="capcut" title="For other editors: video, graphics and captions as separate full-length layers">Layer pack (any editor)</button>
      ${ex.capcut ? `<a download href="${media(ex.capcut)}"><button>⬇ Layer pack (.zip)</button></a>` : ""}</div>
    ${jobBar("capcut_project")}${jobBar("capcut")}
    ${ex.capcut_project ? (ex.capcut_project.in_capcut
      ? `<div class="card" style="margin-top:8px;background:var(--hl)"><b>It's in your CapCut projects.</b> Open CapCut desktop and look for <b>${esc(ex.capcut_project.folder.split(/[\\/]/).pop())}</b>.</div>`
      : `<div class="card" style="margin-top:8px;background:var(--hl)"><b>CapCut desktop isn't on this computer</b>, so your project is packed in a zip.
         Download it on a Windows or Mac computer with CapCut, unzip it, close CapCut, and double-click
         <b>Install in CapCut</b> (Windows .bat or Mac .command). It shows up in CapCut's projects.
         <div class="row" style="margin-top:8px"><a download href="${media(ex.capcut_project.zip)}"><button class="primary">⬇ CapCut project (.zip)</button></a></div></div>`) : ""}
  </div>
  <div class="card"><h3 style="margin-top:0">2 · Frames & photos</h3>
    <div class="muted">Your snaps: stills for your cover or a carousel. Pause on a frame and press <b>Save this frame</b> (or <b>S</b>), then <b>☆ star</b> your cover.</div>
    <div class="row" style="margin-top:8px"><button id="saveFrame">📸 Save this frame</button><button id="addPhotos">＋ Add photos</button></div>
    <div class="files">${(p.frames || []).map((f, k) => `<div class="snap"><img src="${media(f.file)}"><button class="star ${f.star ? "on" : ""}" data-star="${k}" title="Use as my cover">${f.star ? "★ Cover" : "☆"}</button><button class="del" data-delsnap="${k}" title="Remove">×</button></div>`).join("")}${(p.finish_images || []).map(f => `<img src="${media(f)}">`).join("")}</div>
  </div>
  <div class="card"><h3 style="margin-top:0">Storyboard</h3>
    <div class="muted">Every line of your reel as a numbered still, exactly as it will look, to check before you export.</div>
    <div class="row" style="margin-top:8px"><button id="mkBoard">▦ Make storyboard</button></div>${jobBar("storyboard")}
    ${ex.storyboard ? `<a href="${media(ex.storyboard)}" target="_blank"><img src="${media(ex.storyboard)}?v=${p.rev}" style="width:100%;border-radius:10px;margin-top:8px;border:1px solid var(--line)"></a>` : ""}
  </div>
  <div class="card"><h3 style="margin-top:0">3 · Make a carousel or story</h3>
    <div class="muted">Claude writes it from what you said in the video, using your frames.</div>
    <div class="row" style="margin-top:8px"><button class="primary" id="mkCar">Make a carousel</button><button id="mkStory">Make a story</button></div>${jobBar("carousel")}${jobBar("story")}
    ${ex.carousel ? `<h3>Carousel</h3><div class="files">${ex.carousel.map(f => `<a href="${media(f)}" download><img src="${media(f)}?v=${p.rev}"></a>`).join("")}</div>` : ""}
    ${ex.story ? `<h3>Story</h3><div class="files">${ex.story.map(f => `<a href="${media(f)}" download><img src="${media(f)}?v=${p.rev}"></a>`).join("")}</div>` : ""}
  </div>
  <div class="card"><h3 style="margin-top:0">4 · Trial reels</h3>
    <div class="muted">Repackage this reel into three more versions — each with a different opening line, length and hook, all in your same look.</div>
    <div class="row" style="margin-top:8px"><button class="primary" id="mkTrials" ${done ? "" : "disabled"}>Make trial reels</button>
      ${done ? "" : `<small class="muted">🔒 ${S.jobs.render?.status === "running" ? "Unlocks when your reel finishes rendering (see the % above)." : "Unlocks once your reel is rendered: press <b>Lock in my looks</b> (bottom right). Trial reels are re-cuts of the finished video."}</small>`}</div>${jobBar("trials")}
    ${ex.trials ? `<div class="files">${ex.trials.map(t => `<div><video controls src="${media(t.file)}?v=${p.rev}"></video><br><b>${esc(t.name)}</b><br><small>${esc(t.hook)}</small><br><a download href="${media(t.file)}">Download</a></div>`).join("")}</div>` : ""}
  </div>`;
  $("#panel").innerHTML = h;
  $("#lock").onclick = lockIn;
  const cc = $("#capcut"); if (cc) cc.onclick = () => runExport("capcut");
  const cp = $("#ccProj"); if (cp) cp.onclick = () => runExport("capcut_project");
  $("#saveFrame").onclick = saveFrame;
  $("#mkBoard").onclick = () => runExport("storyboard");
  $("#panel").querySelectorAll("[data-star]").forEach(b => b.onclick = () => mutate(p => {
    const k = +b.dataset.star, on = !p.frames[k].star;
    p.frames.forEach(f => f.star = false); p.frames[k].star = on;
  }));
  $("#panel").querySelectorAll("[data-delsnap]").forEach(b => b.onclick = () => mutate(p => p.frames.splice(+b.dataset.delsnap, 1)));
  drawEdgeCard();
  $("#addPhotos").onclick = addPhotosModal;
  $("#mkCar").onclick = () => claudeOr("carousel", "Writing your carousel");
  $("#mkStory").onclick = () => claudeOr("story", "Writing your story");
  $("#mkTrials").onclick = () => claudeOr("trials", "Writing your trial reels");
}
async function drawEdgeCard() {
  const box = $("#edgeCard"); if (!box) return;
  if (S.dirty) await save();
  let r; try { r = await api(`/api/project/${S.name}/edge-check`, {}); } catch { return; }
  if (!r.flags.length || S.edgeOk === S.p.edit_rev) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="card" style="background:var(--hl);margin:8px 0"><b>Some of your looks may be partly hidden or run off the edge. Okay with that?</b>
    <div class="muted" style="font-size:12px">Instagram puts its buttons on the right and your caption at the bottom. Your reel exports either way.</div>
    <div class="row" style="margin-top:8px"><button id="edgeOk">✓ Yes, they're fine</button><button class="primary" id="edgeFix">✥ Move them for me</button>
    <button class="ghost" id="edgeWhich">Which ones? (${r.flags.length})</button></div><div id="edgeList"></div></div>`;
  $("#edgeOk").onclick = () => { S.edgeOk = S.p.edit_rev; box.innerHTML = ""; };
  $("#edgeFix").onclick = async () => { const x = await api(`/api/project/${S.name}/edge-fix`, {}); await reload(); toast(`Moved ${x.moved} look(s) into the safe area.`); };
  $("#edgeWhich").onclick = () => {
    $("#edgeList").innerHTML = r.flags.map(f => `<div class="row" style="margin-top:6px"><button class="ghost" data-jump="${f.at}">▶ ${fmt(f.at)}</button><b>${esc(f.name)}</b><small class="muted">${esc(f.issue)}</small></div>`).join("");
    $("#edgeList").querySelectorAll("[data-jump]").forEach(b => b.onclick = () => seek(+b.dataset.jump));
  };
}
function renderJobsOnly() { updateNextBtn(); if (S.tab === "finish" || (S.tab === "visuals" && S.faceCard)) renderPanel(); }

async function lockIn() {
  if (S.dirty) await save();
  setTab("finish");
  S.jobs.render = await api(`/api/project/${S.name}/render`, {});
  renderPanel(); updateNextBtn();
  $("#panel").scrollTop = 0;  // show "1 · Your reel" with the progress bar
  toast("Rendering your reel: watch the % on the button (bottom right) or at the top of Finish.");
}
async function runExport(kind) { if (S.dirty) await save(); S.jobs[kind] = await api(`/api/project/${S.name}/export`, { kind }); renderPanel(); }
async function claudeOr(kind, label) {
  if (S.dirty) await save();
  if (S.claude) return sendRequest({ kind, text: "" }, `${label}… it'll ping you when it's ready.`);
  runExport(kind);
}
async function saveFrame() {
  const r = await api(`/api/project/${S.name}/frame`, { t: S.outT });
  toast("Frame saved."); await reload();
}
function addPhotosModal() {
  const imgs = S.library.images, chosen = new Set(S.p.finish_images || []);
  openModal(`<h1>Add photos</h1><div class="muted">From library/images (upload more in Add media).</div><div class="grid" style="margin-top:10px">${imgs.map((f, k) => `<div class="tile ${chosen.has(f.path) ? "on" : ""}" data-k="${k}"><img src="${media(f.path)}">${esc(f.name)}</div>`).join("") || "<small>No images yet.</small>"}</div>
    <div class="row" style="margin-top:12px"><span style="flex:1"></span><button class="primary" id="pdone">Done</button></div>`, root => {
    root.querySelectorAll("[data-k]").forEach(t => t.onclick = () => { const f = imgs[+t.dataset.k].path; chosen.has(f) ? chosen.delete(f) : chosen.add(f); t.classList.toggle("on"); });
    root.querySelector("#pdone").onclick = () => { mutate(p => p.finish_images = [...chosen]); closeModal(); };
  });
}

// ------------------------------------------------------------------ Claude requests
async function sendRequest(req, msg) {
  if (S.dirty) await save();
  if ((req.kind === "look" || req.kind === "edit" || req.kind === "ask") && !req.text.trim()) return toast("Tell Claude what you want first.");
  const r = await api(`/api/project/${S.name}/request`, req);
  S.reqStatus[r.id] = r.status;
  closeModal();
  if (r.status === "waiting") toast("Saved for Claude. In Claude Code, say: “check my studio requests”.", null, null, 9000);
  else toast(msg || "Sent to Claude. It'll ping you when it's ready for review.");
  poll();
}

function askClaudeModal(hint) {
  const t = target();
  openModal(`<h1>Ask Claude</h1><div class="muted">About: “${esc(t.text)}”</div>
    <textarea id="askT" placeholder="${esc(hint || "e.g. zoom in a bit on this line, or add a subtle flash when I say “insane”")}"></textarea>
    <div class="row" style="margin-top:8px">${micBtn("askT")}<span style="flex:1"></span><button class="primary" id="askSend">✳ Send to Claude</button></div>`, root => {
    bindMic(root);
    root.querySelector("#askSend").onclick = () => sendRequest({ kind: "edit", text: root.querySelector("#askT").value, w0: t.w0, w1: t.w1, words: t.text });
  });
}

function requestFinished(q) {
  if (q.status === "failed") return toast(`Claude couldn't finish: ${q.note || q.kind}`);
  if (q.options?.length && !q.picked) toast(q.note || "Claude has options ready for you.", "Review", () => optionsModal(q.id), 9000);
  else toast(`Claude: ${q.note || "done"}`);
  S.lookbook && api("/api/lookbook").then(lb => S.lookbook = lb);
}

// Claude doesn't report progress, so this is an estimate from how long that kind of job usually takes
const REQ_TYPICAL = { edit: 120, ask: 120, look: 240, carousel: 180, story: 150, trials: 300, reference: 480 };
function reqPct(r) {
  const el = Math.max(0, Date.now() / 1000 - (r.created || Date.now() / 1000)), typ = REQ_TYPICAL[r.kind] || 180;
  return Math.min(95, Math.round(100 * (1 - Math.exp(-el / typ * 1.4))));
}
function renderTray(reqs) {
  S.hiddenReqs ||= new Set();
  reqs = reqs.filter(r => !r.hidden && !S.hiddenReqs.has(r.id));  // ones you closed with ×
  const active = reqs.filter(r => r.status === "running" || r.status === "waiting").length;
  const ready = reqs.filter(r => r.status === "done" && r.options?.length && !r.picked).length;
  $("#claudeBadge").hidden = !(active + ready); $("#claudeBadge").textContent = active + ready;
  S.requests = reqs;
  if (!$("#claudeTray").hidden) drawTray();
}
function drawTray() {
  const tray = $("#claudeTray");
  if (!tray.querySelector("#reqList")) {  // build once so typing isn't wiped by updates
    tray.innerHTML = `<b>Ask Claude</b>
      <div class="muted" style="font-size:12px;margin:4px 0 8px">Tell Claude what to change, like you'd tell an editor. It updates the studio when it's done.</div>
      <textarea id="askAny" placeholder="e.g. change “fan” to “friend”, make the hook shorter, swap the music for something upbeat"></textarea>
      <label class="row" style="font-size:12px;margin-top:6px"><input type="checkbox" id="askDefault"> Make this my default for every reel</label>
      <div class="row" style="margin:8px 0 4px">${micBtn("askAny")}<span style="flex:1"></span><button class="primary" id="askAnySend">✳ Send</button></div>
      <div id="reqList"></div>`;
    bindMic(tray);
    tray.querySelector("#askAnySend").onclick = () => {
      const ta = tray.querySelector("#askAny"), text = ta.value.trim();
      if (!text) return toast("Type what you'd like Claude to change.");
      const i = Math.max(0, S.curWord), l = linesOf(S.p).find(l => l.w0 <= i && i <= l.w1);
      const def = tray.querySelector("#askDefault").checked;
      sendRequest({ kind: "edit", text, at: fmt(S.outT), playhead_line: l ? l.text : "", default: def },
        def ? "Sent to Claude, and saved as your default for every reel." : "Sent to Claude. The studio updates by itself when it's done.");
      ta.value = ""; tray.querySelector("#askDefault").checked = false;
    };
  }
  const reqs = (S.requests || []).slice().reverse();
  tray.querySelector("#reqList").innerHTML = (S.claude ? "" : `<div class="muted" style="font-size:12px;margin:6px 0">Claude isn't connected to the studio right now, so requests wait until you tell Claude in the Terminal: “check my studio requests”.</div>`) +
    (reqs.length ? `<b style="display:block;margin-top:8px">Earlier requests</b>` + reqs.map(r => `<div class="req"><button class="reqx" data-reqx="${r.id}" title="Close this">×</button><span class="st ${r.status}">${r.status === "running" ? `working… ${reqPct(r)}%` : r.status}</span> ${esc((r.text || r.kind).slice(0, 90))}
      ${r.note ? `<div class="muted">${esc(r.note)}</div>` : ""}
      ${r.status === "done" && r.options?.length ? `<button data-rev="${r.id}" style="margin-top:6px">${r.picked ? "Options" : "Review options"}</button>` : ""}</div>`).join("") : "");
  tray.querySelectorAll("[data-rev]").forEach(b => b.onclick = () => optionsModal(b.dataset.rev));
  tray.querySelectorAll("[data-reqx]").forEach(b => b.onclick = () => {  // close a notification (Claude keeps working if it's still running)
    const id = b.dataset.reqx;
    (S.hiddenReqs ||= new Set()).add(id);
    mutate(p => { const r = (p.requests || []).find(r => r.id === id); if (r) r.hidden = true; }, { render: false });
    renderTray(S.requests || []); drawTray();
  });
}
$("#claudeBtn").onclick = () => { $("#claudeTray").hidden = !$("#claudeTray").hidden; drawTray(); if (!$("#claudeTray").hidden) $("#askAny").focus(); };

async function optionsModal(rid) {
  S.lookbook = await api("/api/lookbook");
  const q = S.p.requests.find(r => r.id === rid) || (S.requests || []).find(r => r.id === rid);
  if (!q) return;
  let picked = q.options[0];
  const t = timeOfWord(q.w0 ?? 0);
  openModal(`<div class="muted" style="font-size:11px;letter-spacing:.08em">SANDBOX · YOUR IDEA</div><h1>Pick a sketch</h1>
    <div class="muted">Three quick takes on “${esc(q.text.split("\n\nChanges:")[0])}”, on your own video. Hover to play, tap one to pick it.</div>
    <div class="grid frames" style="margin-top:12px;grid-template-columns:repeat(3,1fr)">${q.options.map((id, k) => {
      const m = lookMeta(id);
      return `<div class="tile ${k === 0 ? "on" : ""}" data-pick="${id}">${onFrame(id, {}, t)}<b>Sketch ${k + 1}</b><small>${esc(m?.description || m?.name || id)}</small></div>`;
    }).join("")}</div>
    <h3>What should change?</h3><textarea id="chg" placeholder="e.g. like sketch 2 but bigger, and hold it until I stop talking"></textarea>
    <div class="row" style="margin-top:10px">${micBtn("chg")}<button id="cancelIdea" class="ghost">Cancel this idea</button>
      <span style="flex:1"></span><button id="remix">↻ Remix</button><button class="primary" id="lockIt">✓ Lock it in</button></div>`, root => {
    bindMic(root);
    mountSprites(root, true);
    root.querySelectorAll("[data-pick]").forEach(el => el.onclick = () => {
      picked = el.dataset.pick;
      root.querySelectorAll("[data-pick]").forEach(x => x.classList.toggle("on", x === el));
    });
    const mark = val => mutate(p => { const r = p.requests.find(r => r.id === rid); if (r) r.picked = val; }, { render: false });
    root.querySelector("#lockIt").onclick = () => {
      mark(picked);
      addOverlay({ kind: "look", look: picked, params: {}, scale: 1, y: lookY(picked), min_dur: 2, w0: q.w0 ?? 0, w1: q.w1 ?? q.w0 ?? 0 });
    };
    root.querySelector("#cancelIdea").onclick = () => { mark("cancelled"); closeModal(); toast("Idea cancelled."); };
    root.querySelector("#remix").onclick = () => {
      const chg = root.querySelector("#chg").value.trim() || "Three genuinely different new takes (remix).";
      sendRequest({ kind: "look", text: `${q.text.split("\n\nChanges:")[0]}\n\nChanges: ${chg}`, previous: q.options, w0: q.w0, w1: q.w1, words: q.words },
        "Sent to Claude: three new sketches are on the way.");
    };
  });
}

// ------------------------------------------------------------------ mic (dictation)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const micBtn = id => SR ? `<button class="mic" data-mic="${id}" title="Talk instead of typing">🎤</button>` : "";
function bindMic(root) {
  root.querySelectorAll("[data-mic]").forEach(b => b.onclick = () => {
    if (S.rec) { S.rec.stop(); return; }
    const ta = root.querySelector("#" + b.dataset.mic), rec = new SR();
    rec.continuous = true; rec.interimResults = false; rec.lang = "en-US";
    const base = ta.value;
    let said = "";
    rec.onresult = e => { said = [...e.results].map(r => r[0].transcript).join(" "); ta.value = (base + " " + said).trim(); };
    rec.onend = () => { S.rec = null; b.classList.remove("on"); };
    S.rec = rec; b.classList.add("on"); rec.start();
  });
}

// ------------------------------------------------------------------ sprites (look previews)
// w0: the look's first word. Steps timed to words ({"w": i} in params) are worked out on the server from it.
const hasCues = params => JSON.stringify(params || {}).includes('"w":');
function spriteKey(look, params, dur, w0) {
  return JSON.stringify([look, params, Math.round(Math.min(dur, 6) * 4) / 4, hasCues(params) ? [w0, S.p?.edit_rev || 0] : 0]);
}
function getSprite(look, params, dur, w0) {
  dur = Math.max(0.5, Math.round(Math.min(dur, 6) * 4) / 4);
  const k = spriteKey(look, params, dur, w0);
  if (S.sprites[k]) return S.sprites[k];
  if (!S.spriteLoading[k]) {
    S.spriteLoading[k] = true;
    api(`/api/project/${S.name}/sprite`, { look, params, dur, w0: hasCues(params) ? w0 : undefined }).then(m => {
      const img = new Image(); img.src = m.url + "?k=" + encodeURIComponent(k).slice(0, 40);
      img.onload = () => { S.sprites[k] = m; };
    }).catch(e => console.warn("sprite", look, e)).finally(() => setTimeout(() => delete S.spriteLoading[k], 3000));
  }
  return null;
}
// A look drawn on your own frame, at the height it will really sit, at its real size.
const thumbUrl = t => `/api/project/${S.name}/thumb?t=${Math.max(0, +t || 0).toFixed(1)}`;
function lookY(id) {
  const g = lookMeta(id)?.group;
  return g === "hook" || g === "structure" ? 0.14 : g === "cta" ? 0.16 : 0.4;
}
function onFrame(look, params, t, extra = "") {
  return `<div class="sprbox frame" style="background-image:url('${thumbUrl(t)}')"><div class="spr" data-spr="${look}" data-y="${lookY(look)}" data-params='${esc(JSON.stringify(params || {}))}' ${extra}></div></div>`;
}
function timeOfWord(i) { const o = wordOut(S.p.words, S.segs, Math.max(0, i || 0)); return o ? o[0] + 0.4 : 1; }

function mountSprites(root, hoverOnly) {
  const els = [...root.querySelectorAll("[data-spr]")];
  const anim = () => {
    for (const el of els) {
      const params = el.dataset.params ? JSON.parse(el.dataset.params) : {};
      const m = getSprite(el.dataset.spr, params, 3);
      if (!m) continue;
      if (el.parentElement.classList.contains("frame")) {  // true scale on a 1080-wide frame
        const box = el.parentElement, bw = box.clientWidth, bh = box.clientHeight;
        const sc = bw / 1080 * (+el.dataset.scale || 1);
        const w = m.w * sc, h = m.h * sc;
        el.style.width = w + "px"; el.style.height = h + "px";
        el.style.left = (bw - w) / 2 + "px"; el.style.top = Math.max(0, Math.min(bh - h, (+el.dataset.y || 0.4) * bh - h / 2)) + "px";
        el.style.backgroundImage = `url("${m.url}")`;
        el.style.backgroundSize = `${m.n * w}px ${h}px`;
        const playing = !hoverOnly || el.closest(".tile")?.matches(":hover");
        const f = playing ? Math.floor(performance.now() / 1000 * m.fps) % m.n : Math.floor(m.n * 0.6);
        el.style.backgroundPosition = `${-f * w}px 0`;
        continue;
      }
      // size the box to exactly one frame so neighbouring frames never show
      const pw = el.parentElement.clientWidth - 8, ph = parseFloat(el.dataset.h || (el.dataset.h = el.getBoundingClientRect().height));
      const sc = Math.min(pw / m.w, ph / m.h) * 0.95;
      el.style.width = m.w * sc + "px"; el.style.height = m.h * sc + "px";
      el.style.margin = `${(ph - m.h * sc) / 2}px auto`;
      el.style.backgroundImage = `url("${m.url}")`;
      el.style.backgroundSize = `${m.n * m.w * sc}px ${m.h * sc}px`;
      const playing = !hoverOnly || el.closest(".tile")?.matches(":hover");
      const f = playing ? Math.floor(performance.now() / 1000 * m.fps) % m.n : Math.floor(m.n * 0.6);
      el.style.backgroundPosition = `${-f * m.w * sc}px 0`;
    }
  };
  clearInterval(S.spriteAnim);
  S.spriteAnim = setInterval(anim, 100);
}

// ------------------------------------------------------------------ player
function fitStage() {
  const ph = $("#stageWrap").getBoundingClientRect();
  S.k = ph.width / W;
  $("#stage").style.transform = `scale(${S.k})`;
}
window.addEventListener("resize", () => { fitStage(); drawTimeline(); });

function seek(t) {
  S.outT = Math.max(0, Math.min(t, Math.max(0, S.T - 0.01)));
  const [sg, ts] = outToSrc(S.segs, S.outT);
  S.curSeg = sg;
  if (Math.abs(v.currentTime - ts) > 0.03) v.currentTime = ts;
  syncMusic(true);
  draw();
}
function seekWord(i, toZero) {
  if (toZero) return seek(0);
  const w = S.p.words;
  let j = i; while (j < w.length && w[j].cut) j++;
  const o = j < w.length ? wordOut(w, S.segs, j) : null;
  if (o) seek(o[0] + 0.001);
}
$("#cmpBtn").onclick = () => { S.noFilter = !S.noFilter; applyFilter(); };
function applyFilter() {  // CSS approximation of engine/draw.py apply_filter
  const id = S.p.filter || "none", btn = $("#cmpBtn");
  if (btn) {  // "See original": compare the footage with and without the filter (preview only, nothing is saved)
    btn.hidden = id === "none";
    if (id === "none") S.noFilter = false;
    btn.classList.toggle("on", !!S.noFilter);
    btn.textContent = S.noFilter ? "◐ Filter off · tap to turn on" : "◐ Filter on · tap to compare";
  }
  const fl = S.noFilter ? {} : (S.lookbook?.filters || []).find(x => x.id === id) || {};
  const parts = [];
  if (fl.gray) parts.push(`grayscale(${fl.gray})`);
  if (fl.sat && fl.sat !== 1) parts.push(`saturate(${fl.sat})`);
  if (fl.contrast && fl.contrast !== 1) parts.push(`contrast(${fl.contrast})`);
  const br = (fl.bright || 1) * (1 + (fl.lift || 0) * 0.5);
  if (br !== 1) parts.push(`brightness(${br.toFixed(3)})`);
  if (fl.lift) parts.push(`contrast(${(1 - fl.lift).toFixed(3)})`);
  if (fl.warm > 0) parts.push(`sepia(${(fl.warm * 2.2).toFixed(2)})`);
  if (fl.warm < 0) parts.push(`hue-rotate(${Math.round(fl.warm * 120)}deg) saturate(1.05)`);
  const css = parts.join(" ") || "none";
  S.filterCss = css === "none" ? "" : css;  // drawCamera adds word-effect blurs on top of this every frame
  for (const el of [v, bv, $("#bimg")]) el.style.filter = css;
}
function applySpeed() {  // talk faster without chipmunk voices; the export does the same
  const r = +(S.p.speed || 1);
  v.playbackRate = r; bv.playbackRate = r; music.playbackRate = r;
  v.preservesPitch = bv.preservesPitch = music.preservesPitch = true;
}
function play() {
  applySpeed();
  if (!S.segs.length) return;
  if (S.outT >= S.T - 0.05) seek(0);
  S.playing = true;
  const [sg, ts] = outToSrc(S.segs, S.outT); S.curSeg = sg;
  if (Math.abs(v.currentTime - ts) > 0.05) v.currentTime = ts;
  v.play().catch(() => {});
  syncMusic(true); if (S.p.sound.src) music.play().catch(() => {});
  $("#play").textContent = $("#play2").textContent = "❚❚";
}
function pause() {
  S.playing = false; v.pause(); bv.pause(); music.pause();
  $("#play").textContent = $("#play2").textContent = "▶";
}
const toggle = () => S.playing ? pause() : play();
$("#play").onclick = $("#play2").onclick = toggle;
$("#back5").onclick = () => seek(S.outT - 3);
$("#fwd5").onclick = () => seek(S.outT + 3);

function syncMusic(force) {
  if (!S.p.sound.src) return;
  const want = (S.p.sound.offset || 0) + S.outT;
  if (music.duration && want < music.duration && (force || Math.abs(music.currentTime - want) > 0.35)) music.currentTime = want;
}

function tick() {
  if (S.playing && S.segs.length) {
    const ts = v.currentTime;
    let sg = S.curSeg;
    if (!sg || ts < sg.s - 0.25 || ts > sg.e + 0.5) sg = S.segs.find(s => s.s - 0.05 <= ts && ts < s.e) || S.curSeg;
    if (sg && ts >= sg.e - 0.015) {
      const k = S.segs.indexOf(sg);
      if (k + 1 < S.segs.length) { sg = S.segs[k + 1]; v.currentTime = sg.s; }
      else { pause(); S.outT = S.T; }
    }
    S.curSeg = sg;
    const before = S.outT;
    if (S.playing && sg) S.outT = sg.o + Math.max(0, Math.min(sg.e, v.currentTime) - sg.s);
    if (S.playing) playSfxBetween(before, S.outT);
    syncMusic(false);
  }
  draw();
  requestAnimationFrame(tick);
}

function draw() {
  if (!S.p) return;
  const t = S.outT;
  const sp = +(S.p.speed || 1);
  $("#ptime").textContent = `${fmt(t / sp)} / ${fmt(S.T / sp)}`;
  $("#clock").textContent = fmt(t / sp); $("#clockOf").textContent = "of " + fmt(S.T / sp);
  drawBroll(t); drawCamera(t); drawFaces(); drawOverlays(t); drawCaptions(t); drawPlayhead(); markWord(t);
}

function markWord(t) {
  const w = S.p.words; let cur = -1;
  const sg = S.segs.find(s => s.o <= t && t < s.o + s.e - s.s);
  if (sg) for (let i = sg.w0; i <= sg.w1; i++) { const o = wordOut(w, S.segs, i); if (o && o[0] <= t + 0.001) cur = i; }
  if (cur === S.curWord) return;
  S.curWord = cur;
  document.querySelectorAll(".w.active").forEach(e => e.classList.remove("active"));
  document.querySelectorAll(".line.now").forEach(e => e.classList.remove("now"));
  const el = document.querySelector(`.w[data-i="${cur}"]`);
  if (el) { el.classList.add("active"); el.closest(".line")?.classList.add("now"); }
}

function drawBroll(t) {
  const hit = (S.bspans || []).find(([b, sp]) => sp[0] <= t && t < sp[1]);
  const bimg = $("#bimg"), bpanel = $("#bpanel");
  if (!hit) {
    if (bv.style.visibility === "visible") { bv.style.visibility = "hidden"; bv.pause(); }
    bimg.style.display = bpanel.style.display = "none";
    S.inBroll = S.inSplit = S.inCard = false; return;
  }
  const [b, sp] = hit, split = b.layout === "split" || b.layout === "class";  // class page: previewed as a split
  const card = b.layout === "card";  // screenshot/chart on a card over the speaker, blurred (mirrors render.py)
  const isImg = b.src && /\.(png|jpe?g|webp|gif)$/i.test(b.src);
  const box = split ? { top: "0", height: "50%" } : { top: "0", height: "100%" };
  let el;
  if (!b.src) { el = bpanel; bpanel.style.background = b.layout === "class" ? "#8E0C0E" : (b.color || "#FFFFFF"); }
  else if (isImg) { el = bimg; if (bimg.dataset.src !== b.src) { bimg.src = media(b.src); bimg.dataset.src = b.src; } }
  else {
    el = bv;
    if (bv.dataset.src !== b.src) { bv.src = media(b.src); bv.dataset.src = b.src; }
    const want = (b.clip_start || 0) + t - sp[0];
    if (Math.abs(bv.currentTime - want) > 0.3) bv.currentTime = want;
    bv.muted = b.audio !== "under"; bv.volume = 0.35;
    if (S.playing && bv.paused) bv.play().catch(() => {});
    if (!S.playing && !bv.paused) bv.pause();
  }
  for (const o of [bv, bimg, bpanel]) if (o !== el) { if (o === bv) { o.style.visibility = "hidden"; } else o.style.display = "none"; }
  if (card && !b.src) { for (const o of [bv, bimg, bpanel]) { if (o === bv) o.style.visibility = "hidden"; else o.style.display = "none"; } }
  else if (el === bv) bv.style.visibility = "visible"; else el.style.display = "block";
  el.style.top = card ? "16%" : box.top; el.style.height = card ? "52%" : box.height;
  el.style.left = card ? "6%" : "0"; el.style.width = card ? "88%" : "100%";
  el.style.objectFit = card ? "contain" : ""; el.style.borderRadius = card ? "14px" : "";
  const FADE = 0.25;  // "Comes in: Fade" (mirrors render.py)
  el.style.opacity = b.trans === "fade" ? Math.min(1, (t - sp[0]) / FADE, (sp[1] - t) / FADE) : 1;
  S.inBroll = !split && !card; S.inSplit = split; S.inCard = card;
}

const FX_KINDS = { flash: [0.30, 1], whip: [0.30, 1], zoom: [0.35, 1], shake: [0.40, 0], glitch: [0.25, 1], light_leak: [1.0, 0], drip: [0.7, 1] };
function fxNow(t) {  // mirror of engine/fx.py (approximate: the render is exact)
  const out = { dx: 0, scale: 1, rot: 0, filter: "", flash: 0, wash: "#fff" };
  for (const f of S.p.fx || []) {
    const d = FX_KINDS[f.kind]; if (!d || f.w == null) continue;
    const o = wordOut(S.p.words, S.segs, f.w); if (!o) continue;
    const dur = +(f.dur || d[0]), a = d[1] ? o[0] - dur / 2 : o[0];
    if (t < a || t >= a + dur) continue;
    const k = (t - a) / dur, b = Math.sin(Math.PI * k), s = +(f.strength || 1);
    const W = $("#phone").clientWidth;
    if (f.kind === "whip") { out.dx = -(k - 0.5) * W * 0.5 * s; out.filter = `blur(${(6 * b * s).toFixed(1)}px)`; }
    if (f.kind === "zoom") { out.scale = 1 + 0.3 * b * s; out.filter = `blur(${(2 * b).toFixed(1)}px)`; }
    if (f.kind === "shake") { const amp = 10 * s * Math.pow(1 - k, 1.5); out.dx = Math.sin(t * 90) * amp; out.rot = Math.sin(t * 70) * 0.8 * (1 - k); out.scale = 1.05; }
    if (f.kind === "glitch") { out.filter = `saturate(${1 + 2 * b}) hue-rotate(${Math.round(40 * b * Math.sin(t * 60))}deg)`; out.dx = Math.sin(t * 120) * 8 * b; }
    if (f.kind === "flash") { out.flash = Math.pow(b, 1.5); out.wash = "#fff"; }
    if (f.kind === "drip") { out.flash = 1; out.wash = k < 0.5 ? `linear-gradient(#8E0C0E ${k * 200}%, transparent ${k * 200 + 8}%)` : `linear-gradient(transparent ${(k - 0.5) * 230}%, #8E0C0E ${(k - 0.5) * 230 + 4}%)`; }
    if (f.kind === "light_leak") { out.flash = 0.45 * b * s; out.wash = `radial-gradient(circle at ${-20 + 140 * k}% 30%, rgba(255,140,60,.9), rgba(255,80,120,.25) 45%, transparent 70%)`; }
  }
  return out;
}

function drawCamera(t) {
  // speaker zoom (hook push-in, punch-ins) + split-screen shift; mirrored in engine/render.py speaker()
  const z = cameraZoom(S.p, S.p.words, S.segs, t), [fx, fy] = focusOf(S.p);
  const half = Math.floor(H / 2), y0 = Math.min(Math.max(0, fy * H - 0.4 * half), H - (H - half));
  const shift = S.inSplit ? half - Math.floor(y0) : 0;
  const e = fxNow(t);  // transitions on a word (engine/fx.py), approximated with CSS
  const tr = `translate(${e.dx}px, ${shift}px) scale(${z * e.scale}) rotate(${e.rot}deg)`, org = `${fx * 100}% ${fy * 100}%`;
  if (v.style.transform !== tr || v.style.transformOrigin !== org) {
    v.style.transform = fc.style.transform = tr; v.style.transformOrigin = fc.style.transformOrigin = org;
  }
  const vf = [S.filterCss, e.filter, S.inCard ? "blur(18px) brightness(0.78)" : ""]
    .filter(x => x && x !== "none").join(" ") || "none";  // colour filter + word effects (+ the card layout's blur)
  if (v.style.filter !== vf) v.style.filter = vf;
  let fl = $("#fxflash");
  if (!fl) { fl = document.createElement("div"); fl.id = "fxflash"; fl.style.cssText = "position:absolute;inset:0;pointer-events:none;z-index:50;opacity:0"; $("#phone").appendChild(fl); }
  fl.style.background = e.wash; fl.style.opacity = e.flash;
  const dim = Math.max(0, ...S.spans.filter(([ov, [a, b]]) => a <= t && t < b).map(([ov]) => +(ov.dim || 0)));
  $("#dim").style.opacity = Math.min(0.8, dim);
}

const imgCache = {};
function img(src) { if (!imgCache[src]) { const i = new Image(); i.src = src; imgCache[src] = i; } return imgCache[src]; }
const canBlur = (() => { const c = document.createElement("canvas").getContext("2d"); return "filter" in c; })();

function drawBurned(vw, vh, sc, ox, oy, ts) {
  // Preview of "paint out the video's own captions": blur where the engine found them.
  // (The final render repaints those pixels from their surroundings, which looks cleaner.)
  const bc = S.p.burned_captions;
  if (!bc || !bc.remove || !bc.boxes) return;
  for (const b of bc.boxes) {
    if (Math.abs(b[0] - ts) > 0.14) continue;
    const pad = 0.02;
    const x0 = Math.max(0, b[1] - pad) * vw, y0 = Math.max(0, b[2] - pad) * vh, x1 = Math.min(1, b[3] + pad) * vw, y1 = Math.min(1, b[4] + pad) * vh;
    const dx = x0 * sc - ox, dy = y0 * sc - oy, dw = (x1 - x0) * sc, dh = (y1 - y0) * sc;
    fctx.save();
    if (canBlur) { fctx.filter = "blur(26px)"; fctx.drawImage(v, x0, y0, x1 - x0, y1 - y0, dx, dy, dw, dh); fctx.drawImage(v, x0, y0, x1 - x0, y1 - y0, dx, dy, dw, dh); }
    else {
      const tmp = S.pix || (S.pix = document.createElement("canvas")); tmp.width = Math.max(2, dw / 30 | 0); tmp.height = Math.max(2, dh / 30 | 0);
      tmp.getContext("2d").drawImage(v, x0, y0, x1 - x0, y1 - y0, 0, 0, tmp.width, tmp.height);
      fctx.imageSmoothingEnabled = true; fctx.drawImage(tmp, dx, dy, dw, dh);
    }
    fctx.restore();
  }
}

function drawFaces() {
  fctx.clearRect(0, 0, W, H);
  if (S.inBroll || !v.videoWidth) return;
  const vw = v.videoWidth, vh = v.videoHeight, sc = Math.max(W / vw, H / vh), ox = (vw * sc - W) / 2, oy = (vh * sc - H) / 2;
  const ts = v.currentTime;
  drawBurned(vw, vh, sc, ox, oy, ts);
  const f = S.p.faces; if (!f.covers.length) return;
  for (const c of f.covers) {
    const d = f.detected.find(d => d.id === c.face); if (!d) continue;
    const pos = faceAt(d.track, ts); if (!pos) continue;
    const X = pos[0] * vw * sc - ox, Y = pos[1] * vh * sc - oy, size = pos[2] * vw * sc * (c.scale || 1.3) * 1.25;
    if (c.style === "blur" || c.style === "pixelate") {
      fctx.save(); fctx.beginPath(); fctx.ellipse(X, Y, size / 2, size * 0.6, 0, 0, Math.PI * 2); fctx.clip();
      const sx = (X - size / 2 + ox) / sc, sy = (Y - size * 0.6 + oy) / sc, sw = size / sc, sh = size * 1.2 / sc;
      if (c.style === "blur" && canBlur) { fctx.filter = `blur(${Math.max(8, size / 9)}px)`; fctx.drawImage(v, sx, sy, sw, sh, X - size / 2, Y - size * 0.6, size, size * 1.2); }
      else {
        const tmp = S.pix || (S.pix = document.createElement("canvas")); tmp.width = Math.max(2, size / 18 | 0); tmp.height = Math.max(2, size * 1.2 / 18 | 0);
        const tc = tmp.getContext("2d"); tc.drawImage(v, sx, sy, sw, sh, 0, 0, tmp.width, tmp.height);
        fctx.imageSmoothingEnabled = c.style !== "pixelate"; fctx.drawImage(tmp, X - size / 2, Y - size * 0.6, size, size * 1.2);
      }
      fctx.restore();
    } else {
      const im = img(c.style === "emoji" ? `/assets/emoji/${c.emoji}.png` : media(c.image));
      if (im.complete && im.naturalWidth) { const r = size / Math.max(im.naturalWidth, im.naturalHeight); fctx.drawImage(im, X - im.naturalWidth * r / 2, Y - im.naturalHeight * r / 2, im.naturalWidth * r, im.naturalHeight * r); }
    }
  }
}

function drawOverlays(t) {
  const root = $("#ovl"), seen = new Set();
  for (const [ov, [a, b]] of S.spans) {
    if (t < a || t >= b) continue;
    seen.add(ov.id);
    let el = root.querySelector(`[data-id="${ov.id}"]`);
    const local = t - a, st = overlayState(ov, t, a, b);
    let w, hgt;
    if (ov.kind === "look") {
      const m = getSprite(ov.look, ov.params || {}, b - a, ov.w0);
      if (!m) continue;
      if (!el || el.tagName !== "DIV") { el?.remove(); el = document.createElement("div"); el.className = "ov"; el.dataset.id = ov.id; root.appendChild(el); bindOvDrag(el); }
      const sc = ov.scale ?? 1; w = m.w * sc; hgt = m.h * sc;
      const f = Math.min(m.n - 1, Math.floor(local * m.fps));
      el.style.width = w + "px"; el.style.height = hgt + "px";
      el.style.backgroundImage = `url("${m.url}")`; el.style.backgroundSize = `${m.n * w}px ${hgt}px`;
      el.style.backgroundPosition = `${-f * w}px 0`;
    } else {
      const src = ov.kind === "emoji" ? `/assets/emoji/${ov.emoji}.png` : media(ov.src);
      if (!el || el.tagName !== "IMG") { el?.remove(); el = document.createElement("img"); el.className = "ov"; el.dataset.id = ov.id; el.draggable = false; root.appendChild(el); bindOvDrag(el); }
      if (el.dataset.src !== src) { el.src = src; el.dataset.src = src; }
      w = (ov.scale ?? .45) * W; el.style.width = w + "px"; hgt = el.naturalHeight ? w * el.naturalHeight / el.naturalWidth : w;
    }
    const cx = ((ov.x ?? .5) + st.dx) * W, cy = ((ov.y ?? .5) + st.dy) * H;
    el.style.transform = `translate(${cx - w / 2}px, ${cy - hgt / 2}px) rotate(${-st.rot}deg) scale(${st.scale * pushScale(ov, t, a, b)})`;
    el.style.opacity = st.alpha;
    el.classList.toggle("sel", S.selOv === ov.id && S.tab === "visuals");
  }
  root.querySelectorAll(".ov").forEach(el => { if (!seen.has(el.dataset.id)) el.remove(); });
}

function bindOvDrag(el) {
  el.onpointerdown = e => {
    e.preventDefault();
    const id = el.dataset.id, ov = S.p.overlays.find(o => o.id === id); if (!ov) return;
    S.selOv = id;
    const sx = e.clientX, sy = e.clientY, ox = ov.x ?? .5, oy = ov.y ?? .5;
    let moved = false;
    const mv = ev => { moved = true; ov.x = ox + (ev.clientX - sx) / S.k / W; ov.y = oy + (ev.clientY - sy) / S.k / H; };
    const up = () => {
      window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up);
      if (moved) { const x = ov.x, y = ov.y; ov.x = ox; ov.y = oy; mutate(p => { const o = p.overlays.find(o => o.id === id); o.x = +x.toFixed(3); o.y = +y.toFixed(3); }, { render: false }); }
      else if (S.tab === "visuals") overlayEditor(id);
    };
    window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
  };
}

function drawCaptions(t) {
  const g = S.groups.find(g => g.start <= t && t < g.end);
  const root = $("#cap");
  if (!g) { if (S.lastCapKey !== null) { root.innerHTML = ""; S.lastCapKey = null; } return; }
  let active = g.w[0];
  for (const i of g.w) { const o = wordOut(S.p.words, S.segs, i); if (o && o[0] <= t) active = i; }
  const st = S.style, tin = t - g.start;
  const popF = st.pop ? Math.min(5, Math.floor(tin * 30)) : 0;
  let chars = st.type_cps ? Math.floor(tin * st.type_cps) : null;  // typewriter captions (Look F)
  if (chars != null && chars >= g.w.reduce((a, i) => a + S.p.words[i].t.length + 1, 0)) chars = null;
  const key = `${S.groups.indexOf(g)}:${active}:${popF}:${st.id}:${S.inSplit ? 1 : 0}:${chars}`;
  if (key === S.lastCapKey) return;
  S.lastCapKey = key;
  const { lines, space } = captionLayout(S.p.words, g.w, st, W);
  const lh = st.size * 1.18;
  let h = "";
  let left = chars == null ? 1e9 : chars;
  for (const [items] of lines) {
    if (chars != null) items.forEach(it => { const full = it.text; it.text = left <= 0 ? "" : left < full.length ? full.slice(0, left) + "_" : full; left -= full.length + 1; });
    const box = st.box ? `background:${st.box.length === 9 ? hexA(st.box) : st.box};border-radius:${st.size * .22}px;padding:0 ${st.size * .25}px;` : "";
    h += `<div class="cl" style="height:${lh}px;line-height:${lh}px;${box}">` +
      items.map((it, k) => wordSpan(S.p.words[it.i], it.i === active, st, it.text).replace('class="cw" style="', `class="cw" style="margin-right:${k < items.length - 1 ? space : 0}px;`)).join("") + `</div>`;
  }
  const sc = st.pop && tin < 0.15 ? 0.75 + 0.25 * easeOutBack(tin / 0.15) : 1;
  const cy = S.inSplit ? 0.52 : (st.y ?? .7);  // split screen: caption sits on the seam
  root.innerHTML = `<div class="cg" style="left:${(st.x ?? .5) * W}px;top:${cy * H}px;transform:translate(-50%,-50%) scale(${sc})">${h}</div>`;
}
const hexA = h => { const n = parseInt(h.slice(1), 16); return `rgba(${(n >>> 24) & 255},${(n >>> 16) & 255},${(n >>> 8) & 255},${((n & 255) / 255).toFixed(2)})`; };

// ------------------------------------------------------------------ timeline (bottom)
// ------------------------------------------------------------------ timeline: CapCut-style
// The film strip slides under a fixed playhead in the middle. Tap a clip to select it (white frame + handles),
// drag a handle to trim, Split / Delete in the toolbar. Cuts are in seconds of footage (p.time_cuts, p.splits),
// so silent moments like fixing the camera can be cut too. Mirrors engine/timeline.py apply_time_edits.
const tl = $("#tl"), tctx = tl.getContext("2d"), tlBox = $("#tlScroll");
S.pps = 60;  // pixels per second
const TL_H = 112, STRIP_Y = 20, STRIP_H = 56, OV_Y = STRIP_Y + STRIP_H + 6, BR_Y = OV_Y + 11, BAR_H = 8;
const tlPad = () => tlBox.clientWidth / 2;
const timeToX = t => tlPad() + t * S.pps;
const thumbImgs = {};
function stripThumb(srcT) {
  const k = (Math.round(srcT * 2) / 2).toFixed(1);
  if (!thumbImgs[k]) { const im = new Image(); im.onload = () => drawTimelineSoon(); im.src = `/api/project/${S.name}/thumb?t=${k}&src=1&w=96`; thumbImgs[k] = im; }
  return thumbImgs[k];
}
let tlTimer = 0;
function drawTimelineSoon() { clearTimeout(tlTimer); tlTimer = setTimeout(drawTimeline, 60); }
const TDPR = Math.min(devicePixelRatio || 1, 1.5);  // a lighter canvas on high-res screens; still sharp
function drawTimeline() {
  if (!S.p) return;
  S.pps = Math.min(S.pps, (14000 - tlPad() * 2) / Math.max(1, S.T));  // keep the canvas within what Chrome draws quickly
  const cssW = Math.ceil(tlPad() * 2 + S.T * S.pps), cssH = TL_H;
  if (tl.width !== Math.round(cssW * TDPR) || tl.height !== Math.round(cssH * TDPR)) {
    tl.width = Math.round(cssW * TDPR); tl.height = Math.round(cssH * TDPR); tl.style.width = cssW + "px"; tl.style.height = cssH + "px";
  }
  placeTrackButtons();
  const c = tctx; c.setTransform(TDPR, 0, 0, TDPR, 0, 0);
  c.clearRect(0, 0, cssW, cssH);
  const css = getComputedStyle(document.documentElement), ink2 = css.getPropertyValue("--ink2").trim(), accent = css.getPropertyValue("--accent").trim();
  c.font = "10px Montserrat_600SemiBold, sans-serif"; c.fillStyle = ink2;
  const step = S.pps > 120 ? 0.5 : S.pps > 40 ? 1 : S.pps > 15 ? 2 : 5;
  for (let t = 0; t <= S.T + 1e-6; t += step) {
    const x = timeToX(t), major = Math.abs(t / (step * 2) - Math.round(t / (step * 2))) < 1e-6;
    if (major) c.fillText(fmt(t), x + 3, 11);
    c.fillRect(x, major ? 12 : 15, 1, major ? 6 : 3);
  }
  const tileW = Math.round(STRIP_H * 0.75);
  S.segs.forEach((sg, i) => {
    const x = timeToX(sg.o), w = Math.max(2, (sg.e - sg.s) * S.pps - 2);
    c.save(); c.beginPath(); c.roundRect(x, STRIP_Y, w, STRIP_H, 6); c.clip();
    c.fillStyle = "#2a2838"; c.fillRect(x, STRIP_Y, w, STRIP_H);
    for (let tx = x; tx < x + w; tx += tileW) {  // the film strip: one still per tile
      const im = stripThumb(sg.s + (tx - x + tileW / 2) / S.pps);
      if (im.complete && im.naturalWidth) {
        const sh = im.naturalWidth * STRIP_H / tileW;  // centre-crop the tall still into the tile
        c.drawImage(im, 0, (im.naturalHeight - sh) / 2, im.naturalWidth, sh, tx, STRIP_Y, tileW, STRIP_H);
      }
    }
    c.restore();
  });
  const sel = S.selClip != null ? S.segs[S.selClip] : null;
  if (sel) {  // selected clip: white frame and two handles, like CapCut; while you drag a handle the clip resizes live
    let x = timeToX(sel.o), w = Math.max(2, (sel.e - sel.s) * S.pps - 2), len = sel.e - sel.s;
    if (S.trim) {
      const d = S.trim.x - S.trim.x0;
      if (S.trim.side === "r") { w = Math.max(8, w + d); len = Math.max(0.1, len + d / S.pps); }
      else { x += d; w = Math.max(8, w - d); len = Math.max(0.1, len - d / S.pps); }
      const ox = timeToX(sel.o), ow = (sel.e - sel.s) * S.pps;
      c.fillStyle = "rgba(0,0,0,.55)";  // the part you're trimming off goes dark
      if (S.trim.side === "r" && d < 0) c.fillRect(ox + ow + d, STRIP_Y, -d, STRIP_H);
      if (S.trim.side === "l" && d > 0) c.fillRect(ox, STRIP_Y, d, STRIP_H);
      if (d > 0 && S.trim.side === "r" || d < 0 && S.trim.side === "l") {  // extending: show the new footage area
        c.fillStyle = "rgba(255,255,255,.25)";
        c.fillRect(S.trim.side === "r" ? ox + ow : x, STRIP_Y, Math.abs(d), STRIP_H);
      }
    }
    c.strokeStyle = "#333"; c.lineWidth = 5; c.beginPath(); c.roundRect(x, STRIP_Y, w, STRIP_H, 6); c.stroke();
    c.strokeStyle = "#fff"; c.lineWidth = 3; c.stroke();
    for (const hx of [x - 12, x + w]) {
      c.fillStyle = "#fff"; c.beginPath(); c.roundRect(hx, STRIP_Y, 12, STRIP_H, 4); c.fill();
      c.strokeStyle = "#333"; c.lineWidth = 1.5; c.stroke();  // outlined so it shows on the light background
      c.fillStyle = "#888"; c.fillRect(hx + 5, STRIP_Y + STRIP_H / 2 - 9, 2, 18);
    }
    c.fillStyle = "rgba(0,0,0,.6)"; c.beginPath(); c.roundRect(x + 4, STRIP_Y + 4, 40, 15, 4); c.fill();
    c.fillStyle = "#fff"; c.fillText(`${len.toFixed(1)}s`, x + 8, STRIP_Y + 15);
  }
  // tappable bars like CapCut: blue = your graphics (looks, text, stickers), green = cut-away clips (B-roll)
  const bar = (x, w, y, col, label, on) => {
    c.globalAlpha = .85; c.fillStyle = col; c.beginPath(); c.roundRect(x, y, w, BAR_H, 3); c.fill(); c.globalAlpha = 1;
    if (on) { c.strokeStyle = "#fff"; c.lineWidth = 2; c.stroke(); }
    if (BAR_H >= 14 && w > 24) { c.save(); c.beginPath(); c.rect(x + 4, y, w - 8, BAR_H); c.clip(); c.fillStyle = "#fff"; c.font = "11px Montserrat_600SemiBold, sans-serif"; c.fillText(label, x + 6, y + 13); c.restore(); }
  };
  for (const [ov, [a, b]] of S.spans) bar(timeToX(a), Math.max(4, (b - a) * S.pps - 2), OV_Y, accent, ovLabel(ov), ov.id === S.selOv);
  for (const [bb, [a, b]] of S.bspans || []) bar(timeToX(a), Math.max(4, (b - a) * S.pps - 2), BR_Y, "#1F9D6B", bb.src ? bb.src.split("/").pop() : "panel", false);
  if (S.p.sfx_on !== false) for (const [id, t] of sfxTimes()) { c.fillStyle = "#C2410C"; c.beginPath(); c.arc(timeToX(t), 16, 2.5, 0, 7); c.fill(); }
  c.globalAlpha = 1;

  drawPlayhead();
}
let lastFollow = 0;
function ovLabel(ov) {
  if (ov.kind === "look") { const m = lookMeta(ov.look); return (ov.role === "hook" ? "Hook · " : "") + (m?.name || ov.look); }
  return ov.kind === "emoji" ? "Emoji" : (ov.src || ov.kind || "").split("/").pop();
}
function drawPlayhead() {  // the playhead stays in the middle; the strip scrolls under it
  if (!S.p || S.trim) return;
  const now = performance.now();
  if (S.playing && now - lastFollow < 80) return;  // ~12 moves a second while playing: smooth and much lighter
  lastFollow = now;
  const want = Math.round(S.outT * S.pps);
  if (Math.abs(tlBox.scrollLeft - want) > 1) { S.tlAuto = true; tlBox.scrollLeft = want; }
}
tlBox.addEventListener("scroll", () => {
  if (S.tlAuto) { S.tlAuto = false; return; }
  if (S.playing) pause();
  seek(Math.max(0, Math.min(S.T, tlBox.scrollLeft / S.pps)));
});
tlBox.addEventListener("wheel", e => {  // ctrl/pinch = zoom, wheel = scroll through time
  if (e.ctrlKey) { e.preventDefault(); setZoom(S.pps * (e.deltaY < 0 ? 1.15 : 1 / 1.15)); }
  else if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); tlBox.scrollLeft += e.deltaY; }
}, { passive: false });
function setZoom(pps) { S.pps = Math.max(8, Math.min(400, pps)); $("#zoom").value = Math.log2(S.pps / 8); drawTimeline(); }
function clipAtX(x) { return S.segs.findIndex(sg => x >= timeToX(sg.o) && x <= timeToX(sg.o) + (sg.e - sg.s) * S.pps); }
function tlX(e) { const r = tl.getBoundingClientRect(); return e.clientX - r.left; }
tl.onpointerdown = e => {
  const x = tlX(e), y = e.clientY - tl.getBoundingClientRect().top;
  const sel = S.selClip != null ? S.segs[S.selClip] : null;
  if (sel && y > STRIP_Y - 4 && y < STRIP_Y + STRIP_H + 4) {  // grab a handle to trim
    const l = timeToX(sel.o), r = l + (sel.e - sel.s) * S.pps;
    const side = x >= l - 22 && x <= l + 6 ? "l" : x >= r - 6 && x <= r + 22 ? "r" : null;
    if (side) {
      e.preventDefault(); e.stopPropagation();
      S.trim = { side, x0: x, x, clip: S.selClip };
      const mv = ev => { S.trim.x = Math.max(l - (side === "l" ? sel.s * S.pps : 0), tlX(ev)); drawTimeline(); };
      const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); finishTrim(); };
      window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
      return;
    }
  }
  S.tapStart = { x: e.clientX, y };
  // grab and slide the strip: drag right = rewind, drag left = forward (like CapCut)
  const startX = e.clientX, startScroll = tlBox.scrollLeft;
  tl.style.cursor = "grabbing";
  const mv = ev => { if (Math.abs(ev.clientX - startX) > 3) tlBox.scrollLeft = startScroll - (ev.clientX - startX); };
  const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); tl.style.cursor = "grab"; };
  window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
};
tl.onpointerup = e => {  // a tap (not a drag-scroll) selects / deselects a clip
  const st = S.tapStart; S.tapStart = null;
  if (st && Math.abs(e.clientX - st.x) <= 6 && st.y >= OV_Y - 2) {  // tapped a blue / green bar: open it to edit
    const t = (tlX(e) - tlPad()) / S.pps;
    if (st.y < BR_Y - 2) {
      const hits = S.spans.filter(([ov, [a, b]]) => a <= t && t < b);
      if (hits.length) { const [ov, [a]] = hits[hits.length - 1]; seek(a + 0.05); return overlayEditor(ov.id); }
    } else {
      const hit = (S.bspans || []).find(([bb, [a, b]]) => a <= t && t < b);
      if (hit) { seek(hit[1][0] + 0.05); return brollEditor(hit[0].id); }
    }
    return;
  }
  if (!st || Math.abs(e.clientX - st.x) > 6 || st.y < STRIP_Y || st.y > STRIP_Y + STRIP_H) return;
  const i = clipAtX(tlX(e));
  S.selClip = i < 0 || i === S.selClip ? null : i;
  updateTlTools(); drawTimeline();
};
function finishTrim() {
  const { side, x0, x, clip } = S.trim; S.trim = null;
  const sg = S.segs[clip], dt = (x - x0) / S.pps;
  if (!sg || Math.abs(dt) < 0.03) return drawTimeline();
  mutate(p => {
    p.time_cuts = p.time_cuts || [];
    if (side === "l" && dt > 0) p.time_cuts.push([sg.s, Math.min(sg.e - 0.1, sg.s + dt)]);
    if (side === "r" && dt < 0) p.time_cuts.push([Math.max(sg.s + 0.1, sg.e + dt), sg.e]);
    // pulled out: bring footage back, including pauses One Take had trimmed automatically
    if (side === "l" && dt < 0) { const a = Math.max(0, sg.s + dt); unCut(p, a, sg.s); (p.time_keeps = p.time_keeps || []).push([a, sg.s]); }
    if (side === "r" && dt > 0) { const b = Math.min(p.duration, sg.e + dt); unCut(p, sg.e, b); (p.time_keeps = p.time_keeps || []).push([sg.e, b]); }
  });
}
function unCut(p, a, b) {  // give back [a, b]: shrink time cuts, and bring back words cut there
  p.time_cuts = (p.time_cuts || []).flatMap(([s, e]) => e <= a || s >= b ? [[s, e]] : [s < a ? [s, a] : null, e > b ? [b, e] : null].filter(Boolean));
  p.words.forEach(w => { if (w.cut && w.s >= a - 0.05 && w.e <= b + 0.05) { w.cut = false; delete w.why; } });
}
function srcAtPlayhead() { const sg = S.segs.find(s => s.o <= S.outT && S.outT < s.o + s.e - s.s) || S.segs[S.segs.length - 1]; return sg ? [sg, sg.s + (S.outT - sg.o)] : [null, 0]; }
function updateTlTools() {
  const on = S.selClip != null;
  document.querySelectorAll('.tltools [data-op="delete"]').forEach(b => b.classList.toggle("on", on));
}
$("#zoom").min = 0; $("#zoom").max = 5.6; $("#zoom").step = 0.1;
$("#zoom").oninput = e => setZoom(8 * Math.pow(2, +e.target.value));
document.querySelectorAll(".tltools [data-op]").forEach(b => b.onclick = () => tlOp(b.dataset.op));
function tlOp(op) {
  if (op === "zoomIn" || op === "zoomOut") return setZoom(S.pps * (op === "zoomIn" ? 1.5 : 1 / 1.5));
  const [sg, ts] = srcAtPlayhead();
  if (op === "delete") {
    if (S.selClip != null && S.segs[S.selClip]) { const c = S.segs[S.selClip]; S.selClip = null; updateTlTools(); return mutate(p => { (p.time_cuts = p.time_cuts || []).push([c.s, c.e]); }); }
    if (S.sel) return selAction("cut");
    return toast("Tap a clip on the timeline to select it, then Delete.");
  }
  if (!sg) return;
  if (op === "split") { S.selClip = null; return mutate(p => { (p.splits = p.splits || []).push(+ts.toFixed(3)); }); }
  if (op === "cutBefore") return mutate(p => { (p.time_cuts = p.time_cuts || []).push([sg.s, ts]); });
  if (op === "cutAfter") return mutate(p => { (p.time_cuts = p.time_cuts || []).push([ts, sg.e]); });
}
new ResizeObserver(() => drawTimeline()).observe(tlBox);

// CapCut's track buttons: they sit just left of 0:00 inside the scrolling strip, so the clip starts right at the
// playhead and the buttons scroll away as you move along
function placeTrackButtons() {
  const tr = $("#tlTrack"); if (!tr) return;
  tr.style.left = Math.max(4, tlPad() - tr.offsetWidth - 10) + "px";
  const mute = +(S.p.voice_volume ?? 1) === 0;
  $("#tlMute").classList.toggle("on", mute);
  $("#tlMute b").textContent = mute ? "🔇" : "🔊";
  $("#tlMute span").textContent = mute ? "Muted" : "Mute clip";
}
$("#tlMute").onclick = () => {  // silences your voice track (music and sound effects stay)
  const mute = +(S.p.voice_volume ?? 1) !== 0;
  mutate(p => { p.voice_volume = mute ? 0 : 1; });
  v.muted = mute; toast(mute ? "Clip audio muted. Music and sound effects still play." : "Clip audio back on.");
};
$("#tlCover").onclick = async () => {  // the frame under the playhead becomes the reel's cover
  await api(`/api/project/${S.name}/frame`, { t: S.outT });
  await reload();
  const k = (S.p.frames || []).length - 1;
  if (k >= 0) mutate(p => { p.frames.forEach((f, j) => f.star = j === k); });
  toast("This frame is your cover now (Finish → Frames).");
};

// ------------------------------------------------------------------ keys, help, theme
document.addEventListener("keydown", e => {
  if (e.target.matches("input, textarea, select") || !S.p) return;
  const mod = e.metaKey || e.ctrlKey;
  if (e.key === " ") { e.preventDefault(); toggle(); }
  else if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (e.key === "Backspace" || e.key === "Delete") { e.preventDefault(); tlOp("delete"); }
  else if (e.key === "s" && !mod) saveFrame();
  else if (e.key === "b") tlOp("split");
  else if (e.key === "q") tlOp("cutBefore");
  else if (e.key === "w") tlOp("cutAfter");
  else if (e.key === "ArrowRight") seek(S.outT + (e.shiftKey ? 3 : 0.5));
  else if (e.key === "ArrowLeft") seek(S.outT - (e.shiftKey ? 3 : 0.5));
  else if (e.key === "Escape") { closeModal(); S.sel = null; renderPanel(); }
});
$("#undo").onclick = undo; $("#redo").onclick = redo;
$("#helpBtn").onclick = () => openModal(`<h1>Show me around</h1>
  <h3>1 · Cut</h3><div class="muted">Claude already removed pauses, filler words and repeated takes. Check “lines the engine cut” to bring any back or use a different take. Select words and press Delete to cut them.</div>
  <h3>2 · Visuals</h3><div class="muted">Pick a caption style, highlight words, add looks, GIFs, emoji, cut-away clips, and cover faces. Drag stickers on the preview. Describe anything new to Claude — you get three options to pick from.</div>
  <h3>3 · Sound</h3><div class="muted">Choose and swap background music.</div>
  <h3>4 · Finish</h3><div class="muted">Lock in to render. Then download, send to CapCut as layers, save frames, make a carousel, story and trial reels.</div>
  <h3>Shortcuts</h3><div class="kv"><label>Space</label><div>Play / pause</div><label>Delete</label><div>Cut selected words</div><label>Shift-click</label><div>Extend selection</div><label>B / Q / W</label><div>Split · cut before · cut after playhead</div><label>S</label><div>Save this frame</div><label>⌘Z / ⇧⌘Z</label><div>Undo / redo</div><label>← →</label><div>Nudge playhead (shift = 3s)</div></div>`);
$("#themeBtn").onclick = () => {
  const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("cc_theme", next); } catch {}
  drawTimeline();
};
try { const th = localStorage.getItem("cc_theme"); if (th) document.documentElement.dataset.theme = th; } catch {}
new ResizeObserver(() => { fitStage(); drawTimeline(); }).observe($("#phone"));

boot();
