// 천사전 · patterns: the angel's five turns, from the outside in. Each turn opens one more part of its body.
//   1 깃털 (top wings cover the eye) → 2 날개 레이저 (four wings open) → 3 고리 눈 (the ring wakes)
//   → 4 큰 눈 레이저 (the eye opens) → 5 본모습 (everything, two at a time)
// A pattern that has to be played again comes back as a variant, never harder.
"use strict";

// ---------- A timeline: things that happen at set times, and things that run every frame ----------
function runner() { return { t: 0, ev: [], upd: [], done: false, at(t, fn) { this.ev.push({ t, fn }); }, every(fn) { this.upd.push(fn); } }; }
function runStep(R, dt) {
  R.t += dt;
  for (let i = 0; i < R.ev.length; i++) { const e = R.ev[i]; if (!e.done && e.t <= R.t) { e.done = true; e.fn(); } }
  R.upd.forEach((f) => f(dt, R.t));
}
const angelFacing = () => { const dx = P.x - 0, dz = P.z - AZ, d = Math.hypot(dx, dz) || 1; return [dx / d, dz / d]; };

// ---------- Feathers: a burst of feathers along one path from a wing tip ----------
const _a = new V3(), _b = new V3();
function featherBurst(R, t0, side, n, gap, speed) {
  const k = side + "Mid";
  R.at(t0 - 0.5, () => { ANG.wings[k].glare = 1; sfx.omen && glass(1568, 0.025, 0.3); });
  R.at(t0, () => {
    const from = wingTip(k, new V3());
    const ux = P.x - from.x, uz = P.z - from.z, ul = Math.hypot(ux, uz) || 1;
    const to = new V3(P.x + (ux / ul) * 0.8, Y0, P.z + (uz / ul) * 0.8);
    for (let i = 0; i < n; i++) R.at(t0 + i * gap, () => addFeather(from, to, speed || 15));
  });
}

// ---------- Wing lasers: a line of light lying on the floor, swept like a wiper; it bounces once off the fence ----------
function wingSweep(R, t0, side, pair, opts) {
  opts = opts || {};
  R.at(t0, () => {
    const [fx, fz] = angelFacing(), sx = -fz, sz = fx;          // the angel's right, seen from Rota
    const sg = side === "R" ? 1 : -1;
    const px_ = 0 + sx * sg * 1.6 + fx * 0.8, pz_ = AZ + sz * sg * 1.6 + fz * 0.8;
    const c = Math.atan2(fz, fx), half = THREE.MathUtils.degToRad(pair === "Mid" ? 72 : 42);
    const dir = (opts.dir || 1) * sg;                            // a wing sweeps from its own side across
    const mk = (a0, a1) => {
      const b = { k: "wlaser", wing: side + pair, px: px_, pz: pz_, th0: a0, th1: a1, th: a0, st: "aim", t: 0, aim: opts.aim || 0.9, dur: pair === "Mid" ? 2.6 : 1.35, harm: true, floor: true, lum: 0 };
      wingSegs(b); L.push(b); return b;
    };
    if (opts.v) { mk(c, c + half * 1.1); mk(c, c - half * 1.1); }
    else mk(c + dir * half, c - dir * half);
  });
}
function stepWingLaser(b, dt) {
  if (b.st === "aim") { if (b.t >= b.aim) { b.st = "fire"; b.t = 0; sfx.laser(); } }
  else if (b.st === "fire") {
    const k = clamp(b.t / b.dur, 0, 1); b.th = lerp(b.th0, b.th1, k < 0.5 ? 2 * k * k : 1 - 2 * (1 - k) * (1 - k)); wingSegs(b);
    if (b.t >= b.dur) { b.st = "fade"; b.t = 0; }
    if (!b.bounced && b.t > 0.05) { b.bounced = true; sfx.reflect(); }
  } else if (b.t > 0.3) b.dead = true;
}
function drawWingLaser(b) {
  if (b.st === "aim") {
    const m = take("strip", () => mkStrip("#fff2c8", 0.4)); const s = b.seg1;
    placeStrip(m, s[0], s[1], s[2], s[3], 0.07, 0.04); m.material.opacity = 0.25 + 0.25 * Math.sin(b.t * 18) ** 2;
    return;
  }
  const op = b.st === "fade" ? 1 - b.t / 0.3 : 1;
  const s1 = b.seg1, s2 = b.seg2;
  const m1 = take("strip", () => mkStrip("#fff2c8", 1)); placeStrip(m1, s1[0], s1[1], s1[2], s1[3], 0.52, 0.05); m1.material.opacity = op;
  const m2 = take("strip", () => mkStrip("#fff2c8", 1)); placeStrip(m2, s2[0], s2[1], s2[2], s2[3], 0.26, 0.045); m2.material.opacity = 0.55 * op;
  const bm = take("beam", () => beam("#fff0c0", 0.14)); placeBeam(bm, wingTip(b.wing, _a), _b.set(b.px, Y0 + 0.05, b.pz)); bm.material.opacity = 0.8 * op;
  const g1 = take("glow", () => floorGlow("#ffe2a0", 1)); g1.position.set(b.px, Y0 + 0.04, b.pz); g1.scale.setScalar(2.2); g1.material.opacity = op;
  const g2 = take("glow", () => floorGlow("#ffe2a0", 1)); g2.position.set(s1[2], Y0 + 0.04, s1[3]); g2.scale.setScalar(1.6); g2.material.opacity = op;
}

