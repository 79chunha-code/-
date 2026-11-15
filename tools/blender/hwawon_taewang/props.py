"""나무, 자동차, 경비실, 자전거 보관대, 분리수거장, 정자, 놀이터, 가로등 등 소품."""
import math
import random

import bpy
from mathutils import Vector

import lib
from lib import P, MeshBuilder, instance, mat_col, mat_tex, perp, point_in_poly, rect_pts, v3

rng = random.Random(1995)


# ------------------------------------------------------------------ 나무
def _card(mb, c, right, up, w, h, mat):
    r, u = right * (w / 2), up * (h / 2)
    mb.quad3([c - r - u, c + r - u, c + r + u, c - r + u], mat)


def _limb(mb, pts, radii, mat, n=6):
    """굽은 줄기/가지: 3D 점들을 따라가는 관."""
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        d = (b - a).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = d.cross(x).normalized()
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            o0 = x * math.cos(a0) + y * math.sin(a0)
            o1 = x * math.cos(a1) + y * math.sin(a1)
            mb.add([tuple(a + o1 * radii[i]), tuple(a + o0 * radii[i]),
                    tuple(b + o0 * radii[i + 1]), tuple(b + o1 * radii[i + 1])],
                   [((k + 1) / n, i), (k / n, i), (k / n, i + 1), ((k + 1) / n, i + 1)], mat)


def make_pine(seed, M):
    """소나무: 굽은 붉은 줄기 + 층층이 퍼진 잎."""
    r = random.Random(seed)
    mb = MeshBuilder()
    h = r.uniform(6.5, 9.5)
    lean = Vector((r.uniform(-1, 1), r.uniform(-1, 1))).normalized() * r.uniform(0.6, 1.6)
    pts, rad = [], []
    for i in range(6):
        t = i / 5
        wob = Vector((math.sin(t * 5 + seed), math.cos(t * 4 + seed * 2))) * 0.25 * t
        p = lean * (t ** 1.5) + wob
        pts.append((p.x, p.y, h * t))
        rad.append(0.30 * (1 - t * 0.7))
    _limb(mb, pts, rad, M["bark_pine"])
    fol = [M["pine"], M["pine2"]]
    top = Vector(pts[-1])
    for i in range(r.randint(11, 14)):
        t = r.uniform(0.5, 1.0)
        base = Vector(pts[min(5, int(t * 5))])
        ang = r.uniform(0, 6.28)
        reach = r.uniform(0.8, 2.6) * (1.25 - t * 0.5)
        c = Vector((base.x + math.cos(ang) * reach, base.y + math.sin(ang) * reach, h * t + r.uniform(-0.2, 0.5)))
        if reach > 1.3:
            _limb(mb, [tuple(base), tuple(c)], [0.07, 0.03], M["bark_pine"], n=4)
        size = r.uniform(3.0, 4.4)
        m = r.choice(fol)
        tx, ty = r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3)
        _card(mb, c, Vector((1, 0, tx)).normalized(), Vector((0, 1, ty)).normalized(), size, size, m)   # 누운 잎판
        _card(mb, c + Vector((0, 0, 0.35)), Vector((0.7, 0.7, 0)), Vector((-0.7, 0.7, 0)), size * 0.8, size * 0.8, m)
        a2 = r.uniform(0, 3.14)
        d = Vector((math.cos(a2), math.sin(a2), 0))
        _card(mb, c + Vector((0, 0, 0.3)), d, Vector((0, 0, 1)), size, size * 0.5, m)
        _card(mb, c + Vector((0, 0, 0.3)), Vector((-d.y, d.x, 0)), Vector((0, 0, 1)), size, size * 0.5, m)
    _card(mb, top + Vector((0, 0, 0.3)), Vector((1, 0, 0)), Vector((0, 1, 0)), 3.0, 3.0, fol[0])
    return mb.build(f"tree_pine_{seed}")


