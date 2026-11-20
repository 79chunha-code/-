// 천사전 · core: constants, pixel interface surface, pixel font, layout, input (joystick, jump, keys), sound.
// The battle is split into plain scripts that share one global scope, loaded in order by index.html:
//   core.js → world.js → lights.js → patterns.js → stage.js → main.js
"use strict";

const $ = (id) => document.getElementById(id);
const Q = new URLSearchParams(location.search);
const TAU = Math.PI * 2;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const rnd = (a, b) => a + Math.random() * (b - a);
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (k) => { k = clamp(k, 0, 1); return k * k * (3 - 2 * k); };
const angDiff = (a, b) => ((((a - b) + Math.PI) % TAU) + TAU) % TAU - Math.PI;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---------- The floor, in metres ----------
// The fight takes the stone circle in the middle of the plateau: centre at the origin, radius AR. The angel hangs over
// (0, AZ), on the side of the summit (−Z), and never leaves that point. Rota cannot come closer to it than EXR.
const AR = +(Q.get("arena") || 11.5);
const AZ = -(+(Q.get("az") || 7.2));
const EXR = 2.2;
const LIFT = +(Q.get("lift") || 1.4);          // the angel's hem above the floor
const TGT_R = 1.35;                             // the angel's feet: a shadow that reaches this circle hurts it
const PMAX = 6;                                 // Rota's breath
const HIT_R = 0.13;                             // Rota is only hit at the small red point at her feet
const SPEED = 4.0, JUMP_T = 0.7, JUMP_H = 0.62; // run speed m/s, jump time s, jump height m
const SEG = [80, 60, 40, 20, 0];                // the angel's light: each pattern takes one segment down
const DT_MAX = +(Q.get("dtmax") || 1 / 30);     // a slow test machine can pass ?dtmax=0.1

// ---------- Interface palette (the world itself is 3D) ----------
const FH = 270, CW = 480;
let FW = CW, OX = 0;
const PAL = ["#000000", "#12163a", "#232c66", "#3558b8", "#f6f8ff", "#cdd6f1", "#9aa8dc", "#6f7dbd", "#55629f", "#3f4a82",
  "#ffd257", "#fff1b0", "#fffbe6", "#f0932e", "#df4b43", "#ff9a86", "#f2e4c0", "#dcc89a", "#5a3a2a", "#96603c", "#9c2a35", "#6ea2e4"];
const C = {};
["", "INK", "DEEP", "BLUE", "WHITE", "MARB1", "MARB2", "MARB3", "MARB4", "MARB5", "SUN", "SUNP", "SUNC", "ORNG", "RED", "PINK",
  "PAPER", "PAPER2", "BROWN", "BROWN2", "REDD", "SKY3"].forEach((n, i) => { if (n) C[n] = i; });
const pal32 = new Uint32Array(PAL.map((h, i) => (i === 0 ? 0 : (0xff000000 | (parseInt(h.slice(5, 7), 16) << 16) | (parseInt(h.slice(3, 5), 16) << 8) | parseInt(h.slice(1, 3), 16)) >>> 0)));

