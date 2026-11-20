// 천사전 · lights: everything the angel throws (feathers, arrows, lasers, burning floor), Rota's shadows, damage both ways.
"use strict";

// ---------- State shared with the flow ----------
const P = { x: 0, z: 4, vx: 0, vz: 0, hp: PMAX, inv: 0, jumpT: -1, jy: 0, face: Math.PI, moving: 0, lock: false };
const A = { hp: 100, ghost: 100, ghostT: 0, flash: 0, floor: 80 };
let L = [];                        // live lights
let turnDmg = 0, touching = false, touchStr = 0, lastTouch = -9, lastImpact = -9, tickT = 0, boost = 1, impact = 0, freeze = 0, simT = 0;
const shadows = [];                // shadows drawn this frame: {x, z, ux, uz, len, f, hit}
const rotaPos = new V3();
const rotaJump = () => P.jy;
const footFrac = () => clamp(P.jy / JUMP_H, 0, 1);

// ---------- Making lights ----------
function addFeather(from, to, speed) {
  const d = to.clone().sub(from), len = d.length();
  L.push({ k: "feather", p: from.clone(), v: d.multiplyScalar(speed / len), t: 0, lum: 0.55, harm: true, floor: false });
  sfx.featherFire();
}
function addArrow(from, dir, speed, landD) {
  L.push({ k: "arrow", p: from.clone(), y0: from.y - Y0, dir: dir.clone(), sp: speed, land: landD || 99, gone: 0, t: 0, lum: 0.55, harm: true, floor: false });
}
function addBurn(x, z) { L.push({ k: "burn", x, z, t: 0, dur: 2.5, r: 0.4, lum: 0.95, harm: true, floor: true }); }

// ---------- Geometry helpers on the floor ----------
function segDist2(px_, pz_, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz || 1e-9;
  const t = clamp(((px_ - ax) * dx + (pz_ - az) * dz) / l2, 0, 1), qx = ax + dx * t - px_, qz = az + dz * t - pz_;
  return [qx * qx + qz * qz, ax + dx * t, az + dz * t];
}
// where a ray from (x, z) along (ux, uz) leaves the stone circle
function fenceHit(x, z, ux, uz) { const p = x * ux + z * uz, c = x * x + z * z - AR * AR; return -p + Math.sqrt(Math.max(0, p * p - c)); }
// a 3D segment against Rota's body (a vertical segment at her feet)
function beamHitsBody(e, fx, fz, r) {
  const steps = 10;
  for (let i = 0; i <= steps; i++) {
    const k = i / steps, x = lerp(e.x, fx, k), y = lerp(e.y - Y0, 0, k), z = lerp(e.z, fz, k);
    if (y > P.jy - 0.1 && y < P.jy + 1.35 && Math.hypot(x - P.x, z - P.z) < r) return true;
  }
  return false;
}
// the two floor segments of a wing laser: out from its pivot to the fence, then reflected back across the circle
function wingSegs(b) {
  const ux = Math.cos(b.th), uz = Math.sin(b.th);
  const l1 = fenceHit(b.px, b.pz, ux, uz), hx = b.px + ux * l1, hz = b.pz + uz * l1;
  const nl = Math.hypot(hx, hz) || 1, nx = -hx / nl, nz = -hz / nl, dot = ux * nx + uz * nz;
  const rx = ux - 2 * dot * nx, rz = uz - 2 * dot * nz;
  const l2 = fenceHit(hx + rx * 0.01, hz + rz * 0.01, rx, rz);
  b.seg1 = [b.px, b.pz, hx, hz]; b.seg2 = [hx, hz, hx + rx * l2, hz + rz * l2];
}

