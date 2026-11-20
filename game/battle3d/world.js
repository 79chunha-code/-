// 천사전 · world: renderer, sky, the plateau, the sun behind the summit and its shafts of light, the angel, Rota, camera.
"use strict";

const V3 = THREE.Vector3;
const col = (h) => new THREE.Color(h).convertSRGBToLinear();
const EXPO = +(Q.get("expo") || 0.85);
const renderer = new THREE.WebGLRenderer({ canvas: glEl, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(1);
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = EXPO;
const scene = new THREE.Scene();
// the camera follows Rota from behind, on the line from the angel through Rota, looking past her at the angel
const CAM = { back: +(Q.get("camb") || 6.8), up: +(Q.get("camh") || 4.6), ahead: +(Q.get("cama") || 3.5), lookY: +(Q.get("camy") || 2.3), fov: +(Q.get("fov") || 60) };
const cam = new THREE.PerspectiveCamera(CAM.fov, CW / FH, 0.3, 4000);
let Y0 = 0;
const add = (o) => (scene.add(o), o);

function canvasTex(w, h, draw, srgb) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c); if (srgb) t.encoding = THREE.sRGBEncoding; return t;
}
const radial = (stops, n) => canvasTex(n || 64, n || 64, (g, w) => { const r = w / 2, gr = g.createRadialGradient(r, r, 0, r, r, r); stops.forEach(([o, c]) => gr.addColorStop(o, c)); g.fillStyle = gr; g.fillRect(0, 0, w, w); });
const glowTex = radial([[0, "#fff"], [0.22, "rgba(255,255,255,0.6)"], [0.55, "rgba(255,255,255,0.14)"], [1, "rgba(255,255,255,0)"]]);
const softTex = radial([[0, "rgba(255,255,255,1)"], [0.5, "rgba(255,255,255,0.45)"], [1, "rgba(255,255,255,0)"]]);
const fenceTex = canvasTex(4, 64, (g) => { const gr = g.createLinearGradient(0, 0, 0, 64); gr.addColorStop(0, "#000"); gr.addColorStop(0.6, "#444"); gr.addColorStop(1, "#fff"); g.fillStyle = gr; g.fillRect(0, 0, 4, 64); });
const bandTex = canvasTex(64, 4, (g) => { const gr = g.createLinearGradient(0, 0, 64, 0); gr.addColorStop(0, "#000"); gr.addColorStop(0.3, "#888"); gr.addColorStop(0.5, "#fff"); gr.addColorStop(0.7, "#888"); gr.addColorStop(1, "#000"); g.fillStyle = gr; g.fillRect(0, 0, 64, 4); });
const basic = (hex, o) => new THREE.MeshBasicMaterial(Object.assign({ color: col(hex), transparent: true, depthWrite: false }, o || {}));
const bright = (hex, o) => basic(hex, Object.assign({ toneMapped: false }, o || {}));   // light is never dimmed by the camera
const glowMat = (hex, map, o) => bright(hex, Object.assign({ map, blending: THREE.AdditiveBlending }, o || {}));

