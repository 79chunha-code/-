"""Stylised half-timbered houses: stone footing, plaster panels in a timber frame,
jettied upper floor, and a steep, flared, slightly sagging tiled roof.

Local frame: ridge runs along X, ground at z=0, house centred on the origin."""
import math
import random
from mathutils import Matrix, Vector

from meshkit import Mesh, hexc, mix, shade, jit, smoothstep, T, R

TIMBER = hexc("#5a3d2b")
TIMBER_DK = hexc("#3f2a1e")
STONE = [hexc("#a39a8c"), hexc("#857f79"), hexc("#b3a892"), hexc("#77767e"), hexc("#958a7a")]
GLASS_LO, GLASS_HI = hexc("#27425c"), hexc("#7fb2d6")
GLASS_WARM = hexc("#ffd27a")
FLOWERS = [hexc("#e8554e"), hexc("#f2b632"), hexc("#f4f1e8"), hexc("#d86aa6"), hexc("#8f6fd6")]
LEAF = hexc("#5f9a3f")

PLASTERS = [hexc("#efe3c8"), hexc("#f3ead8"), hexc("#e6d3ad"), hexc("#ead9c0"), hexc("#f0dcc0")]
ROOFS = [hexc("#b5532f"), hexc("#a84a2e"), hexc("#c0623a"), hexc("#9c4630"), hexc("#b85a3c")]
ROOF_SLATE = hexc("#3e5f86")
ACCENTS = [hexc("#2f6f7a"), hexc("#94423a"), hexc("#3d5d8c"), hexc("#5f7f45"), hexc("#3a7d6c"), hexc("#8a5a2e")]


def quad_auto(m, pts, col, nref, cols=None):
    """Add a quad/tri, flipping its winding so the normal agrees with nref."""
    a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (b - a).cross(c - a)
    if n.dot(Vector(nref)) < 0:
        pts = pts[::-1]
        if cols:
            cols = cols[::-1]
    m.add(pts, [tuple(range(len(pts)))], cols or [col] * len(pts))


def wall_matrix(p0, u, n_out):
    """Wall space: a = along the wall (left to right seen from outside), b = into the wall, c = up."""
    u, n = Vector(u).normalized(), Vector(n_out).normalized()
    b = -n
    return Matrix(((u.x, b.x, 0, p0[0]), (u.y, b.y, 0, p0[1]), (u.z, b.z, 1, p0[2]), (0, 0, 0, 1)))


def wbox(m, Mw, a0, a1, c0, c1, out0, out1, col, grad=0.9, faces="xXyZz", top=None):
    m.box((a1 - a0, out1 - out0, c1 - c0), col, M=Mw @ T((a0 + a1) / 2, -(out0 + out1) / 2, c0), grad=grad,
          faces=faces, top=top)


def wpt(Mw, a, c, out=0.0):
    return Mw @ Vector((a, -out, c))


