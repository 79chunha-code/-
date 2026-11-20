// 천사전 · stage: the shadow-play screen that comes down between turns.
// An old torn cloth hangs from a rod and is simulated as real cloth. Behind it a lamp lights the puppets; their shadows
// (and the choices, cut out like letters) are projected onto the cloth. Kaelum's journal opens in front of it.
"use strict";

// ---------- Kaelum's journal (초안: 글은 직접 쓰실 자리. 한 장 = 제목, 본문 줄들, 그 차례 동안 남는 한 줄 힌트) ----------
const JOURNAL = {
  first: { title: "천사에 관하여", lines: ["칼은 빛을 벨 수 없다네.", "빛이 자네 곁을 지나면, 그림자는 그 반대쪽으로 선다.", "그 그림자를 천사의 발치에 대게.", "닿아 있는 동안, 천사는 다친다네."] },
  feather: { title: "깃털에 관하여", lines: ["날개 끝의 눈들이 자네를 보면 깃털이 온다.", "옆으로 비키게.", "꽂힌 깃털은 한동안 빛난다네."], hint: "꽂힌 깃털과 천사 <b>사이</b>에 서기" },
  wing: { title: "날개의 빛에 관하여", lines: ["바닥을 쓸고 오는 빛은 뛰어넘게.", "울타리에 부딪혀 돌아오는 빛이", "자네 등 뒤를 비출 걸세."], hint: "<b>점프</b>로 넘고, 돌아오는 빛 앞에 서기" },
  ring: { title: "고리에 관하여", lines: ["고리의 눈들이 돌며 화살을 뿌린다.", "화살 줄기 곁에 바짝 붙어", "함께 돌게."], hint: "화살 줄기 <b>바로 옆</b>에 붙어 같이 돌기" },
  eye: { title: "그 눈에 관하여", lines: ["그 눈이 뜨면 멈추지 말게.", "빛이 지나간 바닥이 타는 동안", "그 앞에 서게."], hint: "멈추지 말고, 탄 자국과 천사 <b>사이</b>에 서기" },
  final: { title: "본모습에 관하여", lines: ["이제 그 모든 것이 둘씩 온다네.", "자네가 배운 대로만 하게."], hint: "둘씩 겹쳐 온다. 배운 대로" },
};

const stageScene = new THREE.Scene(), puppetScene = new THREE.Scene();
const stageCam = new THREE.PerspectiveCamera(40, CW / FH, 0.05, 30);
stageCam.position.set(0, 1.0, 2.6); stageCam.lookAt(0, 1.0, 0);
const lampCam = new THREE.PerspectiveCamera(72, 1, 0.1, 10);
const LAMP_Z = -2.3;
lampCam.position.set(0, 1.0, LAMP_Z); lampCam.lookAt(0, 1.0, 0); lampCam.updateMatrixWorld(); lampCam.updateProjectionMatrix();
const rtMask = new THREE.WebGLRenderTarget(1024, 1024);
const STG = { ready: false, k: 0, want: 0, rodY: 0, cloth: null, rod: null, sim: null, rotaP: null, angelP: null, eyes: [], covers: [], opts: [], sel: 0, menu: false,
  journal: null, jMixer: null, jAct: null, jOpen: 0, jWant: 0, jPage: null, onPick: null, gesture: 0, gestureKind: "", texCache: {} };
const dimQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.MeshBasicMaterial({ color: 0x05040c, transparent: true, opacity: 0, depthTest: false, depthWrite: false }));
dimQuad.position.z = -0.5;
const dimScene = new THREE.Scene(); dimScene.add(dimQuad);

