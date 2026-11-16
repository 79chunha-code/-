"""The mountain, as four walkable zones on the way up:

  forest   - the wooded trail above the village gate
  ridge    - the open ridge of the third morning, where Rota looks up at the sky
  plateau  - the angel's plateau, a ruin above the clouds, and the last night's camp
  summit   - the end of the sky: bare snow, nothing waiting, wrapped in fog

Each zone has its own frame: +Y is the way up, the trail enters from the south."""
import math
import random
from mathutils import Vector, noise

import world
import props
import nature
import layout
from meshkit import Mesh, hexc, mix, shade, jit, smoothstep, T, R
from house import quad_auto, STONE, GLASS_WARM, TIMBER, TIMBER_DK

VCOL = "village_vcol"
fbm = world.fbm

GRASS_A, GRASS_B, GRASS_C = hexc("#7fae52"), hexc("#a3c862"), hexc("#5f9648")
ALP_A, ALP_B = hexc("#8fbf5a"), hexc("#b7d46c")
NEEDLES = hexc("#6f7f45")
DIRT, DIRT2 = hexc("#c8a676"), hexc("#b08e62")
ROCK_A, ROCK_B, ROCK_C = hexc("#8f8c96"), hexc("#75708a"), hexc("#a9a6b4")
SNOW, SNOW_SH = hexc("#f7faff"), hexc("#cfdcf2")
MARBLE = [hexc("#eef0f4"), hexc("#dfe3ec"), hexc("#f4f1ea"), hexc("#d3d9e6")]
WATER, WATER_LT = hexc("#4f9ec4"), hexc("#bfe6f2")


class Zone:
    def __init__(self, name):
        self.name = name
        self.out = {}
        self.occ = []
        self.cameras = {}
        self.fog = None            # (centre, radius, density) for the render-only volume

    def mesh(self, key, mat=VCOL):
        k = self.name + "_" + key
        if k not in self.out:
            self.out[k] = (Mesh(), mat)
        return self.out[k][0]

    def free(self, x, y, r=0.0):
        return all((x - ox) ** 2 + (y - oy) ** 2 > (orr + r) ** 2 for ox, oy, orr in self.occ)


def axis(lo, hi, core_lo, core_hi, step, grow=1.25, max_step=10.0):
    return world._axis(lo, hi, core_lo, core_hi, step, grow, max_step)


def grid(m, hfun, cfun, xs, ys, flat_slope=0.85):
    """Height-field terrain. Gentle ground shades smooth; steep rock shades faceted."""
    nx, ny = len(xs), len(ys)
    Hh = [[hfun(x, y) for x in xs] for y in ys]
    base = len(m.v)
    S = []
    for j, y in enumerate(ys):
        row = []
        for i, x in enumerate(xs):
            i0, i1 = max(0, i - 1), min(nx - 1, i + 1)
            j0, j1 = max(0, j - 1), min(ny - 1, j + 1)
            sx = (Hh[j][i1] - Hh[j][i0]) / (xs[i1] - xs[i0])
            sy = (Hh[j1][i] - Hh[j0][i]) / (ys[j1] - ys[j0])
            sl = math.hypot(sx, sy)
            row.append(sl)
            m.v.append(Vector((x, y, Hh[j][i])))
            m.c.append(cfun(x, y, Hh[j][i], sl))
        S.append(row)
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = base + j * nx + i
            m.f.append((a, a + 1, a + nx + 1, a + nx))
            m.s.append((S[j][i] + S[j][i + 1] + S[j + 1][i] + S[j + 1][i + 1]) / 4 < flat_slope)


def rock_color(x, y, z, k=1.0):
    n = fbm(x, y, 0.06, 3)
    band = 0.5 + 0.5 * math.sin(z * 0.9 + n * 5.0)
    return shade(mix(mix(ROCK_A, ROCK_B, smoothstep(-0.3, 0.4, n)), ROCK_C, band * 0.4), k)


def ground_quad(m, hfun, x, y, w, d, a, col, lift=0.02):
    P = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        qx = x + (sx * w * math.cos(a) - sy * d * math.sin(a))
        qy = y + (sx * w * math.sin(a) + sy * d * math.cos(a))
        P.append((qx, qy, hfun(qx, qy) + lift))
    quad_auto(m, P, col, (0, 0, 1))


def path_stones(m, hfun, px, y0, y1, rng, spread=1.0, step=(0.8, 1.6)):
    cols = [hexc("#d6c6a4"), hexc("#cdbb98"), hexc("#dccfb0")]
    y = y0
    while y < y1:
        y += rng.uniform(*step)
        x = px(y) + rng.uniform(-spread, spread)
        ground_quad(m, hfun, x, y, rng.uniform(0.17, 0.3), rng.uniform(0.14, 0.24), rng.uniform(0, math.pi), jit(rng.choice(cols), 0.06, rng))


def cairn(m, hfun, x, y, rng, n=4, s=1.0):
    z = hfun(x, y)
    for i in range(n):
        nature.rock(m, x + rng.uniform(-0.04, 0.04), y + rng.uniform(-0.04, 0.04), z + i * 0.3 * s - 0.05, rng, s=(0.36 - i * 0.07) * s)


def pennant_poles(Z, hfun, px, ys, rng, half=2.4, torn=0.0):
    m, bm = Z.mesh("Props"), Z.mesh("Bunting")
    old = props.BUNTING
    props.BUNTING = [props.SKY_BLUE, props.CLOTH, hexc("#8fb4e8"), props.CLOTH]
    for y in ys:
        pair = []
        for sx in (-1, 1):
            x = px(y) + sx * half
            z = hfun(x, y)
            m.cyl(0.08, 0.05, 4.2, 6, TIMBER, M=T(x, y, z - 0.3) @ R("Y", rng.uniform(-4, 4)))
            pair.append(Vector((x, y, z + 3.8)))
            Z.occ.append((x, y, 0.5))
        if rng.random() >= torn:
            props.bunting(bm, pair[0], pair[1], rng, sag=0.6)
    props.BUNTING = old


def cloud_sea(m, z, rng, r_in=60.0, r_out=1500.0, cx=0.0, cy=0.0, gap=None):
    top, bot = hexc("#ffffff"), hexc("#c3d3ea")
    r = r_in
    while r < r_out:
        step = 34 + r * 0.075
        n = max(6, int(math.tau * r / (step * 1.5)))
        for k in range(n):
            a = (k + rng.uniform(0, 1)) / n * math.tau
            rr = r + rng.uniform(-0.4, 0.4) * step
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            if gap and gap(x, y):
                continue
            size = step * rng.uniform(0.75, 1.15)
            m.blob(size, top, M=T(x, y, z + rng.uniform(-0.12, 0.12) * size), rng=rng, sub=1 if rr < 420 else 0,
                   squash=(1.3, 1.3, rng.uniform(0.3, 0.45)), lumpy=0.16, col_top=top, col_bot=bot)
        r += step * 1.25


