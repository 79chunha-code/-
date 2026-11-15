"""단지 바닥, 도로, 주차장, 담장, 정문, 상가, 하천, 주변 건물."""
import math
import random

from mathutils import Vector

import lib
from lib import P, MeshBuilder, mat_col, mat_tex, perp, point_in_poly, rect_pts, v3

rng = random.Random(501)

BOUNDARY = [(50, 588), (48, 450), (105, 300), (150, 215), (215, 200), (250, 215),
            (470, 440), (522, 470), (522, 588)]
# 담장이 끊기는 곳 (지도 픽셀): 정문, 후문, 북쪽 쪽문
GATES = [((222, 588), (254, 588)), ((443, 412), (461, 431)), ((176, 208), (192, 204))]
SANGGA = dict(c=(167, 577.5), sx=47.0, sy=10.5)   # 정문 옆 상가


def mats():
    return dict(
        asphalt=mat_tex("Asphalt", "asphalt", normal=0.6),
        dirt=mat_tex("Dirt", "dirt"),
        concrete=mat_tex("Concrete", "concrete"),
        curb=mat_tex("Curb", "curb"),
        grass=mat_tex("Grass", "grass"),
        hedge=mat_tex("Hedge", "hedge"),
        paver_red=mat_tex("Paver_Red", "paver_red"),
        paver_gray=mat_tex("Paver_Gray", "paver_gray"),
        brick=mat_tex("Brick", "brick"),
        lattice=mat_tex("Brick_Lattice", "brick_lattice"),
        rock=mat_tex("Rock", "rock"),
        stone=mat_tex("StoneBlock", "stoneblock"),
        bump=mat_tex("SpeedBump", "speedbump", normal=0),
        line=mat_col("Paint_Line_White", (232, 232, 226), 0.7),
        yellow=mat_col("Paint_Line_Yellow", (232, 186, 44), 0.7),
        water=mat_col("Water", (52, 74, 66), 0.05),
        path=mat_col("Path_Clay", (188, 150, 120), 0.95),
        steel=mat_col("Steel", (150, 154, 160), 0.4, 0.9),
        rail=mat_col("Rail_Paint", (120, 128, 140), 0.5, 0.6),
        dark=mat_col("Dark_Metal", (44, 46, 50), 0.5, 0.6),
        white=mat_col("Paint_White", (228, 230, 232), 0.8),
        shop_gf=mat_tex("Shop_Ground", "shop_gf"),
        shop_up=mat_tex("Shop_Upper", "shop_up"),
        warehouse=mat_tex("Warehouse", "warehouse"),
        stucco=mat_tex("Stucco", "stucco_white"),
        tower=mat_tex("Tower", "tower", normal=0),
        metal_blue=mat_tex("Metal_Blue", "metal_blue"),
        metal_gray=mat_tex("Metal_Gray", "metal_gray"),
        tile_dark=mat_tex("RoofTile_Dark", "rooftile_dark"),
        glass=mat_col("Glass_Dark", (40, 52, 60), 0.08),
        globe=mat_col("Lamp_Globe", (250, 248, 236), 0.3, emission=0.6),
        txt_slow=mat_tex("Text_Slow", "txt_slow", alpha=True, rough=0.7),
        pole=mat_col("Concrete_Pole", (150, 148, 142), 0.9),
        wire=mat_col("Wire", (26, 26, 28), 0.6),
    )