def make_broadleaf(seed, M, h=None, fol_key="leaf"):
    r = random.Random(seed)
    mb = MeshBuilder()
    h = h or r.uniform(5.5, 8.0)
    th = h * 0.42
    _limb(mb, [(0, 0, 0), (0.05, 0.02, th * 0.6), (0.0, 0.1, th)], [0.2, 0.16, 0.12], M["bark"])
    cr = h * 0.36
    cc = Vector((0, 0, th + cr * 0.9))
    for i in range(4):
        ang = i * 1.57 + r.uniform(-0.3, 0.3)
        e = cc + Vector((math.cos(ang) * cr * 0.6, math.sin(ang) * cr * 0.6, r.uniform(-0.2, 0.6) * cr))
        _limb(mb, [(0, 0.1, th), tuple(e)], [0.1, 0.03], M["bark"], n=4)
    fol = [M[fol_key], M[fol_key + "2"]] if fol_key + "2" in M else [M[fol_key]]
    for i in range(r.randint(24, 30)):
        d = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 0.8))).normalized()
        c = cc + Vector((d.x * cr, d.y * cr, d.z * cr * 1.1)) * r.uniform(0.35, 1.0)
        a2 = r.uniform(0, 3.14)
        right = Vector((math.cos(a2), math.sin(a2), 0))
        up = Vector((0, 0, 1)) if r.random() < 0.7 else Vector((-right.y, right.x, 0)).lerp(Vector((0, 0, 1)), 0.4).normalized()
        s = r.uniform(2.2, 3.4) * (h / 7)
        _card(mb, c, right, up, s, s, r.choice(fol))
    return mb.build(f"tree_leaf_{seed}")


def make_meta(seed, M):
    """메타세쿼이아: 키 큰 원뿔."""
    r = random.Random(seed)
    mb = MeshBuilder()
    h = r.uniform(13, 17)
    _limb(mb, [(0, 0, 0), (0, 0, h * 0.5), (0, 0, h * 0.96)], [0.3, 0.18, 0.04], M["bark"])
    tiers = 9
    for i in range(tiers):
        t = i / (tiers - 1)
        z = h * (0.2 + 0.78 * t)
        w = (1 - t) * 4.6 + 1.0
        for k in range(3):
            a2 = k * 1.047 + i * 0.5
            d = Vector((math.cos(a2), math.sin(a2), 0))
            _card(mb, Vector((0, 0, z)), d, Vector((0, 0, 1)), w, h * 0.2, M["meta"])
    return mb.build(f"tree_meta_{seed}")


def make_shrub(M):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.6, location=(0, 0, 0.55), calc_uvs=True)
    ob = bpy.context.active_object
    ob.data.materials.append(M["hedge"])
    for uv in ob.data.uv_layers[0].data:
        uv.uv = (uv.uv[0] * 3, uv.uv[1] * 3)
    me = ob.data
    bpy.data.objects.remove(ob)
    return me


# ------------------------------------------------------------------ 자동차
CAR_TYPES = {
    "sedan": dict(w=1.84, wheel_x=(1.42, -1.38), wr=0.33,
                  body=[(-2.38, 0.34), (2.36, 0.34), (2.40, 0.62), (2.22, 0.80), (1.02, 0.93), (-1.52, 0.96), (-2.30, 0.92), (-2.40, 0.62)],
                  cabin=[(1.00, 0.93), (0.22, 1.42), (-1.12, 1.44), (-1.78, 0.96)]),
    "suv": dict(w=1.88, wheel_x=(1.40, -1.36), wr=0.37,
                body=[(-2.30, 0.40), (2.30, 0.40), (2.34, 0.76), (2.12, 1.00), (1.08, 1.10), (-2.22, 1.12), (-2.33, 0.80)],
                cabin=[(1.04, 1.10), (0.46, 1.68), (-1.98, 1.70), (-2.26, 1.12)]),
    "hatch": dict(w=1.62, wheel_x=(1.20, -1.18), wr=0.29,
                  body=[(-1.80, 0.32), (1.80, 0.32), (1.83, 0.60), (1.66, 0.80), (0.96, 0.90), (-1.74, 0.92), (-1.83, 0.60)],
                  cabin=[(0.92, 0.90), (0.40, 1.46), (-1.44, 1.48), (-1.78, 0.92)]),
    "truck": dict(w=1.74, wheel_x=(1.55, -1.45), wr=0.31,
                  body=[(0.95, 0.42), (2.50, 0.42), (2.55, 0.92), (2.46, 1.16), (0.95, 1.16)],
                  cabin=[(2.44, 1.16), (2.22, 1.92), (1.05, 1.94), (0.98, 1.16)]),
}