// ---------- The big eye's laser: follows Rota a beat late, burns the floor it crosses ----------
function eyeBeam(R, t0, t1, opts) {
  opts = opts || {};
  let b = null;
  R.at(t0, () => {
    b = { k: "elaser", fx: P.x - (P.x - 0) * 0.3, fz: P.z - (P.z - AZ) * 0.3, on: false, warm: 0.5, t: 0, burnT: 0, off: opts.off || 0, offEnd: opts.offEnd === undefined ? opts.off || 0 : opts.offEnd, t0, t1, cut: 0, harm: true, floor: false, lum: 0 };
    b.R = R; L.push(b); sfx.eyeLaser();
  });
  (opts.cuts || []).forEach((ct) => R.at(ct, () => { if (b) { b.cut = 0.9; b.cx = P.x + P.vx * 0.9; b.cz = P.z + P.vz * 0.9; } }));
  R.at(t1, () => { if (b) b.dead = true; });
}
function stepEyeLaser(b, dt) {
  if (b.t > b.warm) b.on = true;
  const k = clamp((b.R.t - b.t0) / Math.max(0.01, b.t1 - b.t0), 0, 1), off = lerp(b.off, b.offEnd, k);
  let tx = P.x, tz = P.z, maxV = 3.7;
  if (off) { const dx = P.x - 0, dz = P.z - AZ, dl = Math.hypot(dx, dz) || 1; tx += (-dz / dl) * off; tz += (dx / dl) * off; maxV = 4.4; }
  if (b.cut > 0) { b.cut -= dt; tx = b.cx; tz = b.cz; maxV = 13; }
  const ex = tx - b.fx, ez = tz - b.fz, el = Math.hypot(ex, ez), step = Math.min(el * (1 - Math.exp(-dt * 2.3)), maxV * dt);
  if (el > 1e-4) { b.fx += (ex / el) * step; b.fz += (ez / el) * step; }
  const r = Math.hypot(b.fx, b.fz); if (r > AR - 0.3) { b.fx *= (AR - 0.3) / r; b.fz *= (AR - 0.3) / r; }
  if (b.on) { b.burnT -= dt; if (b.burnT <= 0) { b.burnT = 0.09; addBurn(b.fx, b.fz); sfx.burn(); } }
}
function drawEyeLaser(b) {
  const op = b.on ? 1 : b.t / b.warm * 0.4;
  const outer = take("beam", () => beam("#ffe6b0", 0.36)); placeBeam(outer, AW.eye, _b.set(b.fx, Y0, b.fz)); outer.material.opacity = 0.5 * op;
  const core = take("beam", () => beam("#ffffff", 0.13)); placeBeam(core, AW.eye, _b.set(b.fx, Y0, b.fz)); core.material.opacity = 0.95 * op;
  const g = take("glow", () => floorGlow("#ffd28a", 1)); g.position.set(b.fx, Y0 + 0.05, b.fz); g.scale.setScalar(2.6); g.material.opacity = op;
}