// ---------- Pixel surface ----------
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const surf = (w, h) => ({ w, h, d: new Uint8Array(w * h) });
let S = null, OFX = 0, cx0 = 0, cy0 = 0, cx1 = 0, cy1 = 0;
function target(s, ofx) { S = s; OFX = ofx || 0; cx0 = 0; cy0 = 0; cx1 = s.w; cy1 = s.h; }
function px(x, y, c) { x += OFX; if (x >= cx0 && x < cx1 && y >= cy0 && y < cy1) S.d[y * S.w + x] = c; }
// lv: dither level 1..16 (16 or undefined = solid)
function rect(x, y, w, h, c, lv) {
  x = Math.round(x) + OFX; y = Math.round(y); w = Math.round(w); h = Math.round(h);
  const x0 = Math.max(cx0, x), y0 = Math.max(cy0, y), x1 = Math.min(cx1, x + w), y1 = Math.min(cy1, y + h), d = S.d, sw = S.w;
  if (lv === undefined || lv >= 16) { for (let yy = y0; yy < y1; yy++) d.fill(c, yy * sw + x0, yy * sw + Math.max(x0, x1)); return; }
  for (let yy = y0; yy < y1; yy++) for (let xx = x0; xx < x1; xx++) if (BAYER[(yy & 3) * 4 + (xx & 3)] < lv) d[yy * sw + xx] = c;
}
function frame(x, y, w, h, c) { rect(x, y, w, 1, c); rect(x, y + h - 1, w, 1, c); rect(x, y, 1, h, c); rect(x + w - 1, y, 1, h, c); }
function disc(cx, cy, r, c, lv) {
  for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y + r * 0.6)); rect(cx - w, cy + y, w * 2 + 1, 1, c, lv); }
}
function ring(cx, cy, r, c) {
  for (let a = 0; a < 64; a++) { const t = a / 64 * TAU; px(Math.round(cx + Math.cos(t) * r), Math.round(cy + Math.sin(t) * r), c); }
}
function blit(sp, x, y, o) {
  x = Math.round(x) + OFX; y = Math.round(y);
  const tint = o && o.tint, d = S.d, sw = S.w, sd = sp.d, w = sp.w;
  for (let yy = 0; yy < sp.h; yy++) {
    const ty = y + yy; if (ty < cy0 || ty >= cy1) continue;
    for (let xx = 0; xx < w; xx++) { const c = sd[yy * w + xx]; if (!c) continue; const tx = x + xx; if (tx < cx0 || tx >= cx1) continue; d[ty * sw + tx] = tint || c; }
  }
}
function spr(rows, map) {
  const s = surf(rows[0].length, rows.length);
  rows.forEach((r, y) => { for (let x = 0; x < r.length; x++) s.d[y * s.w + x] = map[r[x]] || 0; });
  return s;
}
function slab(x, y, w, h, fill, edge) { rect(x - 1, y - 1, w + 2, h + 2, C.INK); rect(x, y, w, h, edge); rect(x + 1, y + 1, w - 2, h - 2, fill); }
const soul = (x, y) => { rect(x, y, 5, 5, C.RED); rect(x, y, 2, 1, C.PINK); px(x, y + 1, C.PINK); };