def _extrude(mb, prof, half_w, mat, side_mat=None, top_mats=None):
    """옆모습(x, z)을 좌우로 밀어서 덩어리를 만든다. +x가 차 앞."""
    n = len(prof)
    for i in range(n):
        (x0, z0), (x1, z1) = prof[i], prof[(i + 1) % n]
        m = top_mats[i] if top_mats else mat
        mb.add([(x0, half_w, z0), (x1, half_w, z1), (x1, -half_w, z1), (x0, -half_w, z0)],
               [(0, 0), (1, 0), (1, 1), (0, 1)], m)
    sm = side_mat or mat
    mb.add([(x, -half_w, z) for x, z in prof], [(x, z) for x, z in prof], sm)
    mb.add([(x, half_w, z) for x, z in reversed(prof)], [(x, z) for x, z in reversed(prof)], sm)


def _wheel(mb, x, y, r, w, tire, hub):
    n = 10
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        p0 = (x + math.cos(a0) * r, r + math.sin(a0) * r)
        p1 = (x + math.cos(a1) * r, r + math.sin(a1) * r)
        mb.add([(p0[0], y - w / 2, p0[1]), (p0[0], y + w / 2, p0[1]), (p1[0], y + w / 2, p1[1]), (p1[0], y - w / 2, p1[1])],
               [(0, 0), (1, 0), (1, 1), (0, 1)], tire)
    for sgn in (-1, 1):
        ring = [(x + math.cos(2 * math.pi * i / n) * r, y + sgn * w / 2, r + math.sin(2 * math.pi * i / n) * r) for i in range(n)]
        hubr = [(x + math.cos(2 * math.pi * i / n) * r * 0.6, y + sgn * (w / 2 + 0.005), r + math.sin(2 * math.pi * i / n) * r * 0.6) for i in range(n)]
        if sgn > 0:
            ring.reverse()
            hubr.reverse()
        mb.add(ring, [(0, 0)] * n, tire)
        mb.add(hubr, [(0, 0)] * n, hub)


def make_car(kind, paint, Mc, tag):
    t = CAR_TYPES[kind]
    mb = MeshBuilder()
    hw = t["w"] / 2
    _extrude(mb, t["body"], hw, paint)
    cab = t["cabin"]
    _extrude(mb, cab, hw - 0.1, Mc["glass"], side_mat=Mc["glass"], top_mats=[Mc["glass"], paint, Mc["glass"], paint])
    for wx in t["wheel_x"]:
        for sgn in (-1, 1):
            _wheel(mb, wx, sgn * (hw - 0.1), t["wr"], 0.22, Mc["tire"], Mc["hub"])
    xf = max(x for x, z in t["body"])
    xr = min(x for x, z in t["body"])
    zl = 0.66 if kind != "suv" else 0.84
    for sgn in (-1, 1):
        y = sgn * (hw - 0.32)
        mb.add([(xf + 0.005, y - 0.2, zl - 0.07), (xf + 0.005, y + 0.2, zl - 0.07), (xf - 0.05, y + 0.2, zl + 0.07), (xf - 0.05, y - 0.2, zl + 0.07)],
               [(0, 0), (1, 0), (1, 1), (0, 1)], Mc["lamp"])
        if kind != "truck":
            mb.add([(xr - 0.005, y + 0.2, zl + 0.02), (xr - 0.005, y - 0.2, zl + 0.02), (xr + 0.03, y - 0.2, zl + 0.16), (xr + 0.03, y + 0.2, zl + 0.16)],
                   [(0, 0), (1, 0), (1, 1), (0, 1)], Mc["tail"])
    if kind == "truck":     # 1톤 트럭 적재함
        bed = Mc["bed"]
        mb.box(Vector((-0.8, 0)), Vector((1, 0)), 3.4, 1.66, 0.72, 0.82, bed, bed, bottom=True)
        for (cx, sx, sy) in ((-0.8, 3.4, 0.05),):
            for sgn in (-1, 1):
                mb.box(Vector((cx, sgn * 0.82)), Vector((1, 0)), sx, sy, 0.82, 1.2, bed, bed)
        mb.box(Vector((-2.48, 0)), Vector((1, 0)), 0.05, 1.66, 0.82, 1.2, bed, bed)
        if tag % 2 == 0:    # 탑차
            mb.box(Vector((-0.8, 0)), Vector((1, 0)), 3.36, 1.7, 0.82, 2.35, Mc["box"], Mc["box"])
        mb.box(Vector((-0.6, 0)), Vector((1, 0)), 3.0, 0.9, 0.42, 0.72, Mc["tire"], Mc["tire"], bottom=True)
        for sgn in (-1, 1):
            mb.add([(xr - 0.12, sgn * 0.6 + 0.12, 0.62), (xr - 0.12, sgn * 0.6 - 0.12, 0.62), (xr - 0.12, sgn * 0.6 - 0.12, 0.74), (xr - 0.12, sgn * 0.6 + 0.12, 0.74)],
                   [(0, 0), (1, 0), (1, 1), (0, 1)], Mc["tail"])
    return mb.build(f"car_{kind}_{tag}")