def far_world(Z, origin, rng, ranges=True, village=True):
    """What lies below and beyond: the valley with the tiny village, and distant ranges."""
    m = Z.mesh("Backdrop")
    ox, oy, oz = origin
    if village:
        mv = Mesh()
        roof = [hexc("#b5532f"), hexc("#a84a2e"), hexc("#c0623a")]
        for name, xr, v, face, spec in layout.HOUSES:
            x, y = layout.site(xr, v)
            z = world.height(x, y)
            w, d = spec["w"], spec["d"]
            hh = 3.0 * spec.get("floors", 2) + 0.6
            M = T(x, y, z) @ R("Z", layout.FACE[face])
            mv.box((w, d, hh), hexc("#efe3c8"), M=M, grad=0.8, faces="xXyY")
            rc = jit(rng.choice(roof), 0.08, rng)
            rh = d * 0.6
            for s in (-1, 1):
                quad_auto(mv, [M @ Vector((-w / 2 - 0.4, s * (d / 2 + 0.5), hh - 0.2)), M @ Vector((w / 2 + 0.4, s * (d / 2 + 0.5), hh - 0.2)),
                               M @ Vector((w / 2 + 0.4, 0, hh + rh)), M @ Vector((-w / 2 - 0.4, 0, hh + rh))], rc, M.to_3x3() @ Vector((0, s, 1)))
            for s in (-1, 1):
                quad_auto(mv, [M @ Vector((s * w / 2, -d / 2, hh)), M @ Vector((s * w / 2, d / 2, hh)), M @ Vector((s * w / 2, 0, hh + rh))],
                          hexc("#efe3c8"), M.to_3x3() @ Vector((s, 0, 0)))
        hx, hy = layout.site(-11.0, 13.3)
        hz = world.height(hx, hy)
        mv.box((13, 8, 7), hexc("#f1e6cf"), M=T(hx, hy, hz), grad=0.8, faces="xXyY")
        mv.cone(9, 5, 4, hexc("#3e5f86"), M=T(hx, hy, hz + 7) @ R("Z", 45))
        mv.box((4, 4, 12), hexc("#9a938a"), M=T(hx + 8.5, hy - 2, hz), grad=0.9, faces="xXyY")
        mv.cone(3.6, 7, 4, hexc("#3e5f86"), M=T(hx + 8.5, hy - 2, hz + 12) @ R("Z", 45))
        # the valley the village sits in
        xs = axis(-260, 260, -70, 70, 9.0, 1.3, 40)
        ys = axis(-330, 240, -110, 90, 9.0, 1.3, 40)
        grid(mv, world.height, lambda x, y, z, sl: world.ground_color(x, y, z, sl), xs, ys, flat_slope=9)
        tr = random.Random(3)
        for k in range(420):
            x, y = tr.uniform(-240, 240), tr.uniform(-300, 230)
            if abs(x) < 56 and -105 < y < 82:
                continue
            nature.pine(mv, x, y, world.height(x, y), tr.uniform(9, 15), tr, lod=1)
        Mv = T(ox, oy, oz)

        def hz_warp(p):
            return p
        base = len(m.v)
        m.merge(mv, M=Mv)
        d0 = math.hypot(ox, oy)
        for i in range(base, len(m.v)):
            m.c[i] = world.haze(m.c[i], d0 * 1.6, 2400.0)
    if village:                                              # the land the valley lies in
        g = world.haze(hexc("#7fa858"), math.hypot(ox, oy) * 1.6, 2400.0)
        m.cyl(2600, 2600, 1.0, 40, g, M=T(ox, oy, oz - 18))
        for (x, y, hh, r, sd) in ((-205, 60, 80, 170, 31), (215, 30, 72, 165, 32), (-230, -150, 55, 190, 33), (240, -170, 50, 180, 34),
                                  (-420, -60, 90, 260, 37), (430, -40, 85, 260, 38), (0, -620, 60, 320, 39)):
            world._peak(m, ox + x, oy + y, hh, r, seed=sd, base_z=oz - 20, rings=14, segs=28, snow_line=9, sharp=1.25, rock_from=0.85)
    if ranges:
        for k in range(22):
            a = k / 22 * math.tau + rng.uniform(-0.1, 0.1)
            d = rng.uniform(1300, 2100)
            world._peak(m, math.cos(a) * d, math.sin(a) * d, rng.uniform(320, 620), rng.uniform(380, 560), seed=40 + k,
                        base_z=oz - 80, rings=12, segs=24, snow_line=0.5, sharp=1.4)


def tent(m, M, rng):
    L, W, Hh = 2.7, 2.1, 1.55
    cloth, trim = hexc("#efe6cf"), props.SKY_BLUE
    for s in (-1, 1):
        P = [M @ Vector((-L / 2, s * W / 2, 0)), M @ Vector((L / 2, s * W / 2, 0)), M @ Vector((L / 2, 0, Hh)), M @ Vector((-L / 2, 0, Hh))]
        nrm = M.to_3x3() @ Vector((0, s, 0.7))
        quad_auto(m, P, cloth, nrm, cols=[shade(cloth, 0.86)] * 2 + [cloth] * 2)
        quad_auto(m, P, shade(cloth, 0.55), -nrm)
        Q = [M @ Vector((-L / 2, s * W / 2 * 1.01, 0.02)), M @ Vector((L / 2, s * W / 2 * 1.01, 0.02)),
             M @ Vector((L / 2, s * W / 2 * 0.86, Hh * 0.15)), M @ Vector((-L / 2, s * W / 2 * 0.86, Hh * 0.15))]
        Q = [q + nrm.normalized() * 0.012 for q in Q]
        quad_auto(m, Q, trim, nrm)
    back = [M @ Vector((-L / 2, -W / 2, 0)), M @ Vector((-L / 2, W / 2, 0)), M @ Vector((-L / 2, 0, Hh))]
    quad_auto(m, back, shade(cloth, 0.9), M.to_3x3() @ Vector((-1, 0, 0)))
    quad_auto(m, back, shade(cloth, 0.5), M.to_3x3() @ Vector((1, 0, 0)))
    for s in (-1, 1):                                          # half-open door flaps
        fl = [M @ Vector((L / 2, s * W / 2, 0)), M @ Vector((L / 2 + 0.25, s * W / 2 * 0.55, 0)), M @ Vector((L / 2, 0, Hh))]
        quad_auto(m, fl, shade(cloth, 0.95), M.to_3x3() @ Vector((1, 0, 0)))
        quad_auto(m, fl, shade(cloth, 0.55), M.to_3x3() @ Vector((-1, 0, 0)))
    m.beam(M @ Vector((-L / 2 - 0.2, 0, Hh + 0.02)), M @ Vector((L / 2 + 0.2, 0, Hh + 0.02)), 0.05, 0.05, TIMBER_DK)
    for sx in (-1, 1):
        m.cyl(0.04, 0.04, Hh + 0.12, 5, TIMBER_DK, M=M @ T(sx * L / 2, 0, 0))
    m.box((L * 0.8, W * 0.5, 0.08), hexc("#8a5a6a"), M=M @ T(-0.1, 0, 0.0), grad=1.0)          # blanket inside


def campfire(m, M, rng, lit=True):
    for k in range(9):
        a = k / 9 * math.tau
        p = M @ Vector((math.cos(a) * 0.55, math.sin(a) * 0.55, 0))
        nature.rock(m, p.x, p.y, p.z - 0.08, rng, s=rng.uniform(0.16, 0.22))
    for k in range(3):
        a = k / 3 * math.pi + 0.3
        m.beam(M @ Vector((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.06)), M @ Vector((-math.cos(a) * 0.3, -math.sin(a) * 0.3, 0.3)), 0.11, 0.11, hexc("#4a3628"))
    if lit:
        m.blob(0.2, hexc("#ffb347"), M=M @ T(0, 0, 0.28), rng=rng, sub=0, squash=(1, 1, 1.5), lumpy=0.2, col_top=hexc("#fff0a0"), col_bot=hexc("#e8632e"))
    else:
        m.blob(0.2, hexc("#3a3632"), M=M @ T(0, 0, 0.12), rng=rng, sub=0, squash=(1, 1, 0.5), lumpy=0.2)