// ---------- The ring: its eyes spin and shoot short arrows outward, like a sprinkler ----------
function ringFire(R, t0, t1, opts) {
  opts = opts || {};
  const eyes = ANG.ringEyes.map((e, i) => ({ i, cool: rnd(0, 0.15) }));
  R.every((dt, t) => {
    if (t < t0 || t > t1) return;
    const k = (t - t0) / (t1 - t0);
    ANG.ringW = opts.w ? opts.w(k, t - t0) : 0.6;
    const tilt = opts.tilt ? opts.tilt(k, t - t0) : 0;
    ANG.tiltAmt = tilt;
    const active = Math.round(lerp(opts.n0 || 3, opts.n1 || 12, clamp(k * (opts.grow || 2.2), 0, 1)));
    const rate = opts.rate || 0.16;
    eyes.forEach((e, n) => {
      if ((n * 5) % 12 >= active) return;
      e.cool -= dt; if (e.cool > 0) return; e.cool = rate;
      const from = ringEyeWorld(e.i, new V3(), _a);
      let land = 99;
      if (tilt > 0.15) { const ang = Math.atan2(_a.z, _a.x); land = 6.5 + 4.6 * Math.sin(ang - (opts.tiltAz || 0) - ANG.ringPhase * 0.2) * tilt; }
      addArrow(from, _a, opts.speed || 8.5, land); sfx.arrow();
    });
  });
  R.at(t1, () => { ANG.ringW = 0.3; ANG.tiltAmt = 0; });
}