# ------------------------------------------------------------------ 주차
def parking_row(mb, M, c, u, L, facing, stalls):
    n = facing.normalized()
    k = int(L // 2.5)
    start = c - u * (k * 2.5 / 2)
    for i in range(k + 1):
        p = start + u * (i * 2.5)
        mb.flat(rect_pts(p, n, 5.0, 0.12), 0.015, M["line"])
        if i < k:
            stalls.append((p + u * 1.25, n))
    lib.block(rect_pts(c, u, k * 2.5 + 0.4, 5.2))
    return k * 2.5


def speed_bump(mb, M, c, u, width):
    """u: 차가 지나가는 방향. 폭 width 만큼 가로지른다."""
    n = perp(u)
    q = rect_pts(c, n, width, 1.8)
    qi = rect_pts(c, n, width, 0.8)
    L = width / 3.6
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        ai, bi = qi[i], qi[(i + 1) % 4]
        mb.add([v3(a, 0.0), v3(b, 0.0), v3(bi, 0.075), v3(ai, 0.075)],
               [(0, 0), (L, 0), (L, 0.4), (0, 0.4)] if i % 2 == 0 else [(0, 0), (0, 0.4), (L, 0.4), (L, 0)], M["bump"])
    mb.add([v3(p, 0.075) for p in qi], [(0, 0.3), (L, 0.3), (L, 0.7), (0, 0.7)], M["bump"])


def road_text(mb, mat, c, facing, w=3.4, h=1.7):
    """바닥 글씨. facing: 글자를 읽는 사람이 바라보는 방향."""
    f = facing.normalized()
    r = Vector((f.y, -f.x))
    p = [c - r * w / 2 - f * h / 2, c + r * w / 2 - f * h / 2, c + r * w / 2 + f * h / 2, c - r * w / 2 + f * h / 2]
    mb.add([v3(q, 0.02) for q in p], [(0, 0), (1, 0), (1, 1), (0, 1)], mat)


def planter(mb, M, c, u, sx, sy, h=0.45, hedge_h=0.7, side=None):
    """돌로 두른 화단 + 위에 낮은 생울타리."""
    mb.box(c, u, sx, sy, 0, h, side or M["stone"], M["grass"], tw=1.2, th=0.8)
    if hedge_h:
        mb.box(c, u, sx - 0.5, sy - 0.5, h, h + hedge_h, M["hedge"], M["hedge"], tw=2.0, th=2.0)
    lib.block(rect_pts(c, u, sx + 0.4, sy + 0.4))
    lib.PLANTERS.append((c, h))


# ------------------------------------------------------------------ 본체
def build(infos, cols):
    M = mats()
    stalls = []
    poly = [P(*q) for q in BOUNDARY]
    g = MeshBuilder()          # 바닥
    s = MeshBuilder()          # 구조물 (담장, 정문, 상가)

    # ---- 땅
    G = 1600
    g.flat([Vector((-G, -G)), Vector((G, -G)), Vector((G, G)), Vector((-G, G))], -0.04, M["dirt"], tile=6.0)
    g.flat(poly, 0.0, M["asphalt"], tile=6.0)

    # ---- 도로
    def road(p0, p1, w, center=None, edge=True, z=-0.01):
        u = (p1 - p0).normalized()
        L = (p1 - p0).length
        c = (p0 + p1) / 2
        g.flat(rect_pts(c, u, L, w), z, M["asphalt"], tile=6.0)
        if center == "dash":
            for i in range(int(L // 6)):
                g.flat(rect_pts(p0 + u * (i * 6 + 1.5), u, 3.0, 0.14), z + 0.012, M["yellow"])
        elif center == "solid":
            g.flat(rect_pts(c, u, L, 0.14), z + 0.012, M["yellow"])
        if edge:
            n = perp(u)
            for sgn in (-1, 1):
                g.flat(rect_pts(c + n * sgn * (w / 2 - 0.25), u, L, 0.12), z + 0.012, M["line"])

    road(P(-260, 598), P(900, 598), 7.0, None)                    # 성화로4길 (남쪽 골목)
    road(P(32, 760), P(38, 450), 6.5, None, edge=False)           # 서쪽 길
    road(P(38, 450), P(140, 172), 6.5, None, edge=False)
    road(P(237, 588), P(237, 760), 7.0, "dash")                   # 정문 앞 길 (성화로2길 쪽)

    ne0, ne1 = P(250, 215), P(522, 470)
    une = (ne1 - ne0).normalized()
    nne = perp(une)
    if nne.dot(Vector((1, 1))) < 0:
        nne = -nne
    r0 = ne0 - une * 220
    r1 = ne1 + une * 320
    Lr = (r1 - r0).length
    cm = (r0 + r1) / 2
    road(r0 + nne * 5.0, r1 + nne * 5.0, 7.0, "solid")            # 비슬로497길
    # 하천 쪽 보도 (붉은 블록)와 난간
    g.box(cm + nne * 10.0, une, Lr, 2.6, -0.02, 0.13, M["curb"], M["paver_red"], tw=3.0, th=3.0)
    rail_c = cm + nne * 11.45
    for k in range(int(Lr // 2.5)):
        p = r0 + nne * 11.45 + une * (k * 2.5)
        s.box(p, une, 0.08, 0.08, 0.13, 1.25, M["rail"], M["rail"])
    for zz in (0.55, 0.9, 1.22):
        s.box(rail_c, une, Lr, 0.05, zz, zz + 0.05, M["rail"], M["rail"], bottom=True)
    # 둑 비탈, 둔치, 물
    zf, zw = -2.4, -3.0

    def strip_slope(o0, z0, o1, z1, mat, tile=5.0):
        a0, a1 = r0 + nne * o0, r1 + nne * o0
        b0, b1 = r0 + nne * o1, r1 + nne * o1
        g.add([v3(a0, z0), v3(a1, z0), v3(b1, z1), v3(b0, z1)],
              [(0, 0), (Lr / tile, 0), (Lr / tile, abs(o1 - o0) / tile), (0, abs(o1 - o0) / tile)], mat)

    strip_slope(11.6, 0.0, 17.0, zf, M["grass"])
    strip_slope(17.0, zf, 20.0, zf, M["grass"])
    strip_slope(20.0, zf + 0.02, 22.5, zf + 0.02, M["path"])
    strip_slope(22.5, zf, 27.0, zf, M["grass"])
    strip_slope(27.0, zf, 28.5, zw, M["grass"])
    strip_slope(28.5, zw, 41.5, zw, M["water"])
    strip_slope(41.5, zw, 43.0, zf, M["grass"])
    strip_slope(43.0, zf, 47.0, zf, M["grass"])
    strip_slope(47.0, zf + 0.02, 49.5, zf + 0.02, M["path"])
    strip_slope(49.5, zf, 52.0, zf, M["grass"])
    strip_slope(52.0, zf, 57.5, 0.0, M["grass"])
    strip_slope(57.5, 0.02, 60.5, 0.02, M["paver_red"], tile=1.6)
    road(r0 + nne * 64.5, r1 + nne * 64.5, 7.0, "solid")          # 건너편 길
    lib.block([r0 - nne * 0.5, r1 - nne * 0.5, r1 + nne * 70, r0 + nne * 70])
    # 보행교
    bc = (ne0 + ne1) / 2 + une * 34
    s.box(bc + nne * 35, nne, 46.5, 2.6, -0.25, 0.1, M["concrete"], M["paver_gray"], bottom=True)
    for sgn in (-1, 1):
        for zz in (0.6, 1.1):
            s.box(bc + nne * 35 + une * sgn * 1.25, nne, 46.5, 0.05, zz, zz + 0.05, M["rail"], M["rail"], bottom=True)

    # ---- 동별: 화단(앞), 보도(뒤), 주차(뒤)
    for info in infos:
        c, u, n, D = info["c"], info["u"], info["n"], info["D"]
        for pc in info["pieces"]:
            a0, a1, o = pc["a0"], pc["a1"], pc["o"]
            am, al = (a0 + a1) / 2, (a1 - a0)
            gc = c + u * am + n * (D / 2 + o + 3.3)
            g.box(gc, u, al + 0.6, 5.2, 0, 0.18, M["curb"], M["grass"], tw=3.0, th=3.0)
            hc = c + u * am + n * (D / 2 + o + 5.4)
            g.box(hc, u, al, 0.9, 0.18, 0.95, M["hedge"], M["hedge"], tw=2.0, th=2.0)
            lib.block(rect_pts(gc, u, al + 0.6, 5.4))
            info["beds"].append((gc, u, al, 3.2))
            sc_ = c + u * am + n * (-D / 2 + o - 2.4)
            g.box(sc_, u, al, 2.6, 0, 0.1, M["curb"], M["paver_gray"], tw=3.0, th=3.0)
        if info["back_parking"]:
            o0 = info["pieces"][0]["o"]
            row_c = c + n * (-D / 2 + o0 - 4.4 - 2.6)
            parking_row(g, M, row_c, u, info["L"] - 6.0, -n, stalls)

    # ---- 중앙 주차장: 105동과 나란한 양면 주차 3줄 + 양끝 화단
    a105, b105 = P(322, 340), P(437, 437)
    u105 = (b105 - a105).normalized()
    sw = Vector((-0.645, -0.764))
    c105 = (a105 + b105) / 2
    for d, Lrow, shift in ((23, 42, 0), (38, 46, -2), (53, 34, -6)):
        rc = c105 + sw * d + u105 * shift
        used = parking_row(g, M, rc + sw * 2.5, u105, Lrow, sw, stalls)
        parking_row(g, M, rc - sw * 2.5, u105, Lrow, -sw, stalls)
        g.flat(rect_pts(rc, u105, used, 0.12), 0.015, M["line"])
        for sgn in (-1, 1):
            planter(g, M, rc + u105 * sgn * (used / 2 + 1.6), u105, 2.6, 10.0)
    # 차로 가운데 노란 선, 바닥 글씨, 과속방지턱
    for d in (30.5, 45.5):
        lc = c105 + sw * d - u105 * 2
        g.flat(rect_pts(lc, u105, 40, 0.12), 0.015, M["yellow"])
    road_text(g, M["txt_slow"], c105 + sw * 30.5 + u105 * 24, -u105)
    road_text(g, M["txt_slow"], c105 + sw * 14 - u105 * 10, u105)
    speed_bump(g, M, c105 + sw * 12 + u105 * 30, u105, 6.5)
    speed_bump(g, M, c105 + sw * 12 - u105 * 22, u105, 6.5)

    # ---- 101동 앞(남쪽) 주차, 정문 진입로
    parking_row(g, M, P(356, 566), Vector((1, 0)), 76, Vector((0, -1)), stalls)
    gate_c = P(238, 588)
    speed_bump(g, M, gate_c + Vector((0, 3.0)), Vector((0, 1)), 13.0)
    g.flat(rect_pts(P(238, 560), Vector((0, 1)), 22, 0.14), 0.015, M["yellow"])
    road_text(g, M["txt_slow"], P(232, 548), Vector((0, 1)))
    speed_bump(g, M, P(238, 520), Vector((0, 1)), 9.0)
    # 후문
    bg0, bg1 = P(*GATES[1][0]), P(*GATES[1][1])
    bgc = (bg0 + bg1) / 2
    speed_bump(g, M, bgc - nne * 3.0, nne, (bg1 - bg0).length)
    for k in range(7):          # 횡단보도
        g.flat(rect_pts(bgc + nne * 5.0 + une * (k - 3) * 1.0, nne, 6.0, 0.5), 0.004, M["line"])

    # 문으로 드나드는 길에는 나무/가로등을 세우지 않는다
    lib.block(rect_pts(P(238, 540), Vector((0, 1)), 54, 14))
    lib.block(rect_pts(bgc - nne * 9, nne, 22, 14))

    # ---- 담장
    gates = [(P(*a), P(*b)) for a, b in GATES]
    sang = rect_pts(P(*SANGGA["c"]), Vector((1, 0)), SANGGA["sx"] + 1.0, SANGGA["sy"] + 3.0)

    def in_gate(p):
        for g0, g1 in gates:
            d = g1 - g0
            t = (p - g0).dot(d) / d.length_squared
            if -0.02 <= t <= 1.02 and ((g0 + d * t) - p).length < 1.2:
                return True
        return point_in_poly(p, sang)

    TILE = 1.26
    for i in range(len(poly)):
        p0, p1 = poly[i], poly[(i + 1) % len(poly)]
        d = p1 - p0
        uu = d.normalized()
        k = max(1, round(d.length / (TILE * 2)))
        seg = d.length / k
        inward = perp(uu)
        if not point_in_poly((p0 + p1) / 2 + inward * 1.0, poly):
            inward = -inward
        lat = i in (5, 6, 7, 8)           # 길가 쪽은 구멍 뚫린 벽돌담
        for j in range(k):
            a = p0 + uu * (j * seg)
            b = a + uu * seg
            mid = (a + b) / 2
            if in_gate(mid):
                continue
            s.box(mid, uu, seg, 0.2, 0, TILE, M["lattice"] if lat else M["brick"], M["brick"], tw=TILE, th=TILE)
            if j % 2 == 0:
                s.box(a, uu, 0.42, 0.42, 0, 1.45, M["brick"], M["concrete"], tw=TILE, th=TILE)
                s.box(a, uu, 0.52, 0.52, 1.45, 1.55, M["concrete"], M["concrete"], bottom=True)
            if not lat:
                g.box(mid + inward * 0.9, uu, seg, 1.0, 0, 1.0, M["hedge"], M["hedge"], tw=2.0, th=2.0)
        lib.block([p0 - inward * 0.5, p1 - inward * 0.5, p1 + inward * 1.6, p0 + inward * 1.6])

    # ---- 문기둥 (강돌) + 둥근 등
    def gate_pillar(p):
        s.box(p, Vector((1, 0)), 1.1, 1.1, 0, 2.3, M["rock"], M["concrete"], tw=1.6, th=1.6)
        s.box(p, Vector((1, 0)), 1.3, 1.3, 2.3, 2.45, M["concrete"], M["concrete"], bottom=True)
        s.cyl(p, 0.06, 2.45, 2.75, M["dark"], n=6)
        s.ball(p, 3.0, 0.27, M["globe"])
        lib.block(rect_pts(p, Vector((1, 0)), 2.0, 2.0))

    for g0, g1 in gates[:2]:
        gate_pillar(g0)
        gate_pillar(g1)

    # ---- 정문 경비실 (팔각, 벽돌 하단 + 유리 + 어두운 지붕), 깃대
    gh = P(262, 579)
    octo = [gh + Vector((math.cos(math.radians(22.5 + 45 * i)), math.sin(math.radians(22.5 + 45 * i)))) * 3.0
            for i in range(8)]
    s.prism(octo, 0, 1.0, M["brick"], M["concrete"], tw=TILE, th=TILE)
    octo2 = [gh + (q - gh) * 0.97 for q in octo]
    s.prism(octo2, 1.0, 2.5, M["glass"], M["concrete"])
    for q in octo:
        s.box(gh + (q - gh) * 0.98, Vector((1, 0)), 0.14, 0.14, 1.0, 2.5, M["dark"], M["dark"])
    octo3 = [gh + (q - gh) * 1.22 for q in octo]
    for i in range(8):
        a, b = octo3[i], octo3[(i + 1) % 8]
        s.add([v3(a, 2.5), v3(b, 2.5), v3(gh, 3.7)], [(0, 0), (2, 0), (1, 2)], M["tile_dark"])
    s.flat(octo3, 2.5, M["dark"], down=True)
    lib.block([gh + (q - gh) * 1.6 for q in octo])
    for i in range(3):
        fp = gh + Vector((-4.6, -1.0 + i * 1.3))
        s.cyl(fp, 0.05, 0, 9.0, M["steel"], n=6, r1=0.03)

    # ---- 상가 (3층)
    sc_ = P(*SANGGA["c"])
    q = rect_pts(sc_, Vector((1, 0)), SANGGA["sx"], SANGGA["sy"])
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        N = ((a + b) / 2 - sc_).normalized()
        long_side = (b - a).length > 20
        if long_side:
            s.wall(a, b, 0, 3.6, N, M["shop_gf"], 24.0, 3.6, u0=0.25 * (i % 2))
            s.wall(a, b, 3.6, 7.2, N, M["shop_up"], 24.0, 3.6, u0=0.5 * (i % 2))
            s.wall(a, b, 7.2, 10.8, N, M["shop_up"], 24.0, 3.6, u0=0.25 + 0.5 * (i % 2))
        else:
            s.wall(a, b, 0, 10.8, N, M["stucco"], 4.0, 4.0)
        s.wall(a, b, 10.8, 11.6, N, M["stucco"], 4.0, 4.0)
    s.flat(q, 11.5, M["concrete"])
    s.box(sc_ + Vector((8, 0)), Vector((1, 0)), 5, 4, 11.5, 14.2, M["stucco"], M["concrete"])
    lib.block(rect_pts(sc_, Vector((1, 0)), SANGGA["sx"] + 2, SANGGA["sy"] + 2))

    # ---- 남쪽 골목 전봇대와 전선
    poles = [P(x, 603.5) for x in range(-60, 700, 62)]
    for p in poles:
        s.cyl(p, 0.17, 0, 10.5, M["pole"], n=8, r1=0.12)
        s.box(p, Vector((0, 1)), 0.1, 2.2, 9.6, 9.72, M["dark"], M["dark"], bottom=True)
        s.box(p + Vector((0.25, 0)), Vector((1, 0)), 0.5, 0.5, 7.6, 8.5, M["steel"], M["steel"], bottom=True)
    for a, b in zip(poles, poles[1:]):
        for oy, zz in ((-0.9, 9.75), (0.0, 9.75), (0.9, 9.75), (0.0, 8.2)):
            m = (a + b) / 2
            s.tube((a.x, a.y + oy, zz), (m.x, m.y + oy, zz - 0.55), 0.018, M["wire"], n=4)
            s.tube((m.x, m.y + oy, zz - 0.55), (b.x, b.y + oy, zz), 0.018, M["wire"], n=4)

    g.build("Ground", cols["Ground"])
    s.build("Structures", cols["Props"])
    build_context(M, cols["Context"], r0, r1, une, nne)
    return stalls


# ------------------------------------------------------------------ 주변 건물
def build_context(M, col, r0, r1, une, nne):
    mb = MeshBuilder()

    def gable(c, u, sx, sy, h, roof, wall, rh=2.2):
        """박공지붕 창고/공장."""
        q = rect_pts(c, u, sx, sy)
        n = perp(u)
        mb.wall(q[0], q[1], 0, h, -n, wall, 12.0, 6.0, u0=rng.random())
        mb.wall(q[2], q[3], 0, h, n, wall, 12.0, 6.0, u0=rng.random())
        for (a, b, N) in ((q[1], q[2], u), (q[3], q[0], -u)):
            mb.wall(a, b, 0, h, N, wall, 12.0, 6.0, u0=rng.random())
            m = (a + b) / 2
            r = Vector((-N.y, N.x))
            if (b - a).dot(r) < 0:
                a, b = b, a
            mb.add([v3(a, h), v3(b, h), v3(m, h + rh)], [(0, 0), (1, 0), (0.5, 0.4)], wall)
        r0_, r1_ = c - u * (sx / 2 + 0.3), c + u * (sx / 2 + 0.3)
        for sgn in (-1, 1):
            e0, e1 = r0_ + n * sgn * (sy / 2 + 0.4), r1_ + n * sgn * (sy / 2 + 0.4)
            pts = [v3(e0, h - 0.1), v3(e1, h - 0.1), v3(r1_, h + rh), v3(r0_, h + rh)]
            if sgn > 0:
                pts = [pts[1], pts[0], pts[3], pts[2]]
            mb.add(pts, [(0, 0), (sx / 2, 0), (sx / 2, sy / 4), (0, sy / 4)], roof)

    def shopbox(c, u, sx, sy, floors):
        q = rect_pts(c, u, sx, sy)
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            N = ((a + b) / 2 - c).normalized()
            mb.wall(a, b, 0, 3.6, N, M["shop_gf"], 24.0, 3.6, u0=rng.randrange(4) / 4)
            if floors > 1:
                mb.wall(a, b, 3.6, 3.6 * floors, N, M["shop_up"], 24.0, 3.6, u0=rng.randrange(4) / 4)
            mb.wall(a, b, 3.6 * floors, 3.6 * floors + 0.7, N, M["stucco"], 4, 4)
        mb.flat(q, 3.6 * floors + 0.6, M["concrete"])

    def house(c, u, sx, sy):
        mb.box(c, u, sx, sy, 0, 5.6, M["stucco"], M["concrete"], tw=4, th=4)
        mb.hip_roof(c, u, sx, sy, 5.6, 1.8, M["tile_dark"], over=0.4)

    def fill(x0, y0, x1, y1, kinds, seed):
        """지도 픽셀 사각형 구역을 건물로 채운다."""
        r = random.Random(seed)
        y = y0
        while y < y1 - 14:
            row_h = r.uniform(26, 40)
            x = x0
            while x < x1 - 14:
                w = r.uniform(24, 46)
                if x + w > x1:
                    w = x1 - x
                c = P(x + w / 2, y + row_h / 2)
                sx, sy = (w - 4) * lib.S, (row_h - 5) * lib.S
                k = r.choice(kinds)
                if k == "gable":
                    gable(c, Vector((1, 0)) if sx >= sy else Vector((0, 1)), max(sx, sy), min(sx, sy),
                          r.uniform(5, 8), r.choice([M["metal_blue"], M["metal_blue"], M["metal_gray"]]), M["warehouse"])
                elif k == "shop":
                    shopbox(c, Vector((1, 0)), sx, sy, r.choice([2, 3, 3, 4]))
                else:
                    house(c, Vector((1, 0)), sx * 0.8, sy * 0.8)
                x += w
            y += row_h

    fill(-250, 606, 226, 800, ["gable", "gable", "shop", "house"], 1)     # 남쪽 블록 (서)
    fill(250, 606, 900, 800, ["gable", "gable", "gable", "shop"], 2)      # 남쪽 블록 (동)
    fill(-250, 150, 20, 590, ["gable", "house", "house", "shop"], 3)      # 서쪽
    fill(536, 480, 900, 590, ["shop", "gable", "house"], 4)               # 동쪽

    # 하천 건너: 사무동과 고층 아파트
    base = (r0 + r1) / 2
    oc = base + nne * 95 - une * 60
    mb.box(oc, une, 70, 24, 0, 17, M["tower"], M["concrete"], tw=12.0, th=11.2)

    def tower(c, u, sx, sy, floors):
        h = floors * 2.8
        q = rect_pts(c, u, sx, sy)
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            N = ((a + b) / 2 - c).normalized()
            mb.wall(a, b, 0, h, N, M["tower"], 12.0, 11.2)
        mb.flat(q, h, M["concrete"])
        mb.box(c, u, sx * 0.4, sy * 0.5, h, h + 4, M["stucco"], M["concrete"])

    for (da, dn, fl) in ((60, 150, 35), (110, 185, 38), (165, 150, 33), (215, 190, 36), (140, 250, 30)):
        tower(base + une * da + nne * dn, une, 34, 20, fl)
    for (da, dn, fl) in ((-150, 105, 15), (-195, 135, 13), (-110, 150, 15), (-250, 110, 18)):
        tower(base + une * da + nne * dn, perp(une), 44, 12, fl)
    mb.build("Context", col)