def car_meshes():
    Mc = dict(glass=mat_col("Car_Glass", (26, 32, 38), 0.06), tire=mat_col("Car_Tire", (24, 24, 26), 0.9),
              hub=mat_col("Car_Hub", (170, 172, 176), 0.3, 0.9), lamp=mat_col("Car_Lamp", (236, 238, 240), 0.1),
              tail=mat_col("Car_Tail", (170, 20, 24), 0.2), bed=mat_col("Truck_Bed", (40, 60, 120), 0.6),
              box=mat_col("Truck_Box", (224, 226, 228), 0.6))
    paints = [((238, 238, 236), 5), ((190, 192, 196), 3), ((110, 114, 120), 3), ((26, 28, 32), 3),
              ((34, 48, 92), 1), ((150, 26, 30), 1), ((196, 188, 170), 1)]
    out = []
    i = 0
    for kind, wk in (("sedan", 5), ("suv", 5), ("hatch", 2), ("truck", 1)):
        for rgb, wp in paints:
            if kind == "truck" and rgb not in ((238, 238, 236), (34, 48, 92)):
                continue
            paint = mat_col(f"Car_Paint_{rgb[0]}_{rgb[1]}_{rgb[2]}", rgb, 0.28, 0.35)
            out.append((make_car(kind, paint, Mc, i), wk * wp))
            i += 1
    return out