def window(m, Mw, a0, a1, c0, c1, n_out, accent, rng, shutters=True, flowers=True, lit=False):
    lo, hi = (shade(GLASS_WARM, 0.8), GLASS_WARM) if lit else (GLASS_LO, GLASS_HI)
    quad_auto(m, [wpt(Mw, a0, c0, 0.015), wpt(Mw, a1, c0, 0.015), wpt(Mw, a1, c1, 0.015), wpt(Mw, a0, c1, 0.015)],
              lo, n_out, cols=[lo, lo, hi, hi])
    f = 0.11
    fc = TIMBER
    wbox(m, Mw, a0 - f, a1 + f, c1, c1 + f, 0.0, 0.10, fc)
    wbox(m, Mw, a0 - f, a0, c0, c1, 0.0, 0.09, fc)
    wbox(m, Mw, a1, a1 + f, c0, c1, 0.0, 0.09, fc)
    wbox(m, Mw, a0 - f - 0.05, a1 + f + 0.05, c0 - 0.1, c0, 0.0, 0.17, shade(fc, 1.15))          # sill
    mc = hexc("#d8c9a8")
    am, cm = (a0 + a1) / 2, c0 + (c1 - c0) * 0.55
    wbox(m, Mw, am - 0.025, am + 0.025, c0, c1, 0.015, 0.045, mc, faces="xXy")
    wbox(m, Mw, a0, a1, cm - 0.025, cm + 0.025, 0.015, 0.045, mc, faces="yZz")
    if shutters:
        sw = min(0.42, (a1 - a0) * 0.5)
        for s0, s1 in ((a0 - f - sw - 0.02, a0 - f - 0.02), (a1 + f + 0.02, a1 + f + sw + 0.02)):
            wbox(m, Mw, s0, s1, c0, c1, 0.0, 0.06, accent, grad=0.82)
            for cc in (c0 + (c1 - c0) * 0.2, c0 + (c1 - c0) * 0.75):
                wbox(m, Mw, s0, s1, cc, cc + 0.07, 0.06, 0.085, shade(accent, 0.7), faces="yZz")
    if flowers:
        bc = hexc("#7a5234")
        wbox(m, Mw, a0 - 0.05, a1 + 0.05, c0 - 0.36, c0 - 0.1, 0.1, 0.36, bc)
        n = max(3, int((a1 - a0) / 0.22))
        fcol = rng.choice(FLOWERS)
        for i in range(n):
            a = a0 + (i + 0.5) / n * (a1 - a0)
            p = wpt(Mw, a, c0 - 0.06 + rng.uniform(-0.02, 0.05), 0.23 + rng.uniform(-0.04, 0.05))
            m.blob(0.13 + rng.uniform(0, 0.05), jit(LEAF, 0.12, rng), M=T(*p), rng=rng, sub=0, squash=(1, 1, 0.8))
            if rng.random() < 0.8:
                q = wpt(Mw, a + rng.uniform(-0.05, 0.05), c0 + 0.07 + rng.uniform(0, 0.06), 0.25 + rng.uniform(-0.04, 0.08))
                m.blob(0.065, jit(fcol, 0.1, rng), M=T(*q), rng=rng, sub=0, col_bot=shade(fcol, 0.9))


def door(m, Mw, ac, n_out, col, rng, w=1.05, h=2.1, step_h=0.0, lantern=True, hood=True):
    a0, a1 = ac - w / 2, ac + w / 2
    planks = 4
    for i in range(planks):                                    # plank door
        p0, p1 = a0 + i * w / planks, a0 + (i + 1) * w / planks
        wbox(m, Mw, p0 + 0.008, p1 - 0.008, 0.0, h, 0.0, 0.05, jit(col, 0.09, rng), grad=0.8, faces="xXy")
    for cc in (0.35, h - 0.5):                                 # iron straps
        wbox(m, Mw, a0, a1, cc, cc + 0.09, 0.05, 0.07, hexc("#2c2b30"), faces="yZz")
    m.blob(0.05, hexc("#d9b35a"), M=T(*wpt(Mw, a1 - 0.16, h * 0.48, 0.09)), sub=0, lumpy=0.0)   # handle
    f = 0.17
    wbox(m, Mw, a0 - f, a0, 0.0, h, 0.0, 0.13, TIMBER)
    wbox(m, Mw, a1, a1 + f, 0.0, h, 0.0, 0.13, TIMBER)
    wbox(m, Mw, a0 - f - 0.1, a1 + f + 0.1, h, h + 0.24, 0.0, 0.17, shade(TIMBER, 1.1))        # lintel
    # little hood over the door
    hd = hexc("#6b4631")
    px = wpt(Mw, ac, h + 0.95, 0.5)
    for s in ((-1, 1) if hood else ()):
        e0 = wpt(Mw, ac + s * (w / 2 + 0.42), h + 0.42, 0.78)
        e1 = wpt(Mw, ac + s * (w / 2 + 0.42), h + 0.42, 0.0)
        r1 = wpt(Mw, ac, h + 0.95, 0.0)
        r0 = wpt(Mw, ac, h + 0.95, 0.78)
        up = Vector((0, 0, 1))
        quad_auto(m, [e0, e1, r1, r0], hd, up, cols=[shade(hd, 0.85)] * 2 + [hd] * 2)
        quad_auto(m, [e0, e1, r1, r0], shade(hd, 0.55), -up)
        m.beam(wpt(Mw, ac + s * (w / 2 + 0.3), h + 0.02, 0.05), wpt(Mw, ac + s * (w / 2 + 0.36), h + 0.42, 0.7), 0.08, 0.08, TIMBER_DK)
    # steps
    n_steps = max(1, int(round(step_h / 0.19)))
    for i in range(n_steps):
        top = -i * (step_h / n_steps)
        out1 = 0.45 + 0.34 * (i + 1)
        wbox(m, Mw, a0 - 0.3 - 0.06 * i, a1 + 0.3 + 0.06 * i, top - step_h / n_steps - (0.6 if i == n_steps - 1 else 0), top,
             -0.05, out1, jit(STONE[i % 4], 0.08, rng), grad=0.82, faces="xXyZ", top=shade(STONE[2], 1.08))
    if lantern:
        s = rng.choice((-1, 1))
        la = ac + s * (w / 2 + 0.55)
        m.beam(wpt(Mw, la, 2.25, 0.0), wpt(Mw, la, 2.25, 0.38), 0.05, 0.05, hexc("#2c2b30"))
        p = wpt(Mw, la, 1.86, 0.34)
        m.box((0.2, 0.2, 0.3), GLASS_WARM, M=T(*p), grad=1.0)
        m.box((0.26, 0.26, 0.05), hexc("#2c2b30"), M=T(p.x, p.y, p.z + 0.3))
        m.cone(0.2, 0.14, 4, hexc("#2c2b30"), M=T(p.x, p.y, p.z + 0.35) @ R("Z", 45))


