"""로타 3D 모델 (얼굴 없는 버전, 4.5등신, T자 자세). 설정화: docs/refs/rota_tpose_color.jpg

    blender -b --factory-startup -P tools/character/rota.py -- [--export] [--render] [--samples N]
    ARMS=down blender ... -- --export   (팔을 내린 전투용 assets/characters/rota_down.glb)

좌표: +X 로타의 왼손 쪽, -Y 앞(얼굴이 보는 쪽), +Z 위. 단위 미터, 발바닥이 z=0.
마을과 같은 정점 색 재질(village_vcol)을 쓴다.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "village"))
from meshkit import Mesh, hexc, mix, shade, R, T, Sc  # noqa: E402

OUT = os.path.join(ROOT, "assets", "characters")

# ---------- palette (from the drawing) ----------
SKIN = hexc("#f7d6bf")
SKIN_SH = hexc("#e6b393")
HAIR = hexc("#20212c")
HAIR_HI = hexc("#3a3e55")
WHITE = hexc("#babcc0")         # light grey cloth
WHITE_SH = hexc("#97a2b4")        # shaded toward a cool grey-blue, like the drawing
BROWN = hexc("#8c5a37")
BROWN_D = hexc("#5f3d26")
BROWN_L = hexc("#b98a5c")
BOOT = hexc("#9a6a3f")
BOOT_TOP = hexc("#dcc193")


# ---------- surfaces of revolution ----------
def ring_pts(cx, cy, z, rx, ry, n, a0=0.0):
    return [(cx + math.cos(a0 + i / n * math.tau) * rx, cy + math.sin(a0 + i / n * math.tau) * ry, z) for i in range(n)]


def lathe(m, rings, n, M=None, cap0=True, cap1=True, keep=None, inward=False):
    """rings: (z, rx, ry, col[, cx, cy]) from bottom to top. Smooth shaded, outward normals.
    keep(face_centre) -> bool can drop faces (used to open the face in the hair)."""
    V, C, F = [], [], []
    for r in rings:
        z, rx, ry, col = r[:4]
        cx, cy = (r[4], r[5]) if len(r) > 4 else (0.0, 0.0)
        V += ring_pts(cx, cy, z, rx, ry, n)
        C += [col] * n
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            f = (k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i)
            if keep is not None:
                c = sum((Vector(V[q]) for q in f), Vector()) / 4
                if not keep(c):
                    continue
            F.append(f[::-1] if inward else f)
    if cap0 and rings[0][1] > 1e-4:
        F.append(tuple(range(n))[::-1])
    if cap1 and rings[-1][1] > 1e-4:
        F.append(tuple((len(rings) - 1) * n + i for i in range(n)))
    m.add(V, F, C, smooth=True, M=M)


def ellipsoid_rings(cz, rx, ry, rz, col_top, col_bot, steps=10, cy=0.0, bottom_pinch=1.0):
    out = []
    for k in range(steps + 1):
        t = k / steps                                # 0 bottom .. 1 top
        phi = math.pi * (1 - t)
        s = math.sin(phi)
        if t < 0.5:
            s *= 1 - (1 - bottom_pinch) * (1 - t / 0.5) ** 1.5
        out.append((cz - math.cos(phi) * rz, max(1e-4, rx * s), max(1e-4, ry * s), mix(col_bot, col_top, t), 0.0, cy))
    return out


# ---------- body measurements ----------
HEAD_C = 1.415                     # centre of the skull
# Below the belt the tunic hangs like the skirt of a robe. ROBE picks the cut (environment variable, default "long").
ROBE = os.environ.get("ROBE", "long")
SKIRTS = {
    # flares straight out from the belt to mid-thigh
    "aline": [(0.60, 0.235, 0.18), (0.68, 0.212, 0.162), (0.76, 0.188, 0.142), (0.84, 0.163, 0.12)],
    # longer, falling to just above the knee
    "long": [(0.47, 0.25, 0.195), (0.56, 0.232, 0.178), (0.66, 0.21, 0.16), (0.76, 0.186, 0.14), (0.84, 0.163, 0.12)],
    # swells out round and tucks back in at the hem
    "round": [(0.645, 0.178, 0.135), (0.665, 0.205, 0.158), (0.70, 0.222, 0.17), (0.75, 0.222, 0.168), (0.80, 0.205, 0.152), (0.845, 0.175, 0.128)],
}
# ARMS: "t" keeps the arms straight out as drawn; "down" lets them hang for the battle (saved as rota_down.glb)
ARMS = os.environ.get("ARMS", "t")
ARM_DROP = 68 if ARMS == "down" else 0          # degrees below horizontal
TUNIC = SKIRTS[ROBE] + [  # z, rx, ry : the tunic's outline from hem to neck
    (0.90, 0.157, 0.112), (1.00, 0.152, 0.106),
    (1.10, 0.165, 0.110), (1.165, 0.168, 0.104), (1.20, 0.075, 0.066)]
HEM = TUNIC[0][0]


def tunic_r(z):
    for (z0, a0, b0), (z1, a1, b1) in zip(TUNIC, TUNIC[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return TUNIC[0][1:] if z < TUNIC[0][0] else TUNIC[-1][1:]


def front_y(x, z, out=0.004):
    rx, ry = tunic_r(z)
    k = max(0.0, 1 - (x / rx) ** 2)
    return -ry * math.sqrt(k) - out


HEAD = [(1.27, 0.02), (1.285, 0.075), (1.315, 0.115), (1.355, 0.138), (1.40, 0.146), (1.45, 0.146), (1.50, 0.132), (1.54, 0.10), (1.565, 0.055)]


def head_r(z):
    for (z0, r0), (z1, r1) in zip(HEAD, HEAD[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return HEAD[0][1] if z < HEAD[0][0] else HEAD[-1][1]


def hair_r(z):
    dz = (z - (HEAD_C + 0.02)) / 0.168
    return 0.168 * math.sqrt(max(0.0, 1 - dz * dz))


def build():
    body, cloth, hair, leather = Mesh(), Mesh(), Mesh(), Mesh()

    # ---------- head (no face) and neck ----------
    lathe(body, [(1.27, 0.02, 0.02, SKIN_SH), (1.285, 0.075, 0.07, SKIN_SH), (1.315, 0.115, 0.108, SKIN), (1.355, 0.138, 0.13, SKIN),
                 (1.40, 0.146, 0.138, SKIN), (1.45, 0.146, 0.14, SKIN), (1.50, 0.132, 0.128, SKIN), (1.54, 0.10, 0.098, SKIN),
                 (1.565, 0.055, 0.055, SKIN), (1.572, 0.01, 0.01, SKIN)], 16)
    lathe(body, [(1.17, 0.045, 0.043, SKIN_SH), (1.30, 0.042, 0.04, SKIN)], 10, cap0=False)

    # ---------- hair: a round bob, open at the face ----------
    def keep(c):
        if c.z < 1.305:                               # the bob ends at the jaw
            return False
        if c.y < -0.02 and c.z < 1.468:               # the face
            return False
        return True
    rings = ellipsoid_rings(HEAD_C + 0.02, 0.168, 0.162, 0.168, HAIR_HI, HAIR, steps=14, cy=0.008)
    lathe(hair, rings, 20, cap0=False, cap1=False, keep=keep)
    hair.add([(0, 0.008, HEAD_C + 0.188)] + [p for p in ring_pts(0, 0.008, rings[-2][0], rings[-2][1], rings[-2][2], 20)],
             [(0, (i + 1) % 20 + 1, i + 1) for i in range(20)], [HAIR_HI] * 21, smooth=True)
    # fringe and side locks: shells that follow the skull, with jagged lower edges
    def shell(a0, a1, n, bottom, z_top=1.495, col=HAIR):
        V, C, F = [], [], []
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            zb = bottom(k / n)
            for z, out in ((z_top, 0.0), (zb, 0.006)):
                r = max(head_r(z) + 0.013, hair_r(z)) + out
                V.append((math.cos(a) * r, math.sin(a) * r * 0.97 + 0.004, z))
                C.append(col if z < z_top else HAIR_HI)
        for k in range(n):
            F.append((2 * k + 1, 2 * k + 3, 2 * k + 2, 2 * k))        # outer side
            F.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))        # inner side, so it has a back
        hair.add(V, F, C, smooth=True)

    # locks of hair: wide at the root, tapering to a soft point, different lengths, narrow gaps between
    LOCKS = [(0.0, 0.11, 0.04), (0.11, 0.22, 0.052), (0.29, 0.43, 0.075), (0.43, 0.57, 0.055),
             (0.57, 0.71, 0.062), (0.71, 0.85, 0.046), (0.85, 1.0, 0.036)]

    def lock(u, depth, root=1.465):
        # a strip of hair: steep sides, a blunt rounded end, only a slight taper
        v = 1 - abs(2 * u - 1)                         # 0 at the gaps, 1 in the middle of the lock
        return root - depth * min(1.0, (v / 0.6) ** 0.5) * (0.85 + 0.15 * v)

    def fringe(t):
        for t0, t1, depth in LOCKS:
            if t0 <= t <= t1:
                return lock((t - t0) / (t1 - t0), depth)
        return 1.47                                    # the part: a wedge of forehead shows
    shell(-160, -20, 112, fringe)
    for a0 in (-178, -2):                              # side locks to the jaw
        shell(a0, a0 + 20, 12, lambda t: lock(t, 0.085, 1.405), z_top=1.47)

    # ---------- tunic: white, shaded pale blue toward the hem ----------
    def slit(c):                                       # the skirt is split up both sides, below the belt
        return not (c.z < 0.79 and abs(c.y) < 0.03)
    rings = []
    for z, rx, ry in TUNIC:
        t = (z - HEM) / (1.2 - HEM)
        rings.append((z, rx, ry, mix(WHITE_SH, WHITE, min(1.0, 0.2 + t))))
    lathe(cloth, rings, 24, cap0=False, keep=slit)
    lathe(cloth, [(z, rx - 0.006, ry - 0.006, shade(WHITE_SH, 0.86)) for z, rx, ry in TUNIC if z <= 0.85], 24,
          cap0=False, cap1=False, keep=slit, inward=True)                       # the lining, seen from below
    # brown edging along the hem
    band = [(HEM - 0.002 + k * 0.012, *(v + 0.003 for v in tunic_r(HEM - 0.002 + k * 0.012))) for k in range(3)]
    lathe(leather, [(z, rx, ry, BROWN_D if k == 0 else BROWN) for k, (z, rx, ry) in enumerate(band)], 24, cap0=False, cap1=False, keep=slit)
    lathe(leather, [(z, rx - 0.011, ry - 0.011, BROWN) for z, rx, ry in band], 24, cap0=False, cap1=False, keep=slit, inward=True)

    # trim lines and cross stitches down the front
    for s in (-1, 1):
        x = s * 0.098
        zs = [HEM + 0.02 + k * 0.02 for k in range(40)]
        for z0, z1 in zip(zs, zs[1:]):
            if z1 > 1.05:
                break
            y0, y1 = front_y(x, z0, 0.003), front_y(x, z1, 0.003)
            cloth.quad((x - s * 0.006, y0, z0), (x + s * 0.006, y0, z0), (x + s * 0.006, y1, z1), (x - s * 0.006, y1, z1), BROWN) if s < 0 else \
                cloth.quad((x - 0.006, y0, z0), (x + 0.006, y0, z0), (x + 0.006, y1, z1), (x - 0.006, y1, z1), BROWN)
        for z in (1.045, 1.0, 0.955, 0.91):
            xc = s * 0.068
            for d in (1, -1):
                a = (xc - 0.014, front_y(xc - 0.014, z - d * 0.014, 0.005), z - d * 0.014)
                b = (xc + 0.014, front_y(xc + 0.014, z + d * 0.014, 0.005), z + d * 0.014)
                u = Vector(b) - Vector(a)
                nrm = Vector((0, -1, 0))
                side = u.cross(nrm).normalized() * 0.0045
                cloth.quad(Vector(a) - side, Vector(b) - side, Vector(b) + side, Vector(a) + side, BROWN_D)

    for s in (-1, 1):                                  # straps hanging from the belt, a loop at each end
        x = s * 0.052
        for z0, z1 in zip([0.86 - k * 0.02 for k in range(6)], [0.84 - k * 0.02 for k in range(6)]):
            y0, y1 = front_y(x, z0, 0.007), front_y(x, z1, 0.007)
            leather.quad((x - 0.008, y1, z1), (x + 0.008, y1, z1), (x + 0.008, y0, z0), (x - 0.008, y0, z0), BROWN)
        leather.box((0.026, 0.012, 0.022), BROWN_D, M=T(x, front_y(x, 0.74, 0.012), 0.732))

    # ---------- the brown hood lying around the neck, dipping to a V ----------
    n = 28
    top, mid, bot = [], [], []
    for i in range(n):
        a = -math.pi / 2 + i / n * math.tau           # i = 0 is the front
        d = min(abs(((a + math.pi / 2) + math.pi) % math.tau - math.pi), math.pi) / math.pi   # 0 at front, 1 at back
        zb = 1.135 - 0.10 * max(0.0, 1 - d / 0.28)
        rx, ry = tunic_r(zb)
        top.append((math.cos(a) * 0.072, math.sin(a) * 0.068, 1.235 - 0.03 * max(0.0, 1 - d / 0.3)))
        mid.append((math.cos(a) * (rx * 0.82 + 0.03), math.sin(a) * (ry * 0.82 + 0.03), (1.235 + zb) / 2 + 0.01))
        bot.append((math.cos(a) * (rx + 0.008), math.sin(a) * (ry + 0.008), zb))
    V = top + mid + bot
    F = []
    for k in range(2):
        for i in range(n):
            j = (i + 1) % n
            F.append(((k + 1) * n + i, (k + 1) * n + j, k * n + j, k * n + i))
    leather.add(V, F, [BROWN_L] * n + [BROWN] * n + [BROWN_D] * n, smooth=True)
    # drawstrings with tassels
    for x in (-0.018, 0.018):
        y = front_y(x, 1.03, 0.012)
        leather.cyl(0.0035, 0.0035, 0.07, 5, BROWN_D, M=T(x, y, 0.965))
        leather.cone(0.008, 0.022, 6, BROWN_D, M=T(x, y, 0.968) @ R("X", 180))

    # ---------- belts: two straps crossing over the hips, a pouch on each side ----------
    for z, tilt in ((0.875, 3.5), (0.858, -3.5)):
        rx, ry = tunic_r(z)
        lathe(leather, [(-0.011, rx + 0.009, ry + 0.009, BROWN_D), (0.011, rx + 0.009, ry + 0.009, BROWN)], 20,
              M=T(0, 0, z) @ R("X", 1.5) @ R("Y", tilt), cap0=False, cap1=False)
    for s in (-1, 1):
        M = T(s * (tunic_r(0.83)[0] + 0.02), 0.0, 0.825)
        leather.box((0.04, 0.06, 0.095), BROWN, M=M, grad=0.8)
        leather.box((0.044, 0.064, 0.03), BROWN_L, M=M @ T(0, 0, 0.075), grad=0.9)

    # ---------- arms in a T (or hanging, see ARMS): puffy short sleeve, white undersleeve, brown cuffs, mitten hands ----------
    for s in (-1, 1):
        A = T(s * 0.13, 0, 1.115) @ R("Y", s * (90 + ARM_DROP))     # local z runs out along the arm
        lathe(cloth, [(0.0, 0.062, 0.066, WHITE), (0.05, 0.07, 0.072, WHITE), (0.12, 0.066, 0.068, WHITE), (0.155, 0.058, 0.06, WHITE_SH)], 12, M=A)
        lathe(leather, [(0.148, 0.061, 0.063, BROWN), (0.175, 0.059, 0.061, BROWN_D)], 12, M=A)      # sleeve cuff
        lathe(cloth, [(0.17, 0.042, 0.044, WHITE), (0.29, 0.04, 0.042, WHITE_SH), (0.30, 0.042, 0.044, WHITE_SH),
                      (0.31, 0.04, 0.042, WHITE), (0.45, 0.036, 0.037, WHITE)], 10, M=A, cap0=False)
        lathe(leather, [(0.43, 0.043, 0.044, BROWN_D), (0.48, 0.042, 0.043, BROWN)], 10, M=A)       # wrist cuff
        H = A @ T(0, 0, 0.525)
        lathe(body, ellipsoid_rings(0, 0.042, 0.03, 0.055, SKIN, SKIN_SH, steps=8), 10, M=H)
        body.cone(0.014, 0.04, 6, SKIN, M=A @ T(0, -0.03, 0.5) @ R("X", -60), smooth=True)          # thumb

    # ---------- legs in white leggings, brown ankle boots ----------
    for s in (-1, 1):
        x = s * 0.078
        lathe(cloth, [(0.17, 0.05, 0.052, WHITE_SH), (0.33, 0.058, 0.06, WHITE), (0.44, 0.056, 0.058, WHITE_SH),
                      (0.46, 0.057, 0.059, WHITE), (0.60, 0.066, 0.068, WHITE), (0.74, 0.074, 0.076, WHITE_SH)],
              12, M=T(x, 0, 0), cap0=False, cap1=False)
        lathe(leather, [(0.0, 0.058, 0.09, BROWN_D, 0, -0.024), (0.035, 0.062, 0.093, BOOT, 0, -0.024), (0.08, 0.06, 0.075, BOOT, 0, -0.012),
                        (0.15, 0.057, 0.06, BOOT), (0.19, 0.062, 0.064, BOOT_TOP), (0.215, 0.061, 0.063, BOOT_TOP)], 14, M=T(x, 0, 0))
    return {"Rota_Body": body, "Rota_Cloth": cloth, "Rota_Hair": hair, "Rota_Leather": leather}


# ---------- scene ----------
def material():
    mat = bpy.data.materials.new("village_vcol")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    for nm in ("Specular IOR Level", "Specular"):
        if nm in bsdf.inputs:
            bsdf.inputs[nm].default_value = 0.2
    return mat


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return {"export": "--export" in a, "render": "--render" in a,
            "samples": int(a[a.index("--samples") + 1]) if "--samples" in a else 48}


def main():
    o = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mat = material()
    obs = []
    tris = 0
    for name, m in build().items():
        ob = m.to_object(name)
        ob.data.materials.append(mat)
        obs.append(ob)
        tris += m.tri_count()
    print("TRIS", tris)
    os.makedirs(OUT, exist_ok=True)
    if o["export"]:
        for ob in scene.objects:
            ob.select_set(ob.type == "MESH")
        name = "rota.glb" if ARMS == "t" else "rota_down.glb"
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name), export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
        print("EXPORTED", name, os.path.getsize(os.path.join(OUT, name)) // 1024, "KB")
    if o["render"]:
        render(scene, o["samples"])


def render(scene, samples):
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#c9d9ee"), 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(50), math.radians(-10), math.radians(-35))
    scene.collection.objects.link(sun)
    floor = Mesh()
    floor.add([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [(0, 1, 2, 3)], hexc("#e9e6dd"))
    fo = floor.to_object("floor")
    fo.data.materials.append(bpy.data.materials["village_vcol"])
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = 900, 1000
    scene.render.image_settings.file_format = "JPEG"
    vs = scene.view_settings
    for vt in ("Khronos PBR Neutral", "Standard"):
        try:
            vs.view_transform = vt
            break
        except TypeError:
            continue
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.lens = 60
    views = {"front": (0, -1), "three_quarter": (-0.7, -0.75), "side": (-1, 0), "back": (0.35, 1)}
    for name, (dx, dy) in views.items():
        d = Vector((dx, dy, 0)).normalized()
        target = Vector((0, 0, 0.82))
        cam.location = target + d * 3.9 + Vector((0, 0, 0.35))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(OUT, "renders", "rota_" + name + ".jpg")
        bpy.ops.render.render(write_still=True)
    # a close look at the head
    target = Vector((0, 0, 1.36))
    cam.data.lens = 85
    cam.location = target + Vector((-0.35, -1.0, 0.12)).normalized() * 1.25
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, "renders", "rota_head.jpg")
    bpy.ops.render.render(write_still=True)


main()
