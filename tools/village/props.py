"""Set dressing: the shadow-play stage, the village hall tower, the mountain gate, stalls, lanterns, fences..."""
import math
import random
from mathutils import Matrix, Vector

from meshkit import Mesh, hexc, mix, shade, jit, smoothstep, T, R, Sc
from house import (quad_auto, wall_matrix, wbox, wpt, RoofShape, tiled_roof, TIMBER, TIMBER_DK, STONE, GLASS_WARM,
                   ROOF_SLATE, FLOWERS, LEAF)

IRON = hexc("#2c2b30")
WOOD = hexc("#8a6442")
WOOD_LT = hexc("#b08a5e")
CLOTH = hexc("#f6efdc")
INDIGO = hexc("#34356e")
SKY_BLUE = hexc("#3f6fb5")
BUNTING = [hexc("#d9534a"), hexc("#f0b840"), hexc("#f4f1e8"), hexc("#3f6fb5"), hexc("#5f9a55")]


def stone_pile(m, w, d, h, rng, M=None, col=None, taper=0.92):
    """A chunky stack of masonry blocks (pillar / wall end)."""
    n = max(2, int(round(h / 0.55)))
    for i in range(n):
        c = jit(col or rng.choice(STONE), 0.1, rng)
        k = 1.0 - (1 - taper) * i / n
        B = T(rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), h * i / n) @ R("Z", rng.uniform(-3, 3))
        m.box((w * k, d * k, h / n + 0.01), c, M=(M @ B) if M is not None else B, grad=0.85, top=shade(c, 1.1))


def lantern(m, p, s=1.0, M=None):
    B = T(*p)
    if M is not None:
        B = M @ B
    m.box((0.22 * s, 0.22 * s, 0.32 * s), GLASS_WARM, M=B, grad=1.0)
    m.box((0.3 * s, 0.3 * s, 0.05 * s), IRON, M=B @ T(0, 0, 0.32 * s), grad=1.0)
    m.box((0.26 * s, 0.26 * s, 0.04 * s), IRON, M=B @ T(0, 0, -0.04 * s), grad=1.0)
    m.cone(0.22 * s, 0.16 * s, 4, IRON, M=B @ T(0, 0, 0.37 * s) @ R("Z", 45))


def lantern_post(m, M, h=3.1, rng=None):
    m.cyl(0.1, 0.07, h, 6, TIMBER_DK, M=M)
    m.box((0.34, 0.34, 0.3), jit(STONE[0], 0.05, rng or random), M=M, grad=0.85)
    m.beam(M @ Vector((0, 0, h - 0.15)), M @ Vector((0.62, 0, h - 0.05)), 0.07, 0.07, TIMBER_DK)
    m.beam(M @ Vector((0, 0, h - 0.7)), M @ Vector((0.4, 0, h - 0.14)), 0.05, 0.05, TIMBER_DK)
    lantern(m, (0.56, 0, h - 0.55), M=M)
    m.beam(M @ Vector((0.56, 0, h - 0.18)), M @ Vector((0.56, 0, h - 0.07)), 0.02, 0.02, IRON)


def barrel(m, M, rng, s=1.0):
    c = jit(WOOD, 0.1, rng)
    m.cyl(0.33 * s, 0.4 * s, 0.45 * s, 9, shade(c, 0.85), M=M, cap=False, col_top=c)
    m.cyl(0.4 * s, 0.33 * s, 0.45 * s, 9, c, M=M, z0=0.45 * s, col_top=shade(c, 1.1))
    for z in (0.14, 0.76):
        m.cyl(0.385 * s, 0.39 * s, 0.05 * s, 9, IRON, M=M, z0=z * s, cap=False)


def crate(m, M, rng, s=0.7):
    c = jit(WOOD_LT, 0.1, rng)
    m.box((s, s, s), c, M=M, grad=0.8)
    for dx in (-1, 1):
        m.box((0.07, s + 0.03, s + 0.015), shade(c, 0.72), M=M @ T(dx * (s / 2 - 0.035), 0, 0), grad=1.0, faces="xXyYZ")


def sack(m, M, rng):
    c = jit(hexc("#c9b48a"), 0.08, rng)
    m.blob(0.34, c, M=M @ T(0, 0, 0.26), rng=rng, sub=1, squash=(1, 0.8, 0.85), lumpy=0.08)
    m.cone(0.09, 0.14, 5, shade(c, 0.9), M=M @ T(0, 0, 0.5))