// ---------- Pixel font (Galmuri, see font.js) ----------
function mkFont(src, cap, pitch) {
  const idx = new Map(), recs = src.data.split(" "), cache = new Map();
  Array.from(src.chars).forEach((ch, i) => idx.set(ch, i));
  const f = { cap, pitch, glyph(ch) {
    let g = cache.get(ch); if (g) return g;
    const i = idx.get(ch); if (i === undefined) return ch === "?" ? null : f.glyph("?");
    const r = recs[i], bin = atob(r.slice(5));
    g = { adv: r.charCodeAt(0) - 48, w: r.charCodeAt(1) - 48, h: r.charCodeAt(2) - 48, xo: r.charCodeAt(3) - 56, yo: r.charCodeAt(4) - 56, bin };
    cache.set(ch, g); return g;
  } };
  return f;
}
const F11 = mkFont(window.GAME_FONTS.f11, 11, 14), F9 = mkFont(window.GAME_FONTS.f9, 9, 12);
function textW(str, f, sc) { let w = 0; for (const ch of str) { const g = f.glyph(ch); if (g) w += g.adv; } return (w - 1) * (sc || 1); }
function glyphAt(g, x, base, c, sc) {
  for (let r = 0, i = 0; r < g.h; r++) for (let k = 0; k < g.w; k++, i++) {
    if (g.bin.charCodeAt(i >> 3) & (0x80 >> (i & 7))) { if (sc === 1) px(x + g.xo + k, base - g.yo - g.h + r, c); else rect(x + (g.xo + k) * sc, base - (g.yo + g.h - r) * sc, sc, sc, c); }
  }
}
function text(str, x, y, c, f, sc) {   // y is the top of a capital/Hangul glyph
  sc = sc || 1; x = Math.round(x); y = Math.round(y);
  for (const ch of str) { const g = f.glyph(ch); if (!g) continue; glyphAt(g, x, y + f.cap * sc, c, sc); x += g.adv * sc; }
  return x;
}
function textO(str, x, y, c, oc, f, sc) {
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) text(str, x + dx, y + dy, oc, f, sc);
  text(str, x, y, c, f, sc);
}
const textC = (str, cx, y, c, f, sc) => text(str, cx - textW(str, f, sc) / 2, y, c, f, sc);
const textCO = (str, cx, y, c, oc, f, sc) => textO(str, Math.round(cx - textW(str, f, sc) / 2), y, c, oc, f, sc);
// "<b>..</b>" marks emphasis. Returns lines of cells {ch, hl}.
function wrap(str, maxW, f) {
  const cells = []; let hl = false;
  for (let i = 0; i < str.length; i++) {
    if (str.startsWith("<b>", i)) { hl = true; i += 2; continue; }
    if (str.startsWith("</b>", i)) { hl = false; i += 3; continue; }
    cells.push({ ch: str[i], hl });
  }
  const adv = (c) => { const g = f.glyph(c.ch); return g ? g.adv : 0; };
  const lines = [[]]; let w = 0, i = 0;
  while (i < cells.length) {
    const cur = lines[lines.length - 1];
    if (cells[i].ch === " ") { if (cur.length) { cur.push(cells[i]); w += adv(cells[i]); } i++; continue; }
    let j = i, ww = 0; while (j < cells.length && cells[j].ch !== " ") { ww += adv(cells[j]); j++; }
    if (w + ww > maxW && cur.length) { lines.push([]); w = 0; continue; }
    if (ww > maxW) { for (; i < j; i++) { if (w + adv(cells[i]) > maxW) { lines.push([]); w = 0; } lines[lines.length - 1].push(cells[i]); w += adv(cells[i]); } continue; }
    for (; i < j; i++) cur.push(cells[i]);
    w += ww;
  }
  return lines;
}
function drawLines(lines, x, y, f, pitch, c, hc) {
  for (const ln of lines) {
    let xx = x;
    for (const cell of ln) { const g = f.glyph(cell.ch); if (g) { glyphAt(g, xx, y + f.cap, cell.hl ? hc : c, 1); xx += g.adv; } }
    y += pitch;
  }
}
const strip = (s) => s.replace(/<\/?b>/g, "");

// ---------- Layout ----------
const stageEl = $("stage"), fieldEl = $("field"), glEl = $("gl"), uiEl = $("ui"), srEl = $("say"), uctx = uiEl.getContext("2d");
let cssPx = 1, rot = false, ui = null, uimg = null, uout = null, glW = 0, glH = 0;
const touchDev = matchMedia("(pointer: coarse)").matches;
function resize() {
  const cs = getComputedStyle(stageEl);
  const pl = parseFloat(cs.paddingLeft), pt = parseFloat(cs.paddingTop);
  let aw = stageEl.clientWidth - pl - parseFloat(cs.paddingRight), ah = stageEl.clientHeight - pt - parseFloat(cs.paddingBottom);
  const midX = pl + aw / 2, midY = pt + ah / 2;
  rot = touchDev && ah > aw * 1.15;            // a phone held upright shows the game turned on its side
  if (rot) [aw, ah] = [ah, aw];
  const fw = clamp(Math.round((FH * aw) / ah / 2) * 2, CW, 640);   // wider screens see more of the plateau
  if (fw !== FW || !ui) {
    FW = fw; OX = (FW - CW) / 2;
    ui = surf(FW, FH); uiEl.width = FW; uiEl.height = FH;
    uimg = uctx.createImageData(FW, FH); uout = new Uint32Array(uimg.data.buffer);
    cam.aspect = FW / FH; cam.updateProjectionMatrix();
    stageCam.aspect = FW / FH; stageCam.updateProjectionMatrix();
  }
  const dpr = window.devicePixelRatio || 1, s = Math.min(aw / FW, ah / FH), k = Math.floor(s * dpr);
  cssPx = k >= 2 && k / (s * dpr) >= 0.85 ? k / dpr : s;
  Object.assign(fieldEl.style, { width: FW * cssPx + "px", height: FH * cssPx + "px", left: midX - (FW * cssPx) / 2 + "px", top: midY - (FH * cssPx) / 2 + "px", transform: rot ? "rotate(90deg)" : "" });
  const q = Math.min(dpr, 1.5), w = Math.max(CW, Math.round(FW * cssPx * q)), h = Math.max(FH, Math.round(FH * cssPx * q));
  if (w !== glW || h !== glH) { glW = w; glH = h; renderer.setSize(w, h, false); }
}
// a pointer event to interface pixels (the field may be turned on its side)
function toUI(e) {
  const r = fieldEl.getBoundingClientRect();
  let u, v;
  if (rot) { u = (e.clientY - r.top) / r.height; v = 1 - (e.clientX - r.left) / r.width; }
  else { u = (e.clientX - r.left) / r.width; v = (e.clientY - r.top) / r.height; }
  return [u * FW - OX, v * FH];
}