// ---------- Each frame: move lights, hurt Rota ----------
const _v = new V3();
function stepLights(dt) {
  for (let i = L.length - 1; i >= 0; i--) {
    const s = L[i]; s.t += dt;
    if (s.k === "feather") {
      s.p.addScaledVector(s.v, dt);
      if (s.p.y <= Y0 + 0.03) {    // stuck in the floor: harmless, glows for a while
        L[i] = { k: "stuck", x: s.p.x, z: s.p.z, yaw: Math.atan2(s.v.x, s.v.z), t: 0, dur: 2.6, lum: 1, harm: false, floor: true };
        sfx.featherStick(); continue;
      }
      if (Math.hypot(s.p.x, s.p.z) > AR + 4) { L.splice(i, 1); continue; }
    } else if (s.k === "stuck") {
      s.lum = 1 - s.t / s.dur; if (s.t > s.dur) { L.splice(i, 1); continue; }
    } else if (s.k === "arrow") {
      s.p.addScaledVector(s.dir, s.sp * dt);
      const tr = s.t * s.sp;
      // arrows drop from the ring to Rota's height, then fly flat; on a tilted ring they slope down to the floor
      const flat = 0.62, y = s.land < 50 ? Math.max(0, lerp(s.y0, 0, tr / s.land)) : flat + (s.y0 - flat) * Math.exp(-tr / 0.9);
      s.p.y = Y0 + y;
      if (y <= 0.02 || Math.hypot(s.p.x, s.p.z) > AR + 1) { L.splice(i, 1); continue; }
    } else if (s.k === "burn") {
      s.lum = 0.95 * (1 - s.t / s.dur); if (s.t > s.dur) { L.splice(i, 1); continue; }
      s.harm = s.t < s.dur * 0.8;
    } else if (s.k === "wlaser") {
      stepWingLaser(s, dt); if (s.dead) { L.splice(i, 1); continue; }
    } else if (s.k === "elaser") {
      stepEyeLaser(s, dt); if (s.dead) { L.splice(i, 1); continue; }
    }
    if (s.harm && P.inv <= 0 && state === "pattern" && hits(s)) hurt();
  }
}
function hits(s) {
  const ground = P.jy < 0.28;
  switch (s.k) {
    case "feather": return Math.hypot(s.p.x - P.x, s.p.z - P.z) < 0.2 + HIT_R && s.p.y - Y0 > P.jy - 0.1 && s.p.y - Y0 < P.jy + 1.3;
    case "arrow": return Math.hypot(s.p.x - P.x, s.p.z - P.z) < 0.15 + HIT_R && s.p.y - Y0 > P.jy - 0.1 && s.p.y - Y0 < P.jy + 1.3;
    case "burn": return ground && Math.hypot(s.x - P.x, s.z - P.z) < s.r + HIT_R;
    case "wlaser": {
      if (s.st !== "fire" || !ground) return false;
      const a = s.seg1, b = s.seg2;
      return segDist2(P.x, P.z, a[0], a[1], a[2], a[3])[0] < (0.17 + HIT_R) ** 2 || segDist2(P.x, P.z, b[0], b[1], b[2], b[3])[0] < (0.1 + HIT_R) ** 2;
    }
    case "elaser": return s.on && (Math.hypot(s.fx - P.x, s.fz - P.z) < 0.5 + HIT_R || beamHitsBody(AW.eye, s.fx, s.fz, 0.3));
  }
  return false;
}
function hurt() {
  P.hp -= 1; P.inv = 1.15; shake = Math.max(shake, 0.16); vibrate(70); sfx.hurt();
  flashWhite = 0.35;
  if (P.hp <= 0) { P.hp = 0; rotaDown(); } else if (P.jy < 0.05) rotaOneShot("Hit", 1.2);
}
let flashWhite = 0;