def stone_course(m, Mw, W, c0, c1, out, rng, courses=1):
    """A row of chunky footing stones along one wall."""
    ch = (c1 - c0) / courses
    for k in range(courses):
        a = -out
        while a < W + out - 0.05:
            w = rng.uniform(0.5, 1.05)
            if a + w > W + out - 0.25:
                w = W + out - a
            col = jit(rng.choice(STONE), 0.12, rng)
            o = out + rng.uniform(-0.04, 0.07)
            wbox(m, Mw, a + 0.012, a + w - 0.012, c0 + k * ch + (0.012 if k else 0), c0 + (k + 1) * ch, -0.05, o, col,
                 grad=0.8, faces="xXyZ", top=shade(col, 1.1))
            a += w


def timber_wall(m, Mw, W, Hh, n_out, plaster, accent, rng, door_at=None, win_prob=0.6, step_h=0.0, braces=True,
                stone=False, lit_prob=0.15, flowers=0.5, min_windows=0, door_w=1.05, door_h=2.1, door_col=None, hood=True):
    """One storey of one wall: plaster panels, frame, windows, optional door. Returns list of window bays."""
    nb = max(2, int(round(W / 1.55)))
    edges = [W * i / nb for i in range(nb + 1)]
    bw = 0.2
    wins = []
    door_bay = None
    if door_at is not None:
        door_bay = min(range(nb), key=lambda i: abs((edges[i] + edges[i + 1]) / 2 - door_at))
    cand = [i for i in range(nb) if i != door_bay]
    rng.shuffle(cand)
    chosen = set(i for i in cand if rng.random() < win_prob)
    for i in cand:
        if len(chosen) >= min_windows:
            break
        chosen.add(i)
    for i in range(nb):
        a0, a1 = edges[i], edges[i + 1]
        pc = jit(plaster, 0.035, rng) if not stone else jit(rng.choice(STONE), 0.05, rng)
        quad_auto(m, [wpt(Mw, a0, 0), wpt(Mw, a1, 0), wpt(Mw, a1, Hh), wpt(Mw, a0, Hh)], pc, n_out,
                  cols=[shade(pc, 0.8)] * 2 + [shade(pc, 1.04)] * 2)
        ac = (a0 + a1) / 2
        if i == door_bay:
            door(m, Mw, ac, n_out, door_col or shade(accent, 0.9), rng, w=door_w, h=door_h, step_h=step_h, hood=hood)
        elif i in chosen:
            ww = min(0.95, (a1 - a0) - 0.62)
            c0 = 0.95 if Hh > 2.3 else 0.75
            c1 = min(Hh - 0.42, c0 + 1.15)
            window(m, Mw, ac - ww / 2, ac + ww / 2, c0, c1, n_out, accent, rng, flowers=rng.random() < flowers,
                   lit=rng.random() < lit_prob)
            wins.append(i)
            if not stone:
                wbox(m, Mw, a0, a1, c0 - 0.32, c0 - 0.14, 0.0, 0.06, TIMBER, faces="yZz")
        elif not stone:
            r = rng.random()
            if braces and r < 0.45:                                     # diagonal brace
                flip = rng.random() < 0.5 if 0 < i < nb - 1 else (i == nb - 1)
                p0 = wpt(Mw, a1 if flip else a0, 0.1, 0.03)
                p1 = wpt(Mw, a0 if flip else a1, Hh - 0.15, 0.03)
                m.beam(p0, p1, 0.17, 0.06, jit(TIMBER, 0.06, rng), up=n_out, faces="xXY")
            elif r < 0.8:
                mid = Hh * rng.uniform(0.45, 0.6)
                wbox(m, Mw, a0, a1, mid, mid + 0.17, 0.0, 0.06, jit(TIMBER, 0.06, rng), faces="yZz")
    if not stone:
        for e in edges:                                                  # posts
            wbox(m, Mw, e - bw / 2, e + bw / 2, 0.0, Hh, 0.0, 0.075, jit(TIMBER, 0.06, rng), faces="xXy")
        wbox(m, Mw, -0.1, W + 0.1, 0.0, 0.2, 0.0, 0.09, TIMBER, faces="xXyZ")              # sill beam
    wbox(m, Mw, -0.1, W + 0.1, Hh - 0.22, Hh, 0.0, 0.1, TIMBER, faces="xXyZz")               # top plate
    return wins


