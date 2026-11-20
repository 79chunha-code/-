// 천사전 · main: loading, the flow of the fight, the interface, the loop.
"use strict";

let state = "loading", overlay = null, loadErr = "";
let pi = 0, rep = 0, R = null, pat = null, tele = false, turnStartHP = 100, turnStartRota = PMAX, stT = 0, firstSeen = false, turnNo = 0;
let prompt = "", hintText = "", dmgTotal = 0;

// ---------- Loading ----------
async function loadAll() {
  try {
    const [plateau, angelG, rotaG, puppets, props] = await Promise.all([
      glb("plateau.glb.gz.txt", "../../assets/mountain/plateau.glb"),
      glb("seraphim.glb.gz.txt", "../../assets/characters/seraphim.glb"),
      glb("rota_gemini.glb.gz.txt", "../../assets/characters/rota_gemini.glb"),
      glb("shadow_puppets.glb.gz.txt", "../../assets/battle/shadow_puppets.glb"),
      glb("props.glb.gz.txt", "../../assets/battle/props.glb"),
    ]);
    const root = plateau.scene; scene.add(root);
    root.traverse((o) => { if (o.isMesh) o.material.side = THREE.FrontSide; });
    root.updateMatrixWorld(true);
    const rc = new THREE.Raycaster(new V3(0, 400, 0), new V3(0, -1, 0));
    const hits = rc.intersectObject(root, true).filter((h) => !/Cloud|Bunting/.test(h.object.name + (h.object.parent ? h.object.parent.name : "")));
    Y0 = hits.length ? hits[0].point.y : 0;
    buildArena();
    setupAngel(angelG); setupRota(rotaG); setupStage(puppets); setupFeathers(props); setupJournal(props);
    angelHold.position.set(0, Y0 + LIFT + 26, AZ);
    resetFight();
    state = "title"; overlay = "title";
  } catch (e) { loadErr = "모델을 불러오지 못했어요. 새로고침해 주세요."; console.error(e); }
}

// ---------- The flow ----------
function resetFight() {
  pi = 0; rep = 0; A.hp = A.ghost = 100; A.floor = SEG[0]; P.hp = PMAX; P.x = 0; P.z = 4.5; P.jumpT = -1; P.jy = 0; P.inv = 0;
  L = []; firstSeen = false; tele = false; dmgTotal = 0; turnNo = 0; boost = 1;
  setEyes(0); ANG.light = 1; ANG.eyeSquash = 1; ANG.wake = 12; ANG.ringEyes.forEach((e) => { e.wake = 1; }); ANG.ringW = 0.3; ANG.tiltAmt = 0;
  if (ANG.root) { angelFade(1); setPose("cover", true); }
  restoreSword(); playRota("Idle"); RO.oneShot = null;
  SUN.reveal = 0; lookUp = 0.75;
}
function go(s) { state = s; stT = 0; }
function begin() {
  overlay = null; audioOn(); droneLevel(1, 3); music(0.6);
  go("descend"); sfx.descend(); say("천사가 하늘에서 내려온다.");
}
function rotaDown() {
  go("down"); P.jumpT = -1; P.jy = 0; rotaOneShot("Fall"); sfx.fall();
  after(2.2, () => { overlay = "lose"; say("로타가 쓰러졌다."); });
}
function retryTurn() {
  overlay = null; A.hp = A.ghost = turnStartHP; P.hp = Math.max(turnStartRota, 3); P.inv = 0;
  L = []; playRota("Idle"); RO.oneShot = null; P.x = 0; P.z = AZ + 6.5;
  openMenu();
}
function openMenu() {
  go("menu"); stageDown();
  after(0.9, () => { if (state !== "menu") return; stageMenu(pickMenu); say("다음 차례, 또는 미리 보기."); });
}
function pickMenu(i) {
  if (i === 0) { startTurn(); return; }
  go("journal"); STG.menu = false; journalOpen(PATTERNS[pi].key); tele = true;
  say(strip(JOURNAL[PATTERNS[pi].key].lines.join(" ")));
}
function closeJournal() {
  journalClose();
  if (state === "firstJournal") { firstSeen = true; after(0.7, openMenu); go("wait"); return; }
  after(0.6, () => { go("menu"); stageMenu(pickMenu); STG.sel = 0; });
  go("wait");
}
function startTurn() {
  stageUp(); pat = PATTERNS[pi]; turnStartHP = A.hp; turnStartRota = P.hp; turnDmg = 0; turnNo++;
  A.floor = SEG[pi]; boost = 1 + 0.25 * rep;
  hintText = tele ? (JOURNAL[pat.key].hint || "") : "";
  if (pat.key === "final") { setEyes(0); ANG.light = 1.1; }
  setPose(pat.pose); go("omen"); after(0.5, () => pat.omen());
  sfx.omen(); music(0.8);
}
function endTurn() {
  go("turnEnd"); sfx.turnEnd();
  const cleared = A.hp <= SEG[pi] + 0.001;
  const kind = turnDmg >= 8 ? "stagger" : "proud";
  if (cleared) { pi = Math.min(4, pi + 1); rep = 0; } else rep++;
  tele = false; hintText = "";
  after(1.0, () => { openMenu(); puppetGesture(kind); });
  say(cleared ? "천사가 휘청인다. 날개의 눈이 감긴다." : "천사는 꼿꼿하다. 같은 빛이 다시 온다.");
}
function angelDies() {
  go("victory"); sfx.victory(); droneLevel(0, 4); music(0.3);
  L = L.filter((s) => s.k === "stuck" || s.k === "burn"); L.forEach((s) => { s.harm = false; });   // the light goes out with it
  R = null;
  say("천사가 가운데 눈을 감는다.");
  after(7.5, () => { overlay = "win"; });
}
function say(s) { srEl.textContent = s; }
function controlsOn() { return ["approach", "omen", "pattern"].includes(state) && !overlay; }
function tapAnywhere() {
  if (overlay) { overlayAct(); return; }
  if (state === "journal" || state === "firstJournal") { if (STG.jOpen > 0.9) closeJournal(); return; }
}
function overlayAct() {
  if (overlay === "title") begin();
  else if (overlay === "lose") retryTurn();
  else if (overlay === "win") { overlay = null; resetFight(); angelHold.position.y = Y0 + LIFT + 26; overlay = "title"; go("title"); stageUp(); }
}