// ---------- The cloth ----------
const clothMat = new THREE.ShaderMaterial({
  uniforms: { map: { value: null }, mask: { value: rtMask.texture }, lampVP: { value: new THREE.Matrix4() }, glow: { value: 1 }, front: { value: 0.07 } },
  vertexShader: [
    "uniform mat4 lampVP; varying vec2 vUv; varying vec4 vL; varying vec3 vW;",
    "void main(){ vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vL = lampVP * w; gl_Position = projectionMatrix * viewMatrix * w; }"].join("\n"),
  fragmentShader: [
    "uniform sampler2D map, mask; uniform float glow, front; varying vec2 vUv; varying vec4 vL; varying vec3 vW;",
    "void main(){",
    "  vec2 q = vL.xy / vL.w * 0.5 + 0.5; float m = 0.0;",
    "  for (int i = -2; i <= 2; i++) for (int j = -2; j <= 2; j++) m += texture2D(mask, q + vec2(float(i), float(j)) * 0.0009).r;",
    "  m /= 25.0;",
    "  float spot = smoothstep(1.35, 0.15, length((vW.xy - vec2(0.0, 1.05)) * vec2(0.62, 0.95)));",
    "  vec3 tex = texture2D(map, vUv).rgb;",
    "  vec3 lamp = vec3(1.0, 0.78, 0.48) * (0.35 + 1.15 * spot) * glow;",
    "  vec3 c = tex * (front + lamp * m);",
    "  gl_FragColor = vec4(c, 1.0);",
    "  #include <encodings_fragment>",
    "}"].join("\n"),
  side: THREE.DoubleSide });