// ---------- Shadows: every light near Rota throws her shadow away from it ----------
// The nearer and brighter the light, the longer the shadow. A jump lengthens it. A shadow that reaches the angel's feet
// hurts it for as long as it stays there.
const SH_D = 2.9;
function lightSources(out) {
  out.length = 0;
  for (const s of L) {
    if (s.k === "feather") out.push([s.p.x, s.p.z, s.lum]);
    else if (s.k === "stuck" || s.k === "burn") out.push([s.x, s.z, s.lum]);
    else if (s.k === "arrow") out.push([s.p.x, s.p.z, s.lum]);
    else if (s.k === "wlaser" && s.st === "fire") {
      const a = segDist2(P.x, P.z, ...s.seg1), b = segDist2(P.x, P.z, ...s.seg2);
      out.push([a[1], a[2], 0.85]); out.push([b[1], b[2], 0.85]);
    } else if (s.k === "elaser" && s.on) out.push([s.fx, s.fz, 1.0]);
  }
  return out;
}
const _srcs = [];
function stepShadows(dt) {
  shadows.length = 0;
  let best = 0;
  if (state === "pattern" || state === "omen") {
    const tx = 0, tz = AZ;
    for (const [lx, lz, lum] of lightSources(_srcs)) {
      const dx = P.x - lx, dz = P.z - lz, d = Math.hypot(dx, dz);
      if (d > SH_D || d < 0.04 || lum <= 0.02) continue;
      const f = Math.pow(1 - d / SH_D, 0.8) * lum;
      if (f < 0.06) continue;
      const ux = dx / d, uz = dz / d, len = (0.9 + 6.2 * f) * (1 + 1.4 * footFrac());
      const [d2] = segDist2(tx, tz, P.x, P.z, P.x + ux * len, P.z + uz * len);
      const hit = d2 < TGT_R * TGT_R && state === "pattern";
      shadows.push({ ux, uz, len, f, hit });
      if (hit && f > best) best = f;
    }
    shadows.sort((a, b) => (b.hit - a.hit) || (b.f - a.f));
    if (shadows.length > 6) shadows.length = 6;
  }
  const was = touching;
  touching = best > 0; touchStr = best;
  if (touching) {
    const first = !was && simT - lastTouch > 0.45;
    lastTouch = simT;
    tickT -= dt;
    if (first) { strikeAngel(1.4 + best, true); tickT = 0.13; }
    else if (tickT <= 0) { strikeAngel(0.55 + 0.6 * best, false); tickT = 0.13; }
  }
}
function strikeAngel(d, first) {
  d *= boost;
  const before = A.hp;
  A.hp = Math.max(A.floor, A.hp - d);
  const took = before - A.hp;
  turnDmg += took; A.ghostT = 0.5;
  inkRipple(first ? 1 : 0.45);
  if (first) {
    freeze = 0.06; shake = Math.max(shake, 0.13); vibrate(28); sfx.shadowFirst(); A.flash = 1;
    if (simT - lastImpact > 1.1 && !reduceMotion) { impact = 0.12; lastImpact = simT; }
  } else { shake = Math.max(shake, 0.035); vibrate(9); sfx.shadowTick(); A.flash = Math.max(A.flash, 0.4); }
  if (A.hp <= 0.001 && before > 0) angelDies();
}

// ---------- Drawing the lights ----------
const lightGroup = add(new THREE.Group());
// glows for every small light: one point cloud
const GLOW_N = 400;
const glowGeo = new THREE.BufferGeometry();
glowGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(GLOW_N * 3), 3));
glowGeo.setAttribute("gcol", new THREE.BufferAttribute(new Float32Array(GLOW_N * 3), 3));
glowGeo.setAttribute("gsize", new THREE.BufferAttribute(new Float32Array(GLOW_N), 1));
const glowPts = new THREE.Points(glowGeo, new THREE.ShaderMaterial({
  uniforms: { map: { value: glowTex }, scale: { value: 400 } },
  vertexShader: "attribute vec3 gcol; attribute float gsize; uniform float scale; varying vec3 vC; void main(){ vC = gcol; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = gsize * scale / -mv.z; gl_Position = projectionMatrix * mv; }",
  fragmentShader: "uniform sampler2D map; varying vec3 vC; void main(){ gl_FragColor = vec4(vC * texture2D(map, gl_PointCoord).a, 1.0); }",
  blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, toneMapped: false }));