def bench(m, M, L=2.4, rng=None):
    c = jit(WOOD, 0.08, rng or random)
    m.box((L, 0.36, 0.07), c, M=M @ T(0, 0, 0.42), grad=1.0)
    for dx in (-1, 1):
        m.box((0.09, 0.3, 0.42), shade(c, 0.8), M=M @ T(dx * (L / 2 - 0.25), 0, 0), grad=0.85, faces="xXyY")


def fence(m, pts, hfun, rng, h=1.0, col=None):
    """Post-and-rail fence along a polyline of (x, y)."""
    col = col or hexc("#8f7252")
    posts = []
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        n = max(1, int(round((b - a).length / 1.6)))
        for k in range(n + (1 if i == len(pts) - 2 else 0)):
            p = a.lerp(b, k / n)
            posts.append(Vector((p.x, p.y, hfun(p.x, p.y))))
    for p in posts:
        m.cyl(0.07, 0.06, h + rng.uniform(-0.05, 0.08), 5, jit(col, 0.1, rng), M=T(p.x, p.y, p.z - 0.1) @ R("Y", rng.uniform(-3, 3)))
    for a, b in zip(posts, posts[1:]):
        for zz in (0.42, 0.78):
            m.beam(a + Vector((0, 0, zz * h + rng.uniform(-0.03, 0.03))), b + Vector((0, 0, zz * h + rng.uniform(-0.03, 0.03))),
                   0.09, 0.04, jit(col, 0.1, rng), grad=1.0)


def bunting(m, a, b, rng, sag=0.9, n=None, size=0.42):
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    n = n or max(4, int(L / 0.62))
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    for i in range(n):
        m.beam(pts[i], pts[i + 1], 0.02, 0.02, hexc("#5a4a3a"), grad=1.0, faces="xXyY")
        p0 = pts[i].lerp(pts[i + 1], 0.12)
        p1 = pts[i].lerp(pts[i + 1], 0.88)
        tipp = (p0 + p1) / 2 + Vector((0, 0, -size))
        c = BUNTING[i % len(BUNTING)]
        m.add([p0, p1, tipp], [(0, 1, 2)], [c, c, shade(c, 0.8)])
        m.add([p1, p0, tipp], [(0, 1, 2)], [c, c, shade(c, 0.8)])


def banner(m, top, n_out, w, h, col, rng, emblem=True):
    """Cloth banner hanging from `top` (centre of its top edge); faces n_out and its back."""
    n = Vector(n_out).normalized()
    side = Vector((0, 0, 1)).cross(n).normalized()
    top = Vector(top)
    seg = 4
    for i in range(seg):
        z0, z1 = -h * i / seg, -h * (i + 1) / seg
        o0, o1 = n * (0.05 * math.sin(i * 1.3)), n * (0.05 * math.sin((i + 1) * 1.3))
        k1 = 1.0 if i < seg - 1 else 0.0
        P = [top + side * (-w / 2) + Vector((0, 0, z0)) + o0, top + side * (w / 2) + Vector((0, 0, z0)) + o0,
             top + side * (w / 2 * k1) + Vector((0, 0, z1)) + o1, top + side * (-w / 2 * k1) + Vector((0, 0, z1)) + o1]
        if i == seg - 1:
            P = [P[0], P[1], top + Vector((0, 0, z1)) + o1]
        c0, c1 = shade(col, 1.0 - 0.05 * i), shade(col, 0.95 - 0.05 * i)
        cols = [c0, c0, c1, c1][:len(P)]
        quad_auto(m, P, col, n, cols=cols)
        quad_auto(m, P, col, -n, cols=cols)
    if emblem:                                     # pale sun disc: the sky's mark
        c = top + Vector((0, 0, -h * 0.36))
        ring = [c + side * (math.cos(a) * w * 0.26) + Vector((0, 0, math.sin(a) * w * 0.26)) for a in
                [i / 10 * math.tau for i in range(10)]]
        for s in (1, -1):
            quad_auto(m, [p + n * (0.07 * s) for p in ring], CLOTH, n * s)
    m.beam(top + side * (-w / 2 - 0.08) + Vector((0, 0, 0.03)), top + side * (w / 2 + 0.08) + Vector((0, 0, 0.03)), 0.06, 0.06, TIMBER_DK, grad=1.0)