function setupStage(g) {
  const root = g.scene;
  const cloth = root.getObjectByName("Screen_Cloth"), rod = root.getObjectByName("Screen_Rod");
  clothMat.uniforms.map.value = cloth.material.map; if (cloth.material.map) cloth.material.map.encoding = THREE.sRGBEncoding;
  cloth.material = clothMat; cloth.frustumCulled = false;
  stageScene.add(cloth); stageScene.add(rod);
  STG.cloth = cloth; STG.rod = rod; STG.rod0 = rod.position.clone();
  const rodLight = new THREE.PointLight(col("#ffcf90"), 0.9, 6); rodLight.position.set(0, 2.3, 1.2); stageScene.add(rodLight);
  stageScene.add(new THREE.AmbientLight(col("#8088b0"), 0.35));
  const jl = new THREE.PointLight(col("#ffe0b0"), 2.2, 5); jl.position.set(0.3, 1.6, 2.3); stageScene.add(jl);
  buildSim(cloth.geometry);
  // puppets: black cut-outs (their holes let the lamp through)
  const black = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide });
  const rotaP = root.getObjectByName("Puppet_Rota_Torso"), angelP = root.getObjectByName("Puppet_Angel_Robe");
  [rotaP, angelP].forEach((p) => { p.traverse((o) => { if (o.isMesh) o.material = black; }); puppetScene.add(p); });
  STG.rotaP = rotaP; STG.angelP = angelP;
  STG.rotaP0 = rotaP.position.clone(); STG.angelP0 = angelP.position.clone();
  STG.parts = {};
  [rotaP, angelP].forEach((p) => p.traverse((o) => { STG.parts[o.name] = { o, q: o.quaternion.clone() }; }));
  for (let i = 1; i <= 18; i++) {
    const e = root.getObjectByName("Puppet_Angel_WingEye_" + String(i).padStart(2, "0")) || angelP.getObjectByName("Puppet_Angel_WingEye_" + String(i).padStart(2, "0"));
    if (!e) continue;
    const cover = new THREE.Mesh(new THREE.CircleGeometry(0.026, 14), black); cover.position.z = 0.002; cover.visible = false; e.add(cover);
    STG.covers.push(cover);
  }
  // the two choices, cut out of black paper and held up to the cloth
  ["다음 차례", "미리 보기"].forEach((label, i) => {
    const t = canvasTex(512, 128, (c, w, h) => { c.fillStyle = "#fff"; const sc = 8; pixText(c, label, (w - textW(label, F11, sc)) / 2, (h - 11 * sc) / 2, sc, F11); });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.2), new THREE.MeshBasicMaterial({ color: 0x000000, alphaMap: t, alphaTest: 0.5, side: THREE.DoubleSide, transparent: false }));
    const mark = new THREE.Mesh(new THREE.CircleGeometry(0.035, 4), black); mark.position.set(-0.47, 0, 0); m.add(mark);
    m.position.set(i ? 0.62 : -0.62, 0.48, -0.1); puppetScene.add(m);
    STG.opts.push({ m, mark, label, x: i ? 0.62 : -0.62 });
  });
  STG.ready = true;
}
function setupJournal(props) {
  const j = props.scene.getObjectByName("Journal"); if (!j) return;
  const hold = new THREE.Group(); hold.add(j); j.position.set(0, 0, 0);
  hold.rotation.set(1.12, 0, 0); hold.scale.setScalar(3.2); hold.position.set(0, -1.2, 1.25);
  stageScene.add(hold); STG.journal = hold; hold.visible = false;
  j.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; if (o.material.map) o.material.map.encoding = THREE.sRGBEncoding; } });
  STG.pageL = j.getObjectByName("Journal_PageL"); STG.pageR = j.getObjectByName("Journal_PageR");
  // the pages are paper in lamplight: drawn unlit so the writing always reads
  if (STG.pageL) { STG.pageLimg = STG.pageL.material.map && STG.pageL.material.map.image; STG.pageL.material = new THREE.MeshBasicMaterial({ color: col("#fff3dc") }); }
  if (STG.pageR) { STG.pageRimg = STG.pageR.material.map && STG.pageR.material.map.image; STG.pageR.material = new THREE.MeshBasicMaterial({ color: col("#fff3dc") }); }
  const clip = props.animations.find((a) => a.name === "Open");
  if (clip) { STG.jMixer = new THREE.AnimationMixer(j); STG.jAct = STG.jMixer.clipAction(clip); STG.jAct.setLoop(THREE.LoopOnce); STG.jAct.clampWhenFinished = true; STG.jClip = clip; }
  // centre the open book on the screen
  if (STG.jAct) { STG.jAct.play(); STG.jMixer.setTime(clip.duration); }
  hold.position.set(0, 0, 1.25); hold.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(j), c = box.getCenter(new V3());
  STG.jx = -c.x; STG.jy = 0.92 - c.y;
  if (STG.jAct) { STG.jAct.stop(); STG.jMixer.setTime(0); }
  hold.position.set(STG.jx, -1.2, 1.25);
}
// write a page of the journal onto the two open pages
function writePage(key) {
  const pg = JOURNAL[key]; if (!pg || !STG.pageL) return;
  const draw = (img, lines, title) => canvasTex(512, 512, (c, w, h) => {
    if (img) c.drawImage(img, 0, 0, w, h); else { c.fillStyle = "#e9d9b0"; c.fillRect(0, 0, w, h); }
    c.fillStyle = "#3b2618";
    let y = 50;
    if (title) { pixText(c, title, 44, y, 3, F11); y += 52; c.fillRect(44, y - 10, w - 88, 3); }
    for (const ln of lines) {
      for (const row of wrap(ln, Math.floor((w - 88) / 3), F11)) { pixText(c, row.map((q) => q.ch).join(""), 44, y, 3, F11); y += 40; }
      y += 10;
    }
  }, true);
  const half = Math.ceil(pg.lines.length / 2);
  const left = pg.lines.slice(0, half), right = pg.lines.slice(half);
  if (pg.hint) right.push("", "— " + strip(pg.hint));
  const tl = draw(STG.pageLimg, left, pg.title), tr = draw(STG.pageRimg, right, null);
  tl.flipY = tr.flipY = false;                                // like the model's own textures
  STG.pageL.material.map = tl; STG.pageL.material.needsUpdate = true;
  STG.pageR.material.map = tr; STG.pageR.material.needsUpdate = true;
}
// draw with the game's pixel font onto a 2D canvas (no system font needed)
function pixText(c, str, x, y, sc, f) {
  for (const ch of str) {
    const g = f.glyph(ch); if (!g) continue;
    const base = y + f.cap * sc;
    for (let r = 0, i = 0; r < g.h; r++) for (let k = 0; k < g.w; k++, i++) if (g.bin.charCodeAt(i >> 3) & (0x80 >> (i & 7))) c.fillRect(x + (g.xo + k) * sc, base - (g.yo + g.h - r) * sc, sc, sc);
    x += g.adv * sc;
  }
}