glowPts.frustumCulled = false; glowPts.renderOrder = 9; lightGroup.add(glowPts);
let featherInst = null, stuckInst = null;
const FEATHER_N = 140;
function setupFeathers(props) {
  const f = props.scene.getObjectByName("Feather_Light");
  const geo = f.geometry.clone(); geo.applyMatrix4(new THREE.Matrix4().makeScale(1.9, 1.9, 1.9));
  const mat = f.material.clone(); mat.depthWrite = false; mat.toneMapped = false; mat.emissiveIntensity = 2.2; mat.side = THREE.DoubleSide;
  featherInst = new THREE.InstancedMesh(geo, mat, FEATHER_N); featherInst.frustumCulled = false; featherInst.renderOrder = 8; lightGroup.add(featherInst);
  stuckInst = new THREE.InstancedMesh(geo, mat.clone(), FEATHER_N); stuckInst.frustumCulled = false; stuckInst.renderOrder = 8; lightGroup.add(stuckInst);
}
const arrowInst = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.035, 0.012, 0.62, 5).rotateX(Math.PI / 2), bright("#fff3cf", { blending: THREE.AdditiveBlending }), 260);
arrowInst.frustumCulled = false; arrowInst.renderOrder = 8; lightGroup.add(arrowInst);
// floor strips for the wing lasers and their aim lines, beams for the lasers in the air, glow discs where they touch
function mkStrip(hex, op) { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), bright(hex, { map: bandTex, opacity: op, blending: THREE.AdditiveBlending, side: THREE.DoubleSide })); m.renderOrder = 7; m.visible = false; lightGroup.add(m); return m; }
function beam(hex, r) { const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 10, 1, true).translate(0, 0.5, 0), bright(hex, { opacity: 0.85, blending: THREE.AdditiveBlending, side: THREE.DoubleSide })); m.renderOrder = 8; m.visible = false; lightGroup.add(m); return m; }
function floorGlow(hex, s) { const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s).rotateX(-Math.PI / 2), glowMat(hex, softTex, { opacity: 0.9 })); m.renderOrder = 7; m.visible = false; lightGroup.add(m); return m; }
const pool = { strip: [], beam: [], glow: [], burn: [] };
function take(kind, mk) { const a = pool[kind]; const m = a.find((q) => !q.used) || (a.push(mk()), a[a.length - 1]); m.used = true; m.visible = true; return m; }
function placeStrip(m, ax, az, bx, bz, w, y) {
  const dx = bx - ax, dz = bz - az, l = Math.hypot(dx, dz);
  m.position.set((ax + bx) / 2, Y0 + y, (az + bz) / 2); m.rotation.set(0, -Math.atan2(dz, dx), 0); m.scale.set(l, 1, w);
}
function placeBeam(m, a, b) {
  m.position.copy(a); _v.copy(b).sub(a); const l = _v.length();
  m.quaternion.setFromUnitVectors(_up, _v.normalize()); m.scale.set(1, l, 1);
}
const _up = new V3(0, 1, 0), _m4 = new THREE.Matrix4(), _qq = new THREE.Quaternion(), _sc = new V3(1, 1, 1), _p3 = new V3();
const _zAx = new V3(0, 0, 1);
function syncLights() {
  for (const k in pool) pool[k].forEach((m) => { m.used = false; });
  let nf = 0, ns = 0, na = 0, ng = 0;
  const gp = glowGeo.attributes.position.array, gc = glowGeo.attributes.gcol.array, gs = glowGeo.attributes.gsize.array;
  const glow = (x, y, z, r, g, b, size) => { if (ng >= GLOW_N) return; gp[ng * 3] = x; gp[ng * 3 + 1] = y; gp[ng * 3 + 2] = z; gc[ng * 3] = r; gc[ng * 3 + 1] = g; gc[ng * 3 + 2] = b; gs[ng] = size; ng++; };
  for (const s of L) {
    if (s.k === "feather" && featherInst && nf < FEATHER_N) {
      _v.copy(s.v).normalize(); _qq.setFromUnitVectors(_zAx, _v);
      _m4.compose(s.p, _qq, _sc); featherInst.setMatrixAt(nf++, _m4);
      glow(s.p.x, s.p.y, s.p.z, 0.9, 0.95, 1.0, 1.3);
    } else if (s.k === "stuck" && stuckInst && ns < FEATHER_N) {
      _qq.setFromEuler(_e.set(-1.0, s.yaw, 0, "YXZ"));
      _m4.compose(_p3.set(s.x, Y0 + 0.28, s.z), _qq, _sc); stuckInst.setMatrixAt(ns++, _m4);
      glow(s.x, Y0 + 0.3, s.z, 1.0 * s.lum, 0.85 * s.lum, 0.55 * s.lum, 2.2 * (0.4 + 0.6 * s.lum));
    } else if (s.k === "arrow" && na < 260) {
      _qq.setFromUnitVectors(_zAx, s.dir); _m4.compose(s.p, _qq, _sc); arrowInst.setMatrixAt(na++, _m4);
      glow(s.p.x, s.p.y, s.p.z, 1.0, 0.86, 0.55, 0.55);
    } else if (s.k === "burn") {
      const m = take("burn", () => floorGlow("#ffb85a", 1)); const k = 1 - s.t / s.dur;
      m.position.set(s.x, Y0 + 0.035, s.z); m.scale.setScalar(s.r * 2.6 * (0.7 + 0.3 * k)); m.material.opacity = 0.95 * k;
    } else if (s.k === "wlaser") drawWingLaser(s);
    else if (s.k === "elaser") drawEyeLaser(s);
  }
  if (featherInst) { featherInst.count = nf; featherInst.instanceMatrix.needsUpdate = true; stuckInst.count = ns; stuckInst.instanceMatrix.needsUpdate = true; }
  arrowInst.count = na; arrowInst.instanceMatrix.needsUpdate = true;
  glowGeo.setDrawRange(0, ng);
  glowGeo.attributes.position.needsUpdate = glowGeo.attributes.gcol.needsUpdate = glowGeo.attributes.gsize.needsUpdate = true;
  glowPts.material.uniforms.scale.value = glH * 0.55;
  for (const k in pool) pool[k].forEach((m) => { if (!m.used) m.visible = false; });
}