// ---------- Sky: deep blue overhead, pale at the horizon, warmer toward the hidden sun ----------
const SUN = { reveal: 0, dir: new V3(0, 0.8, -0.6).normalize(), pos: new V3(), peak: new V3(0, 290, -215) };
const sky = (() => {
  const R = 3000, sg = new THREE.SphereGeometry(R, 48, 24), cs = [];
  const top = col("#0a1238"), mid = col("#1d3478"), hor = col("#7c86bf"), low = col("#8a90c0"), pos = sg.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / R;
    const c = y > 0.3 ? mid.clone().lerp(top, (y - 0.3) / 0.7) : y > 0 ? hor.clone().lerp(mid, y / 0.3) : low.clone();
    cs.push(c.r, c.g, c.b);
  }
  sg.setAttribute("color", new THREE.Float32BufferAttribute(cs, 3));
  const m = new THREE.Mesh(sg, new THREE.ShaderMaterial({
    uniforms: { sunDir: { value: SUN.dir }, reveal: { value: 0 } },
    vertexShader: "attribute vec3 color; varying vec3 vC; varying vec3 vD; void main(){ vC = color; vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: "uniform vec3 sunDir; uniform float reveal; varying vec3 vC; varying vec3 vD; void main(){ float k = max(dot(vD, sunDir), 0.0); vec3 warm = vec3(1.0, 0.72, 0.38) * (pow(k, 6.0) * (0.25 + 0.9 * reveal) + pow(k, 40.0) * (0.4 + 1.6 * reveal)); gl_FragColor = vec4(vC + warm, 1.0); }",
    side: THREE.BackSide, depthWrite: false, fog: false }));
  return add(m);
})();
scene.fog = new THREE.Fog(col("#6f78b0"), 70, 900);
// in the mountain's shadow: the stones stay dim, the angel carries its own light
const HEMI = +(Q.get("hemi") || 0.32), KEY = +(Q.get("key") || 0.36);
const hemi = add(new THREE.HemisphereLight(col("#8fa2e0"), col("#1c2048"), HEMI));
const keyL = add(new THREE.DirectionalLight(col("#dfe8ff"), KEY)); keyL.position.set(-4, 9, 12); keyL.target.position.set(0, 4, AZ); scene.add(keyL.target);
const rimL = add(new THREE.DirectionalLight(col("#ffcf8a"), 0)); rimL.position.set(0, 60, -90);   // the hidden sun rims the angel from behind
const studio = new THREE.PMREMGenerator(renderer).fromScene(new THREE.RoomEnvironment(), 0.04).texture;

// ---------- The light fence around the stone circle ----------
const arena = add(new THREE.Group());
function buildArena() {
  arena.position.y = Y0;
  const wash = new THREE.Mesh(new THREE.CircleGeometry(AR, 96), basic("#0a0e36", { opacity: 0.3 }));
  wash.rotation.x = -Math.PI / 2; wash.position.y = 0.01; wash.renderOrder = 1; arena.add(wash);
  const fence = new THREE.Mesh(new THREE.CylinderGeometry(AR, AR, 0.42, 160, 1, true), bright("#ffe2a0", { alphaMap: fenceTex, opacity: 0.55, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  fence.position.y = 0.21; fence.renderOrder = 6; arena.add(fence);
  const line = new THREE.Mesh(new THREE.RingGeometry(AR - 0.03, AR + 0.03, 160), bright("#fff4cc", { opacity: 0.9, side: THREE.DoubleSide }));
  line.rotation.x = -Math.PI / 2; line.position.y = 0.02; line.renderOrder = 2; arena.add(line);
}

// ---------- The sun behind the summit, and its shafts of light ----------
// The light is not painted: a glowing source sits behind the summit, the scene is drawn in black in front of it, and the
// light is smeared outward from the source, so the summit, the angel's wings and ring become the dark gaps between shafts.
// A wide glow around the source keeps the shafts alive when the sun itself is above the top of the screen.
const RAY_EXP = +(Q.get("rayexp") || 0.85);
const rayBlack = new THREE.MeshBasicMaterial({ color: 0x000000 });
const sunDisc = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial([[0, "#fffdf4"], [0.55, "rgba(255,240,205,1)"], [0.8, "rgba(255,214,150,0.5)"], [1, "rgba(255,200,130,0)"]], 128), depthWrite: false, transparent: true, fog: false }));
const sunGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial([[0, "rgba(255,226,170,1)"], [0.35, "rgba(255,200,140,0.5)"], [0.7, "rgba(255,180,120,0.12)"], [1, "rgba(255,170,110,0)"]], 128), depthWrite: false, transparent: true, fog: false }));
sunDisc.layers.set(1); sunGlow.layers.set(1); scene.add(sunDisc); scene.add(sunGlow);
// the visible sun (seen when the camera looks up): drawn in the normal pass too
const sunSeen = add(new THREE.Sprite(new THREE.SpriteMaterial({ map: sunDisc.material.map, color: col("#fff4dc"), depthWrite: false, transparent: true, fog: false, toneMapped: false })));
const quadV = "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }";
const blurQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  uniforms: { tOcc: { value: null }, lightPos: { value: new THREE.Vector2(0.5, 0.5) }, exposure: { value: 0.75 }, decay: { value: 0.975 }, density: { value: 0.95 }, weight: { value: 0.2 }, tint: { value: new THREE.Color(1, 0.86, 0.62) } },
  vertexShader: quadV,
  fragmentShader: [
    "uniform sampler2D tOcc; uniform vec2 lightPos; uniform float exposure, decay, density, weight; uniform vec3 tint; varying vec2 vUv;",
    "void main(){ vec2 tc = vUv; vec2 d = (tc - lightPos) * (density / 72.0); float k = 1.0; vec3 c = vec3(0.0);",
    "  for (int i = 0; i < 72; i++) { tc -= d; vec2 q = clamp(tc, 0.0, 1.0); c += texture2D(tOcc, q).rgb * k * weight * step(abs(tc.x - q.x) + abs(tc.y - q.y), 0.0001); k *= decay; }",
    "  gl_FragColor = vec4(c * tint * exposure, 1.0); }"].join("\n"),
  depthTest: false, depthWrite: false }));
const addQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
  uniforms: { t: { value: null } }, vertexShader: quadV,
  fragmentShader: "uniform sampler2D t; varying vec2 vUv; void main(){ gl_FragColor = texture2D(t, vUv); }",
  blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false, transparent: true }));
const blurScene = new THREE.Scene(), addScene = new THREE.Scene(), quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
blurScene.add(blurQuad); addScene.add(addQuad);
let rtOcc = null, rtRay = null;
function placeSun() {
  // the sun climbs from just behind the summit's tip (angel at full light) to clear above it (angel gone)
  const tip = SUN.peak.clone(); tip.y += Y0;
  const from = new V3(0, Y0 + 1.6, 4);
  const base = tip.clone().sub(from).normalize();
  const el = Math.asin(base.y) + THREE.MathUtils.degToRad(lerp(-3.2, 7.5, SUN.reveal));
  const az = Math.atan2(base.x, -base.z);
  SUN.dir.set(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
  SUN.pos.copy(from).addScaledVector(SUN.dir, 2400);
  sunDisc.position.copy(SUN.pos); sunDisc.scale.setScalar(260 * (1 + 0.4 * SUN.reveal));
  sunGlow.position.copy(SUN.pos); sunGlow.scale.setScalar(2400 * (0.7 + 0.5 * SUN.reveal));
  sunSeen.position.copy(SUN.pos); sunSeen.scale.setScalar(230);
  sky.material.uniforms.reveal.value = SUN.reveal;
  rimL.position.copy(SUN.dir).multiplyScalar(100); rimL.intensity = 0.15 + 0.9 * SUN.reveal;
}
function renderRays(strength) {
  const w = Math.max(1, Math.round(glW / 3)), h = Math.max(1, Math.round(glH / 3));
  if (!rtOcc || rtOcc.width !== w || rtOcc.height !== h) {
    if (rtOcc) { rtOcc.dispose(); rtRay.dispose(); }
    rtOcc = new THREE.WebGLRenderTarget(w, h); rtRay = new THREE.WebGLRenderTarget(w, h);
  }
  const v = SUN.pos.clone().project(cam);
  if (v.z > 1 || strength <= 0.01) return;
  const fog = scene.fog, sv = sky.visible, ss = sunSeen.visible;
  scene.fog = null; sky.visible = false; sunSeen.visible = false;
  renderer.setRenderTarget(rtOcc); renderer.setClearColor(0x000000, 1); renderer.clear();
  scene.overrideMaterial = rayBlack; renderer.render(scene, cam);
  scene.overrideMaterial = null;
  renderer.autoClear = false; cam.layers.set(1); renderer.render(scene, cam); cam.layers.set(0);
  scene.fog = fog; sky.visible = sv; sunSeen.visible = ss;
  const u = blurQuad.material.uniforms;
  u.tOcc.value = rtOcc.texture; u.lightPos.value.set((v.x + 1) / 2, (v.y + 1) / 2); u.exposure.value = RAY_EXP * strength;
  renderer.setRenderTarget(rtRay); renderer.clear(); renderer.render(blurScene, quadCam);
  renderer.setRenderTarget(null);
  addQuad.material.uniforms.t.value = rtRay.texture; renderer.render(addScene, quadCam);
  renderer.autoClear = true;
}

// ---------- The angel (Gemini's seraphim, assets/characters/seraphim.glb) ----------
// Wing pivots are posed by code (which pair covers the eye, which spreads); the wings' own flapping comes from the
// model's Idle clip. Every wing eye has an open and a closed mesh; the ring spins by code.
const angelHold = add(new THREE.Group());
const ANG = { root: null, mixer: null, head: null, eye: null, ringTilt: null, ringSpin: null, ringEyes: [], wings: {}, eyes: [], emis: [], ringW: 0.35, ringPhase: 0, light: 1, fade: 1, eyeSquash: 1, yaw: 0, wake: 12 };
const WING_KEYS = ["RTop", "LTop", "RMid", "LMid", "RLow", "LLow"];
// pose: per wing [raise, forward, roll (deg), shift up, shift forward (m)]; R/L mirror automatically
const COVER_TOP = [+(Q.get("cr") || 140), +(Q.get("cf") || 0), +(Q.get("cl") || 0), +(Q.get("cu") || 1.7), +(Q.get("cz") || 2.0)];
const POSES = {
  spread: { Top: [0, 0, 0, 0, 0], Mid: [0, 0, 0, 0, 0], Low: [0, 0, 0, 0, 0] },
  cover: { Top: COVER_TOP, Mid: [0, 0, 0, 0, 0], Low: [-120, 0, 0, 0, 1.2] },   // two wings cross before the eye, two before the robe
  open4: { Top: COVER_TOP, Mid: [6, 0, 0, 0, 0], Low: [-4, 0, 0, 0, 0] },
  raised: { Top: [30, 6, 0, 0.2, 0], Mid: [6, 0, 0, 0, 0], Low: [-6, 0, 0, 0, 0] },
};
let poseNow = null;
const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _e = new THREE.Euler();
const ANGEL_SCALE = +(Q.get("as") || 1.0);
function setupAngel(g) {
  const root = g.scene; ANG.root = root; angelHold.add(root); root.scale.setScalar(ANGEL_SCALE);
  const by = (n) => root.getObjectByName(n);
  ANG.head = by("Seraphim_Head"); ANG.eye = by("Seraphim_CentralEye"); ANG.ringTilt = by("Seraphim_RingTilt"); ANG.ringSpin = by("Seraphim_RingSpin");
  const halo = by("Seraphim_GoldenHaloRays"); if (halo) halo.visible = false;
  for (let i = 0; i < 12; i++) { const e = by("Seraphim_RingEye_" + String(i).padStart(2, "0")); if (e) ANG.ringEyes.push({ o: e, s: e.scale.clone(), wake: 1 }); }
  WING_KEYS.forEach((k) => {
    const piv = by("Seraphim_WingPivot_" + k), wing = by("Seraphim_Wing_" + k), eyes = [];
    for (let i = 0; i < 9; i++) {
      const open = by("Seraphim_WingEyeOpen_" + k + "_" + i), shut = by("Seraphim_WingEyeClosed_" + k + "_" + i);
      if (open && shut) { const e = { k, i, open, shut, closed: false }; eyes.push(e); ANG.eyes.push(e); shut.visible = false; }
    }
    // each wing's eyes get their own material so one wing can glare at Rota alone
    const mats = new Map();
    eyes.forEach((e) => e.open.traverse((o) => { if (o.isMesh) { const m = o.material; if (!mats.has(m)) mats.set(m, m.clone()); o.material = mats.get(m); } }));
    ANG.wings[k] = { piv, wing, eyes, q0: piv.quaternion.clone(), p0: piv.position.clone(), cur: [0, 0, 0, 0, 0], want: [0, 0, 0, 0, 0], glare: 0, glareMats: [...mats.values()], tremble: 0 };
  });
  // the eyes close in an order that spreads over all six wings, outermost first
  ANG.eyes.sort((a, b) => (a.i - b.i) || (WING_KEYS.indexOf(a.k) - WING_KEYS.indexOf(b.k)));
  ANG.eyes.reverse();
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = false;
    const ms = Array.isArray(o.material) ? o.material : [o.material];
    ms.forEach((m) => {
      if (m.userData.seen) return; m.userData.seen = true;
      m.envMap = studio; m.envMapIntensity = 0.8;
      if (m.emissive && (m.emissive.r + m.emissive.g + m.emissive.b) > 0.01) { m.userData.e0 = m.emissiveIntensity; ANG.emis.push(m); }
      m.userData.wasT = m.transparent; m.userData.o0 = m.opacity;
    });
  });
  const clip = g.animations.find((a) => a.name === "Idle");
  if (clip) {
    clip.tracks = clip.tracks.filter((t) => !/RingSpin/.test(t.name));
    ANG.mixer = new THREE.AnimationMixer(root); ANG.mixer.clipAction(clip).play();
  }
  setPose("cover", true);
}
function setPose(name, snap) {
  const p = POSES[name]; poseNow = name;
  WING_KEYS.forEach((k) => {
    const w = ANG.wings[k]; if (!w) return;
    const v = p[k.slice(1)];
    w.want = v.slice();
    if (snap) w.cur = v.slice();
  });
}
// how many wing eyes are shut follows the angel's light; the last pattern opens them all again
function setEyes(shut) {
  ANG.eyes.forEach((e, n) => { const c = n < shut; if (c !== e.closed) { e.closed = c; e.open.visible = !c; e.shut.visible = c; } });
}
function wingEyePos(k, out) {
  const w = ANG.wings[k]; const e = w.eyes.find((q) => !q.closed) || w.eyes[0];
  return e.open.getWorldPosition(out);
}
function wingTip(k, out) { const w = ANG.wings[k]; return w.eyes[0].open.getWorldPosition(out); }
const AW = { eye: new V3(), foot: new V3(), ringC: new V3() };
function updateAngel(dt, look) {
  if (!ANG.root) return;
  if (ANG.mixer) ANG.mixer.update(dt);
  // turn to face Rota, slowly
  if (look) { const want = Math.atan2(look.x - angelHold.position.x, look.z - angelHold.position.z); ANG.yaw += angDiff(want, ANG.yaw) * (1 - Math.exp(-dt * 1.6)); }
  angelHold.rotation.y = ANG.yaw;
  // wing poses
  WING_KEYS.forEach((k) => {
    const w = ANG.wings[k]; if (!w) return;
    const s = k[0] === "R" ? 1 : -1;
    for (let i = 0; i < 5; i++) w.cur[i] += (w.want[i] - w.cur[i]) * (1 - Math.exp(-dt * 3.2));
    const tr = w.tremble > 0 ? Math.sin(performance.now() * 0.09 + s) * 5 * w.tremble : 0;
    w.tremble = Math.max(0, w.tremble - dt);
    const [rz, ry, rx, up, fw] = w.cur;
    _q.setFromEuler(_e.set(THREE.MathUtils.degToRad(rx), THREE.MathUtils.degToRad(-s * ry), THREE.MathUtils.degToRad(s * (rz + tr)), "YXZ"));
    w.piv.quaternion.copy(_q).multiply(w.q0);
    w.piv.position.set(w.p0.x, w.p0.y + up, w.p0.z + fw);
    w.glare = Math.max(0, w.glare - dt * 1.8);
    w.glareMats.forEach((m) => { if (m.emissive) { if (m.userData.g0 === undefined) m.userData.g0 = m.emissiveIntensity; m.emissiveIntensity = (m.userData.g0 || 1) * (1 + 6 * w.glare) * ANG.light; } });
  });
  // the ring
  ANG.ringPhase += ANG.ringW * dt;
  if (ANG.ringSpin) ANG.ringSpin.rotation.y = ANG.ringPhase;
  ANG.ringEyes.forEach((r) => { r.o.scale.copy(r.s).multiplyScalar(0.35 + 0.65 * r.wake); });
  // the central eye follows Rota
  if (ANG.eye && look) {
    ANG.eye.parent.worldToLocal(_t.copy(look));
    const yawE = Math.atan2(_t.x, _t.z), pitchE = -Math.atan2(_t.y, Math.hypot(_t.x, _t.z));
    ANG.eye.rotation.set(clamp(pitchE, -0.7, 0.7), clamp(yawE, -0.6, 0.6), 0, "YXZ");
    ANG.eye.scale.set(1, ANG.eyeSquash, 1);
  }
  // its own light dims as it is hurt
  ANG.emis.forEach((m) => { if (!ANG.wings.RTop || !ANG.wings.RTop.glareMats.includes(m)) m.emissiveIntensity = m.userData.e0 * ANG.light; });
  ANG.eye.getWorldPosition(AW.eye);
  AW.foot.set(angelHold.position.x, Y0, angelHold.position.z);
  if (ANG.ringSpin) ANG.ringSpin.getWorldPosition(AW.ringC);
}
function angelFade(k) {
  ANG.fade = k;
  ANG.root.traverse((o) => { if (!o.isMesh) return; (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.transparent = k < 1 || m.userData.wasT; m.opacity = (m.userData.o0 === undefined ? 1 : m.userData.o0) * k; m.depthWrite = k >= 0.98; }); });
}
// where a ring eye is and which way it looks (outward, flat)
function ringEyeWorld(i, out, dir) {
  const r = ANG.ringEyes[i]; r.o.getWorldPosition(out);
  if (dir) { dir.set(out.x - AW.ringC.x, 0, out.z - AW.ringC.z).normalize(); }
  return out;
}