def camp(Z, hfun, x, y, yaw, rng, journal=False, lit=True, clear=4.2):
    m = Z.mesh("Props")
    z = hfun(x, y)
    M = T(x, y, z) @ R("Z", yaw)
    tent(m, M @ T(-2.4, 0.4, 0) @ R("Z", 12), rng)
    campfire(m, M @ T(1.0, 0, 0), rng, lit=lit)
    m.cyl(0.2, 0.2, 1.6, 8, hexc("#6b4a35"), M=M @ T(1.2, 1.5, 0.2) @ R("X", 90) @ R("Y", 20) @ T(0, 0, -0.8), bottom=True)   # log seat
    # tripod with a kettle
    top = M @ Vector((1.0, 0, 1.25))
    for k in range(3):
        a = k / 3 * math.tau + 0.5
        m.beam(M @ Vector((1.0 + math.cos(a) * 0.7, math.sin(a) * 0.7, 0)), top, 0.035, 0.035, TIMBER_DK)
    m.beam(top, top + Vector((0, 0, -0.5)), 0.012, 0.012, props.IRON)
    m.cyl(0.13, 0.11, 0.16, 7, props.IRON, M=T(top.x, top.y, top.z - 0.66))
    # pack, bedroll, and the staff
    P = M @ T(-0.3, -1.5, 0)
    m.blob(0.3, hexc("#8a6442"), M=P @ T(0, 0, 0.28), rng=rng, sub=1, squash=(0.9, 0.7, 1.1), lumpy=0.08)
    m.cyl(0.13, 0.13, 0.62, 7, hexc("#7a8fb0"), M=P @ T(0, 0, 0.62) @ R("Y", 90) @ T(0, 0, -0.31), bottom=True)
    s0 = M @ Vector((0.25, -1.75, -0.1))
    m.beam(s0, s0 + Vector((0.12, 0.2, 2.0)), 0.045, 0.045, hexc("#6b4a35"))
    if journal:                                                  # the journal, open on a flat stone
        jx, jy, _ = M @ Vector((2.3, -0.9, 0))
        nature.rock(m, jx, jy, hfun(jx, jy) - 0.12, rng, s=0.55)
        J = T(jx, jy, hfun(jx, jy) + 0.3) @ R("Z", yaw + 30)
        m.box((0.56, 0.4, 0.035), hexc("#6a3f2a"), M=J, grad=1.0)
        for s in (-1, 1):
            quad_auto(m, [J @ Vector((0, -0.18, 0.045)), J @ Vector((s * 0.26, -0.18, 0.06)), J @ Vector((s * 0.26, 0.18, 0.06)), J @ Vector((0, 0.18, 0.045))],
                      hexc("#f3ead2"), (0, 0, 1))
            for k in range(5):
                yy = -0.13 + k * 0.065
                quad_auto(m, [J @ Vector((s * 0.04, yy, 0.064)), J @ Vector((s * 0.22, yy, 0.068)), J @ Vector((s * 0.22, yy + 0.012, 0.068)), J @ Vector((s * 0.04, yy + 0.012, 0.064))],
                          hexc("#5a4a3a"), (0, 0, 1))
        m.box((0.03, 0.5, 0.012), props.SKY_BLUE, M=J @ T(0.0, -0.06, 0.05), grad=1.0)
        props.lantern(m, (jx + 0.5, jy + 0.2, hfun(jx + 0.5, jy + 0.2) + 0.04))
    Z.occ.append((x, y, clear))