// ---------- Rota's shadows on the floor, and the ink at the angel's feet ----------
const SHADOW_N = 6;
const inkTex = canvasTex(64, 16, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, "rgba(255,255,255,0.95)"); gr.addColorStop(0.75, "rgba(255,255,255,0.7)"); gr.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = gr; g.beginPath(); g.moveTo(0, 2); g.lineTo(w, h * 0.38); g.lineTo(w, h * 0.62); g.lineTo(0, h - 2); g.fill(); });
const shadowMeshes = Array.from({ length: SHADOW_N }, () => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).translate(0.5, 0, 0).rotateX(-Math.PI / 2), basic("#0c0620", { map: inkTex, opacity: 0.8 }));
  m.renderOrder = 5; m.visible = false; add(m); return m;
});
const ripples = Array.from({ length: 6 }, () => {
  const m = new THREE.Mesh(new THREE.RingGeometry(0.75, 1, 40).rotateX(-Math.PI / 2), basic("#14082a", { opacity: 0 }));
  m.renderOrder = 4; m.visible = false; m.life = 0; add(m); return m;
});
function inkRipple(k) {
  const m = ripples.find((q) => q.life <= 0) || ripples[0];
  m.life = 1; m.k = k; m.visible = true;
}
const rotaDot = add(new THREE.Mesh(new THREE.PlaneGeometry(0.13, 0.13).rotateX(-Math.PI / 2).rotateY(Math.PI / 4), basic("#ff5a4e", { opacity: 1, depthTest: false })));
rotaDot.renderOrder = 14;
const rotaBlob = add(new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9).rotateX(-Math.PI / 2), basic("#05030f", { map: softTex, opacity: 0.55 })));
rotaBlob.renderOrder = 3;
function syncShadows(dt) {
  shadowMeshes.forEach((m, i) => {
    const s = shadows[i];
    if (!s) { m.visible = false; return; }
    m.visible = true;
    m.position.set(P.x, Y0 + 0.025 + i * 0.002, P.z);
    m.rotation.set(0, -Math.atan2(s.uz, s.ux), 0);
    m.scale.set(s.len, 1, 0.42 + 0.25 * s.f);
    m.material.opacity = (s.hit ? 0.92 : 0.35 + 0.45 * s.f);
    m.material.color.copy(s.hit ? col("#2a0d4a") : col("#0c0620"));
  });
  ripples.forEach((m) => {
    if (m.life <= 0) { m.visible = false; return; }
    m.life -= dt * 1.6;
    const k = 1 - m.life;
    m.position.set(0, Y0 + 0.03, AZ); m.scale.setScalar(TGT_R * (0.5 + 1.3 * k));
    m.material.opacity = 0.75 * m.life * m.k;
  });
}