def stall(m, M, rng, c1=None, c2=None):
    c1 = c1 or rng.choice([hexc("#c9483f"), hexc("#3f6fb5"), hexc("#d9a53a"), hexc("#5f9a55")])
    c2 = c2 or CLOTH
    w, d = 2.8, 1.7
    for sx in (-1, 1):
        for sy, hh in ((-1, 2.05), (1, 2.55)):
            m.cyl(0.06, 0.05, hh, 5, TIMBER_DK, M=M @ T(sx * w / 2, sy * d / 2, 0))
    m.box((w + 0.1, d * 0.8, 0.08), WOOD_LT, M=M @ T(0, 0, 0.85), grad=1.0)
    m.box((w, d * 0.7, 0.75), shade(WOOD, 0.9), M=M @ T(0, 0, 0.1), grad=0.8, faces="xXyY")
    n = 7
    for i in range(n):                              # striped awning
        x0, x1 = -w / 2 - 0.2 + i * (w + 0.4) / n, -w / 2 - 0.2 + (i + 1) * (w + 0.4) / n
        c = c1 if i % 2 == 0 else c2
        P = [M @ Vector((x0, -d / 2 - 0.45, 1.98)), M @ Vector((x1, -d / 2 - 0.45, 1.98)),
             M @ Vector((x1, d / 2 + 0.1, 2.6)), M @ Vector((x0, d / 2 + 0.1, 2.6))]
        up = M.to_3x3() @ Vector((0, -0.4, 1))
        quad_auto(m, P, c, up, cols=[shade(c, 0.9)] * 2 + [c] * 2)
        quad_auto(m, P, shade(c, 0.6), -up)
        v0, v1 = M @ Vector((x0, -d / 2 - 0.45, 1.98)), M @ Vector((x1, -d / 2 - 0.45, 1.98))
        tipp = (v0 + v1) / 2 + Vector((0, 0, -0.22))
        m.add([v1, v0, tipp], [(0, 1, 2)], [c] * 3)
        m.add([v0, v1, tipp], [(0, 1, 2)], [c] * 3)
    goods = [hexc("#d9432f"), hexc("#f0a030"), hexc("#7fb040"), hexc("#e8d27a"), hexc("#b04a7a")]
    for i in range(4):                              # baskets of produce
        bx = -w / 2 + 0.45 + i * (w - 0.9) / 3
        m.cyl(0.26, 0.3, 0.16, 7, hexc("#b89462"), M=M @ T(bx, -0.1, 0.93), cap=False)
        g = rng.choice(goods)
        for k in range(6):
            a = k / 6 * math.tau
            m.blob(0.1, jit(g, 0.1, rng), M=M @ T(bx + math.cos(a) * 0.14, -0.1 + math.sin(a) * 0.14, 1.07), rng=rng, sub=0, lumpy=0.05)
        m.blob(0.11, jit(g, 0.1, rng), M=M @ T(bx, -0.1, 1.17), rng=rng, sub=0, lumpy=0.05)


def cart(m, M, rng):
    c = jit(WOOD, 0.08, rng)
    m.box((2.0, 1.1, 0.12), c, M=M @ T(0, 0, 0.62), grad=1.0)
    for sy in (-1, 1):
        m.box((2.0, 0.06, 0.4), shade(c, 0.9), M=M @ T(0, sy * 0.55, 0.72), grad=0.85)
        W = M @ T(-0.25, sy * 0.68, 0.5) @ R("X", 90)
        m.cyl(0.5, 0.5, 0.08, 10, TIMBER_DK, M=W @ T(0, 0, -0.04), bottom=True)
        m.cyl(0.1, 0.1, 0.14, 6, IRON, M=W @ T(0, 0, -0.07), bottom=True)
        m.beam(M @ Vector((1.0, sy * 0.45, 0.66)), M @ Vector((2.3, sy * 0.4, 0.25)), 0.06, 0.06, c)
    m.box((0.06, 1.1, 0.4), shade(c, 0.9), M=M @ T(-1.0, 0, 0.72), grad=0.85)
    for i in range(3):
        m.cyl(0.33, 0.33, 0.5, 8, jit(hexc("#d8c36a"), 0.08, rng), M=M @ T(-0.5 + i * 0.6, 0, 0.72) @ R("X", 90) @ T(0, 0.33, -0.25), bottom=True)


def hay_bale(m, M, rng):
    c = jit(hexc("#d8c36a"), 0.08, rng)
    m.cyl(0.55, 0.55, 0.9, 10, c, M=M @ T(0, 0, 0.55) @ R("X", 90) @ T(0, 0, -0.45), bottom=True, col_top=shade(c, 1.08))