class RoofShape:
    def __init__(self, L, D, z0, Hr, ov=0.6, prow=0.35, sag=0.12, lift=0.22, k=0.42):
        self.L, self.D, self.z0, self.Hr, self.ov, self.prow, self.sag, self.lift, self.k = L, D, z0, Hr, ov, prow, sag, lift, k
        self.Y = D / 2 + ov
        self.sw = (D / 2) / self.Y
        self._scale = Hr / (self._raw(0) - self._raw(self.sw))

    def _raw(self, s):
        t = 1 - s
        return t * (1 - self.k) + self.k * max(t, 0.0) ** 2.3

    def zr(self, s):
        return (self._raw(s) - self._raw(self.sw)) * self._scale

    def P(self, u, s, side):
        x = (u - 0.5) * (self.L + 2 * self.prow * (1 - s))
        e = (2 * u - 1) ** 2
        dz = (1 - s) * (self.lift * e - self.sag * (1 - e))
        return Vector((x, side * s * self.Y, self.z0 + self.zr(s) + dz))

    def u_at(self, x, s):
        return 0.5 + x / (self.L + 2 * self.prow * (1 - s))

    def normal(self, u, s, side):
        a, b = self.P(u, max(0, s - 0.02), side), self.P(u, min(1.02, s + 0.02), side)
        ts = (b - a).normalized()
        return (Vector((1, 0, 0)).cross(ts) * side).normalized(), ts