// ---------- Rota (Gemini's model, assets/characters/rota_gemini.glb) ----------
const rota = add(new THREE.Group());
const RO = { model: null, mixer: null, acts: {}, cur: null, sword: null, swordFloor: null, oneShot: null };
const ROTA_SCALE = +(Q.get("rs") || 0.95);
function setupRota(g) {
  const m = g.scene; m.scale.setScalar(ROTA_SCALE); rota.add(m); RO.model = m;
  m.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; o.material.envMap = studio; o.material.envMapIntensity = 0.5; } });
  RO.sword = m.getObjectByName("Rota_Sword");
  RO.mixer = new THREE.AnimationMixer(m);
  g.animations.forEach((c) => { const a = RO.mixer.clipAction(c); RO.acts[c.name] = a; });
  ["Jump", "Slash", "Hit", "Fall"].forEach((n) => { const a = RO.acts[n]; if (a) { a.setLoop(THREE.LoopOnce); a.clampWhenFinished = true; } });
  RO.mixer.addEventListener("finished", (e) => { if (RO.oneShot && e.action === RO.acts[RO.oneShot] && RO.oneShot !== "Fall") { RO.oneShot = null; } });
  playRota("Idle");
}
function playRota(name, fade, speed) {
  const a = RO.acts[name]; if (!a) return;
  if (RO.cur === name && !["Jump", "Slash", "Hit"].includes(name)) return;
  const prev = RO.acts[RO.cur];
  a.reset(); a.timeScale = speed || 1; a.enabled = true; a.setEffectiveWeight(1); a.play();
  if (prev && prev !== a) prev.crossFadeTo(a, fade === undefined ? 0.18 : fade, false);
  RO.cur = name;
}
function rotaOneShot(name, speed) { RO.oneShot = name; playRota(name, 0.08, speed); }
function dropSword(x, z, yaw) {
  if (!RO.sword || RO.swordFloor) return;
  const s = RO.sword.clone(); RO.sword.visible = false;
  s.scale.setScalar(ROTA_SCALE * 0.8); s.position.set(x, Y0 + 0.04, z);
  s.rotation.set(Math.PI / 2, 0, yaw); add(s); RO.swordFloor = s;
}
function restoreSword() { if (RO.swordFloor) { scene.remove(RO.swordFloor); RO.swordFloor = null; } if (RO.sword) RO.sword.visible = true; }