def laundry(m, a, b, rng):
    a, b = Vector(a), Vector(b)
    for p in (a, b):
        m.cyl(0.05, 0.04, 2.1, 5, TIMBER_DK, M=T(p.x, p.y, p.z))
    ta, tb = a + Vector((0, 0, 2.0)), b + Vector((0, 0, 2.0))
    n = 6
    side = (tb - ta).normalized()
    nrm = Vector((0, 0, 1)).cross(side)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = ta.lerp(tb, t)
        p.z -= 0.25 * 4 * t * (1 - t)
        pts.append(p)
    cols = [CLOTH, hexc("#9fc0e0"), hexc("#e6b0a0"), CLOTH, hexc("#c8d89a"), CLOTH]
    for i in range(n):
        m.beam(pts[i], pts[i + 1], 0.015, 0.015, hexc("#5a4a3a"), grad=1.0, faces="xXyY")
        if rng.random() < 0.75:
            p0, p1 = pts[i].lerp(pts[i + 1], 0.1), pts[i].lerp(pts[i + 1], 0.9)
            hh = rng.uniform(0.6, 1.1)
            c = cols[i % len(cols)]
            P = [p0, p1, p1 + Vector((0, 0, -hh)) + nrm * 0.06, p0 + Vector((0, 0, -hh)) + nrm * 0.06]
            quad_auto(m, P, c, nrm, cols=[c, c, shade(c, 0.88), shade(c, 0.88)])
            quad_auto(m, P, c, -nrm, cols=[c, c, shade(c, 0.88), shade(c, 0.88)])