# =============================================================== 1. forest trail
def zone_forest():
    Z = Zone("Forest")
    rng = random.Random(1001)

    def px(y):
        return 14.0 * math.sin(y / 26.0) + 5.0 * math.sin(y / 11.0)

    def brook_y(x):
        return 82.0 + 0.22 * x + 4.0 * math.sin(x / 9.0)

    LOOK = (px(128) + 34.0, 128.0)                       # the lookout crag

    def h(x, y):
        z = 0.26 * y + 0.0008 * y * y
        if y < -12:
            z -= 0.9 * (-12 - y)                             # below the start the hill falls away to the valley
        z += fbm(x, y, 0.03) * 2.2 + fbm(x, y, 0.1, 2) * 0.5
        d = abs(x - px(y))
        z -= 0.5 * (1 - smoothstep(0.5, 3.5, d)) * fbm(x, y, 0.1, 2)          # the trail is trodden smooth
        z -= 1.7 * math.exp(-((y - brook_y(x)) / 2.6) ** 2)                    # brook gully
        dl = math.hypot(x - LOOK[0], y - LOOK[1])
        z += 3.2 * (1 - smoothstep(4.0, 11.0, dl))
        ds = LOOK[1] - y                                    # south of the crag the ground falls away: a view
        if ds > 0:
            z -= 15.0 * smoothstep(5.0, 13.0, ds) * smoothstep(LOOK[0] - 10.0, LOOK[0] - 3.0, x) * (1 - smoothstep(120.0, 170.0, ds))
        return z

    def pmask(x, y):
        d = abs(x - px(y)) + fbm(x, y, 0.25, 2) * 0.5
        m_ = 1 - smoothstep(1.1, 2.3, d)
        dl = math.hypot(x - LOOK[0], y - LOOK[1])
        # spur path to the lookout
        ds = abs(y - 128.0) if 0 < x - px(128) < 34 else 9
        m_ = max(m_, 1 - smoothstep(0.8, 1.7, ds))
        return m_

    def col(x, y, z, sl):
        n1, n2 = fbm(x, y, 0.05, 3), fbm(x + 31, y - 9, 0.16, 2)
        c = mix(GRASS_C, GRASS_A, smoothstep(-0.3, 0.4, n1))
        c = mix(c, NEEDLES, smoothstep(0.0, 0.5, n2) * 0.55)
        c = mix(c, rock_color(x, y, z), smoothstep(0.8, 1.2, sl))
        dl = math.hypot(x - LOOK[0], y - LOOK[1])
        c = mix(c, rock_color(x, y, z, 1.08), (1 - smoothstep(4.5, 7.0, dl)) * 0.8)
        c = mix(c, mix(DIRT, DIRT2, smoothstep(-0.3, 0.4, n2)), pmask(x, y))
        wet = math.exp(-((y - brook_y(x)) / 1.5) ** 2)
        c = mix(c, hexc("#6f6a5e"), wet * 0.8)
        return c

    grid(Z.mesh("Terrain"), h, col, axis(-170, 170, -55, 55, 1.3), axis(-90, 300, -14, 196, 1.3))
    sm, pm, tm, gm = Z.mesh("Stonework"), Z.mesh("Props"), Z.mesh("Trees"), Z.mesh("GroundCover")

    path_stones(sm, h, px, -12, 196, rng, spread=0.9)
    y = 6.0
    k = 0
    while y < 190:
        if abs(y - brook_y(px(y))) > 6:
            cairn(pm, h, px(y) + (2.2 if k % 2 else -2.2), y, rng)
        y += rng.uniform(12, 17)
        k += 1
    pennant_poles(Z, h, px, (4, 20, 150, 172), rng)

    # the brook, and a little arched bridge over it
    wm = Z.mesh("Water")
    x = -150.0
    while x < 150:
        x2 = x + 2.2
        P = []
        for xx, s in ((x, -1), (x2, -1), (x2, 1), (x, 1)):
            yy = brook_y(xx) + s * 1.15
            P.append((xx, yy, h(xx, brook_y(xx)) + 0.28))
        c = jit(WATER, 0.05, rng)
        quad_auto(wm, P, c, (0, 0, 1), cols=[c, c, mix(c, WATER_LT, 0.25), mix(c, WATER_LT, 0.25)])
        if rng.random() < 0.5:                                # a lick of white water
            fx, fy = x + 1.1, brook_y(x + 1.1) + rng.uniform(-0.7, 0.7)
            fz = h(fx, brook_y(fx)) + 0.3
            quad_auto(wm, [(fx - 0.4, fy - 0.08, fz), (fx + 0.4, fy - 0.08, fz), (fx + 0.3, fy + 0.08, fz), (fx - 0.3, fy + 0.08, fz)], WATER_LT, (0, 0, 1))
        if rng.random() < 0.4:
            rx, ry = x + rng.uniform(0, 2), brook_y(x) + rng.choice((-1, 1)) * rng.uniform(1.0, 1.7)
            nature.rock(pm, rx, ry, h(rx, ry) - 0.1, rng, s=rng.uniform(0.3, 0.7))
        x = x2
    # find the crossing
    by = 82.0
    for _ in range(6):
        by = brook_y(px(by))
    bx = px(by)
    dxdy = (px(by + 0.5) - px(by - 0.5))
    yaw = -math.degrees(math.atan(dxdy))
    B = T(bx, by, 0) @ R("Z", yaw)
    z0, z1 = h(bx, by - 3.6), h(bx, by + 3.6)
    n = 12
    deck = []
    for i in range(n + 1):
        t = i / n
        yy = -3.6 + 7.2 * t
        deck.append(Vector((0, yy, z0 + (z1 - z0) * t + 0.55 * math.sin(math.pi * t) + 0.12)))
    for i in range(n):
        a, b = deck[i], deck[i + 1]
        c = jit(props.WOOD_LT, 0.09, rng)
        pm.beam(B @ a, B @ b, 1.9, 0.09, c, up=(0, 0, 1), grad=1.0)
    for sx in (-1, 1):
        for i in range(0, n + 1, 3):
            p = deck[i] + Vector((sx * 0.88, 0, 0))
            pm.beam(B @ p, B @ (p + Vector((0, 0, 1.0))), 0.09, 0.09, TIMBER_DK)
        for i in range(0, n, 3):
            a = deck[i] + Vector((sx * 0.88, 0, 0.95))
            b = deck[min(n, i + 3)] + Vector((sx * 0.88, 0, 0.95))
            pm.beam(B @ a, B @ b, 0.08, 0.08, TIMBER)
        for end in (0, n):
            p = deck[end] + Vector((sx * 0.88, 0, -0.9))
            props.stone_pile(sm, 0.5, 0.6, 1.0, rng, M=B @ T(p.x, p.y, p.z))
    Z.occ.append((bx, by, 5.0))

    # the lookout: a bench, a signpost, and the whole valley below
    lx, ly = LOOK
    lz = h(lx, ly)
    props.bench(pm, T(lx - 0.5, ly - 1.6, h(lx - 0.5, ly - 1.6)) @ R("Z", 8), L=2.2, rng=rng)
    S0 = T(lx + 2.4, ly - 0.5, h(lx + 2.4, ly - 0.5))
    pm.cyl(0.08, 0.06, 2.3, 6, TIMBER, M=S0)
    for zz, ang, cc in ((2.0, -100, props.WOOD_LT), (1.6, 80, props.WOOD)):
        pm.box((1.0, 0.06, 0.26), cc, M=S0 @ T(0, 0, zz) @ R("Z", ang) @ T(0.45, 0, 0), grad=0.95)
    Z.occ.append((lx, ly, 8.5))
    for k in range(7):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(4.5, 8.0)
        nature.rock(pm, lx + math.cos(a) * rr, ly + math.sin(a) * rr, h(lx + math.cos(a) * rr, ly + math.sin(a) * rr), rng, s=rng.uniform(0.6, 1.5))

    # forest
    fm = Z.mesh("Forest")
    y = -85.0
    while y < 295:
        x = -165.0
        while x < 165:
            tx, ty = x + rng.uniform(-2.6, 2.6), y + rng.uniform(-2.6, 2.6)
            x += 6.2
            if abs(tx - px(ty)) < 5.2 or abs(ty - brook_y(tx)) < 2.6 or not Z.free(tx, ty, 1.0):
                continue
            # keep the view from the lookout open to the south
            if ty < ly + 3 and tx > lx - 9 and abs(tx - lx) < 9 + (ly - ty) * 0.6 and ly - ty < 60:
                continue
            thin = 0.62 * (1 - 0.8 * smoothstep(150, 196, ty) * (1 - smoothstep(25, 60, abs(tx - px(ty)))))   # the wood opens near the top
            if rng.random() > thin * (0.7 + 0.6 * (fbm(tx, ty, 0.03, 2) + 0.5)):
                continue
            near = abs(tx - px(ty)) < 45 and -20 < ty < 200
            hh = rng.uniform(12, 21) if near else rng.uniform(10, 17)
            if rng.random() < 0.1 and near:
                nature.leafy(fm, tx, ty, h(tx, ty), hh * 0.6, rng)
            else:
                nature.pine(fm, tx, ty, h(tx, ty), hh, rng, lod=0 if near else 1, slim=True)
            Z.occ.append((tx, ty, 0.9))
        y += 6.2
    # the forest floor
    for k in range(2600):
        x, y = rng.uniform(-45, 45), rng.uniform(-12, 195)
        if pmask(x, y) > 0.15 or abs(y - brook_y(x)) < 1.6:
            continue
        r = rng.random()
        z = h(x, y)
        if r < 0.72:
            nature.grass_tuft(gm, x, y, z, rng, s=rng.uniform(0.9, 1.6))
        elif r < 0.84:
            nature.flower(gm, x, y, z, rng, col=rng.choice([hexc("#f4f1e8"), hexc("#8fb4e8"), hexc("#f2c232")]))
        elif r < 0.92:                                        # mushrooms
            cap = rng.choice([hexc("#d8433a"), hexc("#d8433a"), hexc("#e8c98a")])
            for i in range(rng.randint(1, 3)):
                mx, my = x + rng.uniform(-0.25, 0.25), y + rng.uniform(-0.25, 0.25)
                s = rng.uniform(0.6, 1.3)
                gm.cyl(0.035 * s, 0.03 * s, 0.16 * s, 5, hexc("#f1e8d2"), M=T(mx, my, h(mx, my)), cap=False)
                gm.cone(0.11 * s, 0.09 * s, 7, cap, M=T(mx, my, h(mx, my) + 0.15 * s), col_top=shade(cap, 1.15))
        elif r < 0.96:
            nature.bush(tm, x, y, z, rng, s=rng.uniform(0.5, 0.9))
        elif r < 0.985:
            nature.rock(pm, x, y, z, rng, s=rng.uniform(0.3, 1.1))
        else:                                                 # fallen log or stump
            if rng.random() < 0.5:
                a = rng.uniform(0, 180)
                L = rng.uniform(2.5, 5)
                pm.cyl(0.26, 0.22, L, 8, hexc("#5f4532"), M=T(x, y, z + 0.2) @ R("Z", a) @ R("X", 90) @ T(0, 0, -L / 2), bottom=True, col_top=hexc("#c9a777"))
            else:
                pm.cyl(0.34, 0.28, 0.5, 8, hexc("#5f4532"), M=T(x, y, z - 0.05), col_top=hexc("#c9a777"))

    # what stands beyond
    bk = Z.mesh("Backdrop")
    world._peak(bk, 40, 820, 640, 600, seed=1.3, base_z=60, rings=54, segs=84, snow_line=0.4, sharp=1.75)
    world._peak(bk, -420, 760, 300, 380, seed=4.1, base_z=40, rings=22, segs=40, snow_line=0.66, sharp=1.5)
    world._peak(bk, 460, 700, 270, 360, seed=7.7, base_z=40, rings=22, segs=40, snow_line=0.7, sharp=1.45)
    for (x, y, hh, r, s) in ((-250, 120, 110, 220, 31), (260, 90, 100, 210, 32), (-280, 360, 160, 230, 35), (270, 380, 150, 230, 36)):
        world._peak(bk, x, y, hh, r, seed=s, base_z=10, rings=16, segs=30, snow_line=9, sharp=1.25, rock_from=0.8)
    far_world(Z, (LOOK[0] + 6, -285, -95), rng)
    cm = Z.mesh("Clouds", "village_cloud")
    cr = random.Random(5)
    for k in range(30):
        a, d = cr.uniform(0, math.tau), cr.uniform(500, 1500)
        _cumulus(cm, math.cos(a) * d, math.sin(a) * d, cr.uniform(330, 520), cr.uniform(35, 75), cr)
    for k in range(7):
        a = k / 7 * math.tau + cr.uniform(-0.2, 0.2)
        _cumulus(cm, 40 + math.cos(a) * 170, 820 + math.sin(a) * 140, 60 + 640 * cr.uniform(0.5, 0.6), cr.uniform(30, 48), cr)

    Z.h = h
    Z.cameras = {
        "trail": ((px(44) + 0.8, 44.0, None), (px(74), 74, h(px(74), 74) + 5), 22),
        "bridge": ((px(by - 9), by - 9, None), (bx, by + 8, h(bx, by) + 4), 24),
        "lookout": ((lx - 1.0, ly + 2.5, None), (lx + 6, ly - 400, -105), 28),
        "upper": ((px(176), 176, None), (40, 700, 300), 22),
    }
    return Z