// ---------- Simulation ----------
function step(dt) {
  simT += dt; stT += dt;
  P.inv = Math.max(0, P.inv - dt);
  flashWhite = Math.max(0, flashWhite - dt * 2);
  // keys on the screen and overlays
  if (overlay) { if (IN.okEdge) overlayAct(); }
  else if (state === "menu" && STG.menu) { if (IN.leftEdge) stagePick(-1); if (IN.rightEdge) stagePick(1); if (IN.okEdge) stageConfirm(); }
  else if ((state === "journal" || state === "firstJournal") && IN.okEdge && STG.jOpen > 0.9) closeJournal();

  if (state === "descend") {
    const k = clamp(stT / 4.2, 0, 1);
    angelHold.position.y = Y0 + LIFT + 26 * Math.pow(1 - smooth(k), 1.6);
    lookUp = 0.75 * (1 - smooth(clamp((stT - 1.5) / 2.5, 0, 1)));
    if (k >= 1) { go("approach"); setPose("cover"); prompt = "천사에게 다가가기"; say("천사에게 다가가 칼을 휘두르세요."); }
  }
  if (state === "approach" && Math.hypot(P.x, P.z - AZ) < EXR + 0.55) {
    go("slash"); prompt = ""; P.jumpT = -1; P.jy = 0;
    rotaOneShot("Slash", 1.0);
    after(0.45, () => sfx.slash());
    after(0.62, () => { sfx.passThrough(); A.flash = 1; flashWhite = 0.25; say("칼이 빛을 그냥 통과한다."); });
    after(1.25, () => { const fx = Math.sin(P.face + 0.9), fz = Math.cos(P.face + 0.9); dropSword(P.x + fx * 0.55, P.z + fz * 0.55, P.face + 1.2); sfx.swordDrop(); playRota("Idle", 0.3); RO.oneShot = null; });
    after(2.6, () => { go("firstJournal"); stageDown(); after(1.1, () => journalOpen("first")); });
  }
  if (["approach", "omen", "pattern"].includes(state)) moveRota(dt);
  if (state === "omen" && stT >= pat.omenT) { go("pattern"); R = runner(); pat.run(R, rep); }
  if (state === "pattern" && R) {
    runStep(R, dt);
    const busy = L.some((s) => s.harm && s.k !== "burn");
    if ((R.t >= pat.dur && !busy) || R.t >= pat.dur + 3.5) { L.forEach((s) => { if (s.k === "wlaser" || s.k === "elaser") s.dead = true; }); endTurn(); }
  }
  stepLights(dt); stepShadows(dt);
  // the angel's look follows its light
  // wing eyes close as the angel's light goes; in the last pattern they all open again and close over its last segment
  if (state !== "title" && state !== "loading") {
    const last = pat && pat.key === "final" && ["omen", "pattern", "turnEnd", "victory", "down"].includes(state);
    setEyes(last ? Math.round(54 * clamp((SEG[3] - A.hp) / SEG[3], 0, 1)) : Math.round(54 * 0.85 * (100 - A.hp) / 100));
  }
  ANG.light = (state === "victory" ? lerp(ANG.light, 0, dt * 0.5) : (0.45 + 0.55 * A.hp / 100) * (pat && pat.key === "final" && ["omen", "pattern"].includes(state) ? 1.2 : 1)) + A.flash * 0.6;
  SUN.reveal += ((state === "victory" ? 1 : (100 - A.hp) / 100 * 0.92) - SUN.reveal) * (1 - Math.exp(-dt * 0.8));
  if (state === "victory") {
    ANG.eyeSquash = Math.max(0.04, 1 - stT / 1.4);
    if (stT > 1.6) angelFade(clamp(1 - (stT - 1.6) / 2.6, 0, 1));
    lookUp = 0.85 * smooth(clamp((stT - 2) / 3, 0, 1));
  }
  if (RISE.t >= 0) { RISE.t += dt; const k = RISE.t / 2.4; angelHold.position.y = Y0 + LIFT + Math.sin(Math.PI * clamp(k, 0, 1)) * 4.5; if (k >= 1) { RISE.t = -1; setPose("spread"); } }
  if (TIPGLOW.on > 0) TIPGLOW.on -= dt;
  A.flash = Math.max(0, A.flash - dt * 4);
  if (A.ghostT > 0) A.ghostT -= dt; else A.ghost = Math.max(A.hp, A.ghost - 30 * dt);
  stageStep(dt);
}
function moveRota(dt) {
  if (RO.oneShot === "Slash" || RO.oneShot === "Fall") return;
  const dx = P.x, dz = P.z - AZ; let d = Math.hypot(dx, dz) || 1, th = Math.atan2(dz, dx);
  const air = P.jumpT >= 0;
  let ix = IN.x, iy = IN.y;
  if (air) { ix = lerp(P.ax, ix, 0.2); iy = lerp(P.ay, iy, 0.2); }
  const sp = SPEED * (state === "approach" ? 0.9 : 1);
  th -= ix * sp * dt / d; d = Math.max(EXR, d - iy * sp * dt);
  let nx = Math.cos(th) * d, nz = AZ + Math.sin(th) * d;
  const r = Math.hypot(nx, nz); if (r > AR - 0.35) { nx *= (AR - 0.35) / r; nz *= (AR - 0.35) / r; }
  P.vx = (nx - P.x) / Math.max(dt, 1e-4); P.vz = (nz - P.z) / Math.max(dt, 1e-4);
  P.x = nx; P.z = nz;
  const mv = Math.hypot(ix, iy); P.moving = mv;
  if (mv > 0.05) P.face = Math.atan2(P.vx, P.vz); else P.face = Math.atan2(-dx, -dz);
  if (IN.jumpEdge && !air) { P.jumpT = 0; P.ax = IN.x; P.ay = IN.y; rotaOneShot("Jump", 1.35); sfx.move(); }
  if (P.jumpT >= 0) { P.jumpT += dt; const k = P.jumpT / JUMP_T; P.jy = 4 * JUMP_H * k * (1 - k); if (k >= 1) { P.jumpT = -1; P.jy = 0; RO.oneShot = null; } }
  if (!RO.oneShot) playRota(mv > 0.55 ? "Run" : mv > 0.05 ? "Walk" : "Idle", 0.2, mv > 0.55 ? 1 : 1.2);
}