// ---------- Input ----------
// Touch: a fixed joystick at the bottom right, a jump button at the bottom left. Keys: arrows/WASD, Space or Z to jump.
const IN = { x: 0, y: 0, jump: false, jumpEdge: false, ok: false, okEdge: false, left: false, right: false, leftEdge: false, rightEdge: false, back: false };
const JOY = { cx: 0, cy: 0, r: 26, id: null, kx: 0, ky: 0 }, JUMPB = { cx: 0, cy: 0, r: 20, id: null, down: false };
function placeControls() { JOY.cx = CW + OX - 52; JOY.cy = FH - 50; JUMPB.cx = 44 - OX; JUMPB.cy = FH - 46; }
const keys = new Set();
const tapHandlers = [];             // interface buttons drawn on the canvas: {x, y, w, h, fn}
addEventListener("keydown", (e) => {
  const k = e.key.toLowerCase();
  if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(k)) e.preventDefault();
  if (!keys.has(k)) {
    if (k === " " || k === "z" || k === "j") IN.jumpEdge = true;
    if (k === "enter" || k === "z" || k === " ") IN.okEdge = true;
    if (k === "arrowleft" || k === "a") IN.leftEdge = true;
    if (k === "arrowright" || k === "d") IN.rightEdge = true;
  }
  keys.add(k); audioOn();
});
addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
addEventListener("blur", () => keys.clear());
fieldEl.addEventListener("pointerdown", (e) => {
  audioOn(); e.preventDefault();
  const [x, y] = toUI(e);
  for (let i = tapHandlers.length - 1; i >= 0; i--) { const b = tapHandlers[i]; if (x >= b.x && x < b.x + b.w && y >= b.y && y < b.y + b.h) { b.fn(); return; } }
  if (controlsOn()) {
    if (Math.hypot(x - JUMPB.cx, y - JUMPB.cy) < JUMPB.r + 14 || (x < CW / 2 - 40 && y > FH * 0.45)) { JUMPB.id = e.pointerId; JUMPB.down = true; IN.jumpEdge = true; fieldEl.setPointerCapture(e.pointerId); return; }
    if (x > CW / 2 - 20 && y > FH * 0.3) { JOY.id = e.pointerId; fieldEl.setPointerCapture(e.pointerId); joyMove(x, y); return; }
  }
  IN.okEdge = true; tapAnywhere();
});
fieldEl.addEventListener("pointermove", (e) => { if (e.pointerId === JOY.id) { const [x, y] = toUI(e); joyMove(x, y); } });
const endPtr = (e) => { if (e.pointerId === JOY.id) { JOY.id = null; JOY.kx = JOY.ky = 0; } if (e.pointerId === JUMPB.id) { JUMPB.id = null; JUMPB.down = false; } };
fieldEl.addEventListener("pointerup", endPtr); fieldEl.addEventListener("pointercancel", endPtr);
function joyMove(x, y) {
  let dx = x - JOY.cx, dy = y - JOY.cy; const d = Math.hypot(dx, dy) || 1;
  if (d > JOY.r) { dx *= JOY.r / d; dy *= JOY.r / d; }
  JOY.kx = dx / JOY.r; JOY.ky = dy / JOY.r;
}
function readInput() {
  let x = 0, y = 0;
  if (keys.has("arrowleft") || keys.has("a")) x -= 1;
  if (keys.has("arrowright") || keys.has("d")) x += 1;
  if (keys.has("arrowup") || keys.has("w")) y += 1;
  if (keys.has("arrowdown") || keys.has("s")) y -= 1;
  if (JOY.id !== null) { x = JOY.kx; y = -JOY.ky; if (Math.hypot(x, y) < 0.18) x = y = 0; }
  const m = Math.hypot(x, y); if (m > 1) { x /= m; y /= m; }
  IN.x = x; IN.y = y;
  IN.jump = keys.has(" ") || keys.has("z") || keys.has("j") || JUMPB.down;
}
function clearEdges() { IN.jumpEdge = IN.okEdge = IN.leftEdge = IN.rightEdge = false; }