def tiled_roof(m, rs, col, rng, tile=0.56, moss=0.25):
    slope_len = sum((rs.P(0.5, (i + 1) / 12, 1) - rs.P(0.5, i / 12, 1)).length for i in range(12))
    rows = max(5, int(round(slope_len / tile)))
    cols_n = max(5, int(round((rs.L + rs.prow) / (tile * 0.95))))
    moss_c = hexc("#6f8f4a")
    under = shade(TIMBER_DK, 0.9)
    for side in (-1, 1):
        for r in range(rows):
            s0, s1 = r / rows, (r + 1) / rows
            if r == rows - 1:
                s1 += 0.035
            off = 0.5 if r % 2 else 0.0
            n, ts = rs.normal(0.5, (s0 + s1) / 2, side)
            for c in range(-1, cols_n):
                u0, u1 = (c + off) / cols_n, (c + 1 + off) / cols_n
                u0, u1 = max(0.0, u0), min(1.0, u1)
                if u1 - u0 < 0.02:
                    continue
                tc = jit(col, 0.13, rng)
                rr = rng.random()
                if rr < 0.07:
                    tc = shade(tc, 1.25)
                elif rr < 0.13:
                    tc = shade(tc, 0.72)
                if rng.random() < moss * (s1 ** 2.5):
                    tc = mix(tc, moss_c, rng.uniform(0.35, 0.8))
                drop = rng.uniform(-0.03, 0.05) / (slope_len)
                th = 0.065
                A, B = rs.P(u0, s0, side), rs.P(u1, s0, side)
                C0, D0 = rs.P(u1, s1 + drop, side), rs.P(u0, s1 + drop, side)
                C, D = C0 + n * th, D0 + n * th
                if r == rows - 1:                      # close the eave so nothing shows through from below
                    C0, D0 = C0 - n * 0.06, D0 - n * 0.06
                quad_auto(m, [A, B, C, D], tc, n, cols=[shade(tc, 0.84), shade(tc, 0.84), tc, tc])
                quad_auto(m, [D, C, C0, D0], shade(tc, 0.6), ts)
        # underside + bargeboards
        seg = 7
        for i in range(seg):
            s0, s1 = i / seg, (i + 1) / seg * (1.035 if i == seg - 1 else 1)
            n, _ = rs.normal(0.5, (s0 + s1) / 2, side)
            for j in range(8):
                ua, ub = j / 8, (j + 1) / 8
                dn = n * 0.035
                quad_auto(m, [rs.P(ua, s0, side) - dn, rs.P(ub, s0, side) - dn, rs.P(ub, s1, side) - dn, rs.P(ua, s1, side) - dn], under, -n)
            for u in (0.0, 1.0):
                p0, p1 = rs.P(u, s0, side) - n * 0.04, rs.P(u, s1, side) - n * 0.04
                sx = -0.06 if u == 0 else 0.06
                p0.x += sx
                p1.x += sx
                m.beam(p0, p1, 0.24, 0.08, hexc("#6b4631"), up=(1, 0, 0), grad=1.0)
    # ridge cap
    rc = shade(col, 0.72)
    seg = 8
    for i in range(seg):
        p0, p1 = rs.P(i / seg, 0, 1), rs.P((i + 1) / seg, 0, 1)
        p0.z += 0.02
        p1.z += 0.02
        m.beam(p0, p1, 0.34, 0.16, jit(rc, 0.08, rng), up=(0, 0, 1), grad=1.0)
    for u in (0.0, 1.0):                                     # finials
        p = rs.P(u, 0, 1)
        m.cyl(0.07, 0.03, 0.55, 5, TIMBER_DK, M=T(p.x, p.y, p.z))


def gable_wall(m, rs, xg, sign, W, plaster, accent, rng, window_ok=True):
    """Triangular wall under the roof at x = xg (sign = outward direction along X)."""
    n_out = Vector((sign, 0, 0))
    pts = []
    seg = 6
    for side in (-1, 1):
        ss = [rs.sw * (1 - i / seg) for i in range(seg + 1)] if side == -1 else [rs.sw * i / seg for i in range(1, seg + 1)]
        for s in ss:
            p = rs.P(rs.u_at(xg, s), s, side)
            pts.append(Vector((xg, p.y, p.z - 0.05)))
    base = Vector((xg, 0, rs.z0))
    pc = jit(plaster, 0.03, rng)
    hi = shade(pc, 1.05)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ca = mix(shade(pc, 0.86), hi, smoothstep(0, rs.Hr, a.z - rs.z0))
        cb = mix(shade(pc, 0.86), hi, smoothstep(0, rs.Hr, b.z - rs.z0))
        quad_auto(m, [base, a, b], pc, n_out, cols=[shade(pc, 0.86), ca, cb])
    out = Vector((sign * 0.04, 0, 0))
    for i in range(len(pts) - 1):                                # rake timbers
        d = Vector((0, 0, -0.13))
        m.beam(pts[i] + out + d, pts[i + 1] + out + d, 0.2, 0.08, jit(TIMBER, 0.05, rng), up=n_out, faces="xXY")
    apex = max(pts, key=lambda p: p.z)
    hc = rs.z0 + rs.Hr * 0.46

    def y_at(z):
        best = min(pts, key=lambda p: abs(p.z - z) + (0 if p.y > 0 else 9))
        return abs(best.y)
    yc = y_at(hc)
    m.beam(Vector((xg, -yc, hc)) + out, Vector((xg, yc, hc)) + out, 0.18, 0.08, TIMBER, up=n_out, faces="xXY")
    m.beam(Vector((xg, 0, hc)) + out, apex + out + Vector((0, 0, -0.1)), 0.18, 0.08, TIMBER, up=n_out, faces="xXY")
    for s in (-1, 1):
        m.beam(Vector((xg, s * yc * 0.55, rs.z0)) + out, Vector((xg, s * yc * 0.55, hc)) + out, 0.16, 0.07, TIMBER, up=n_out, faces="xXY")
    if window_ok and rs.Hr > 2.6:
        Mw = wall_matrix((xg, -sign * 0.0, rs.z0), (0, sign, 0), (sign, 0, 0))
        window(m, Mw, -0.3, 0.3, hc * 0 + rs.Hr * 0.1, rs.Hr * 0.1 + 0.62, n_out, accent, rng, shutters=False, flowers=False,
               lit=rng.random() < 0.2)