// ---------- Drawing the 3D ----------
const tipSprites = ["RMid", "LMid", "RLow", "LLow"].map((k) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: col("#ffe6b0"), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, toneMapped: false })); s.visible = false; s.k = k; add(s); return s; });
function render3D(dt) {
  if (!ANG.root) { placeCamera(dt, P.x, P.z); renderer.render(scene, cam); return; }
  placeSun();
  rotaPos.set(P.x, Y0 + 1.2, P.z);
  updateAngel(dt, rotaPos);
  if (!["descend", "title"].includes(state) && RISE.t < 0) angelHold.position.y = Y0 + LIFT + Math.sin(simT * 0.9) * 0.12;
  // Rota
  if (RO.mixer) RO.mixer.update(dt);
  const blink = P.inv > 0 && state === "pattern" && !reduceMotion && Math.floor(P.inv * 14) % 2 === 0;
  rota.visible = state !== "title" && !blink;
  rota.position.set(P.x, Y0 + P.jy, P.z);
  rota.rotation.y += angDiff(P.face, rota.rotation.y) * Math.min(1, dt * 12);
  rotaDot.visible = ["pattern", "omen"].includes(state); rotaDot.position.set(P.x, Y0 + 0.06, P.z);
  rotaBlob.position.set(P.x, Y0 + 0.02, P.z); rotaBlob.material.opacity = 0.5 * (1 - footFrac() * 0.5); rotaBlob.scale.setScalar(1 - footFrac() * 0.3);
  tipSprites.forEach((s) => { s.visible = TIPGLOW.on > 0; if (s.visible) { wingTip(s.k, s.position); s.scale.setScalar(1.6 * (1.8 - TIPGLOW.on) + 0.3); } });
  syncLights(); syncShadows(dt);
  placeCamera(dt, P.x, P.z);
  glEl.style.filter = impact > 0 ? "grayscale(1) contrast(6) brightness(1.05)" : "";
  renderer.render(scene, cam);
  const rays = (0.32 + 0.75 * SUN.reveal) * (1 - 0.7 * STG.k) * (state === "victory" ? 1.3 : 1);
  if (!Q.has("norays")) renderRays(rays);
  renderStage();
}