// ---------- Sound: bells and glass for the light, low muffled thuds for the shadow ----------
let ac = null, muted = false, master = null, drone = null;
function audioOn() {
  try {
    if (!ac) { ac = new (window.AudioContext || window.webkitAudioContext)(); master = ac.createGain(); master.gain.value = 0.9; master.connect(ac.destination); }
    if (ac.state === "suspended") ac.resume();
  } catch (e) { ac = null; }
}
function osc(type, f, t, dur, vol, out, f1) {
  const o = ac.createOscillator(), g = ac.createGain();
  o.type = type; o.frequency.setValueAtTime(f, t); if (f1) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
  g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vol, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(out || master); o.start(t); o.stop(t + dur + 0.05);
}
// a struck bell: inharmonic partials that die away at different speeds
function bell(f, vol, dur, delay) {
  if (!ac || muted) return;
  const t = ac.currentTime + (delay || 0);
  [[1, 1], [2.0, 0.5], [2.76, 0.35], [5.4, 0.18], [8.93, 0.08]].forEach(([r, a], i) => osc("sine", f * r, t, dur / (1 + i * 0.6), vol * a));
}
// a glass ting: two close high sines and a click
function glass(f, vol, dur, delay) {
  if (!ac || muted) return;
  const t = ac.currentTime + (delay || 0);
  osc("sine", f, t, dur, vol); osc("sine", f * 1.007, t, dur * 0.8, vol * 0.7); osc("triangle", f * 2.41, t, dur * 0.3, vol * 0.25);
}
let noiseBuf = null;
function noise(dur, vol, freq, type, delay, q) {
  if (!ac || muted) return;
  if (!noiseBuf) { noiseBuf = ac.createBuffer(1, ac.sampleRate * 1.5, ac.sampleRate); const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; }
  const t = ac.currentTime + (delay || 0), s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
  s.buffer = noiseBuf; f.type = type || "bandpass"; f.frequency.value = freq; f.Q.value = q || 0.8;
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  s.connect(f).connect(g).connect(master); s.start(t); s.stop(t + dur);
}
function thud(f, vol, dur) { if (!ac || muted) return; const t = ac.currentTime; osc("sine", f, t, dur, vol, null, f * 0.5); noise(dur * 0.6, vol * 0.7, 180, "lowpass"); }
function droneLevel(v, sec) {
  if (!ac) return;
  if (!drone) {
    const g = ac.createGain(), f = ac.createBiquadFilter(); g.gain.value = 0; f.type = "lowpass"; f.frequency.value = 420;
    f.connect(g).connect(master);
    [110, 164.8, 220.4, 329.6].forEach((hz, i) => { const o = ac.createOscillator(); o.type = "sine"; o.frequency.value = hz; o.detune.value = (i - 1.5) * 6; const og = ac.createGain(); og.gain.value = 1 / (1 + i); o.connect(og).connect(f); o.start(); });
    drone = g;
  }
  const t = ac.currentTime; drone.gain.cancelScheduledValues(t); drone.gain.setValueAtTime(drone.gain.value, t);
  drone.gain.linearRampToValueAtTime(muted ? 0 : v * 0.035, t + (sec || 0.5));
}
let sndGate = {};
function gate(k, sec) { const n = performance.now(); if ((sndGate[k] || 0) > n) return false; sndGate[k] = n + sec * 1000; return true; }
const sfx = {
  select() { glass(1760, 0.05, 0.25); },
  move() { glass(1320, 0.03, 0.12); },
  featherFire() { if (gate("ff", 0.07)) glass(rnd(2400, 2900), 0.03, 0.18); },
  featherStick() { if (gate("fs", 0.05)) glass(rnd(3200, 3600), 0.02, 0.35); },
  bristle() { for (let i = 0; i < 9; i++) glass(rnd(2600, 4200), 0.018, 0.09, i * 0.03); noise(0.35, 0.05, 5200, "highpass"); },
  charge() { if (!ac || muted) return; const t = ac.currentTime; osc("sine", 440, t, 1.2, 0.03, null, 1320); osc("sine", 660, t, 1.2, 0.02, null, 1980); },
  laser() { bell(392, 0.07, 2.4); noise(0.9, 0.08, 1400, "bandpass", 0, 2); },
  reflect() { glass(2093, 0.04, 0.6); },
  arrow() { if (gate("ar", 0.09)) glass(rnd(3000, 3800), 0.012, 0.06); },
  ringWake(i) { glass(880 * Math.pow(1.122, i), 0.035, 0.5); },
  eyeOpen() { bell(98, 0.12, 4.0); bell(147, 0.06, 3.5, 0.15); },
  eyeLaser() { bell(131, 0.09, 3); noise(1.6, 0.06, 600, "bandpass"); },
  burn() { if (gate("bn", 0.25)) noise(0.25, 0.04, 900, "bandpass"); },
  shadowFirst() { thud(70, 0.28, 0.5); bell(233, 0.05, 1.4, 0.02); bell(247, 0.04, 1.2, 0.02); },
  shadowTick() { if (gate("st", 0.06)) thud(rnd(95, 110), 0.12, 0.12); },
  hurt() { noise(0.25, 0.25, 3800, "highpass"); glass(1600, 0.06, 0.3); osc && ac && !muted && osc("triangle", 900, ac.currentTime, 0.35, 0.06, null, 260); },
  fall() { bell(110, 0.1, 3); noise(0.8, 0.12, 300, "lowpass"); },
  slash() { noise(0.18, 0.18, 2600, "bandpass", 0, 1.5); },
  passThrough() { glass(2637, 0.07, 1.4); glass(3136, 0.05, 1.2, 0.06); bell(523, 0.04, 2, 0.1); },
  swordDrop() { if (!ac || muted) return; [0, 0.16, 0.27].forEach((d, i) => { glass(rnd(1900, 2300) / (1 + i * 0.2), 0.05 / (1 + i), 0.5, d); }); },
  cloth() { noise(0.9, 0.09, 700, "lowpass"); noise(0.6, 0.04, 2400, "bandpass", 0.2); },
  page() { noise(0.25, 0.08, 2600, "bandpass"); },
  descend() { [262, 330, 392, 523, 659].forEach((f, i) => bell(f, 0.035, 4, i * 0.25)); },
  omen() { bell(196, 0.05, 2.2); },
  rise() { [392, 523, 659, 784].forEach((f, i) => glass(f * 2, 0.03, 0.8, i * 0.08)); },
  victory() { [784, 659, 523, 392, 330, 262].forEach((f, i) => bell(f, 0.05, 5, i * 0.45)); },
  turnEnd() { bell(523, 0.04, 1.5); bell(784, 0.03, 1.5, 0.12); },
};
function vibrate(ms) { if (navigator.vibrate && !reduceMotion) try { navigator.vibrate(ms); } catch (e) { /* not allowed */ } }

// ---------- Music: an empty slot until the composed tracks exist (?music=file.mp3 plays one in a loop) ----------
const MUSIC = { el: null, want: 0 };
function music(level) {
  if (!Q.get("music")) return;
  if (!MUSIC.el) { MUSIC.el = new Audio(Q.get("music")); MUSIC.el.loop = true; MUSIC.el.volume = 0; MUSIC.el.play().catch(() => {}); }
  MUSIC.want = muted ? 0 : level;
}
function musicStep(dt) { if (MUSIC.el) MUSIC.el.volume = clamp(MUSIC.el.volume + clamp(MUSIC.want - MUSIC.el.volume, -dt * 0.5, dt * 0.5), 0, 1); }