def _cumulus(m, cx, cy, cz, size, rng, n=None):
    top, bot = hexc("#ffffff"), hexc("#c7d6ea")
    for i in range(n or rng.randint(5, 8)):
        ox = rng.uniform(-1, 1) * size * 1.6
        oy = rng.uniform(-1, 1) * size * 0.9
        oz = rng.uniform(0, 0.45) * size * (1 - abs(ox) / (size * 1.7))
        r = size * rng.uniform(0.45, 0.85) * (1 - 0.35 * abs(ox) / (size * 1.6))
        m.blob(r, top, M=T(cx + ox, cy + oy, cz + oz), rng=rng, sub=1, squash=(1.25, 1.0, 0.62), lumpy=0.12, col_top=top, col_bot=bot)


# =============================================================== 2. the ridge of the third morning
def zone_ridge():
    Z = Zone("Ridge")
    rng = random.Random(2002)

    def cx(y):
        return 10.0 * math.sin(y / 40.0)

    CAMP = (cx(72) + 11.0, 72.0)
    SKYROCK = (cx(128) - 9.5, 128.0)

    def h(x, y):
        zc = 0.17 * y + 3.0 * math.sin(y / 23.0)
        d = x - cx(y)
        wide = 7.5 + 2.0 * math.sin(y / 17.0)
        for (ox, oy), r in ((CAMP, 9.0), (SKYROCK, 6.0)):       # shoulders
            wide = max(wide, wide + 0.0)
        e = abs(d)
        dc = math.hypot(x - CAMP[0], y - CAMP[1])
        ds = math.hypot(x - SKYROCK[0], y - SKYROCK[1])
        z = zc - 0.018 * min(e, wide) ** 2
        if e > wide:
            z -= (e - wide) * 1.25 + ((e - wide) / 14.0) ** 2 * 6
            z += (noise.ridged_multi_fractal(Vector((x * 0.04, y * 0.04, 2.0)), 1.0, 2.0, 3, 1.0, 2.0) - 1.0) * min(9.0, (e - wide) * 0.8)
        # flat shoulders hold the camp and the sky-watching rock
        zs = 0.17 * CAMP[1] + 3.0 * math.sin(CAMP[1] / 23.0) - 0.9
        z += (zs - z) * (1 - smoothstep(6.5, 10.5, dc))
        zr = 0.17 * SKYROCK[1] + 3.0 * math.sin(SKYROCK[1] / 23.0) - 0.4
        z += (zr - z) * (1 - smoothstep(3.5, 6.5, ds))
        z += fbm(x, y, 0.05) * 0.5
        return z

    def px(y):
        return cx(y) + 1.6 * math.sin(y / 9.0)

    def pmask(x, y):
        d = abs(x - px(y)) + fbm(x, y, 0.25, 2) * 0.5
        return 1 - smoothstep(0.7, 1.7, d)

    def col(x, y, z, sl):
        n1, n2 = fbm(x, y, 0.05, 3), fbm(x + 31, y - 9, 0.16, 2)
        c = mix(ALP_A, ALP_B, smoothstep(-0.3, 0.4, n1))
        c = mix(c, GRASS_C, smoothstep(0.1, 0.6, n2) * 0.4)
        c = mix(c, rock_color(x, y, z), smoothstep(0.7, 1.05, sl))
        c = mix(c, mix(DIRT, DIRT2, smoothstep(-0.3, 0.4, n2)), pmask(x, y) * 0.9)
        return c

    grid(Z.mesh("Terrain"), h, col, axis(-130, 130, -36, 36, 1.25, 1.22, 9), axis(-110, 450, -24, 204, 1.25, 1.22, 9))
    sm, pm, tm, gm = Z.mesh("Stonework"), Z.mesh("Props"), Z.mesh("Trees"), Z.mesh("GroundCover")
    path_stones(sm, h, px, -24, 204, rng, spread=0.6, step=(1.0, 2.2))
    y, k = 0.0, 0
    while y < 200:
        if math.hypot(px(y) - CAMP[0], y - CAMP[1]) > 12:
            cairn(pm, h, px(y) + (1.9 if k % 2 else -1.9), y, rng, n=rng.choice((3, 4, 5)))
        y += rng.uniform(16, 24)
        k += 1
    pennant_poles(Z, h, px, (30, 150), rng, half=2.2)
    camp(Z, h, CAMP[0], CAMP[1], 200, rng, lit=False, clear=8.0)                       # morning: the fire has burned out
    # the sky-watching rock: a broad flat slab at the edge of everything
    sx, sy = SKYROCK
    sz = h(sx, sy)
    for (dx, dy, s, sq) in ((0, 0, 2.6, 0.28), (-1.6, 0.6, 1.7, 0.4), (1.2, -1.3, 1.3, 0.5)):
        c = jit(ROCK_C, 0.06, rng)
        sub = Mesh()
        sub.blob(s, c, rng=rng, sub=1, squash=(1.25, 1.0, sq), lumpy=0.14, col_top=shade(c, 1.12), col_bot=shade(c, 0.7))
        Mr = T(sx + dx, sy + dy, sz + s * sq * 0.6) @ R("Z", rng.uniform(0, 360))
        for face in sub.f:
            pm.add([sub.v[i] for i in face], [tuple(range(len(face)))], [sub.c[i] for i in face], M=Mr)
    Z.occ.append((sx, sy, 3.5))
    # boulders, the last wind-bent pines, and a meadow in flower
    for k in range(60):
        x, y = rng.uniform(-30, 30), rng.uniform(-20, 200)
        if pmask(x, y) > 0.1 or not Z.free(x, y, 0.8):
            continue
        nature.rock(pm, x, y, h(x, y), rng, s=rng.uniform(0.3, 1.6) * (1.6 if abs(x - cx(y)) > 9 else 1))
    for k in range(16):
        y = rng.uniform(-22, 40)
        x = cx(y) + rng.choice((-1, 1)) * rng.uniform(4, 12)
        if Z.free(x, y, 1.0):
            nature.pine(tm, x, y, h(x, y), rng.uniform(3.5, 6.5), rng)
            Z.occ.append((x, y, 1.0))
    fl = [hexc("#f4f1e8"), hexc("#f2c232"), hexc("#8fb4e8"), hexc("#d86aa6"), hexc("#f6f0a0"), hexc("#b79ae8")]
    for k in range(5200):
        y = rng.uniform(-22, 202)
        x = cx(y) + rng.gauss(0, 7.5)
        if abs(x - cx(y)) > 17 or pmask(x, y) > 0.15 or not Z.free(x, y, -0.5):
            continue
        z = h(x, y)
        if rng.random() < 0.52:
            nature.grass_tuft(gm, x, y, z, rng, s=rng.uniform(0.7, 1.2))
        else:
            drift = fl[int((fbm(x, y, 0.06, 2) * 0.5 + 0.5) * 5.99) % 6]
            nature.flower(gm, x, y, z, rng, col=drift if rng.random() < 0.75 else rng.choice(fl))

    bk = Z.mesh("Backdrop")
    world._peak(bk, 30, 690, 730, 440, seed=1.3, base_z=-60, rings=58, segs=90, snow_line=0.36, sharp=1.75)
    world._peak(bk, -520, 500, 330, 380, seed=4.1, base_z=-80, rings=22, segs=40, snow_line=0.5, sharp=1.5)
    world._peak(bk, 560, 420, 300, 360, seed=7.7, base_z=-80, rings=22, segs=40, snow_line=0.52, sharp=1.45)
    # the ridge's own flanks, falling away into the clouds
    world._peak(bk, 0, 60, 30, 420, seed=12.5, base_z=-150, rings=20, segs=40, snow_line=9, sharp=0.9)
    far_world(Z, (-30, -1250, -520), rng)
    cm = Z.mesh("Clouds", "village_cloud")
    cr = random.Random(6)
    cloud_sea(cm, -70.0, cr, r_in=170, r_out=1500, cy=-200, gap=lambda x, y: y < -500 and abs(x) < 520 and y > -1700)
    for k in range(7):
        a = k / 7 * math.tau + cr.uniform(-0.2, 0.2)
        _cumulus(cm, 30 + math.cos(a) * 150, 690 + math.sin(a) * 120, -60 + 730 * cr.uniform(0.62, 0.72), cr.uniform(26, 40), cr)
    for k in range(10):
        a, d = cr.uniform(0, math.tau), cr.uniform(500, 1300)
        _cumulus(cm, math.cos(a) * d, math.sin(a) * d, cr.uniform(260, 420), cr.uniform(40, 80), cr)

    Z.h = h
    Z.cameras = {
        "ridge": ((px(8), 8, None), (px(90), 90, h(px(90), 90) + 9), 22),
        "camp": ((CAMP[0] - 6.5, CAMP[1] - 5.5, None), (CAMP[0] + 1.0, CAMP[1] + 1.5, h(*CAMP) + 0.8), 22),
        "sky_rock": ((sx + 7.0, sy - 4.0, None), (sx - 14, sy + 20, sz + 16), 20),
        "back_down": ((px(150), 150, None), (px(60) - 20, -300, -160), 24),
    }
    return Z


