"""천사 (하늘 끝 직전의 중간 보스). 키 6.5m.

    blender -b --factory-startup -P tools/character/angel.py -- [--export] [--render] [--samples N]

정한 사양 (대화로 하나씩 정함):
- 몸: 다리가 안 보이는 긴 흰 로브, 종처럼 퍼진 밑단, 팔 없음, 깃과 밑단에 하늘색 테두리, 깃 안에서 하늘색 빛이 샘
- 머리: 목 위에 떠 있는 사실적인 맨 눈알 (하늘색 홍채, 흰자에 엷은 핏줄). 눈알 지름과 몸(로브) 높이가 1:1
- 토성처럼 누운 고리: 속이 빈 낮은 원통(띠)에 작은 눈알 12개가 반쯤 박혀 있음
- 눈알 뒤의 빛: 그림으로 그리지 않고 진짜 빛으로 둔다. Angel_HaloLight(빈 오브젝트)가 빛의 자리이고, 그 앞을 가리는
  눈알, 고리의 눈알, 깃털 사이 틈으로 빛줄기가 새어 나온다 (손가락 사이로 새는 빛처럼). 게임에서는 이 자리에 조명과
  빛줄기 효과를 단다. 렌더는 옅은 안개 속에 진짜 조명을 둬서 같은 모습을 낸다. 빛은 금색, 몸과 눈은 하늘색
- 날개 세 쌍: 겹겹이 쌓인 둥근 깃털, 바깥쪽 큰 깃털에만 단순한 눈 무늬
  피해를 입으면 날개 눈이 하나씩 감김: 열린 눈(Angel_WingEyeOpen_*) 뒤에 감긴 눈(Angel_WingEyeClosed_*)이 있어서
  게임에서 열린 눈을 숨기면 속눈썹 달린 곡선이 드러난다
- 움직임 (내보낸 파일의 Idle 애니메이션, 8초 반복): 몸 전체가 천천히 오르내림, 고리가 돎, 날개가 어긋난 박자로 펄럭임

좌표: -Y 앞, +Z 위, 단위 미터. 로브 밑단이 z=0 (떠 있는 높이는 게임에서 정한다).
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "village"))
from meshkit import Mesh, hexc, mix, shade  # noqa: E402

OUT = os.path.join(ROOT, "assets", "characters")
TEX = os.path.join(OUT, "angel_tex")

WHITE = hexc("#f4f6fb")
WHITE_SH = hexc("#c9d4ea")
WHITE_DEEP = hexc("#9fb0d2")
SKY = hexc("#7fb8ec")
SKY_D = hexc("#4f8fd6")
SKY_GLOW = hexc("#9fd4ff")
GOLD_GLOW = hexc("#ffd27a")     # the halo and the light in the collar are gold; body and eyes stay sky blue

# The eye and the body are the same size (1:1): the robe stands 2.4 m, the eye is 2.4 m across.
# The robe is drawn at a 3.62 m scale and shrunk by BODY (x, y, z).
COLLAR_Z = 3.62
BODY = (0.70, 0.70, 2.4 / 3.62)
BODY_TOP = 2.4
EYE_R = 1.2
EYE_Z = BODY_TOP + 0.12 + EYE_R          # the eye floats just above the collar
FPS, LOOP = 30, 240         # 8 second idle loop
RING_TILT = (math.radians(18), math.radians(-16), 0)    # like Saturn's ring: nearly flat, tipped toward the viewer


def srgb(c):
    return [((x / 255) / 12.92 if x / 255 <= 0.04045 else (((x / 255) + 0.055) / 1.055) ** 2.4) for x in c]


# =====================================================================================
# textures, painted with numpy
# =====================================================================================
def save_image(name, rgba, w, h):
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    path = os.path.join(TEX, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return bpy.data.images.load(path)


def lin(a):
    a = np.asarray(a, dtype=np.float64)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def eyeball_texture(name, w, h, iris=0.47, pupil=0.17, veins=True, simple=False, seed=3):
    """Equirectangular texture; the eye looks along -Y, which sits at u=0.5, v=0.5."""
    rng = np.random.default_rng(seed)
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    lon = (U - 0.5) * 2 * np.pi
    lat = (V - 0.5) * np.pi
    x = np.sin(lon) * np.cos(lat)
    y = -np.cos(lon) * np.cos(lat)
    z = np.sin(lat)
    th = np.arccos(np.clip(-y, -1, 1))          # angle away from where the eye looks
    ph = np.arctan2(z, x)
    out = np.zeros((h, w, 4))
    # sclera: white, a little cooler and greyer toward the back
    scl = np.stack([0.96 - 0.06 * th / np.pi, 0.95 - 0.07 * th / np.pi, 0.94 - 0.03 * th / np.pi], -1)
    if veins:
        vein = np.zeros_like(th)
        for k in range(26):
            p0 = rng.uniform(-np.pi, np.pi)
            amp, fr, phs = rng.uniform(0.05, 0.25), rng.uniform(3, 9), rng.uniform(0, 6)
            wid = rng.uniform(0.004, 0.009)
            start = rng.uniform(0.9, 1.25)
            path = p0 + amp * np.sin(th * fr + phs)
            d = np.angle(np.exp(1j * (ph - path))) * np.sin(th)
            fade = np.clip((th - start) / 0.5, 0, 1) * np.clip((2.6 - th) / 0.8, 0, 1)
            vein = np.maximum(vein, np.exp(-(d / wid) ** 2) * fade * rng.uniform(0.35, 0.7))
        red = np.array(lin([0.78, 0.30, 0.32]))
        scl = scl * (1 - vein[..., None] * 0.55) + red * vein[..., None] * 0.55
    out[..., :3] = scl
    # iris
    r = th / iris
    inside = r < 1
    if simple:
        col = np.where((r < 0.62)[..., None], lin([0.55, 0.80, 0.98]), lin([0.33, 0.62, 0.92]))
    else:
        fib = 0.5 + 0.5 * np.sin(ph * 70 + 3 * np.sin(ph * 11)) * np.sin(ph * 23 + r * 9)
        fib = fib * 0.55 + 0.45 * rng.random(th.shape) ** 3
        base = np.stack([np.interp(r, [0, 0.4, 0.8, 1], v_) for v_ in
                         (lin([0.62, 0.55, 0.30, 0.10]), lin([0.86, 0.82, 0.60, 0.25]), lin([0.98, 0.98, 0.92, 0.52]))], -1)
        col = base * (0.78 + 0.32 * fib[..., None])
        collar = np.exp(-((r - 0.42) / 0.05) ** 2)[..., None]       # a lighter ring around the pupil
        col = col * (1 - 0.3 * collar) + lin([0.85, 0.95, 1.0]) * 0.3 * collar
    limbal = np.clip((r - 0.86) / 0.14, 0, 1)[..., None]             # dark rim at the edge of the iris
    col = col * (1 - 0.75 * limbal) + lin([0.05, 0.12, 0.30]) * 0.75 * limbal
    out[..., :3] = np.where(inside[..., None], col, out[..., :3])
    out[..., :3] = np.where((th < pupil)[..., None], lin([0.02, 0.02, 0.04]), out[..., :3])
    out[..., 3] = 1
    return save_image(name, out, w, h)


def wing_eye_texture(name, closed=False, w=128, h=64):
    """A simple drawn eye for the feathers. x in [-1,1], y in [-0.5,0.5]."""
    X, Y = np.meshgrid((np.arange(w) + 0.5) / w * 2 - 1, ((np.arange(h) + 0.5) / h - 0.5))
    out = np.zeros((h, w, 4))
    ink = lin([0.11, 0.17, 0.36])
    top = 0.36 * (1 - X ** 2) ** 0.8                 # upper lid
    bot = -0.26 * (1 - X ** 2) ** 0.9                # lower lid
    if not closed:
        inside = (Y < top) & (Y > bot) & (np.abs(X) < 0.98)
        out[inside] = [*lin([0.97, 0.98, 1.0]), 1]
        rr = np.hypot(X * 1.0, (Y + 0.02) * 2.0)
        iris = inside & (rr < 0.44)
        out[iris] = [*lin([0.45, 0.74, 0.97]), 1]
        out[inside & (rr < 0.44) & (Y + 0.02 > 0.08)] = [*lin([0.25, 0.52, 0.88]), 1]
        out[inside & (rr < 0.2)] = [*lin([0.03, 0.04, 0.08]), 1]
        out[inside & (np.hypot(X + 0.12, (Y - 0.1) * 2) < 0.08)] = [1, 1, 1, 1]
        line = (np.abs(Y - top) < 0.05 + 0.03 * (1 - X ** 2)) & (np.abs(X) < 1.0)
        line |= (np.abs(Y - bot) < 0.025) & (np.abs(X) < 0.9)
        line |= (X < -0.82) & (np.abs(Y - (0.02 + (X + 0.82) * -0.6)) < 0.04) & (X > -1.0)   # outer flick
        out[line] = [*ink, 1]
    else:
        arc = bot * 0.55 + 0.06                       # a closed eye: a gentle curve, lashes hanging below
        line = (np.abs(Y - arc) < 0.045) & (np.abs(X) < 0.95)
        out[line] = [*ink, 1]
        for xl in (-0.6, -0.3, 0.0, 0.3, 0.6):
            yl = bot * 0.55 + 0.06
            lash = (np.abs(X - xl - (Y - (-0.26 * (1 - xl ** 2) ** 0.9 * 0.55)) * 0.4) < 0.035)
            lash &= (Y < -0.26 * (1 - xl ** 2) ** 0.9 * 0.55 + 0.05) & (Y > -0.26 * (1 - xl ** 2) ** 0.9 * 0.55 - 0.2)
            out[lash] = [*ink, 1]
    return save_image(name, np.flipud(out), w, h)


def halo_texture(name, s=1024, seed=21):
    """Light bursting from behind the eye, like a lamp behind fingers in haze: a hot core with a wide bloom,
    a few broad soft shafts with narrower ones between them, dark gaps, all fading out before the card's edge."""
    rng = np.random.default_rng(seed)
    X, Y = np.meshgrid((np.arange(s) + 0.5) / s * 2 - 1, (np.arange(s) + 0.5) / s * 2 - 1)   # Y is up
    r = np.hypot(X, Y)
    a = np.arctan2(Y, X)
    core = 1.2 * np.exp(-(r / 0.06) ** 2) + 0.75 * np.exp(-(r / 0.18) ** 2) + 0.25 * np.exp(-(r / 0.36) ** 2)
    specs = []
    for t in np.linspace(-0.25 * np.pi, 1.25 * np.pi, 8) + rng.uniform(-0.12, 0.12, 8):        # broad shafts
        specs.append((t, rng.uniform(0.07, 0.15), rng.uniform(0.55, 0.9), rng.uniform(0.25, 0.45)))
    for t in rng.uniform(-0.25 * np.pi, 1.25 * np.pi, 6):                                       # narrow ones
        specs.append((t, rng.uniform(0.025, 0.05), rng.uniform(0.6, 1.0), rng.uniform(0.25, 0.5)))
    for t in rng.uniform(-0.8 * np.pi, -0.2 * np.pi, 3):                                        # short, faint, downward
        specs.append((t, rng.uniform(0.06, 0.12), rng.uniform(0.35, 0.5), rng.uniform(0.12, 0.22)))
    beams = np.zeros_like(r)
    for t, wid, length, gain in specs:
        d = np.angle(np.exp(1j * (a - t)))
        beams += np.exp(-(d / wid) ** 2) * np.exp(-r / length) * np.clip(r / 0.04, 0, 1) * gain
    haze = 0.2 * np.exp(-r / 0.28)
    e = np.clip((1.0 - r) / 0.45, 0, 1)
    edge = e * e * (3 - 2 * e)
    alpha = np.clip((core + beams + haze) * edge, 0, 1)
    t = np.clip(r / 0.9, 0, 1)[..., None]
    col = lin([1.0, 0.99, 0.95]) * (1 - t) + lin([1.0, 0.84, 0.55]) * t
    out = np.concatenate([col, alpha[..., None]], -1)
    return save_image(name, out, s, s)