// ---------- Cloth simulation (verlet on the cloth's own vertices; the top row hangs from the rod) ----------
function buildSim(geo) {
  const pos = geo.attributes.position, n = pos.count, idx = geo.index.array;
  const p = new Float32Array(n * 3), o = new Float32Array(n * 3), rest = new Float32Array(n * 3);
  for (let i = 0; i < n * 3; i++) { p[i] = o[i] = rest[i] = pos.array[i]; }
  const seen = new Set(), cons = [];
  const edge = (a, b) => { const k = a < b ? a * 65536 + b : b * 65536 + a; if (seen.has(k)) return; seen.add(k); cons.push(a, b, Math.hypot(rest[a * 3] - rest[b * 3], rest[a * 3 + 1] - rest[b * 3 + 1], rest[a * 3 + 2] - rest[b * 3 + 2])); };
  for (let i = 0; i < idx.length; i += 3) { edge(idx[i], idx[i + 1]); edge(idx[i + 1], idx[i + 2]); edge(idx[i + 2], idx[i]); }
  let ymax = -1e9; for (let i = 0; i < n; i++) ymax = Math.max(ymax, rest[i * 3 + 1]);
  const pin = new Uint8Array(n); for (let i = 0; i < n; i++) if (rest[i * 3 + 1] > ymax - 0.02) pin[i] = 1;
  STG.sim = { n, p, o, rest, cons: new Float32Array(cons), pin, acc: 0, ymax };
}
let windT = 0;
function stepSim(dt) {
  const S_ = STG.sim; if (!S_ || (STG.k <= 0.001 && STG.want === 0)) return;
  S_.acc = Math.min(S_.acc + dt, 1 / 20);                     // at most two steps a frame, so a slow phone stays smooth
  const h = 1 / 40;
  while (S_.acc >= h) {
    S_.acc -= h; windT += h;
    const { n, p, o, rest, cons, pin } = S_, oy = STG.rodY;
    for (let i = 0; i < n; i++) {
      const j = i * 3;
      if (pin[i]) { o[j] = p[j]; o[j + 1] = p[j + 1]; o[j + 2] = p[j + 2]; p[j] = rest[j]; p[j + 1] = rest[j + 1] + oy; p[j + 2] = rest[j + 2]; continue; }
      const vx = (p[j] - o[j]) * 0.98, vy = (p[j + 1] - o[j + 1]) * 0.98, vz = (p[j + 2] - o[j + 2]) * 0.975;
      o[j] = p[j]; o[j + 1] = p[j + 1]; o[j + 2] = p[j + 2];
      // gravity, a breath of air from the lamp, and a soft pull back toward the frame's plane
      const wz = (Math.sin(windT * 1.3 + rest[j] * 1.7) * 0.5 + Math.sin(windT * 2.9 + rest[j + 1] * 2.3) * 0.3) * 0.0016;
      p[j] += vx; p[j + 1] += vy - 9.8 * h * h; p[j + 2] += vz + wz - p[j + 2] * 0.015;
    }
    for (let it = 0; it < 3; it++) {
      for (let c = 0; c < cons.length; c += 3) {
        const a = cons[c] * 3, b = cons[c + 1] * 3, r = cons[c + 2];
        const dx = p[b] - p[a], dy = p[b + 1] - p[a + 1], dz = p[b + 2] - p[a + 2], d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1e-6;
        const k = (d - r) / d * 0.5, pa = pin[cons[c]], pb = pin[cons[c + 1]];
        if (pa && pb) continue;
        if (pa) { p[b] -= dx * k * 2; p[b + 1] -= dy * k * 2; p[b + 2] -= dz * k * 2; }
        else if (pb) { p[a] += dx * k * 2; p[a + 1] += dy * k * 2; p[a + 2] += dz * k * 2; }
        else { p[a] += dx * k; p[a + 1] += dy * k; p[a + 2] += dz * k; p[b] -= dx * k; p[b + 1] -= dy * k; p[b + 2] -= dz * k; }
      }
    }
  }
  const pos = STG.cloth.geometry.attributes.position; pos.array.set(S_.p); pos.needsUpdate = true;
}