# ---------- the shadow-play stage ----------
def stage(rng):
    """Open-air shadow theatre. Local frame: audience sits toward -Y."""
    m = Mesh()
    W, D, Hs = 7.6, 4.4, 1.0
    for i in range(11):                                         # plank deck
        y0 = -D / 2 + i * D / 11
        c = jit(WOOD_LT, 0.09, rng)
        m.box((W, D / 11 - 0.015, 0.09), c, M=T(0, y0 + D / 22, Hs - 0.09), grad=1.0, top=shade(c, 1.06))
    m.box((W - 0.2, D - 0.2, Hs - 0.09), shade(WOOD, 0.62), M=T(0, 0, 0), grad=0.8, faces="xXyY")
    n = 12
    for i in range(n):                                          # scalloped valance along the front
        x0, x1 = -W / 2 + i * W / n, -W / 2 + (i + 1) * W / n
        c = INDIGO if i % 2 == 0 else shade(INDIGO, 1.25)
        P = [Vector((x0, -D / 2 - 0.02, Hs - 0.09)), Vector((x1, -D / 2 - 0.02, Hs - 0.09)), Vector((x1, -D / 2 - 0.02, 0.5)),
             Vector(((x0 + x1) / 2, -D / 2 - 0.02, 0.32)), Vector((x0, -D / 2 - 0.02, 0.5))]
        quad_auto(m, P, c, (0, -1, 0))
    Hp = 4.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((0.24, 0.24, Hp), jit(TIMBER, 0.05, rng), M=T(sx * (W / 2 - 0.12), sy * (D / 2 - 0.12), 0), grad=0.85, faces="xXyY")
            m.beam((sx * (W / 2 - 0.12), sy * (D / 2 - 0.12), Hp - 0.9), (sx * (W / 2 - 1.0), sy * (D / 2 - 0.12), Hp - 0.05), 0.14, 0.14, TIMBER_DK)
        m.beam((sx * (W / 2 - 0.12), -D / 2 + 0.12, Hp - 0.9), (sx * (W / 2 - 0.12), -D / 2 + 1.0, Hp - 0.05), 0.14, 0.14, TIMBER_DK)
    for sy in (-1, 1):
        m.box((W + 0.5, 0.24, 0.26), TIMBER, M=T(0, sy * (D / 2 - 0.12), Hp), grad=1.0)
    for sx in (-1, 1):
        m.box((0.24, D, 0.26), TIMBER, M=T(sx * (W / 2 - 0.12), 0, Hp), grad=1.0)
    rs = RoofShape(W + 1.1, D + 0.2, Hp + 0.26, 1.75, ov=0.7, prow=0.45, sag=0.1, lift=0.3)
    tiled_roof(m, rs, ROOF_SLATE, rng, tile=0.5, moss=0.1)
    for sg in (-1, 1):                                           # open timber gables
        xg = sg * (W / 2 - 0.12)
        apex = rs.P(rs.u_at(xg, 0), 0, 1)
        m.beam((xg, 0, Hp + 0.26), (xg, 0, apex.z - 0.1), 0.18, 0.18, TIMBER)
        for s in (-1, 1):
            m.beam((xg, s * (D / 2 - 0.2), Hp + 0.3), (xg, 0, apex.z - 0.45), 0.14, 0.14, TIMBER_DK)
    # the screen
    sw, z0, z1, ys = 5.2, Hs + 0.35, Hs + 3.05, 0.55
    f = 0.16
    for (a, b) in (((-sw / 2 - f, z0 - f), (sw / 2 + f, z0)), ((-sw / 2 - f, z1), (sw / 2 + f, z1 + f)),
                   ((-sw / 2 - f, z0), (-sw / 2, z1)), ((sw / 2, z0), (sw / 2 + f, z1))):
        m.box((b[0] - a[0], 0.14, b[1] - a[1]), TIMBER, M=T((a[0] + b[0]) / 2, ys, a[1]), grad=1.0)
    for sx in (-1, 1):
        m.box((0.14, 0.14, z0 - Hs), TIMBER, M=T(sx * (sw / 2 + f / 2), ys, Hs), grad=1.0)
    glow = mix(CLOTH, GLASS_WARM, 0.25)
    for nrm, yy in (((0, -1, 0), ys - 0.02), ((0, 1, 0), ys + 0.02)):
        seg = 8
        for i in range(seg):                                     # brighter toward the centre, as if lit from behind
            x0, x1 = -sw / 2 + i * sw / seg, -sw / 2 + (i + 1) * sw / seg
            k0 = 1 - abs(x0) / (sw / 2) * 0.22
            k1 = 1 - abs(x1) / (sw / 2) * 0.22
            quad_auto(m, [(x0, yy, z0), (x1, yy, z0), (x1, yy, z1), (x0, yy, z1)], CLOTH, nrm,
                      cols=[shade(CLOTH, k0 * 0.93), shade(CLOTH, k1 * 0.93), shade(glow, k1), shade(glow, k0)])
    # the tableau on the screen: a mountain, a small hero raising a staff, a winged figure at the summit
    ink = hexc("#2a2540")
    yy = ys - 0.035

    def sil(pts2):
        quad_auto(m, [(x, yy, z) for x, z in pts2], ink, (0, -1, 0))

    sil([(-2.6, z0), (-0.2, z0), (-1.05, z0 + 1.85)])                       # mountain
    sil([(-1.6, z0), (0.9, z0), (0.1, z0 + 1.15), (-0.5, z0 + 0.9)])
    hx = 1.55                                                                # hero
    sil([(hx - 0.2, z0), (hx + 0.2, z0), (hx + 0.12, z0 + 0.62), (hx - 0.12, z0 + 0.62)])
    sil([(hx + math.cos(a) * 0.12, z0 + 0.76 + math.sin(a) * 0.12) for a in [i / 8 * math.tau for i in range(8)]])
    sil([(hx + 0.1, z0 + 0.5), (hx + 0.16, z0 + 0.5), (hx + 0.5, z0 + 1.25), (hx + 0.44, z0 + 1.25)])   # raised staff
    ax, az = -1.05, z0 + 2.15                                                # winged figure
    sil([(ax, az - 0.22), (ax + 0.09, az), (ax, az + 0.2), (ax - 0.09, az)])
    sil([(ax + 0.06, az + 0.02), (ax + 0.62, az + 0.26), (ax + 0.44, az - 0.06)])
    sil([(ax - 0.06, az + 0.02), (ax - 0.44, az - 0.06), (ax - 0.62, az + 0.26)])
    sil([(1.85 + math.cos(a) * 0.3, z1 - 0.55 + math.sin(a) * 0.3) for a in [i / 12 * math.tau for i in range(12)]])  # sun
    # wing curtains
    for sx in (-1, 1):
        x_in, x_out = sx * (sw / 2 + f), sx * (W / 2 - 0.3)
        folds = 6
        for i in range(folds):
            xa = x_in + (x_out - x_in) * i / folds
            xb = x_in + (x_out - x_in) * (i + 1) / folds
            ya, yb = ys + (0.09 if i % 2 else -0.09), ys + (-0.09 if i % 2 else 0.09)
            c = shade(INDIGO, 1.15 if i % 2 else 0.9)
            P = [(xa, ya, Hs), (xb, yb, Hs), (xb, yb, Hp), (xa, ya, Hp)]
            quad_auto(m, P, c, (0, -1, 0), cols=[shade(c, 0.8)] * 2 + [c] * 2)
            quad_auto(m, P, c, (0, 1, 0), cols=[shade(c, 0.8)] * 2 + [c] * 2)
    for i in range(5):                                                       # lantern row
        x = -W / 2 + 0.9 + i * (W - 1.8) / 4
        m.beam((x, -D / 2 + 0.12, Hp), (x, -D / 2 + 0.12, Hp - 0.35), 0.02, 0.02, IRON)
        lantern(m, (x, -D / 2 + 0.12, Hp - 0.72), s=0.9)
    for i in range(4):                                                       # side steps
        m.box((1.3, 0.34, Hs * (4 - i) / 4.6), jit(WOOD, 0.08, rng), M=T(-W / 2 - 0.2 - 0.34 * i - 0.17, -D / 2 + 0.9, 0) @ R("Z", 90), grad=0.85)
    # a rack of rod puppets waiting at the side
    rk = T(W / 2 - 0.75, -D / 2 + 0.7, Hs)
    m.box((0.9, 0.3, 0.1), TIMBER_DK, M=rk, grad=1.0)
    for i, (hh, kind) in enumerate(((1.25, 0), (1.05, 1), (1.4, 2))):
        px = -0.3 + i * 0.3
        m.cyl(0.015, 0.015, hh, 4, WOOD_LT, M=rk @ T(px, 0, 0.1))
        zc = hh + 0.1
        if kind == 0:
            quad_auto(m, [rk @ Vector((px - 0.1, 0, zc - 0.25)), rk @ Vector((px + 0.1, 0, zc - 0.25)), rk @ Vector((px, 0, zc + 0.2))], ink, (0, -1, 0))
            quad_auto(m, [rk @ Vector((px - 0.1, 0, zc - 0.25)), rk @ Vector((px + 0.1, 0, zc - 0.25)), rk @ Vector((px, 0, zc + 0.2))], ink, (0, 1, 0))
        else:
            ring = [rk @ Vector((px + math.cos(a) * (0.13 if kind == 1 else 0.17), 0, zc + math.sin(a) * 0.13)) for a in [k / 7 * math.tau for k in range(7)]]
            quad_auto(m, ring, ink, (0, -1, 0))
            quad_auto(m, ring, ink, (0, 1, 0))
    return m