# ------------------------------------------------------------------ 본체
def build(infos, stalls, cols):
    M = dict(
        bark=mat_tex("Bark", "bark"), bark_pine=mat_tex("Bark_Pine", "bark_pine"),
        pine=mat_tex("Foliage_Pine", "fol_pine", alpha=True, rough=0.8),
        pine2=mat_tex("Foliage_Pine2", "fol_pine2", alpha=True, rough=0.8),
        leaf=mat_tex("Foliage_Leaf", "fol_leaf", alpha=True, rough=0.7),
        leaf2=mat_tex("Foliage_Leaf2", "fol_leaf2", alpha=True, rough=0.7),
        meta=mat_tex("Foliage_Meta", "fol_meta", alpha=True, rough=0.8),
        hedge=mat_tex("Hedge", "hedge"), brick=mat_tex("Brick", "brick"),
        tile_blue=mat_tex("RoofTile_Blue", "rooftile_blue"), tile_dark=mat_tex("RoofTile_Dark", "rooftile_dark"),
        booth=mat_tex("Booth", "booth"), concrete=mat_tex("Concrete", "concrete"),
        stone=mat_tex("StoneBlock", "stoneblock"), grass=mat_tex("Grass", "grass"),
        dark=mat_col("Dark_Metal", (44, 46, 50), 0.5, 0.6), steel=mat_col("Steel", (150, 154, 160), 0.4, 0.9),
        white=mat_col("Paint_White", (228, 230, 232), 0.8), wood=mat_col("Wood", (132, 92, 60), 0.8),
        globe=mat_col("Lamp_Globe", (250, 248, 236), 0.3, emission=0.6),
        shelter=mat_col("Shelter_Roof", (52, 56, 70), 0.25),
        bin_gray=mat_col("Bin_Gray", (110, 114, 118), 0.6), bin_green=mat_col("Bin_Green", (40, 110, 80), 0.6),
        bin_blue=mat_col("Bin_Blue", (40, 80, 150), 0.6),
        cone=mat_col("Cone_Orange", (236, 96, 30), 0.6), pot=mat_col("Pot_White", (224, 222, 214), 0.6),
        sand=mat_col("Sand", (206, 186, 150), 0.95), red=mat_col("Play_Red", (220, 60, 50), 0.5),
        yellow=mat_col("Play_Yellow", (246, 196, 40), 0.5), blue=mat_col("Play_Blue", (40, 110, 210), 0.5),
        rubber=mat_col("Play_Rubber", (150, 70, 60), 0.9),
    )
    plates = {str(no): mat_tex(f"Plate_{no}", f"plate_{no}", rough=0.5) for no in range(101, 110)}
    boundary = [P(*q) for q in __import__("site_build").BOUNDARY]
    mb = MeshBuilder()
    X = Vector((1, 0))

    # ---- 경비실 (동마다 하나, 파란 기와지붕)
    def booth(c, u, plate):
        q = rect_pts(c, u, 2.6, 2.4)
        n = perp(u)
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            N = ((a + b) / 2 - c).normalized()
            mb.wall(a, b, 0, 2.4, N, M["booth"], 6.0, 2.4, u0=0.5 if i == 0 else 0.0, fit_u=0.5)
        mb.flat(q, 2.4, M["white"])
        mb.hip_roof(c, u, 2.6, 2.4, 2.4, 0.95, M["tile_blue"], over=0.55)
        pc = c - n * 1.76
        mb.quad3([v3(pc - u * 0.5, 2.05), v3(pc + u * 0.5, 2.05), v3(pc + u * 0.5, 2.38), v3(pc - u * 0.5, 2.38)], plate)
        lib.block(rect_pts(c, u, 4.2, 4.0))

    for info in infos:
        k = len(info["pieces"]) // 2
        pc = info["pieces"][k]
        c, u, n, D = info["c"], info["u"], info["n"], info["D"]
        am = (pc["a0"] + pc["a1"]) / 2
        bc = c + u * (am + 4.6) + n * (-D / 2 + pc["o"] - 2.5)
        booth(bc, -u if True else u, plates[info["no"]])
    bgc = (P(443, 412) + P(461, 431)) / 2      # 후문 경비실
    booth(bgc + Vector((-7.5, -5.5)), Vector((0.73, -0.68)), plates["104"])

    # ---- 분리수거장 (벽돌 + 적갈색 지붕)과 수거함
    def hut(c, u):
        mb.box(c, u, 5.6, 3.4, 0, 2.5, M["brick"], M["concrete"], tw=1.26, th=1.26)
        mb.hip_roof(c, u, 5.6, 3.4, 2.5, 1.1, M["tile_dark"], over=0.5)
        n = perp(u)
        for i, m in enumerate((M["bin_gray"], M["bin_gray"], M["bin_green"], M["bin_blue"])):
            p = c + n * 2.8 + u * (i * 1.5 - 2.2)
            mb.box(p, u, 1.25, 0.95, 0.12, 1.15, m, m, bottom=True)
            mb.box(p, u, 1.3, 1.0, 1.15, 1.22, M["dark"], M["dark"])
        lib.block(rect_pts(c, u, 8.0, 8.0))

    hut(lib.geo(128.4922046, 35.8025299) + Vector((13.0, -6.5)), Vector((0.9, -0.43)))
    hut(P(150, 478), X)

    # ---- 자전거 보관대 (남쪽 담장 안쪽)
    def shelter(c, u):
        n = perp(u)
        L, D_ = 6.0, 2.0
        for sgn in (-1, 1):
            mb.box(c + u * sgn * (L / 2 - 0.1) - n * 0.8, u, 0.08, 0.08, 0, 1.9, M["dark"], M["dark"])
        prev = None
        for i in range(7):
            a = math.radians(i * 15)
            p = (-0.9 + math.sin(a) * D_, 1.9 + (1 - math.cos(a)) * -1.3 + 0.2)
            if prev:
                a0 = c + n * prev[0]
                a1 = c + n * p[0]
                mb.quad3([v3(a0 - u * L / 2, prev[1]), v3(a0 + u * L / 2, prev[1]), v3(a1 + u * L / 2, p[1]), v3(a1 - u * L / 2, p[1])], M["shelter"])
                mb.quad3([v3(a0 + u * L / 2, prev[1]), v3(a0 - u * L / 2, prev[1]), v3(a1 - u * L / 2, p[1]), v3(a1 + u * L / 2, p[1])], M["shelter"])
            prev = p
        for k in range(8):       # 자전거 거치대
            bp = c + u * (-L / 2 + 0.5 + k * 0.7)
            mb.box(bp, n, 0.9, 0.04, 0, 0.75, M["steel"], M["steel"])
        lib.block(rect_pts(c, u, L + 0.6, 3.0))

    for x in (286, 300, 420, 434, 500):
        shelter(P(x, 583.2), X)

    # ---- 정자 (가운데 정원) + 정원 화단
    pc = P(203, 356)
    mb.box(pc, X, 20, 15, 0, 0.3, M["stone"], M["grass"], tw=1.2, th=0.8)
    mb.box(pc, X, 6.2, 6.2, 0.3, 0.75, M["wood"], M["wood"])
    hexa = [pc + Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)))) * 2.7 for i in range(6)]
    for q in hexa:
        mb.cyl(q, 0.13, 0.75, 3.2, M["wood"], n=6)
    hexo = [pc + (q - pc) * 1.45 for q in hexa]
    for i in range(6):
        mb.add([v3(hexo[i], 3.1), v3(hexo[(i + 1) % 6], 3.1), v3(pc, 4.9)], [(0, 0), (3, 0), (1.5, 3)], M["tile_blue"])
    mb.flat(hexo, 3.1, M["wood"], down=True)
    garden = rect_pts(pc, X, 20, 15)
    lib.block(rect_pts(pc, X, 20.6, 15.6))
    for sgn in (-1, 1):       # 벤치
        bp = pc + Vector((sgn * 6.5, -4))
        mb.box(bp, X, 1.8, 0.45, 0.62, 0.7, M["wood"], M["wood"], bottom=True)
        mb.box(bp + Vector((0, 0.25)), X, 1.8, 0.06, 0.7, 1.15, M["wood"], M["wood"])
        for s2 in (-0.75, 0.75):
            mb.box(bp + Vector((s2, 0)), X, 0.08, 0.4, 0.3, 0.62, M["dark"], M["dark"])

    # ---- 놀이터 (북쪽)
    gc, gu = P(199, 236), Vector((0.995, 0.083))
    gn = perp(gu)
    mb.box(gc, gu, 18, 9, 0, 0.1, M["concrete"], M["rubber"])
    sp = gc - gu * 5
    mb.box(sp, gu, 2.0, 2.0, 1.5, 1.62, M["yellow"], M["yellow"], bottom=True)
    for dx in (-0.9, 0.9):
        for dy in (-0.9, 0.9):
            mb.cyl(sp + gu * dx + gn * dy, 0.06, 0.1, 3.0, M["blue"], n=6)
    mb.hip_roof(sp, gu, 2.0, 2.0, 3.0, 0.8, M["red"], over=0.25)
    s0, s1 = sp + gu * 1.0, sp + gu * 4.2
    w = gn * 0.45
    mb.quad3([v3(s0 - w, 1.6), v3(s0 + w, 1.6), v3(s1 + w, 0.2), v3(s1 - w, 0.2)], M["yellow"])
    mb.quad3([v3(s0 + w, 1.6), v3(s0 - w, 1.6), v3(s1 - w, 0.2), v3(s1 + w, 0.2)], M["yellow"])
    sc_ = gc + gu * 4.5
    for dx in (-2.0, 2.0):
        mb.tube(v3(sc_ + gu * dx - gn * 0.8, 0.1), v3(sc_ + gu * dx, 2.6), 0.05, M["blue"])
        mb.tube(v3(sc_ + gu * dx + gn * 0.8, 0.1), v3(sc_ + gu * dx, 2.6), 0.05, M["blue"])
    mb.tube(v3(sc_ - gu * 2.0, 2.6), v3(sc_ + gu * 2.0, 2.6), 0.05, M["blue"])
    for dx in (-0.9, 0.9):
        mb.box(sc_ + gu * dx, gu, 0.5, 0.22, 0.55, 0.6, M["red"], M["red"], bottom=True)
        for ex in (-0.22, 0.22):
            mb.tube(v3(sc_ + gu * (dx + ex), 0.6), v3(sc_ + gu * (dx + ex), 2.6), 0.012, M["steel"], n=4)
    lib.block(rect_pts(gc, gu, 20, 11))

    # ---- 가로등: 담장 안쪽 둥근 등, 주차장 높은 등
    def globe_lamp(p):
        mb.cyl(p, 0.07, 0, 3.4, M["dark"], n=6, r1=0.05)
        mb.ball(p, 3.62, 0.27, M["globe"])

    def tall_lamp(p, d):
        mb.cyl(p, 0.09, 0, 7.5, M["steel"], n=6, r1=0.06)
        e = p + d * 1.6
        mb.tube((p.x, p.y, 7.4), (e.x, e.y, 7.7), 0.04, M["steel"])
        mb.box(e, d, 0.7, 0.28, 7.6, 7.72, M["dark"], M["globe"], bottom=True)

    for x in range(270, 520, 42):
        globe_lamp(P(x, 585.6))
    for p, d in ((P(330, 420), Vector((0.76, -0.65))), (P(290, 470), Vector((1, 0))), (P(380, 470), Vector((-1, 0))),
                 (P(170, 420), Vector((1, 0))), (P(200, 300), Vector((0, -1))), (P(120, 500), Vector((1, 0))),
                 (P(420, 500), Vector((0, 1))), (P(260, 380), Vector((1, 0)))):
        if lib.is_free(p):
            tall_lamp(p, d)
    # 하천길 가로등
    ne0, ne1 = P(250, 215), P(522, 470)
    une = (ne1 - ne0).normalized()
    nne = perp(une)
    if nne.dot(Vector((1, 1))) < 0:
        nne = -nne
    for k in range(-5, 14):
        tall_lamp(ne0 + une * (k * 32) + nne * 9.2, -nne)

    # ---- 화분 (문 옆), 고깔
    shrub = make_shrub(M)

    def pot(p):
        mb.cyl(p, 0.22, 0, 0.25, M["pot"], n=8, r1=0.16)
        mb.cyl(p, 0.16, 0.25, 0.5, M["pot"], n=8, r1=0.42)
        instance(shrub, cols["Props"], "PotShrub", p, z=0.45, scale=0.95)

    lot_e = lib.geo(128.4922046, 35.8025299)
    for i in range(5):
        pot(lot_e + Vector((2.5 + i * 1.6, -4.5 + i * 0.3)))
    for g0, g1 in ((P(222, 588), P(254, 588)), (P(443, 412), P(461, 431))):
        d = (g1 - g0).normalized()
        nn = perp(d)
        if not point_in_poly((g0 + g1) / 2 + nn * 3, boundary):
            nn = -nn
        for q in (g0 + d * 1.2 + nn * 1.5, g1 - d * 1.2 + nn * 1.5):
            pot(q)
        for q in (g0 + d * 3.0 + nn * 4, g1 - d * 3.0 + nn * 4):
            mb.cyl(q, 0.18, 0, 0.04, M["cone"], n=6)
            mb.cyl(q, 0.13, 0.04, 0.7, M["cone"], n=8, r1=0.03)

    mb.build("Props", cols["Props"])

    # ---- 자동차
    cars = car_meshes()
    meshes, weights = [c[0] for c in cars], [c[1] for c in cars]
    ncar = 0
    for p, facing in stalls:
        if rng.random() < 0.8:
            me = rng.choices(meshes, weights)[0]
            ang = math.atan2(facing.y, facing.x) + (math.pi if rng.random() < 0.3 else 0) + rng.uniform(-0.04, 0.04)
            off = facing.normalized() * rng.uniform(-0.25, 0.25)
            instance(me, cols["Cars"], f"Car_{ncar:03d}", p + off, ang)
            ncar += 1
    for p, ang in ((P(238, 640), math.pi / 2), (P(330, 599.5), 0.0), (P(120, 596.5), math.pi), (ne0 + une * 70 + nne * 3.4, math.atan2(une.y, une.x)),
                   (ne0 + une * 20 + nne * 6.6, math.atan2(-une.y, -une.x))):
        instance(rng.choices(meshes, weights)[0], cols["Cars"], f"Car_{ncar:03d}", p, ang)
        ncar += 1

    # ---- 나무
    pines = [make_pine(s, M) for s in (1, 2, 3, 4)]
    leafs = [make_broadleaf(s, M) for s in (11, 12, 13)]
    metas = [make_meta(s, M) for s in (21, 22)]
    nt = 0

    def tree(p, kinds, smin=0.85, smax=1.15, z=0.0):
        nonlocal nt
        instance(rng.choice(kinds), cols["Trees"], f"Tree_{nt:03d}", p, rng.uniform(0, 6.28), rng.uniform(smin, smax), z=z)
        nt += 1

    for info in infos:                          # 동 앞 화단
        for gc_, u, L, w in info["beds"]:
            k = max(1, int(L / 6.0))
            for i in range(k):
                p = gc_ + u * (-L / 2 + (i + 0.5) * L / k + rng.uniform(-1, 1)) + perp(u) * rng.uniform(-0.8, 0.8)
                tree(p, pines if rng.random() < 0.6 else leafs, 0.8, 1.1)
            for i in range(int(L / 3.0)):       # 둥근 관목
                p = gc_ + u * (-L / 2 + rng.uniform(0, L)) + perp(u) * rng.uniform(-1.6, 0.6)
                instance(shrub, cols["Trees"], f"Shrub_{nt:03d}", p, rng.uniform(0, 6), rng.uniform(0.8, 1.5), z=0.18)
                nt += 1
    for q in garden:                             # 정자 주변
        tree(pc + (q - pc) * 0.8, pines, 0.9, 1.2)
    tree(pc + Vector((0, 6.0)), pines)
    tree(pc + Vector((-8, 0.5)), leafs)
    for c_, h_ in lib.PLANTERS:                   # 주차장 끝 화단
        tree(c_, pines, 0.7, 0.95, z=h_)
    for i in range(len(boundary)):               # 담장 안쪽
        p0, p1 = boundary[i], boundary[(i + 1) % len(boundary)]
        d = p1 - p0
        uu = d.normalized()
        inward = perp(uu)
        if not point_in_poly((p0 + p1) / 2 + inward * 2, boundary):
            inward = -inward
        k = int(d.length / 8.0)
        for j in range(1, k):
            p = p0 + d * (j / k) + inward * rng.uniform(3.0, 4.2)
            if lib.is_free(p, 1.2):
                tree(p, pines if rng.random() < 0.45 else leafs)
    for j in range(-22, 50):                     # 하천변 메타세쿼이아
        for off in (13.0, 56.0):
            tree(ne0 + une * (j * 7.5 + rng.uniform(-0.5, 0.5)) + nne * off, metas, 0.85, 1.15)
    for j in range(-10, 30):                     # 둔치 잡목
        if rng.random() < 0.5:
            p = ne0 + une * (j * 11 + rng.uniform(-3, 3)) + nne * rng.choice([18.5, 24.5, 45.0, 51.0])
            instance(rng.choice(leafs), cols["Trees"], f"Tree_{nt:03d}", p, rng.uniform(0, 6), rng.uniform(0.5, 0.8), z=-2.4)
            nt += 1
    return ncar, nt