// ---------- Interface ----------
const ICON = { "#": C.WHITE };
const icoOn = spr(["...#.....", "..##..#..", "####...#.", "####.#.#.", "####...#.", "..##..#..", "...#....."], ICON);
const icoOff = spr(["...#.....", "..##.#.#.", "####.....", "####..#..", "####.....", "..##.#.#.", "...#....."], ICON);
const RIGHT = () => CW + OX - 8, LEFT = () => 8 - OX;
function tap(x, y, w, h, fn) { tapHandlers.push({ x, y, w, h, fn }); }
function drawHud() {
  if (state === "loading") {
    const ks = Object.keys(prog), p = ks.length ? ks.reduce((a, k) => a + prog[k], 0) / 5 : 0;
    textCO(loadErr || "고원으로 오르는 중 " + Math.round(p * 100) + "%", CW / 2, FH / 2 - 6, C.WHITE, C.INK, F11, 1);
    return;
  }
  if (state === "title") return;
  const lx_ = LEFT(), rx = RIGHT();
  // Rota's breath, top left
  slab(lx_, 6, 80, 13, C.INK, C.WHITE);
  text("로타", lx_ + 4, 8, C.WHITE, F9);
  for (let i = 0; i < PMAX; i++) { const x = lx_ + 28 + i * 8; if (i < P.hp) { rect(x, 9, 6, 6, C.RED); rect(x, 9, 2, 1, C.PINK); px(x, 10, C.PINK); } else frame(x, 9, 6, 6, C.MARB5); }
  // the angel's light, top centre, with a mark for every pattern
  if (!["descend", "approach", "slash"].includes(state) || A.hp < 100) {
    const bw = 200, bx = Math.round(CW / 2 - bw / 2);
    slab(bx - 4, 6, bw + 8, 13, C.INK, C.WHITE);
    rect(bx, 10, bw, 5, C.MARB5);
    const gw = Math.round(bw * A.ghost / 100), hw = Math.round(bw * A.hp / 100);
    rect(bx, 10, gw, 5, C.RED); rect(bx, 10, hw, 5, C.SUN); if (hw > 0) { rect(bx, 10, hw, 1, C.SUNP); rect(bx, 14, hw, 1, C.ORNG); }
    SEG.slice(0, 4).forEach((s) => { const x = bx + Math.round(bw * s / 100); rect(x, 8, 1, 9, C.INK); });
    if (touching && state === "pattern") frame(bx - 2, 8, bw + 4, 9, C.SUN);
  }
  // the journal's hint, or what to do
  const line = state === "pattern" || state === "omen" ? hintText : prompt && state === "approach" ? prompt : "";
  if (line) { const ls = wrap(line, 260, F9)[0], w = textW(strip(line), F9) + 12, x = Math.round(CW / 2 - w / 2); slab(x, 23, w, 13, C.INK, C.MARB5); drawLines([ls], x + 6, 25, F9, 12, C.WHITE, C.SUN); }
  // sound
  slab(rx - 16, 6, 16, 13, C.INK, C.WHITE); blit(muted ? icoOff : icoOn, rx - 12, 9);
  tap(rx - 19, 3, 22, 19, () => { muted = !muted; droneLevel(muted ? 0 : 1, 0.2); if (MUSIC.el) MUSIC.want = muted ? 0 : 0.6; });
  // touch controls
  placeControls();
  if (controlsOn() && (touchDev || Q.has("touch"))) {
    disc(JOY.cx, JOY.cy, JOY.r + 4, C.INK, 7); ring(JOY.cx, JOY.cy, JOY.r + 4, C.MARB3);
    disc(Math.round(JOY.cx + JOY.kx * JOY.r), Math.round(JOY.cy + JOY.ky * JOY.r), 10, JOY.id !== null ? C.WHITE : C.MARB2);
    disc(JUMPB.cx, JUMPB.cy, JUMPB.r, JUMPB.down ? C.SUN : C.INK, JUMPB.down ? 16 : 9); ring(JUMPB.cx, JUMPB.cy, JUMPB.r, C.WHITE);
    textC("점프", JUMPB.cx, JUMPB.cy - 5, C.WHITE, F9);
  } else if (controlsOn() && simT < 999) {
    text("방향키: 이동   Space: 점프", lx_, FH - 14, C.MARB3, F9);
  }
  // on the screen: how to choose
  if (state === "menu" && STG.menu && STG.k > 0.9 && !overlay) {
    optionRects().forEach((r, i) => tap(r.x, r.y, r.w, r.h, () => { if (STG.sel !== i) { STG.sel = i; } stageConfirm(); }));
  }
  if ((state === "journal" || state === "firstJournal") && STG.jOpen > 0.9) {
    const s = touchDev ? "눌러서 일지를 덮는다" : "Z / Enter: 일지를 덮는다";
    textCO(s, CW / 2, FH - 18, C.WHITE, C.INK, F9, 1);
  }
}
const THEME = {
  stone: { bg: C.INK, edge: C.WHITE, frame: C.MARB5, fg: C.WHITE, hl: C.SUN, sub: C.MARB2, eye: C.SKY3, btn: C.WHITE, btnFg: C.INK },
  paper: { bg: C.PAPER, edge: C.BROWN, frame: C.BROWN2, fg: C.BROWN, hl: C.REDD, sub: C.BROWN2, eye: C.BROWN2, btn: C.BROWN, btnFg: C.PAPER },
};
function overlaySpec() {
  if (overlay === "title") return { th: "stone", w: 330, eye: "셋째 날 · 천사의 고원", title: "천사가 내려온다", body: ["해는 아직 정상 뒤에 숨어 있다.", "천사의 빛만이 고원을 비춘다."], btn: "일어선다" };
  if (overlay === "lose") return { th: "stone", w: 290, eye: "로타가 쓰러졌다", title: "빛이 너무 밝았다", body: ["다시 일어나게. 빛이 있는 한 그림자도 있다네."], btn: "이 차례부터 다시" };
  return { th: "paper", w: 320, eye: "그날 밤 · 로타는 맹세를 깨고 일지를 넘겼다", title: "괴물에 관하여", body: ["천사를 넘었다면, 남은 것은 정상뿐이네.", "괴물은 천사보다 훨씬 약하니 걱정 말게.", "<b>너도 꼭, 나와 같이 하늘 같은 자가 되길.</b>"], btn: "처음부터 다시" };
}
function drawOverlay() {
  if (!overlay) return;
  rect(-OX, 0, FW, FH, C.INK, overlay === "title" ? 6 : 10);
  const sp = overlaySpec(), th = THEME[sp.th], w = sp.w, x = Math.round((CW - w) / 2), ix = x + 9, iw = w - 18;
  const eye = wrap(sp.eye, iw, F9), tsc = textW(sp.title, F11, 2) <= iw ? 2 : 1;
  const body = (sp.body || []).map((s) => wrap(s, iw - 6, F11));
  let h = 7 + eye.length * 12 + 1 + 11 * tsc + 8;
  body.forEach((l) => (h += l.length * 15 + 3));
  h += 6 + 19 + 7;
  let y = Math.max(2, Math.round((FH - h) / 2));
  slab(x, y, w, h, th.bg, th.edge); frame(x + 2, y + 2, w - 4, h - 4, th.frame);
  y += 7;
  drawLines(eye, ix, y, F9, 12, th.eye, th.eye); y += eye.length * 12 + 1;
  text(sp.title, ix, y, th.fg, F11, tsc); y += 11 * tsc + 3;
  rect(ix, y, iw, 1, th.frame); y += 5;
  for (const l of body) { rect(ix, y, 2, l.length * 15 - 4, th.hl); drawLines(l, ix + 6, y, F11, 15, th.fg, th.hl); y += l.length * 15 + 3; }
  y += 6;
  slab(ix, y, iw, 19, th.btn, th.edge);
  textC(sp.btn, ix + iw / 2, y + 4, th.btnFg, F11);
  if (Math.floor(performance.now() / 350) % 2) soul(Math.round(ix + iw / 2 - textW(sp.btn, F11) / 2) - 11, y + 7);
  tap(-OX, 0, FW, FH, overlayAct);
}
function drawUI() {
  tapHandlers.length = 0;
  ui.d.fill(0); target(ui, OX);
  if (flashWhite > 0) rect(-OX, 0, FW, FH, C.WHITE, Math.round(flashWhite * 20));
  drawHud(); drawOverlay();
  const d = ui.d; for (let i = 0; i < d.length; i++) uout[i] = pal32[d[i]];
  uctx.putImageData(uimg, 0, 0);
}