# =============================================================== 3. the angel's plateau
def zone_plateau():
    Z = Zone("Plateau")
    rng = random.Random(3003)
    RAD = 34.0

    def px(y):
        return 2.0 * math.sin(y / 9.0) if y < -RAD else 0.0

    def h(x, y):
        r = math.hypot(x, y)
        ang = math.atan2(y, x)
        edge = RAD + 3.0 * fbm(math.cos(ang) * 1.6, math.sin(ang) * 1.6, 1.0, 2)
        z = fbm(x, y, 0.08, 2) * 0.12
        if r > edge:
            e = r - edge
            z -= e * 1.7 + (e / 12.0) ** 2 * 5
            z += (noise.ridged_multi_fractal(Vector((x * 0.05, y * 0.05, 5.0)), 1.0, 2.0, 3, 1.0, 2.0) - 1.0) * min(8.0, e * 0.9)
        # the approach from the south: a ramp of broad steps
        if y < -RAD + 4 and abs(x - px(y)) < 9:
            t = smoothstep(9.0, 3.0, abs(x - px(y)))
            zr = -0.36 * (-RAD + 4 - y)
            z = z + (max(z, zr) - z) * t if zr > z else z
        # the way on: a spur climbing north toward the summit
        if y > RAD - 4 and abs(x) < 8:
            t = smoothstep(8.0, 2.5, abs(x))
            zr = 0.55 * (y - (RAD - 4))
            z = z + (zr - z) * t if zr > z else z
        return z

    def col(x, y, z, sl):
        n1 = fbm(x, y, 0.05, 3)
        r = math.hypot(x, y)
        c = mix(ALP_A, GRASS_C, smoothstep(-0.2, 0.5, n1))
        c = mix(c, rock_color(x, y, z, 1.05), 0.55 + 0.3 * smoothstep(-0.2, 0.3, fbm(x, y, 0.2, 2)))
        c = mix(c, rock_color(x, y, z), smoothstep(0.6, 1.0, sl))
        snow = smoothstep(0.15, 0.5, fbm(x + 50, y, 0.045, 3)) * (1 - smoothstep(0.5, 0.9, sl)) * smoothstep(15, 30, r)
        c = mix(c, mix(SNOW_SH, SNOW, smoothstep(-0.2, 0.3, n1)), snow)
        if r < 26:
            c = mix(c, hexc("#b9bcc8"), 1 - smoothstep(23.5, 25.5, r))          # worn stone under the ruin
        return c

    grid(Z.mesh("Terrain"), h, col, axis(-150, 150, -46, 46, 1.25, 1.22, 9), axis(-150, 150, -70, 62, 1.25, 1.22, 9))
    sm, pm, gm = Z.mesh("Stonework"), Z.mesh("Props"), Z.mesh("GroundCover")

    def hz(x, y):
        return h(x, y) + 0.03

    # the old floor: rings of pale stone around a sun, cracked and half lost
    star_a, star_b = hexc("#6f8fc2"), hexc("#f1ead6")
    m = sm
    for i in range(16):
        a0, a1 = i / 16 * math.tau, (i + 1) / 16 * math.tau
        quad_auto(m, [(0, 0, hz(0, 0) + 0.26), (math.cos(a0) * 0.9, math.sin(a0) * 0.9, hz(0, 0) + 0.26), (math.cos(a1) * 0.9, math.sin(a1) * 0.9, hz(0, 0) + 0.26)], star_b, (0, 0, 1))
    for i in range(12):
        a = i / 12 * math.tau
        tipr = 3.4 if i % 3 == 0 else 2.2
        c = star_a if i % 3 == 0 else shade(star_a, 1.3)
        quad_auto(m, [(math.cos(a - 0.3) * 0.85, math.sin(a - 0.3) * 0.85, hz(0, 0) + 0.262), (math.cos(a + 0.3) * 0.85, math.sin(a + 0.3) * 0.85, hz(0, 0) + 0.262),
                      (math.cos(a) * tipr, math.sin(a) * tipr, hz(0, 0) + 0.262)], c, (0, 0, 1), cols=[c, c, shade(c, 0.85)])
    m.cyl(5.2, 5.2, 0.26, 28, jit(MARBLE[1], 0.03, rng), M=T(0, 0, h(0, 0) - 0.02), col_top=MARBLE[0])       # the dais
    m.cyl(6.0, 6.0, 0.13, 28, jit(MARBLE[3], 0.03, rng), M=T(0, 0, h(0, 0) - 0.02), col_top=MARBLE[1])
    r = 6.6
    ring_i = 0
    while r < 24.0:
        n = max(8, int(math.tau * r / rng.uniform(0.95, 1.2)))
        off = rng.uniform(0, 1)
        blue = ring_i in (3, 11)
        for k in range(n):
            a0, a1 = (k + off + 0.04) / n * math.tau, (k + off + 0.96) / n * math.tau
            am = (a0 + a1) / 2
            lost = fbm(math.cos(am) * r * 0.12, math.sin(am) * r * 0.12, 1.0, 2) > 0.28 - (r / 24.0) * 0.35
            if lost and not blue:
                continue
            c = jit(hexc("#9fb4d6") if blue else rng.choice(MARBLE), 0.05, rng)
            P = [(math.cos(a) * rr, math.sin(a) * rr) for a, rr in ((a0, r - 0.42), (a1, r - 0.42), (a1, r + 0.42), (a0, r + 0.42))]
            quad_auto(m, [(qx, qy, hz(qx, qy)) for qx, qy in P], c, (0, 0, 1))
        r += 0.9
        ring_i += 1
    # the ring of pillars
    NP = 12
    tops = {}
    for i in range(NP):
        a = (i + 0.5) / NP * math.tau
        x, y = math.cos(a) * 20.5, math.sin(a) * 20.5
        z = h(x, y)
        kind = [1.0, 0.45, 1.0, 1.0, 0.2, 0.75, 1.0, 0.0, 0.6, 1.0, 1.0, 0.3][i]
        Hp = 7.2 * kind
        c = jit(rng.choice(MARBLE), 0.04, rng)
        m.box((1.7, 1.7, 0.45), shade(c, 0.95), M=T(x, y, z - 0.1) @ R("Z", math.degrees(a)), grad=0.9)
        m.cyl(0.75, 0.72, 0.25, 10, c, M=T(x, y, z + 0.35))
        if Hp > 0.5:
            nseg = max(1, int(Hp / 1.5))
            for sgi in range(nseg):
                cc = jit(c, 0.04, rng)
                m.cyl(0.62, 0.58, Hp / nseg - 0.03, 10, shade(cc, 0.92), M=T(x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.02, 0.02), z + 0.6 + sgi * Hp / nseg) @ R("Z", rng.uniform(0, 36)), col_top=cc)
            if kind == 1.0:
                m.cyl(0.6, 0.86, 0.35, 10, c, M=T(x, y, z + 0.6 + Hp))
                m.box((1.8, 1.8, 0.3), c, M=T(x, y, z + 0.95 + Hp) @ R("Z", math.degrees(a)), grad=0.95)
                tops[i] = Vector((x, y, z + 1.25 + Hp))
        if kind < 1.0:                                           # what fell lies where it fell
            for q in range(rng.randint(1, 3)):
                fx, fy = x + rng.uniform(-3.5, 3.5), y + rng.uniform(-3.5, 3.5)
                L = rng.uniform(0.9, 2.2)
                cc = jit(c, 0.05, rng)
                m.cyl(0.6, 0.58, L, 10, shade(cc, 0.9), M=T(fx, fy, h(fx, fy) + 0.5) @ R("Z", rng.uniform(0, 360)) @ R("X", 90 + rng.uniform(-6, 6)) @ T(0, 0, -L / 2),
                      bottom=True, col_top=cc)
        Z.occ.append((x, y, 1.6))
    for i, j in ((2, 3), (9, 10)):                               # two lintels still span
        a, b = tops[i], tops[j]
        m.beam(a + Vector((0, 0, 0.15)), b + Vector((0, 0, 0.15)), 1.3, 0.7, jit(MARBLE[1], 0.03, rng), up=(0, 0, 1), grad=0.95)
    bm = Z.mesh("Bunting")
    old = props.BUNTING
    props.BUNTING = [props.SKY_BLUE, props.CLOTH, hexc("#8fb4e8")]
    props.bunting(bm, tops[0], tops[2] + Vector((0, 0, -0.4)), rng, sag=2.2)
    props.BUNTING = old
    # the broken arch on the north side: the way to the summit
    for sx in (-1, 1):
        x, y = sx * 3.2, RAD - 5.0
        props.stone_pile(m, 1.5, 1.5, 6.5 if sx < 0 else 4.2, rng, M=T(x, y, h(x, y) - 0.3), col=MARBLE[1])
    a0 = Vector((-3.2, RAD - 5.0, h(-3.2, RAD - 5) + 6.2))
    for k in range(4):
        t0, t1 = k / 6, (k + 1) / 6
        p0 = a0 + Vector((6.4 * t0, 0, 1.6 * math.sin(math.pi * t0)))
        p1 = a0 + Vector((6.4 * t1, 0, 1.6 * math.sin(math.pi * t1)))
        m.beam(p0, p1, 1.2, 0.9, jit(MARBLE[2], 0.04, rng), up=(0, 1, 0), grad=0.95)
    for i in range(26):                                          # steps cut into the spur beyond it
        y = RAD - 2.0 + i * 1.1
        c = jit(rng.choice(STONE), 0.08, rng)
        m.box((3.0 - i * 0.04, 1.14, 0.5), c, M=T(rng.uniform(-0.1, 0.1), y, h(0, y + 0.55) - 0.32), grad=0.82, faces="yZxX", top=shade(c, 1.1))
    # the south stair
    for i in range(34):
        y = -RAD + 3.0 - i * 1.05
        c = jit(rng.choice(STONE), 0.08, rng)
        x = px(y)
        m.box((4.2, 1.1, 0.6), c, M=T(x, y, h(x, y + 0.55) - 0.56), grad=0.82, faces="yZxX", top=shade(c, 1.1))
    # the last night's camp, at the southern lip, with the journal open beside the fire
    camp(Z, h, -11.0, -27.0, 35, rng, journal=True, lit=True)
    for k in range(40):
        a, rr = rng.uniform(0, math.tau), rng.uniform(22, 40)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        if Z.free(x, y, 0.8) and abs(x) > 4:
            nature.rock(pm, x, y, h(x, y), rng, s=rng.uniform(0.3, 1.8))
    for k in range(900):
        a, rr = rng.uniform(0, math.tau), rng.uniform(6, 33)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        if not Z.free(x, y, 0.2) or (rr < 24 and fbm(x * 0.12, y * 0.12, 1.0, 2) < 0.1):
            continue
        if rng.random() < 0.7:
            nature.grass_tuft(gm, x, y, h(x, y), rng, s=rng.uniform(0.5, 0.9))
        else:
            nature.flower(gm, x, y, h(x, y), rng, col=rng.choice([hexc("#f4f1e8"), hexc("#8fb4e8"), hexc("#b79ae8")]))

    bk = Z.mesh("Backdrop")
    world._peak(bk, 0, 215, 330, 205, seed=1.3, base_z=-40, rings=50, segs=72, snow_line=0.18, sharp=1.75, rock_from=-0.6)      # the summit, right there
    world._peak(bk, 0, 0, 20, 300, seed=14.5, base_z=-160, rings=18, segs=36, snow_line=0.3, sharp=0.85, rock_from=-0.6)          # the plateau's own flanks
    for (x, y, hh, r, s) in ((-900, 500, 260, 420, 4.1), (950, 380, 230, 400, 7.7), (-700, -900, 150, 380, 8.8), (800, -1000, 170, 400, 9.9), (0, 1200, 330, 520, 3.3)):
        world._peak(bk, x, y, hh, r, seed=s, base_z=-160, rings=18, segs=32, snow_line=0.25, sharp=1.5)
    cm = Z.mesh("Clouds", "village_cloud")
    cr = random.Random(7)
    cloud_sea(cm, -36.0, cr, r_in=95, r_out=1700, gap=lambda x, y: math.hypot(x, y - 215) < 150)
    for k in range(14):                                          # fog gathers only at the summit
        a = k / 14 * math.tau + cr.uniform(-0.2, 0.2)
        d = cr.uniform(18, 70)
        _cumulus(cm, math.cos(a) * d, 215 + math.sin(a) * d, -40 + 330 * cr.uniform(0.78, 0.98), cr.uniform(22, 36), cr, n=6)
    for k in range(8):
        a, d = cr.uniform(0, math.tau), cr.uniform(600, 1400)
        _cumulus(cm, math.cos(a) * d, math.sin(a) * d, cr.uniform(160, 330), cr.uniform(40, 80), cr)

    Z.h = h
    Z.cameras = {
        "arrive": ((px(-RAD - 7), -RAD - 7, None), (0, 60, 22), 20),
        "ruin": ((-13, -15, None), (4, 8, 5.5), 20),
        "camp": ((-3.5, -30, None), (-12.5, -26, h(-11, -27) + 0.7), 26),
        "onward": ((0, 8, None), (0, 215, 200), 20),
    }
    return Z