# =====================================================================================
# materials
# =====================================================================================
def mat_vcol(name="angel_vcol", rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    a = nt.nodes.new("ShaderNodeVertexColor")
    a.layer_name = "Col"
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def mat_image(name, img, rough=0.5, mask=False, blend=False, emit=0.0, closest=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    if closest:
        t.interpolation = "Closest"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if mask:
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        nt.links.new(t.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], b.inputs["Alpha"])
    elif blend:
        nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    if emit > 0:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    return m


def mat_glow(name, col, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Emission Color"].default_value = (*col, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


# =====================================================================================
# geometry helpers
# =====================================================================================
def shrink(mesh):
    mesh.v = [Vector((p.x * BODY[0], p.y * BODY[1], p.z * BODY[2])) for p in mesh.v]
    return mesh


def obj_from(mesh, name, mat, parent=None):
    ob = mesh.to_object(name)
    ob.data.materials.append(mat)
    if parent:
        ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e.rotation_euler = rot
    if parent:
        e.parent = parent
    return e


def textured_mesh(name, V, F, UV, mat, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = UV[me.loops[li].vertex_index]
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def eyeball(name, r, mat, segs=48, rings=24, parent=None, look=(0, -1, 0)):
    """UV sphere whose texture centre faces `look`."""
    V, F, UV = [], [], []
    for j in range(rings + 1):
        lat = -math.pi / 2 + math.pi * j / rings
        for i in range(segs + 1):
            lon = -math.pi + 2 * math.pi * i / segs
            V.append((math.sin(lon) * math.cos(lat) * r, -math.cos(lon) * math.cos(lat) * r, math.sin(lat) * r))
            UV.append((i / segs, j / rings))
    for j in range(rings):
        for i in range(segs):
            a = j * (segs + 1) + i
            F.append((a, a + 1, a + segs + 2, a + segs + 1))
    ob = textured_mesh(name, V, F, UV, mat, parent)
    for p in ob.data.polygons:
        p.use_smooth = True
    q = Vector((0, -1, 0)).rotation_difference(Vector(look).normalized())
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = q
    return ob


# =====================================================================================
# the robe
# =====================================================================================
def robe():
    m = Mesh()
    lining = Mesh()
    # (z, radius) outline: a bell at the bottom, a slim waist, rounded shoulders, a collar opening
    prof = [(0.0, 1.12), (0.25, 1.02), (0.6, 0.86), (1.0, 0.70), (1.5, 0.56), (2.0, 0.48), (2.45, 0.46),
            (2.85, 0.52), (3.2, 0.60), (3.42, 0.58), (3.55, 0.46), (3.62, 0.30)]
    n = 72
    folds = 16

    def radius(z, a):
        base = np.interp(z, [p[0] for p in prof], [p[1] for p in prof])
        k = max(0.0, 1 - z / 2.2) ** 1.6                       # folds deepen toward the hem
        return base * (1 + 0.045 * k * math.sin(a * folds + 0.6 * math.sin(a * 5)))

    zs = [0.0, 0.08, 0.16] + [0.25 + i * (3.62 - 0.25) / 26 for i in range(27)]
    rings = []
    for z in zs:
        t = z / 3.62
        col = mix(WHITE_SH, WHITE, min(1.0, 0.25 + t * 1.2))
        if z <= 0.16:
            col = SKY if z > 0.0 else SKY_D                   # sky blue hem band
        if z >= 3.55:
            col = SKY
        rings.append([(math.cos(i / n * math.tau) * radius(z, i / n * math.tau),
                       math.sin(i / n * math.tau) * radius(z, i / n * math.tau) * 0.92, z, col) for i in range(n)])
    V, C, F = [], [], []
    for ring in rings:
        for x, y, z, c in ring:
            V.append((x, y, z))
            C.append(c)
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            F.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    m.add(V, F, C, smooth=True)
    # lining inside the bell, seen from below
    LV = [(x * 0.97, y * 0.97, z) for (x, y, z) in V[: n * 8]]
    LF = [tuple(reversed(f)) for f in F if max(f) < n * 8]
    lining.add(LV, LF, [WHITE_DEEP] * len(LV), smooth=True)
    # rolled sky blue collar
    for i in range(n):
        a0, a1 = i / n * math.tau, (i + 1) / n * math.tau
        for s0, s1 in ((0, 1), (1, 2), (2, 3), (3, 0)):
            pts = []
            for a in (a0, a1):
                for s in (s0, s1):
                    ang = s / 4 * math.tau
                    rr = 0.31 + 0.045 * math.cos(ang)
                    pts.append((math.cos(a) * rr, math.sin(a) * rr * 0.92, COLLAR_Z + 0.04 * math.sin(ang)))
            m.add([pts[0], pts[2], pts[3], pts[1]], [(0, 1, 2, 3)], [SKY] * 4, smooth=True)
    return m, lining


def collar_light(mat, parent):
    # light pouring out of the collar: a glowing well and a soft cone above it
    m = Mesh()
    n = 32
    ring0 = [(math.cos(i / n * math.tau) * 0.27, math.sin(i / n * math.tau) * 0.25, COLLAR_Z - 0.09) for i in range(n)]
    ring1 = [(math.cos(i / n * math.tau) * 0.29, math.sin(i / n * math.tau) * 0.27, COLLAR_Z - 0.03) for i in range(n)]
    V = ring0 + ring1 + [(0, 0, COLLAR_Z - 0.09)]
    F = [(n + i, n + (i + 1) % n, (i + 1) % n, i) for i in range(n)] + [(i, (i + 1) % n, 2 * n) for i in range(n)]
    m.add(V, F, [GOLD_GLOW] * len(V), smooth=True)
    return obj_from(shrink(m), "Angel_CollarLight", mat, parent)


# =====================================================================================
# wings
# =====================================================================================
def feather(m, root, d, side_v, length, width, col_root, col_tip, lift=0.0, layer=0.0, segs=9):
    """A rounded feather: root point, direction d (unit, in the wing plane), side_v (unit, in the wing plane,
    perpendicular to d), length, width. Built double sided with a raised shaft. layer pushes it toward -Y."""
    root = Vector(root)
    nrm = Vector((0, -1, 0))
    pts_l, pts_r, shaft = [], [], []
    for k in range(segs + 1):
        s = k / segs
        # narrow at the quill, full in the middle, a round tip
        half = width * 0.5 * min(1.0, (s / 0.25) ** 0.6) * math.sqrt(max(0.0, 1 - max(0.0, (s - 0.5) / 0.5) ** 2))
        half = max(half, 0.004)
        bend = lift * s * s
        c = root + d * (length * s) + nrm * (layer + bend)
        pts_l.append(c + side_v * half + nrm * 0.0)
        pts_r.append(c - side_v * half)
        shaft.append(c + nrm * 0.012 * (1 - s))
    cols = [mix(col_root, col_tip, (k / segs) ** 1.5) for k in range(segs + 1)]
    V, C, F = [], [], []
    for k in range(segs + 1):
        V += [tuple(pts_l[k]), tuple(shaft[k]), tuple(pts_r[k])]
        C += [shade(cols[k], 0.96), cols[k], shade(cols[k], 0.96)]
    for k in range(segs):
        a = k * 3
        F += [(a, a + 3, a + 4, a + 1), (a + 1, a + 4, a + 5, a + 2)]
    m.add(V, F, C, smooth=True)
    # back side
    off = Vector((0, 0.006, 0))
    VB = [tuple(Vector(p) + off) for p in V]
    m.add(VB, [tuple(reversed(f)) for f in F], [shade(c, 0.85) for c in C], smooth=True)


def build_wing(span, droop):
    """One wing in its own frame: the arm runs along +X, feathers hang toward -Z. Returns (mesh, eye spots)."""
    m = Mesh()
    eyes = []
    # the arm: a gentle curve from the root to the tip
    def arm(t):
        return Vector((span * t, 0.0, 0.18 * span * math.sin(math.pi * t) * (1 - 0.4 * t)))

    def arm_dir(t):
        e = 1e-3
        return (arm(min(1, t + e)) - arm(max(0, t - e))).normalized()
    down = Vector((0, 0, -1))
    # primaries: long feathers fanning from the outer half; these carry the eyes
    NP = 7
    for i in range(NP):
        t = 1.0 - i * 0.075
        root = arm(t)
        ang = math.radians(8 + i * (droop / NP))
        dvec = (arm_dir(t) * math.cos(ang) + down * math.sin(ang)).normalized()
        side = Vector((0, -1, 0)).cross(dvec).normalized()
        length = span * (0.55 - 0.025 * i)
        width = span * 0.115
        feather(m, root, dvec, side, length, width, WHITE, mix(WHITE, SKY, 0.55), lift=0.04, layer=0.0 + i * 0.006)
        lay, sp = 0.0 + i * 0.006, 0.66
        eyes.append((root + dvec * length * sp + Vector((0, -(lay + 0.04 * sp * sp) - 0.012, 0)), dvec, side, width))
    # secondaries along the inner half
    NS = 8
    for i in range(NS):
        t = 0.48 - i * 0.055
        root = arm(t)
        ang = math.radians(droop + 8 + i * 2)
        dvec = (arm_dir(t) * math.cos(ang) + down * math.sin(ang)).normalized()
        side = Vector((0, -1, 0)).cross(dvec).normalized()
        feather(m, root, dvec, side, span * (0.36 - 0.012 * i), span * 0.11, WHITE, mix(WHITE, SKY, 0.35), lift=0.03, layer=0.05 + i * 0.004)
    # coverts: two rows of small feathers over the bases
    for row, (cnt, ln, wd, lay) in enumerate(((12, 0.2, 0.085, 0.11), (14, 0.13, 0.07, 0.16))):
        for i in range(cnt):
            t = 0.03 + i * (0.97 / cnt)
            root = arm(t) + Vector((0, 0, -0.02 * row))
            ang = math.radians(droop * 0.8 + 10)
            dvec = (arm_dir(t) * math.cos(ang) + down * math.sin(ang)).normalized()
            side = Vector((0, -1, 0)).cross(dvec).normalized()
            feather(m, root, dvec, side, span * ln, span * wd, WHITE, mix(WHITE, WHITE_SH, 0.6), lift=0.02, layer=lay + 0.003 * (i % 2), segs=7)
    # a smooth leading edge over the arm
    lead = Mesh()
    for k in range(16):
        t0, t1 = k / 16, (k + 1) / 16
        a, b = arm(t0), arm(t1)
        r0 = span * 0.035 * (1 - 0.6 * t0)
        r1 = span * 0.035 * (1 - 0.6 * t1)
        for q in range(8):
            q0, q1 = q / 8 * math.tau, (q + 1) / 8 * math.tau
            def ring(c, r, qq):
                return tuple(c + Vector((0, math.cos(qq) * r * 0.8 - 0.2, math.sin(qq) * r)))
            m.add([ring(a, r0, q0), ring(b, r1, q0), ring(b, r1, q1), ring(a, r0, q1)], [(0, 1, 2, 3)], [WHITE] * 4, smooth=True)
    return m, eyes


def mirror_mesh(m):
    out = Mesh()
    out.v = [Vector((-p.x, p.y, p.z)) for p in m.v]
    out.c = list(m.c)
    out.f = [tuple(reversed(f)) for f in m.f]
    out.s = list(m.s)
    return out


# =====================================================================================
# assembly
# =====================================================================================
WINGS = [  # name, root (x, y, z), angle of the arm above horizontal, sweep back, span, droop of the feathers
    ("Top", (0.24, 0.30, 2.32), 30, 10, 4.2, 72),
    ("Mid", (0.30, 0.34, 2.04), 4, 14, 3.6, 75),
    ("Low", (0.28, 0.30, 1.76), -20, 12, 2.9, 62),
]


def build(scene):
    os.makedirs(TEX, exist_ok=True)
    vcol = mat_vcol()
    eye_img = eyeball_texture("angel_eye", 1024, 512)
    small_img = eyeball_texture("angel_small_eye", 256, 128, iris=0.55, pupil=0.24, veins=False, simple=True, seed=9)
    open_img = wing_eye_texture("angel_wing_eye_open")
    closed_img = wing_eye_texture("angel_wing_eye_closed", closed=True)
    m_eye = mat_image("angel_eye", eye_img, rough=0.18)
    m_small = mat_image("angel_small_eye", small_img, rough=0.25)
    m_open = mat_image("angel_wing_eye_open", open_img, rough=0.5, mask=True)
    m_closed = mat_image("angel_wing_eye_closed", closed_img, rough=0.5, mask=True)
    m_light = mat_glow("angel_collar_light", GOLD_GLOW, 6.0)

    root = empty("Angel")
    body, lining = robe()
    obj_from(shrink(body), "Angel_Robe", vcol, root)
    obj_from(shrink(lining), "Angel_RobeLining", vcol, root)
    collar_light(m_light, root)

    # the head: a floating eye, the ring of eyes, the halo behind
    head = empty("Angel_Head", (0, 0, EYE_Z), parent=root)
    eyeball("Angel_Eye", EYE_R, m_eye, parent=head)
    tilt = empty("Angel_RingTilt", (0, 0, 0), RING_TILT, parent=head)
    ring = empty("Angel_Ring", parent=tilt)
    R = EYE_R * 1.7
    er = EYE_R * 0.19                                     # ring eye radius
    bh, bt = er * 2.3, 0.07                               # band height and wall thickness
    band = Mesh()
    nb = 120
    for i in range(nb):
        a0, a1 = i / nb * math.tau, (i + 1) / nb * math.tau
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        ro, ri, zb, zt = R, R - bt, -bh / 2, bh / 2
        band.add([(c0 * ro, s0 * ro, zb), (c1 * ro, s1 * ro, zb), (c1 * ro, s1 * ro, zt), (c0 * ro, s0 * ro, zt)],
                 [(0, 1, 2, 3)], [WHITE_SH, WHITE_SH, WHITE, WHITE], smooth=True)                      # outer face
        band.add([(c1 * ri, s1 * ri, zb), (c0 * ri, s0 * ri, zb), (c0 * ri, s0 * ri, zt), (c1 * ri, s1 * ri, zt)],
                 [(0, 1, 2, 3)], [WHITE_DEEP, WHITE_DEEP, WHITE_SH, WHITE_SH], smooth=True)            # inner face
        band.add([(c0 * ri, s0 * ri, zt), (c0 * ro, s0 * ro, zt), (c1 * ro, s1 * ro, zt), (c1 * ri, s1 * ri, zt)],
                 [(0, 1, 2, 3)], [SKY] * 4)                                                           # top rim
        band.add([(c1 * ri, s1 * ri, zb), (c1 * ro, s1 * ro, zb), (c0 * ro, s0 * ro, zb), (c0 * ri, s0 * ri, zb)],
                 [(0, 1, 2, 3)], [SKY_D] * 4)                                                         # bottom rim
    for i in range(12):
        a = i / 12 * math.tau
        out = Vector((math.cos(a), math.sin(a), 0))
        # half sunk into the outer face, looking straight out
        e = eyeball("Angel_RingEye_%02d" % i, er, m_small, segs=24, rings=12, parent=ring, look=tuple(out))
        e.location = out * R
        # a sky blue socket around each eye
        for q in range(24):
            q0, q1 = q / 24 * math.tau, (q + 1) / 24 * math.tau
            tang = Vector((-math.sin(a), math.cos(a), 0))
            up = Vector((0, 0, 1))
            def sp(qq, rr, lift):
                return tuple(out * (R + lift) + (tang * math.cos(qq) + up * math.sin(qq)) * rr)
            band.add([sp(q0, er * 1.0, 0.004), sp(q1, er * 1.0, 0.004), sp(q1, er * 1.18, 0.03), sp(q0, er * 1.18, 0.03)],
                     [(0, 1, 2, 3)], [SKY] * 4, smooth=True)
            band.add([sp(q0, er * 1.18, 0.03), sp(q1, er * 1.18, 0.03), sp(q1, er * 1.32, 0.004), sp(q0, er * 1.32, 0.004)],
                     [(0, 1, 2, 3)], [SKY_D] * 4, smooth=True)
    obj_from(band, "Angel_RingBand", vcol, ring)
    # where the light behind the eye sits; its scale breathes (the engine reads it as the light's strength)
    empty("Angel_HaloLight", (0, EYE_R + 0.35, 0), parent=head)

    # wings
    wing_objs = []
    eye_count = 0
    for name, (wx, wy, wz), up, sweep, span, droop in WINGS:
        mesh, spots = build_wing(span, droop)
        for side, tag in ((1, "R"), (-1, "L")):
            piv = empty("Angel_WingPivot_%s%s" % (tag, name), (side * wx, wy, wz),
                        (0, math.radians(-up) * side, math.radians(-sweep) * side), parent=root)
            mm = mesh if side > 0 else mirror_mesh(mesh)
            wob = obj_from(mm, "Angel_Wing_%s%s" % (tag, name), vcol, piv)
            wing_objs.append((wob, name, side))
            for k, (pos, dvec, sidev, width) in enumerate(spots):
                pos = Vector((pos.x * side, pos.y, pos.z))
                dv = Vector((dvec.x * side, dvec.y, dvec.z))
                sv = Vector((sidev.x * side, sidev.y, sidev.z))
                hw, hh = width * 0.42, width * 0.21
                for img_mat, kind, dy in ((m_closed, "Closed", 0.0), (m_open, "Open", -0.003)):
                    # the eye lies across the feather: its width along the feather's side, height along its length
                    c = pos + Vector((0, dy, 0))
                    ax, ay = sv * hw, dv * (-hh)
                    V = [tuple(c - ax - ay), tuple(c + ax - ay), tuple(c + ax + ay), tuple(c - ax + ay)]
                    UV = [(0, 0), (1, 0), (1, 1), (0, 1)] if side > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)]
                    F = [(0, 1, 2, 3)] if side > 0 else [(3, 2, 1, 0)]
                    UVf = UV if side > 0 else UV
                    textured_mesh("Angel_WingEye%s_%s%s_%d" % (kind, tag, name, k), V, F, UVf, img_mat, parent=wob)
                eye_count += 1
    return root, head, ring, wing_objs, eye_count


def animate(scene, root, head, ring, halo, wings):
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 0, LOOP
    for f in range(0, LOOP + 1, 4):
        t = f / LOOP                                      # 0..1 over the loop
        root.location = (0, 0, 0.10 * math.sin(t * math.tau * 2))
        root.keyframe_insert("location", frame=f)
        head.location = (0, 0, EYE_Z + 0.05 * math.sin(t * math.tau * 2 - 0.9))
        head.keyframe_insert("location", frame=f)
        ring.rotation_euler = (0, 0, t * math.tau)
        ring.keyframe_insert("rotation_euler", frame=f)
        k = 1 + 0.035 * math.sin(t * math.tau * 2 + 0.5)   # the light breathes
        halo.scale = (k, k, k)
        halo.keyframe_insert("scale", frame=f)
        for wob, name, side in wings:
            ph = {"Top": 0.0, "Mid": 1.1, "Low": 2.2}[name]
            beat = math.sin(t * math.tau * 2 - ph)
            wob.rotation_euler = (0, math.radians(3.5) * beat * side, math.radians(-7) * beat * side)
            wob.keyframe_insert("rotation_euler", frame=f)
    for ob in [root, head, ring, halo] + [w[0] for w in wings]:
        if ob.animation_data and ob.animation_data.action:
            act = ob.animation_data.action
            curves = []
            if hasattr(act, "fcurves"):
                curves = act.fcurves
            for fc in curves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return {"export": "--export" in a, "render": "--render" in a,
            "samples": int(a[a.index("--samples") + 1]) if "--samples" in a else 48}


def main():
    o = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    root, head, ring, wings, n_eyes = build(scene)
    halo = bpy.data.objects["Angel_HaloLight"]
    animate(scene, root, head, ring, halo, wings)
    tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in scene.objects if ob.type == "MESH")
    print("TRIS", tris, "WING EYES", n_eyes)
    if o["export"]:
        for ob in scene.objects:
            ob.select_set(True)
        kw = dict(filepath=os.path.join(OUT, "angel.glb"), export_format="GLB", use_selection=True, export_yup=True,
                  export_apply=True, export_animations=True)
        try:
            bpy.ops.export_scene.gltf(**kw, export_animation_mode="SCENE")
        except TypeError:
            bpy.ops.export_scene.gltf(**kw)
        print("EXPORTED", os.path.getsize(os.path.join(OUT, "angel.glb")) // 1024, "KB")
    if o["render"]:
        render(scene, o["samples"])


HALO_W = float(os.environ.get("HALO_W", "8000"))
QUICK = os.environ.get("QUICK") is not None
HAZE = float(os.environ.get("HAZE", "0.07"))
HALO_BACK = float(os.environ.get("HALO_BACK", "0.6"))
HAZE_DEPTH = float(os.environ.get("HAZE_DEPTH", "5.0"))


def render(scene, samples):
    scene.frame_set(0)
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*hexc("#26355a"), 1)      # dusk, so the light behind the eye reads
    bg.inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 1.6
    sun.data.angle = math.radians(6)
    sun.rotation_euler = (math.radians(48), math.radians(-12), math.radians(-30))
    scene.collection.objects.link(sun)
    fl = Mesh()
    fl.add([(-20, -20, -1.2), (20, -20, -1.2), (20, 20, -1.2), (-20, 20, -1.2)], [(0, 1, 2, 3)], hexc("#d8dce6"))
    flo = fl.to_object("floor")
    flo.data.materials.append(bpy.data.materials["angel_vcol"])
    for ob in scene.objects:                               # the angel floats a little off the floor
        if ob.name == "Angel":
            ob.location.z = 0.0
    # the light behind the eye, in a thin haze: the eye, the ring's eyes and the feathers cut it into shafts
    bpy.context.view_layer.update()
    # a small lamp close behind the eye: the eye hides its centre, and the light that slips past the eye's rim is cut
    # into shafts by the ring's eyes and the feathers, fanning out wide like light between fingers held over a lamp
    lamp = bpy.data.objects.new("halo_lamp", bpy.data.lights.new("halo_lamp", "POINT"))
    lamp.data.energy = HALO_W
    lamp.data.shadow_soft_size = 0.02
    lamp.data.color = (1.0, 0.86, 0.6)
    scene.collection.objects.link(lamp)
    lamp.location = bpy.data.objects["Angel_HaloLight"].matrix_world.translation + Vector((0, HALO_BACK, 0))
    if hasattr(sun.data, "volume_factor"):
        sun.data.volume_factor = 0.0                       # only the angel's light shows in the haze
    # haze only around the angel, so a long stretch of lit fog toward the camera does not wash the shafts out
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.6, 3.6))
    dom = bpy.context.active_object
    dom.name = "haze"
    dom.scale = (18, HAZE_DEPTH, 13)
    hm = bpy.data.materials.new("haze")
    hm.use_nodes = True
    nt = hm.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = HAZE
    vol.inputs["Anisotropy"].default_value = 0.55          # light scatters forward, toward the camera in front
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    dom.data.materials.append(hm)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.volume_bounces = 0
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1100
    scene.render.image_settings.file_format = "JPEG"
    vs = scene.view_settings
    for vt in ("AgX", "Khronos PBR Neutral", "Standard"):
        try:
            vs.view_transform = vt
            break
        except TypeError:
            continue
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 50
    rd = os.path.join(OUT, "renders")
    os.makedirs(rd, exist_ok=True)
    target = Vector((0, 0, 3.1))
    views = (("front", (0, -1, 0.06), 15.5), ("three_quarter", (-0.75, -0.8, 0.1), 15.5),
             ("side", (-1, 0, 0.05), 15.5), ("back", (0.3, 1, 0.08), 15.5))
    if QUICK:
        scene.render.resolution_x, scene.render.resolution_y = 500, 550
        views = views[:1]
    for name, d, dist in views:
        dv = Vector(d).normalized()
        cam.location = target + dv * dist
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(rd, "angel_" + name + ".jpg")
        bpy.ops.render.render(write_still=True)
    if QUICK:
        return
    # the eye up close
    cam.data.lens = 85
    t2 = Vector((0, 0, EYE_Z))
    cam.location = t2 + Vector((-0.35, -1, 0.15)).normalized() * EYE_R * 8.0
    cam.rotation_euler = (t2 - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(rd, "angel_head.jpg")
    bpy.ops.render.render(write_still=True)
    # next to Rota, for scale
    rota = os.path.join(OUT, "rota.glb")
    if os.path.exists(rota):
        bpy.ops.import_scene.gltf(filepath=rota)
        for ob in bpy.context.selected_objects:
            if ob.parent is None:
                ob.location = (2.6, -1.4, -1.2)
        cam.data.lens = 40
        t3 = Vector((1.0, 0, 2.6))
        cam.location = t3 + Vector((0.15, -1, 0.12)).normalized() * 15.5
        cam.rotation_euler = (t3 - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(rd, "angel_scale.jpg")
        bpy.ops.render.render(write_still=True)


main()