# ---------- hall tower ----------
def spire(m, half, z0, H, col, rng, rows=9):
    for side in range(4):
        Rm = R("Z", 90 * side)
        nrm0 = Rm.to_3x3() @ Vector((0, -1, 0.5)).normalized()
        for r in range(rows):
            t0, t1 = r / rows, (r + 1) / rows

            def hw(t):
                return half * 1.22 * (1 - t) ** 1.55 + 0.03
            za, zb = z0 + H * (1 - t0), z0 + H * (1 - t1)            # a = upper, b = lower
            ha, hb = hw(1 - t0), hw(1 - t1)
            nt = max(1, int(round(2 * hb / 0.5)))
            for k in range(nt):
                c = jit(col, 0.13, rng)
                a0, a1 = -1 + 2 * k / nt, -1 + 2 * (k + 1) / nt
                lift = 0.07
                P = [Rm @ Vector((a0 * ha, -ha, za)), Rm @ Vector((a1 * ha, -ha, za)),
                     Rm @ Vector((a1 * hb, -hb - lift, zb)), Rm @ Vector((a0 * hb, -hb - lift, zb))]
                quad_auto(m, P, c, nrm0, cols=[shade(c, 0.85)] * 2 + [c] * 2)
                Q = [P[3], P[2], Rm @ Vector((a1 * hb, -hb, zb - 0.02)), Rm @ Vector((a0 * hb, -hb, zb - 0.02))]
                quad_auto(m, Q, shade(c, 0.6), Rm.to_3x3() @ Vector((0, -1, -0.5)))
    b = half * 1.22 + 0.1
    m.add([(-b, -b, z0), (-b, b, z0), (b, b, z0), (b, -b, z0)], [(0, 1, 2, 3)], [shade(TIMBER_DK, 0.8)] * 4)
    m.cyl(0.06, 0.02, 1.3, 5, IRON, M=T(0, 0, z0 + H - 0.1))
    m.blob(0.16, hexc("#e0b84a"), M=T(0, 0, z0 + H + 0.75), sub=1, lumpy=0)