// ---------- Showing and hiding ----------
// k: 0 = rolled up above the screen, 1 = hanging in front of the battle
function stageDown() { if (STG.want !== 1) sfx.cloth(); STG.want = 1; }
function stageUp() { if (STG.want !== 0) sfx.cloth(); STG.want = 0; STG.menu = false; }
function stageMenu(onPick) { STG.menu = true; STG.sel = 0; STG.onPick = onPick; }
function journalOpen(key) { if (!STG.journal) return; writePage(key); STG.jWant = 1; STG.journal.visible = true; STG.jKey = key; sfx.page(); if (STG.jAct) { STG.jAct.reset(); STG.jAct.timeScale = 1; STG.jAct.play(); } }
function journalClose() { if (!STG.journal) return; STG.jWant = 0; sfx.page(); if (STG.jAct) { STG.jAct.paused = false; STG.jAct.timeScale = -1.4; STG.jAct.play(); } }
function puppetGesture(kind) { STG.gesture = 2.4; STG.gestureKind = kind; }
function stageStep(dt) {
  if (!STG.ready) return;
  // the rod comes down fast and stops; the cloth keeps swinging on its own
  STG.k += clamp(STG.want - STG.k, -dt * 1.25, dt * 1.25);
  const e = STG.want ? 1 - Math.pow(1 - STG.k, 3) : STG.k * STG.k;
  const vis = visHeight(), top = 1.0 + vis / 2;               // the frame's top edge at the cloth
  const ym = STG.sim ? STG.sim.ymax : 2;
  STG.rodY = lerp(top + 0.25 - ym + 2.1, top - ym - 0.03, e);
  STG.rod.position.set(STG.rod0.x, STG.rod0.y + STG.rodY, STG.rod0.z);
  // stretch the cloth sideways to the screen's width
  const sx = (vis * stageCam.aspect) / 2.95; STG.cloth.scale.x = Math.max(1, sx); STG.rod.scale.x = Math.max(1, sx);
  stepSim(dt);
  dimQuad.material.opacity = 0.45 * e;
  // puppets follow the fight: Rota's puppet left or right of the angel by where she stands around it
  const ang = Math.atan2(P.x, P.z - AZ), dist = Math.hypot(P.x, P.z - AZ);
  const rp = STG.rotaP, ap = STG.angelP, t = performance.now() / 1000;
  rp.position.set(STG.rotaP0.x - 0.2 + clamp(ang * 0.55, -0.6, 0.6), STG.rotaP0.y - 0.06 + Math.sin(t * 2.1) * 0.012 + STG.rodY * 0.0, STG.rotaP0.z - 0.25 * clamp((dist - 2.2) / 6, 0, 1));
  ap.position.set(STG.angelP0.x + 0.08, STG.angelP0.y + 0.05 + Math.sin(t * 0.9) * 0.02, STG.angelP0.z - 0.04);
  const part = (n) => STG.parts[n];
  const rotP = (n, rad) => { const q = part(n); if (q) q.o.quaternion.copy(q.q).multiply(_q2.setFromAxisAngle(_zAx, rad)); };
  // wings flap, the ring turns; a hurt angel staggers, an untouched one stands tall
  STG.gesture = Math.max(0, STG.gesture - dt);
  const gk = STG.gesture / 2.4, stag = STG.gestureKind === "stagger" ? gk : 0, proud = STG.gestureKind === "proud" ? gk : 0;
  const flap = Math.sin(t * 1.6) * 0.06;
  [["Top", 1], ["Mid", 0.8], ["Bot", 0.6]].forEach(([w, a]) => {
    const droop = stag * 0.35 * Math.sin(t * 9) * a - stag * 0.25, lift = proud * 0.22;
    rotP("Puppet_Angel_Wing" + w + "L", -(flap * a + lift) + droop); rotP("Puppet_Angel_Wing" + w + "R", flap * a + lift - droop);
  });
  rotP("Puppet_Angel_Ring", t * 0.4);
  rotP("Puppet_Angel_Robe", stag * 0.22 * Math.sin(t * 7.5));
  rotP("Puppet_Rota_ArmUpperR", Math.sin(t * 1.7) * 0.08); rotP("Puppet_Rota_ArmUpperL", -Math.sin(t * 1.5) * 0.06 - 0.1);
  rotP("Puppet_Rota_Head", Math.sin(t * 0.8) * 0.05);
  // closed wing eyes are covered on the puppet too
  const shut = Math.round(18 * ANG.eyes.filter((q) => q.closed).length / Math.max(1, ANG.eyes.length));
  STG.covers.forEach((c, i) => { c.visible = i < shut; });
  // the choices: the chosen one is held flat against the cloth (sharp), the other drifts back toward the lamp
  STG.opts.forEach((o, i) => {
    const on = STG.menu && !STG.jWant, sel = i === STG.sel;
    o.m.visible = STG.menu && STG.k > 0.6 && STG.jWant === 0;
    o.m.position.z = lerp(o.m.position.z, sel ? -0.02 : -0.24, 1 - Math.exp(-dt * 10));
    o.mark.visible = sel && on;
  });
  // the journal rises from below and opens
  if (STG.journal) {
    STG.jOpen += clamp(STG.jWant - STG.jOpen, -dt * 2.2, dt * 1.6);
    const je = smooth(STG.jOpen);
    STG.journal.position.set(STG.jx || 0, lerp(STG.jy - 1.6, STG.jy, je), 1.25); STG.journal.visible = STG.jOpen > 0.01;
    if (STG.jMixer) STG.jMixer.update(dt);
  }
  // the lamp's view of the puppets
  lampCam.updateMatrixWorld();
  clothMat.uniforms.lampVP.value.multiplyMatrices(lampCam.projectionMatrix, lampCam.matrixWorldInverse);
  clothMat.uniforms.glow.value = 0.85 + 0.15 * Math.sin(t * 7.3) * Math.sin(t * 3.1);
}
function visHeight() { return 2 * stageCam.position.z * Math.tan(THREE.MathUtils.degToRad(stageCam.fov / 2)); }
function stagePick(dir) { if (!STG.menu) return; STG.sel = (STG.sel + dir + 2) % 2; sfx.move(); }
function stageConfirm() { if (!STG.menu || STG.k < 0.9) return; sfx.select(); const f = STG.onPick; if (f) f(STG.sel); }
// screen rectangles of the two choices (their shadows on the cloth), for taps
function optionRects() {
  return STG.opts.map((o) => {
    const p = o.m.position, k = (0 - LAMP_Z) / (p.z - LAMP_Z);
    const cx = lampCam.position.x + (p.x - lampCam.position.x) * k, cy = lampCam.position.y + (p.y - lampCam.position.y) * k;
    const w = 0.8 * k, h = 0.2 * k;
    const a = new V3(cx - w / 2, cy + h / 2, 0).project(stageCam), b = new V3(cx + w / 2, cy - h / 2, 0).project(stageCam);
    return { x: (a.x + 1) / 2 * FW - OX, y: (1 - a.y) / 2 * FH, w: (b.x - a.x) / 2 * FW, h: (a.y - b.y) / 2 * FH };
  });
}
function renderStage() {
  if (!STG.ready || STG.k <= 0.001) return;
  renderer.setRenderTarget(rtMask); renderer.setClearColor(0xffffff, 1); renderer.clear(); renderer.render(puppetScene, lampCam);
  renderer.setRenderTarget(null);
  renderer.autoClear = false;
  renderer.render(dimScene, quadCam);
  renderer.clearDepth(); renderer.render(stageScene, stageCam);
  renderer.autoClear = true;
}