// ---------- The five patterns ----------
// omen: what the angel does while Rota takes her place; run(R, rep): the turn itself.
const PATTERNS = [
  { key: "feather", name: "깃털", pose: "cover", omenT: 1.8, dur: 16,
    omen() { ANG.wings.RMid.tremble = 1.6; ANG.wings.LMid.tremble = 1.6; sfx.bristle(); },
    run(R, rep) {
      // one wing at a time, faster and denser, then a great X from both wings; played again, in reverse
      const seq = [];
      const sides = ["L", "R", "L", "R", "L", "R", "L", "R", "L"], gaps = [1.7, 1.55, 1.4, 1.2, 1.05, 0.9, 0.8, 0.72, 0.66], ns = [4, 4, 4, 5, 5, 5, 6, 6, 6];
      let t = 0.6; sides.forEach((s, i) => { seq.push([t, s, ns[i], 0.085 - i * 0.004]); t += gaps[i]; });
      const xT = t + 0.6;
      if (!rep) { seq.forEach(([tt, s, n, g]) => featherBurst(R, tt, s, n, g)); featherBurst(R, xT, "L", 7, 0.07); featherBurst(R, xT, "R", 7, 0.07); }
      else {
        featherBurst(R, 0.8, "L", 7, 0.07); featherBurst(R, 0.8, "R", 7, 0.07);
        const back = seq.slice().reverse(); let tt = 2.6;
        back.forEach(([, s, n, g], i) => { featherBurst(R, tt, s === "L" ? "R" : "L", n, g + 0.01); tt += [0.66, 0.72, 0.8, 0.9, 1.05, 1.2, 1.4, 1.55, 1.7][i]; });
      }
    } },
  { key: "wing", name: "날개 레이저", pose: "open4", omenT: 1.8, dur: 18,
    omen() { sfx.charge(); TIPGLOW.on = 1.8; },
    run(R, rep) {
      // left and right in turn, then the middle and lower pairs in turn, then a line that splits into a V
      let t = 0.5;
      const step = (side, pair, gap, o) => { wingSweep(R, t, side, pair, o); t += gap; };
      if (!rep) {
        step("L", "Mid", 3.0); step("R", "Mid", 3.0); step("L", "Mid", 2.6);
        step("R", "Low", 2.0); step("L", "Mid", 2.6); step("R", "Low", 1.8);
        step("L", "Mid", 3.0, { v: true }); step("R", "Mid", 3.0, { v: true });
      } else {
        // sometimes all four wings at once: one jump clears two lines
        step("L", "Mid", 3.0); step("R", "Low", 0); step("R", "Mid", 2.8);
        step("L", "Low", 0); step("L", "Mid", 3.0, { v: true }); step("R", "Low", 0); step("R", "Mid", 3.0);
        step("L", "Mid", 0); step("R", "Mid", 3.0);
      }
    } },
  { key: "ring", name: "고리 눈", pose: "open4", omenT: 2.6, dur: 18,
    omen() { ANG.ringEyes.forEach((e, i) => { e.wake = 0; after(0.12 + i * 0.17, () => { e.wake = 1; sfx.ringWake(i); }); }); ANG.ringW = 0; },
    run(R, rep) {
      if (!rep) {
        // speed, then a sudden turn, then the ring tilts
        ringFire(R, 0.3, 17, {
          w: (k, t) => (t < 6 ? lerp(0.35, 1.25, t / 6) : t < 6.5 ? lerp(1.25, 0, (t - 6) / 0.5) : t < 11 ? -lerp(0.2, 1.05, (t - 6.5) / 4.5) : -0.7),
          tilt: (k, t) => (t > 11 ? clamp((t - 11) / 1.2, 0, 1) : 0), n0: 3, n1: 12, grow: 1.6,
        });
      } else {
        ringFire(R, 0.3, 17, { w: (k, t) => 0.55 + 0.25 * Math.sin(t * 0.5), tilt: () => 1, tiltAz: Math.atan2(P.z - AZ, P.x), n0: 6, n1: 12, grow: 1.5 });
      }
    } },
  { key: "eye", name: "큰 눈 레이저", pose: "raised", omenT: 2.4, dur: 19,
    omen() { sfx.eyeOpen(); },
    run(R, rep) {
      if (!rep) {
        eyeBeam(R, 0.2, 7.2, { cuts: [4.4] });
        eyeBeam(R, 7.5, 13.4, { off: 3.2, offEnd: 0.6, cuts: [11.2] }); eyeBeam(R, 7.5, 13.4, { off: -3.2, offEnd: -0.6 });
        eyeBeam(R, 13.8, 19, { cuts: [16.5] });
        ringFire(R, 13.8, 19, { w: () => 0.45, n0: 4, n1: 5, rate: 0.3, speed: 7.5 });
      } else {
        eyeBeam(R, 0.2, 9.5, { off: 2.6, offEnd: 0.9, cuts: [6] }); eyeBeam(R, 0.2, 9.5, { off: -2.6, offEnd: -0.9 });
        eyeBeam(R, 9.8, 19, { off: 1.8, cuts: [14] }); eyeBeam(R, 9.8, 19, { off: -1.8 });
        ringFire(R, 12, 19, { w: () => -0.4, n0: 4, n1: 4, rate: 0.34, speed: 7.5 });
      }
    } },
  { key: "final", name: "본모습", pose: "spread", omenT: 2.6, dur: 26,
    omen() { RISE.t = 0; sfx.descend(); },
    run(R, rep) {
      // two at a time; played again, the pairs change
      const pairs = rep % 2 ? [["wing", "ring"], ["feather", "ring"], ["wing", "eye"]] : [["feather", "wing"], ["ring", "eye"], ["feather", "eye"]];
      pairs.forEach((pr, i) => { const t0 = 0.4 + i * 8.6; pr.forEach((m) => MODULES[m](R, t0, t0 + 8)); });
    } },
];
// lighter versions of each part, for the last pattern
const MODULES = {
  feather(R, t0, t1) { let t = t0 + 0.6, s = "L"; while (t < t1 - 0.4) { featherBurst(R, t, s, 5, 0.08); s = s === "L" ? "R" : "L"; t += 1.25; } },
  wing(R, t0, t1) { let t = t0 + 0.3, i = 0; while (t < t1 - 2.5) { wingSweep(R, t, i % 2 ? "R" : "L", i % 3 === 2 ? "Low" : "Mid", { v: i === 3 }); t += 2.7; i++; } },
  ring(R, t0, t1) { ringFire(R, t0, t1, { w: (k, t) => 0.8 * Math.cos(t * 0.45), n0: 4, n1: 8, rate: 0.22 }); },
  eye(R, t0, t1) { eyeBeam(R, t0, t1, { cuts: [t0 + 4] }); },
};
const TIPGLOW = { on: 0, sprites: [] };
const RISE = { t: -1 };
function after(sec, fn) { timers.push({ t: sec, fn }); }
let timers = [];