def tower(rng, plaster, size=4.2, stone_h=9.0, belfry_h=2.6, spire_h=6.5, roof=ROOF_SLATE):
    m = Mesh()
    h = size / 2
    # stone shaft in courses
    n = int(stone_h / 0.6)
    for i in range(n):
        z = stone_h * i / n
        for side in range(4):
            Mw = wall_matrix(R("Z", 90 * side) @ Vector((-h, -h, z)), R("Z", 90 * side).to_3x3() @ Vector((1, 0, 0)),
                             R("Z", 90 * side).to_3x3() @ Vector((0, -1, 0)))
            a = 0.0
            off = 0.4 if i % 2 else 0.0
            first = True
            while a < size - 0.01:
                w = rng.uniform(0.7, 1.2) - (off if first else 0)
                first = False
                w = min(max(w, 0.3), size - a)
                if size - (a + w) < 0.3:
                    w = size - a
                c = jit(rng.choice(STONE), 0.1, rng)
                wbox(m, Mw, a, a + w - 0.015, 0, stone_h / n - 0.015, -0.2, rng.uniform(0.0, 0.05), c, grad=0.88, faces="xXyZ")
                a += w
    m.box((size - 0.3, size - 0.3, stone_h), shade(STONE[1], 0.6), M=T(0, 0, 0), grad=1.0, faces="xXyY")
    # clock face + slit windows
    for side in (0, 3):
        Rm = R("Z", 90 * side)
        c = Rm @ Vector((0, -h - 0.06, stone_h - 1.7))
        nrm = Rm.to_3x3() @ Vector((0, -1, 0))
        ring = [c + Rm.to_3x3() @ Vector((math.cos(a) * 1.0, 0, math.sin(a) * 1.0)) for a in [i / 16 * math.tau for i in range(16)]]
        quad_auto(m, ring, hexc("#f2ead2"), nrm)
        ring2 = [c + nrm * -0.01 + Rm.to_3x3() @ Vector((math.cos(a) * 1.16, 0, math.sin(a) * 1.16)) for a in [i / 16 * math.tau for i in range(16)]]
        quad_auto(m, ring2, TIMBER_DK, nrm)
        for ang, L in ((math.radians(60), 0.5), (math.radians(-170), 0.78)):
            tip = c + nrm * 0.03 + Rm.to_3x3() @ Vector((math.cos(ang) * L, 0, math.sin(ang) * L))
            m.beam(c + nrm * 0.03, tip, 0.07, 0.03, IRON, up=nrm, grad=1.0)
        for i in range(12):
            a = i / 12 * math.tau
            p = c + nrm * 0.02 + Rm.to_3x3() @ Vector((math.cos(a) * 0.84, 0, math.sin(a) * 0.84))
            m.box((0.08, 0.04, 0.08), TIMBER_DK, M=T(*p) @ Rm @ T(0, 0, -0.04), grad=1.0)
    for side in range(4):
        Rm = R("Z", 90 * side)
        Mw = wall_matrix(Rm @ Vector((-h, -h, 0)), Rm.to_3x3() @ Vector((1, 0, 0)), Rm.to_3x3() @ Vector((0, -1, 0)))
        for zz in (2.6, 5.0):
            quad_auto(m, [wpt(Mw, h - 0.17, zz, 0.07), wpt(Mw, h + 0.17, zz, 0.07), wpt(Mw, h + 0.17, zz + 1.0, 0.07), wpt(Mw, h - 0.17, zz + 1.0, 0.07)],
                      hexc("#27425c"), Rm.to_3x3() @ Vector((0, -1, 0)))
    # belfry
    z = stone_h
    m.box((size + 0.5, size + 0.5, 0.3), TIMBER, M=T(0, 0, z), grad=1.0)
    z += 0.3
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((0.3, 0.3, belfry_h), TIMBER, M=T(sx * (h - 0.05), sy * (h - 0.05), z), grad=0.9, faces="xXyY")
    for side in range(4):
        Rm = R("Z", 90 * side)
        m.box((size, 0.14, 0.16), TIMBER_DK, M=Rm @ T(0, -h + 0.05, z + 0.85), grad=1.0)
        for sx in (-1, 1):
            m.beam(Rm @ Vector((sx * (h - 0.1), -h + 0.05, z + belfry_h - 0.9)), Rm @ Vector((sx * (h - 0.95), -h + 0.05, z + belfry_h)), 0.14, 0.12, TIMBER_DK)
    m.box((size + 0.3, size + 0.3, 0.26), TIMBER, M=T(0, 0, z + belfry_h), grad=1.0)
    bell = hexc("#c9a23a")
    m.cyl(0.62, 0.3, 0.75, 10, shade(bell, 0.8), M=T(0, 0, z + 0.95), col_top=bell, smooth=True)
    m.cyl(0.05, 0.05, 0.6, 5, TIMBER_DK, M=T(0, 0, z + 1.7))
    spire(m, h + 0.25, z + belfry_h + 0.26, spire_h, roof, rng)
    return m