def chimney(m, x, y, z0, z1, rng):
    st = hexc("#8f8880")
    n = max(3, int((z1 - z0) / 0.55))
    w = 0.78
    for i in range(n):
        zz = z0 + (z1 - z0) * i / n
        M = T(x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), zz) @ R("Z", rng.uniform(-4, 4))
        m.box((w - 0.02 * i, w - 0.02 * i, (z1 - z0) / n + 0.01), jit(st, 0.08, rng), M=M, grad=0.9, faces="xXyYZ")
    m.box((w + 0.22, w + 0.22, 0.14), shade(st, 0.8), M=T(x, y, z1), grad=1.0)
    for dx in (-0.16, 0.16):
        m.cyl(0.11, 0.09, 0.3, 6, hexc("#a5583a"), M=T(x + dx, y, z1 + 0.14))


def build_house(seed=0, w=7.5, d=6.0, floors=2, h1=2.6, h2=2.35, base_h=0.55, jetty=0.32, pitch=1.2,
                plaster=None, roof=None, accent=None, door_wall="eave", chimneys=1, stone_ground=False,
                lean=1.0, moss=0.25, sign=None, win_prob=0.6, tile=0.56, door_w=1.05, door_h=2.1, door_col=None):
    """Returns (Mesh in local coords, info dict). The door faces -Y (eave) or -X (gable)."""
    rng = random.Random(seed)
    m = Mesh()
    plaster = plaster or rng.choice(PLASTERS)
    roof = roof or rng.choice(ROOFS)
    accent = accent or rng.choice(ACCENTS)

    def storey(z, W, D, Hh, ground):
        """Four walls of one storey. Order: front(-Y), right(+X), back(+Y), left(-X)."""
        walls = [((-W / 2, -D / 2, z), (1, 0, 0), (0, -1, 0), W, "eave"),
                 ((W / 2, -D / 2, z), (0, 1, 0), (1, 0, 0), D, "gable+"),
                 ((W / 2, D / 2, z), (-1, 0, 0), (0, 1, 0), W, "back"),
                 ((-W / 2, D / 2, z), (0, -1, 0), (-1, 0, 0), D, "gable")]
        for p0, u, n, Wl, tag in walls:
            Mw = wall_matrix(p0, u, n)
            is_door = ground and tag == door_wall
            timber_wall(m, Mw, Wl, Hh, n, plaster, accent, rng, door_at=(Wl * rng.uniform(0.35, 0.65)) if is_door else None,
                        win_prob=win_prob if tag != "back" else win_prob * 0.6, step_h=base_h, stone=stone_ground and ground,
                        min_windows=1 if tag in ("eave", door_wall) else 0, door_w=door_w, door_h=door_h, door_col=door_col,
                        hood=not (floors == 1 and door_wall == "eave"))   # a low eave already shelters the door
            if ground:
                stone_course(m, wall_matrix((p0[0], p0[1], 0), u, n), Wl, -0.7, base_h, 0.12, rng, courses=2)

    storey(base_h, w, d, h1, True)
    z = base_h + h1
    W2, D2 = w, d
    if floors == 2:
        W2, D2 = w + jetty * 0.6, d + jetty * 2
        # jetty: floor slab + joist ends
        m.box((W2 + 0.1, D2 + 0.1, 0.2), TIMBER, M=T(0, 0, z - 0.02), grad=1.0)
        nj = int(W2 / 0.7)
        for i in range(nj + 1):
            x = -W2 / 2 + 0.15 + i * (W2 - 0.3) / nj
            for s in (-1, 1):
                m.box((0.16, 0.26, 0.16), jit(TIMBER_DK, 0.08, rng), M=T(x, s * (D2 / 2 + 0.1), z - 0.16), grad=1.0)
        for s in (-1, 1):                                              # corner brackets
            for sx in (-1, 1):
                m.beam((sx * (w / 2 - 0.05), s * d / 2, z - 0.75), (sx * (w / 2 - 0.05), s * (D2 / 2), z - 0.05), 0.12, 0.12, TIMBER_DK)
        storey(z + 0.18, W2, D2, h2, False)
        z += 0.18 + h2
    Hr = (D2 / 2) * pitch
    rs = RoofShape(W2 + 0.9, D2, z, Hr, ov=0.62, prow=0.38, sag=0.05 + 0.012 * W2, lift=0.2)
    tiled_roof(m, rs, roof, rng, tile=tile, moss=moss)
    for sg in (-1, 1):
        gable_wall(m, rs, sg * W2 / 2, sg, D2, plaster, accent, rng)
    for i in range(chimneys):
        cx = rng.uniform(0.15, 0.32) * W2 * (1 if i == 0 else -1)
        cy = rng.choice((-1, 1)) * D2 * 0.16
        ztop = z + Hr * (1 - abs(cy) / (D2 / 2)) + rng.uniform(0.9, 1.4)
        chimney(m, cx, cy, z - 0.3, ztop, rng)
    if sign:
        hang_sign(m, wall_matrix((-w / 2, -d / 2, base_h), (1, 0, 0), (0, -1, 0)) if door_wall == "eave"
                  else wall_matrix((-w / 2, d / 2, base_h), (0, -1, 0), (-1, 0, 0)), (w if door_wall == "eave" else d) * 0.12, sign, rng)

    # stylised lean: a little shear, a little top-heaviness
    Ht = z + Hr
    sx, sy = rng.uniform(-0.018, 0.018) * lean, rng.uniform(-0.018, 0.018) * lean
    grow = 0.035 * lean

    def warp(p):
        k = 1.0 + grow * max(0.0, p.z) / Ht
        return (p.x * k + sx * p.z, p.y * k + sy * p.z, p.z)

    out = Mesh()
    out.merge(m, warp=warp)
    return out, {"w": w, "d": d, "height": Ht, "door_wall": door_wall, "base_h": base_h}