# =============================================================== 4. the summit
def zone_summit():
    Z = Zone("Summit")
    rng = random.Random(4004)

    def px(y):
        return 1.6 * math.sin(y / 5.0) * smoothstep(-4, -12, y)

    def h(x, y):
        r = math.hypot(x, y)
        z = -0.012 * r * r if r < 7 else -0.012 * 49 - (r - 7) * 1.15 - ((r - 7) / 9.0) ** 2 * 4
        z += fbm(x, y, 0.1, 2) * (0.1 + 0.5 * smoothstep(5, 14, r))
        if r > 9:
            z += (noise.ridged_multi_fractal(Vector((x * 0.07, y * 0.07, 8.0)), 1.0, 2.0, 3, 1.0, 2.0) - 1.0) * min(6.0, (r - 9) * 0.8)
        if y < -4 and abs(x - px(y)) < 5:                         # the last stair
            t = smoothstep(5.0, 1.6, abs(x - px(y)))
            zr = -0.6 - 0.62 * (-4 - y)
            if zr > z:
                z += (zr - z) * t
        return z

    def col(x, y, z, sl):
        n1 = fbm(x, y, 0.07, 3)
        c = mix(SNOW_SH, SNOW, smoothstep(-0.35, 0.25, n1))
        rk = smoothstep(0.75, 1.15, sl + fbm(x, y, 0.2, 2) * 0.2)
        return mix(c, rock_color(x, y, z), rk)

    grid(Z.mesh("Terrain"), h, col, axis(-120, 120, -24, 24, 1.0, 1.22, 8), axis(-130, 120, -46, 22, 1.0, 1.22, 8), flat_slope=0.75)
    sm, pm = Z.mesh("Stonework"), Z.mesh("Props")
    for i in range(46):
        y = -5.0 - i * 0.9
        x = px(y)
        c = jit(rng.choice(STONE), 0.08, rng)
        c = mix(c, SNOW, 0.35 if rng.random() < 0.5 else 0.0)
        sm.box((2.2 + rng.uniform(-0.2, 0.2), 0.95, 0.75), c, M=T(x, y, h(x, y + 0.47) - 0.7), grad=0.85, faces="yZxX", top=mix(c, SNOW, 0.5))
    # nothing waits here. Only the flat stone at the very top, and one old pole with a strip of faded blue.
    c = jit(ROCK_C, 0.05, rng)
    sub = Mesh()
    sub.blob(1.5, c, rng=rng, sub=1, squash=(1.3, 1.0, 0.22), lumpy=0.12, col_top=mix(c, SNOW, 0.35), col_bot=shade(c, 0.7))
    for face in sub.f:
        pm.add([sub.v[i] for i in face], [tuple(range(len(face)))], [sub.c[i] for i in face], M=T(0.4, 0.8, h(0.4, 0.8) + 0.12))
    P0 = Vector((-3.4, 1.2, h(-3.4, 1.2) - 0.3))
    tip = P0 + Vector((0.5, 0.15, 3.6))
    pm.beam(P0, tip, 0.09, 0.09, hexc("#7d6a58"))
    faded = hexc("#8aa7d2")
    q = tip + Vector((0, 0, -0.15))
    for k in range(4):
        a = q + Vector((0.34 * k, 0.05 * math.sin(k * 1.4), -0.1 * k))
        b = q + Vector((0.34 * (k + 1), 0.05 * math.sin((k + 1) * 1.4), -0.1 * (k + 1)))
        w0, w1 = 0.5 - 0.09 * k, 0.5 - 0.09 * (k + 1)
        Pq = [a, b, b + Vector((0, 0, -w1)), a + Vector((0, 0, -w0))]
        cc = shade(faded, 1.0 - 0.06 * k)
        quad_auto(pm, Pq, cc, (0, -1, 0))
        quad_auto(pm, Pq, cc, (0, 1, 0))
    for k in range(26):
        a, rr = rng.uniform(0, math.tau), rng.uniform(4, 16)
        x, y = math.cos(a) * rr, math.sin(a) * rr
        if y < -3 and abs(x - px(y)) < 2.5:
            continue
        nature.rock(pm, x, y, h(x, y), rng, s=rng.uniform(0.25, 1.3))

    bk = Z.mesh("Backdrop")
    world._peak(bk, 0, 0, 30, 260, seed=1.3, base_z=-330, rings=40, segs=72, snow_line=0.0, sharp=1.2, rock_from=-0.6)      # the mountain's own shoulders
    for k in range(9):                                            # other summits, far off, breaking the clouds
        a = k / 9 * math.tau + rng.uniform(-0.2, 0.2)
        d = rng.uniform(1100, 2000)
        world._peak(bk, math.cos(a) * d, math.sin(a) * d, rng.uniform(260, 420), rng.uniform(380, 520), seed=60 + k, base_z=-420,
                    rings=14, segs=28, snow_line=0.3, sharp=1.5)
    cm = Z.mesh("Clouds", "village_cloud")
    cr = random.Random(8)
    cloud_sea(cm, -230.0, cr, r_in=200, r_out=2200)
    for k in range(11):                                           # the fog that wraps the top
        a = k / 11 * math.tau + cr.uniform(-0.2, 0.2)
        d = cr.uniform(34, 62)
        _cumulus(cm, math.cos(a) * d, math.sin(a) * d, cr.uniform(-26, -8), cr.uniform(16, 26), cr, n=6)

    Z.h = h
    Z.fog = ((0, 0, -12), 80.0, 0.011, 0.34)       # centre, radius, density, vertical squash: thick around, thin above
    Z.cameras = {
        "last_steps": ((px(-15), -15, None), (0, 3, 3), 20),
        "top": ((1.8, -4.2, None), (-3.0, 6, 3.4), 20),
        "horizon": ((1.5, 3.5, None), (-700, -900, -150), 24),
    }
    return Z


ZONES = {"forest": zone_forest, "ridge": zone_ridge, "plateau": zone_plateau, "summit": zone_summit}