# ---------- gates ----------
def mountain_gate(rng):
    """The gate where the village ends and the mountain path begins. Path runs along +Y through the origin."""
    m = Mesh()
    half = 2.5
    for sx in (-1, 1):
        stone_pile(m, 1.25, 1.25, 3.2, rng, M=T(sx * half, 0, -0.5))
        m.box((1.45, 1.45, 0.18), shade(STONE[2], 1.05), M=T(sx * half, 0, 2.7), grad=1.0)
        m.box((0.42, 0.42, 2.6), TIMBER, M=T(sx * half, 0, 2.88), grad=0.9, faces="xXyY")
        lantern(m, (sx * (half - 0.95), -0.2, 2.15), s=1.15)
        m.beam((sx * half, -0.2, 2.75), (sx * (half - 0.95), -0.2, 2.72), 0.06, 0.06, IRON)
    m.box((2 * half + 2.6, 0.4, 0.42), TIMBER, M=T(0, 0, 4.55), grad=1.0)
    for sx in (-1, 1):                                            # upturned ends, like a prow
        m.beam((sx * (half + 1.3), 0, 4.76), (sx * (half + 1.95), 0, 5.12), 0.42, 0.4, TIMBER, up=(0, 1, 0))
        m.beam((sx * (half - 0.2), 0, 3.5), (sx * (half - 1.3), 0, 4.5), 0.2, 0.2, TIMBER_DK, up=(0, 1, 0))
    m.box((2 * half + 1.2, 0.3, 0.3), TIMBER_DK, M=T(0, 0, 5.2), grad=1.0)
    rs = RoofShape(2 * half + 3.6, 1.7, 5.5, 1.25, ov=0.75, prow=0.55, sag=0.02, lift=0.42)
    tiled_roof(m, rs, ROOF_SLATE, rng, tile=0.46, moss=0.3)
    for sx in (-0.5, 0.5):
        banner(m, (sx * 2.3, -0.05, 4.5), (0, -1, 0), 0.95, 2.0, SKY_BLUE, rng)
    # boundary walls
    for sx in (-1, 1):
        x = half + 0.6
        while x < half + 9.0:
            w = rng.uniform(0.8, 1.4)
            hh = rng.uniform(0.85, 1.15) * (1.0 - 0.35 * (x - half) / 9.0)
            c = jit(rng.choice(STONE), 0.1, rng)
            m.box((w - 0.03, rng.uniform(0.6, 0.75), hh + 0.4), c, M=T(sx * (x + w / 2), rng.uniform(-0.05, 0.05), -0.4) @ R("Z", rng.uniform(-3, 3)), grad=0.82, top=shade(c, 1.1))
            x += w
    return m


def entry_arch(rng):
    m = Mesh()
    half = 2.9
    for sx in (-1, 1):
        stone_pile(m, 0.9, 0.9, 1.3, rng, M=T(sx * half, 0, -0.4))
        m.cyl(0.19, 0.15, 3.9, 7, TIMBER, M=T(sx * half, 0, 0.8))
        m.beam((sx * half, 0, 3.4), (sx * (half - 1.0), 0, 4.35), 0.16, 0.16, TIMBER_DK, up=(0, 1, 0))
        lantern(m, (sx * (half + 0.55), 0, 2.4))
        m.beam((sx * half, 0, 2.85), (sx * (half + 0.6), 0, 2.8), 0.05, 0.05, IRON)
    m.box((2 * half + 1.6, 0.3, 0.32), TIMBER, M=T(0, 0, 4.4), grad=1.0)
    m.box((2.6, 0.1, 0.7), WOOD_LT, M=T(0, 0, 3.45), grad=0.92)
    for dx in (-1.0, 1.0):
        m.beam((dx, 0, 4.4), (dx, 0, 4.13), 0.03, 0.03, IRON)
    for s in (-1, 1):
        ring = [Vector((math.cos(a) * 0.24, s * 0.06, 3.8 + math.sin(a) * 0.24)) for a in [i / 10 * math.tau for i in range(10)]]
        quad_auto(m, ring, SKY_BLUE, (0, s, 0))
    return m