def hang_sign(m, Mw, a, kind, rng):
    iron = hexc("#2c2b30")
    m.beam(wpt(Mw, a, 2.75, 0.0), wpt(Mw, a, 2.75, 1.05), 0.07, 0.07, iron)
    m.beam(wpt(Mw, a, 2.3, 0.0), wpt(Mw, a, 2.72, 0.5), 0.05, 0.05, iron)
    col = {"inn": hexc("#3b5f9a"), "bakery": hexc("#c08a2e"), "smith": hexc("#55565e"), "shop": hexc("#6a8f3a")}.get(kind, hexc("#9a3b34"))
    c = wpt(Mw, a, 2.2, 0.62)
    u = (Mw.to_3x3() @ Vector((0, -1, 0))).normalized()
    side = (Mw.to_3x3() @ Vector((1, 0, 0))).normalized()
    B = Matrix(((u.x, side.x, 0, c.x), (u.y, side.y, 0, c.y), (u.z, side.z, 1, c.z), (0, 0, 0, 1)))
    m.box((0.72, 0.06, 0.5), col, M=B @ T(0, 0, -0.03), grad=0.85)
    m.box((0.8, 0.09, 0.06), TIMBER_DK, M=B @ T(0, 0, 0.46), grad=1.0)
    for s in (-1, 1):
        m.blob(0.13, hexc("#f1e3b8"), M=B @ T(0, s * 0.05, 0.22), sub=0, lumpy=0, squash=(1, 0.25, 1))
    for dx in (-0.25, 0.25):
        m.beam(B @ Vector((dx, 0, 0.5)), B @ Vector((dx, 0, 0.56)), 0.025, 0.025, iron)