// ---------- Loop ----------
let last = 0;
function tick(now) {
  const dt = Math.min(DT_MAX, (now - last) / 1000 || 0); last = now;
  readInput();
  for (let i = timers.length - 1; i >= 0; i--) { const t = timers[i]; t.t -= dt; if (t.t <= 0) { timers.splice(i, 1); t.fn(); } }
  if (freeze > 0) freeze -= dt; else if (state !== "loading") step(dt);
  shake = Math.max(0, shake - dt * 1.3); impact = Math.max(0, impact - dt);
  musicStep(dt);
  render3D(freeze > 0 ? 0 : dt);
  drawUI();
  clearEdges();
  requestAnimationFrame(tick);
}
addEventListener("resize", resize);
resize();
loadAll();
requestAnimationFrame((t) => { last = t; tick(t); });
// for testing: __game.set({ pi: 2, go: "turn" }) jumps to a pattern
window.__game = { get state() { return state; }, get t() { return R ? R.t : 0; }, A, P, get L() { return L; }, get stage() { return STG; }, get touching() { return touching; },
  pose(name, part, v) { POSES[name][part] = v; setPose(name, true); },
  set(o) {
    if (o.pi !== undefined) pi = o.pi; if (o.rep !== undefined) rep = o.rep;
    if (o.ahp !== undefined) A.hp = A.ghost = o.ahp; if (o.php !== undefined) P.hp = o.php; if (o.inv !== undefined) P.inv = o.inv;
    if (o.x !== undefined) { P.x = o.x; P.z = o.z; }
    if (o.go === "begin") begin();
    if (o.go === "turn") { overlay = null; angelHold.position.y = Y0 + LIFT; firstSeen = true; if (RO.sword && !RO.swordFloor) dropSword(1, AZ + 4, 0); STG.k = 0; STG.want = 0; lookUp = 0; startTurn(); }
    if (o.go === "menu") { overlay = null; angelHold.position.y = Y0 + LIFT; lookUp = 0; openMenu(); }
    if (o.go === "journal") { overlay = null; angelHold.position.y = Y0 + LIFT; lookUp = 0; go("firstJournal"); stageDown(); after(1.1, () => journalOpen(o.key || "first")); }
  } };