// ---------- Camera ----------
// The camera stands behind Rota on the line from the angel through her and looks past her at the angel. It swings
// round a little late, which keeps it steady while she circles. lookUp raises the view to the summit (intro, victory).
const camDir = { x: 0, z: -1 }, camPos = new V3(), camLook = new V3(), _c = new V3(), _t = new V3();
let camInit = false, lookUp = 0, shake = 0;
function placeCamera(dt, px_, pz_) {
  const fx = angelHold.position.x - px_, fz = angelHold.position.z - pz_, fd = Math.hypot(fx, fz) || 1, k = camInit ? 1 - Math.exp(-dt * 3) : 1;
  camDir.x += (fx / fd - camDir.x) * k; camDir.z += (fz / fd - camDir.z) * k;
  const m = Math.hypot(camDir.x, camDir.z) || 1, dx = camDir.x / m, dz = camDir.z / m;
  const kp = camInit ? 1 - Math.exp(-dt * 6) : 1;
  const back = CAM.back * (1 + 0.15 * lookUp), up = CAM.up - 2.6 * lookUp;
  camPos.lerp(_c.set(px_ - dx * back, Y0 + up, pz_ - dz * back), kp);
  camLook.lerp(_c.set(px_ + dx * CAM.ahead * (1 + 2.5 * lookUp), Y0 + CAM.lookY + 15 * lookUp * lookUp, pz_ + dz * CAM.ahead * (1 + 2.5 * lookUp)), kp);
  camInit = true;
  const sh = shake > 0.005 && !reduceMotion ? shake : 0;
  cam.position.set(camPos.x + rnd(-sh, sh), camPos.y + rnd(-sh, sh), camPos.z + rnd(-sh, sh));
  cam.lookAt(camLook);
}

// ---------- Loading ----------
// Published next to the page each model is a gzipped .glb in base64 (*.glb.gz.txt); in the repository it is the .glb itself.
const prog = {};
async function fetchBytes(url, key) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + " " + r.status);
  const total = +r.headers.get("content-length") || 0;
  if (!r.body || !total) return new Uint8Array(await r.arrayBuffer());
  const rd = r.body.getReader(), parts = []; let got = 0;
  for (;;) { const { done, value } = await rd.read(); if (done) break; parts.push(value); got += value.length; prog[key] = got / total; }
  const out = new Uint8Array(got); let o = 0; for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
async function glb(packed, repo) {
  prog[repo] = 0;
  let buf;
  try {
    const txt = new TextDecoder().decode(await fetchBytes(packed, repo)), bin = atob(txt.trim()), gz = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) gz[i] = bin.charCodeAt(i);
    buf = await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
  } catch (e) { buf = (await fetchBytes(repo, repo)).buffer; }
  prog[repo] = 1;
  return new Promise((ok, fail) => new THREE.GLTFLoader().parse(buf, "", ok, fail));
}
