// Mirror of engine/timeline.py + draw.anim_state + analyze.face_at.
// Keep in sync so the live preview matches the rendered reel.
"use strict";

const PUNCT_END = /[.,!?;:…]$/;

function buildSegments(words, duration, s) {
  const maxGap = s.max_gap, padB = s.pad_before, padA = s.pad_after;
  const n = words.length, segs = [];
  let cur = null;
  for (let i = 0; i < n; i++) {
    const w = words[i];
    if (w.cut) { cur = null; continue; }
    if (cur && cur.w1 === i - 1 && w.s - words[i - 1].e <= maxGap) cur.w1 = i;
    else { cur = { w0: i, w1: i }; segs.push(cur); }
  }
  let t = 0;
  for (const sg of segs) {
    let st = Math.max(0, words[sg.w0].s - padB);
    let en = Math.min(duration, words[sg.w1].e + padA);
    if (sg.w0 > 0 && words[sg.w0 - 1].cut) st = Math.min(Math.max(st, words[sg.w0 - 1].e), words[sg.w0].s);
    if (sg.w1 + 1 < n && words[sg.w1 + 1].cut) en = Math.min(en, Math.max(words[sg.w1].e, words[sg.w1 + 1].s));
    if (en - st < 0.05) en = st + 0.05;
    sg.s = +st.toFixed(3); sg.e = +en.toFixed(3); sg.o = +t.toFixed(3);
    t += sg.e - sg.s;
  }
  return segs;
}

const totalLen = segs => segs.reduce((a, sg) => a + sg.e - sg.s, 0);

function segOfWord(segs, i) {
  for (const sg of segs) if (sg.w0 <= i && i <= sg.w1) return sg;
  return null;
}

function wordOut(words, segs, i) {
  const sg = segOfWord(segs, i);
  if (!sg) return null;
  const w = words[i];
  return [Math.max(sg.o, sg.o + w.s - sg.s), sg.o + Math.min(w.e, sg.e) - sg.s];
}

function rangeOut(words, segs, w0, w1) {
  let a = null, b = null;
  for (let i = w0; i <= w1; i++) {
    const s = wordOut(words, segs, i);
    if (!s) continue;
    a = a === null ? s[0] : Math.min(a, s[0]);
    b = b === null ? s[1] : Math.max(b, s[1]);
  }
  return a === null ? null : [a, b];
}

function outToSrc(segs, t) {
  for (const sg of segs) if (sg.o <= t && t < sg.o + (sg.e - sg.s)) return [sg, sg.s + (t - sg.o)];
  if (segs.length) { const sg = segs[segs.length - 1]; return [sg, sg.e]; }
  return [null, 0];
}

function srcToOut(segs, ts) {
  for (const sg of segs) if (sg.s <= ts && ts < sg.e) return sg.o + (ts - sg.s);
  return null;
}

function captionGroups(words, segs, style) {
  const maxWords = style.mode === "single" ? 1 : (style.max_words || 3);
  const maxChars = style.max_chars || 18;
  const groups = [];
  let cur = null, prev = null;
  for (const sg of segs) {
    for (let i = sg.w0; i <= sg.w1; i++) {
      const w = words[i];
      const [st, en] = wordOut(words, segs, i);
      const joined = cur ? cur.w.map(j => words[j].t).join(" ") + " " + w.t : "";
      const brk = cur === null || cur.w.length >= maxWords || joined.length > maxChars ||
        (prev !== null && words[prev].l !== w.l) || !!w.cbreak ||
        (prev !== null && PUNCT_END.test(words[prev].t.trim())) ||
        (prev !== null && st - cur.end > 0.6);
      if (brk) { cur = { w: [], start: st, end: en }; groups.push(cur); }
      cur.w.push(i); cur.end = en; prev = i;
    }
  }
  for (let k = 0; k + 1 < groups.length; k++) {
    const a = groups[k], b = groups[k + 1];
    a.end = b.start - a.end < 0.5 ? b.start : a.end + 0.25;
  }
  if (groups.length) groups[groups.length - 1].end += 0.3;
  return groups;
}

function overlaySpan(p, words, segs, ov) {
  if (ov.role === "hook") return [0, Math.min(p.hook_duration || 3, totalLen(segs))];
  const sp = rangeOut(words, segs, ov.w0, ov.w1 ?? ov.w0);
  if (!sp) return null;
  if (ov.min_dur && sp[1] - sp[0] < ov.min_dur) sp[1] = sp[0] + ov.min_dur;
  return sp;
}

// ---- animation (engine/draw.py anim_state)
const ANIM_DUR = 0.3;
const ANIM_DURS = { "snap": 0.1, "slide-up": 0.2, "slide-down": 0.2 };
const animDur = k => ANIM_DURS[k] ?? ANIM_DUR;
const easeOutCubic = x => 1 - Math.pow(1 - x, 3);
const easeOutBack = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

function animState(kind, p) {
  p = Math.max(0, Math.min(1, p));
  const e = easeOutCubic(p);
  const st = { dx: 0, dy: 0, scale: 1, alpha: 1, rot: 0 };
  switch (kind) {
    case "fade": st.alpha = p; break;
    case "pop": st.scale = Math.max(0, easeOutBack(p)); st.alpha = Math.min(1, p * 3); break;
    case "slide-left": st.dx = -(1 - e) * 0.7; break;
    case "slide-right": st.dx = (1 - e) * 0.7; break;
    case "slide-up": st.dy = (1 - e) * 0.5; break;
    case "slide-down": st.dy = -(1 - e) * 0.5; break;
    case "spin": st.rot = (1 - e) * 360; st.scale = e; break;
    case "snap": st.scale = 0.4 + 0.6 * e; break;
    case "zoom": st.scale = 1 + (1 - e) * 1.5; st.alpha = p; break;
  }
  return st;
}

function overlayState(ov, t, s, e) {
  const ai = ov.anim_in ?? "pop", ao = ov.anim_out ?? "fade";
  if (ai && ai !== "none" && t - s < animDur(ai)) return animState(ai, (t - s) / animDur(ai));
  if (ao && ao !== "none" && e - t < animDur(ao)) return animState(ao, (e - t) / animDur(ao));
  return animState("none", 1);
}

const pushScale = (ov, t, s, e) => ov.push ? 1 + 0.06 * Math.max(0, Math.min(1, (t - s) / Math.max(0.1, e - s))) : 1;

const CAM_ANCHOR = [0.5, 0.38];
const focusOf = p => p.focus || CAM_ANCHOR;
function cameraZoom(p, words, segs, t) {
  const cam = p.camera || {};
  const starts = (cam.punches || []).map(i => wordOut(words, segs, i)).filter(Boolean).map(s => s[0]).sort((a, b) => a - b);
  const passed = starts.filter(s => s <= t).length;
  let z = passed % 2 ? (cam.punch_scale ?? 1.12) : 1;
  const push = +(cam.push_in || 0);
  if (push > 0 && (!starts.length || t < starts[0])) { const k = Math.min(1, t / push); z *= 1 + (cam.push_amount ?? 0.08) * (1 - (1 - k) ** 2); }
  return z;
}

// ---- faces (engine/analyze.py face_at)
function faceAt(track, t, hold = 0.6, maxGap = 1.6) {
  if (!track || !track.length || t < track[0][0] - hold || t > track[track.length - 1][0] + hold) return null;
  if (t <= track[0][0]) return track[0].slice(1);
  if (t >= track[track.length - 1][0]) return track[track.length - 1].slice(1);
  let lo = 0, hi = track.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (track[mid][0] <= t) lo = mid; else hi = mid; }
  const a = track[lo], b = track[hi];
  if (b[0] - a[0] > maxGap) return t - a[0] < hold ? a.slice(1) : (b[0] - t < hold ? b.slice(1) : null);
  const k = (t - a[0]) / (b[0] - a[0]);
  return [1, 2, 3].map(i => a[i] + (b[i] - a[i]) * k);
}

// ---- caption layout (engine/draw.py caption_layout)
const _mc = document.createElement("canvas").getContext("2d");
function measure(text, font, size) { _mc.font = `${size}px "${font}"`; return _mc.measureText(text).width; }
function caseText(t, style) { return style.uppercase ? t.toUpperCase() : style.lowercase ? t.toLowerCase() : t; }

function captionLayout(words, idxs, style, W) {
  const size = style.size, maxw = W * 0.84;
  const items = idxs.map(i => {
    const w = words[i], emph = !!w.hl;
    const font = emph ? (style.emph_font || style.font) : style.font;
    const sz = size * (emph ? (style.emph_scale || 1) : 1);
    const text = caseText(w.t, style);
    return { i, text, font, size: sz, w: measure(text, font, sz), emph };
  });
  const space = measure(" ", style.font, size);
  const lines = []; let cur = [], cw = 0;
  for (const it of items) {
    let add = it.w + (cur.length ? space : 0);
    if (cur.length && cw + add > maxw) { lines.push([cur, cw]); cur = []; cw = 0; add = it.w; }
    cur.push(it); cw += add;
  }
  if (cur.length) lines.push([cur, cw]);
  return { lines, space };
}
