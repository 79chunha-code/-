"""World layout: the height field, terraces, paths and the big mountain.

Axes: +X east, +Y north (uphill, toward the mountain), +Z up. Units are metres.
The village steps up a hillside in five terraces; the mountain rises behind it."""
import math
from mathutils import Vector, noise

from meshkit import Mesh, hexc, mix, shade, smoothstep

# (centre v, z below, z above)  -- v is "terrace space": y minus the curve of the hillside
BANKS = [(-52.0, 0.0, 4.0), (-18.0, 4.0, 8.0), (22.0, 8.0, 12.5), (52.0, 12.5, 17.0)]
TERRACE_Z = [0.0, 4.0, 8.0, 12.5, 17.0]
LANES_V = [-70.0, -35.0, -2.0, 37.0, 63.5]      # a lane along each terrace
VILLAGE_HALF_W = 52.0
BANK_W, STAIR_W = 0.6, 3.2                  # half-widths of a bank: walled / under the street stairs
GATE_Y = 77.0
PLAZA = (0.0, -2.0, 15.5, 10.0)                 # cx(rel. to street), v centre, half x, half v
MOUNTAIN = (40.0, 640.0, 560.0, 520.0)         # x, y, peak height, base radius

HAZE = hexc("#bcd6ea")


def curve(x):
    return 5.0 * math.sin(x / 28.0) + 2.0 * math.sin(x / 11.0 + 1.0)


def street_x(y):
    """Centre line of the main street / mountain path."""
    x = 3.0 * math.sin(y / 23.0)
    if y > GATE_Y:
        t = y - GATE_Y
        x += 9.0 * math.sin(t / 16.0) * min(1.0, t / 20.0)
    return x


def tv(x, y):
    return y - curve(x)


def fbm(x, y, s=1.0, oct=4):
    return noise.fractal(Vector((x * s, y * s, 3.7)), 1.0, 2.0, oct)


def _ramp(v):
    """The same climb as the terraces, but as one even slope (used where the hillside is wild)."""
    pts = list(zip(LANES_V, TERRACE_Z))
    if v <= pts[0][0]:
        return pts[0][1]
    for (v0, z0), (v1, z1) in zip(pts, pts[1:]):
        if v <= v1:
            return z0 + (z1 - z0) * (v - v0) / (v1 - v0)
    return pts[-1][1]


def height(x, y):
    v = tv(x, y)
    dx = abs(x - street_x(y))
    z = 0.0
    wide = 1.0 - smoothstep(2.6, 3.4, dx)          # banks become stair ramps at the street
    for c, z0, z1 in BANKS:
        s_wall = smoothstep(c - BANK_W, c + BANK_W, v)
        t = min(1.0, max(0.0, (v - (c - STAIR_W)) / (2 * STAIR_W)))
        s_stair = t - 0.5 / (z1 - z0) * math.sin(math.pi * t)      # sits just under the stone steps
        z += (z1 - z0) * (s_wall + (s_stair - s_wall) * wide)
    z += (_ramp(v) - z) * smoothstep(VILLAGE_HALF_W - 4, VILLAGE_HALF_W + 9, abs(x))
    if v < -96:
        z -= ((-96 - v) / 55.0) ** 1.35 * 11.0
    if v > GATE_Y + 2:
        u = (v - GATE_Y - 2) / 45.0
        z += 46.0 * (1.0 - math.exp(-(u ** 1.5) * 0.75))
    side = max(0.0, abs(x) - VILLAGE_HALF_W - 4.0 * math.sin(y / 31.0))
    u = side / 34.0
    z += 30.0 * (1.0 - math.exp(-(u ** 1.6) * 0.8))
    # roughness grows away from the lived-in ground
    wild = smoothstep(0, 22, side) + smoothstep(GATE_Y, GATE_Y + 30, v) + smoothstep(-96, -130, v)
    amp = 0.10 + 2.6 * min(1.0, wild)
    z += fbm(x, y, 0.035) * amp + fbm(x, y, 0.11, 2) * amp * 0.25
    return z


def path_mask(x, y):
    """0..1: how much this spot is trodden path (1 = bare earth)."""
    v = tv(x, y)
    n = fbm(x, y, 0.22, 2) * 0.55
    d_main = abs(x - street_x(y)) + n
    w_main = 2.3 if y < GATE_Y else 1.5
    m = 1.0 - smoothstep(w_main - 0.5, w_main + 0.9, d_main)
    if y < -128:
        m *= smoothstep(-175, -150, y) * 0 + 1
    if abs(x) < VILLAGE_HALF_W - 2:
        for lv in LANES_V:
            d = abs(v - lv) + n
            edge = smoothstep(VILLAGE_HALF_W - 2, VILLAGE_HALF_W - 12, abs(x))
            m = max(m, (1.0 - smoothstep(1.2, 2.3, d)) * edge)
    return m


def plaza_mask(x, y):
    cx, cv, hx, hv = PLAZA
    v = tv(x, y)
    dx = abs(x - street_x(y) - cx) / hx
    dv = abs(v - cv) / hv
    d = (dx ** 4 + dv ** 4) ** 0.25           # squircle
    return 1.0 - smoothstep(0.93, 1.03, d + fbm(x, y, 0.3, 2) * 0.03)


def haze(col, dist, k=2400.0):
    return mix(col, HAZE, 1.0 - math.exp(-dist / k))


# ---------- terrain mesh ----------
def _axis(lo, hi, core_lo, core_hi, step, grow=1.22, max_step=9.0):
    pts = []
    x = core_lo
    while x <= core_hi + 1e-6:
        pts.append(x)
        x += step
    s, x = step, core_lo
    left = []
    while x > lo:
        s = min(max_step, s * grow)
        x -= s
        left.append(x)
    s, x = step, pts[-1]
    right = []
    while x < hi:
        s = min(max_step, s * grow)
        x += s
        right.append(x)
    return left[::-1] + pts + right


G1, G2, G3 = hexc("#7fae52"), hexc("#a3c862"), hexc("#5f9648")
DIRT, DIRT2 = hexc("#c8a676"), hexc("#b08e62")
PAVE = hexc("#958a79")
ROCK = hexc("#8d8a86")
FOREST_FLOOR = hexc("#5b8a45")


def ground_color(x, y, z=None, slope=0.0):
    n1 = fbm(x, y, 0.045, 3)
    n2 = fbm(x + 40, y - 17, 0.15, 2)
    c = mix(G1, G2, smoothstep(-0.25, 0.45, n1))
    c = mix(c, G3, smoothstep(0.05, 0.6, n2) * 0.7)
    side = max(0.0, abs(x) - VILLAGE_HALF_W)
    c = mix(c, FOREST_FLOOR, smoothstep(4, 30, side) * 0.6)
    c = mix(c, ROCK, smoothstep(0.75, 1.25, slope) * 0.75)
    pm = path_mask(x, y)
    c = mix(c, mix(DIRT, DIRT2, smoothstep(-0.3, 0.4, n2)), pm)
    c = mix(c, PAVE, plaza_mask(x, y))
    return c


def build_terrain():
    m = Mesh()
    xs = _axis(-190, 190, -62, 62, 1.25)
    vs = _axis(-260, 215, -100, 92, 1.25)
    # the grid lives in terrace space, with rows exactly on the bank edges, so banks stay crisp
    edges = [c + s * w for c, _, _ in BANKS for s in (-1, 1) for w in (BANK_W, STAIR_W)]
    vs = sorted([v for v in vs if all(abs(v - e) > 0.35 for e in edges)] + edges)
    nx, ny = len(xs), len(vs)
    H = [[height(x, v + curve(x)) for x in xs] for v in vs]
    verts, cols = [], []
    for j, v in enumerate(vs):
        for i, x in enumerate(xs):
            y = v + curve(x)
            z = H[j][i]
            i0, i1 = max(0, i - 1), min(nx - 1, i + 1)
            j0, j1 = max(0, j - 1), min(ny - 1, j + 1)
            sx = (H[j][i1] - H[j][i0]) / (xs[i1] - xs[i0])
            sy = (H[j1][i] - H[j0][i]) / (vs[j1] - vs[j0])
            c = ground_color(x, y, z, math.hypot(sx, sy))
            d = math.hypot(x, y)
            if d > 120:
                c = haze(c, d - 120, 700)
            verts.append((x, y, z))
            cols.append(c)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    m.add(verts, faces, cols, smooth=True)
    return m


# ---------- mountains ----------
SNOW, SNOW_SH = hexc("#f6f9ff"), hexc("#cfdcf0")
MROCK, MROCK2, MROCK3 = hexc("#7d8296"), hexc("#655f78"), hexc("#9a9bb0")
MFOREST, MGRASS = hexc("#4f7f4a"), hexc("#7fa858")


def _peak(m, cx, cy, H, Rb, seed, base_z=0.0, rings=46, segs=72, snow_line=0.62, sharp=1.9, ref=(0, 0), rock_from=0.13):
    verts, cols = [], []
    for r in range(rings + 1):
        t = (r / rings) ** 1.5                      # denser rings near the summit
        for s in range(segs):
            a = s / segs * math.tau
            rr = t * Rb
            # ridged buttresses radiating from the summit
            rid = noise.ridged_multi_fractal(Vector((math.cos(a) * 1.7 + seed, math.sin(a) * 1.7, t * 1.3)), 1.0, 2.1, 4, 1.0, 2.0)
            wob = 1.0 + 0.24 * (rid - 1.0) * smoothstep(0.02, 0.4, t)
            x = cx + math.cos(a) * rr * wob
            y = cy + math.sin(a) * rr * wob
            prof = (1.0 - t) ** sharp                # concave, horn-like profile
            prof = prof * 0.86 + 0.14 * (1.0 - smoothstep(0.0, 0.18, t))  # needle at the very top
            z = base_z + H * prof
            z += (rid - 1.0) * H * 0.12 * smoothstep(0.03, 0.5, t) * (1 - t)
            z += noise.fractal(Vector((x * 0.012, y * 0.012, seed)), 1.0, 2.0, 4) * H * 0.035 * smoothstep(0.05, 0.3, t)
            verts.append((x, y, z))
            hrel = (z - base_z) / H
            nb = noise.fractal(Vector((x * 0.02, y * 0.02, seed + 9)), 1.0, 2.0, 3) * 0.09
            c = mix(MFOREST, MGRASS, smoothstep(-0.2, 0.5, nb * 6))
            band = 0.5 + 0.5 * math.sin(hrel * 46.0 + nb * 30.0)             # faint strata
            rockc = mix(mix(MROCK, MROCK2, smoothstep(-0.05, 0.08, nb)), MROCK3, band * 0.35)
            c = mix(c, rockc, smoothstep(rock_from, rock_from + 0.14, hrel + nb))
            snow = smoothstep(snow_line - 0.06, snow_line + 0.05, hrel + nb * 1.6)
            snow *= 1.0 - 0.75 * smoothstep(0.75, 1.1, rid) * (1 - smoothstep(0.8, 0.95, hrel))  # rock ribs poke through
            c = mix(c, mix(SNOW_SH, SNOW, smoothstep(0.9, 1.3, rid + nb * 3)), snow)
            cols.append(haze(c, math.hypot(x - ref[0], y - ref[1])))
    faces = []
    for r in range(rings):
        for s in range(segs):
            a = r * segs + s
            b = r * segs + (s + 1) % segs
            faces.append((a, a + segs, b + segs, b))
    m.add(verts, faces, cols, smooth=False)


def build_mountains():
    m = Mesh()
    mx, my, mh, mr = MOUNTAIN
    _peak(m, mx, my, mh, mr, seed=1.3, base_z=10.0, rings=54, segs=84, snow_line=0.4, sharp=1.75)
    # shoulders behind / beside the great peak
    _peak(m, -330, 590, 250, 330, seed=4.1, base_z=5, rings=26, segs=44, snow_line=0.68, sharp=1.5)
    _peak(m, 370, 540, 215, 300, seed=7.7, base_z=5, rings=26, segs=44, snow_line=0.72, sharp=1.45)
    _peak(m, -120, 900, 300, 380, seed=2.2, base_z=0, rings=22, segs=40, snow_line=0.6, sharp=1.6)
    _peak(m, 260, 950, 280, 360, seed=5.5, base_z=0, rings=22, segs=40, snow_line=0.6, sharp=1.6)
    # far ranges all around so the horizon is never empty
    import random
    rng = random.Random(11)
    for k in range(26):
        a = k / 26 * math.tau + rng.uniform(-0.08, 0.08)
        d = rng.uniform(950, 1500)
        south = math.sin(a) < -0.2
        h = rng.uniform(70, 150) if south else rng.uniform(140, 300)
        _peak(m, math.cos(a) * d, math.sin(a) * d, h, rng.uniform(260, 420), seed=20 + k, base_z=-40,
              rings=12, segs=24, snow_line=0.8 if south else 0.62, sharp=1.35)
    # near wooded ridges that cradle the valley
    for (x, y, h, r, s) in [(-205, 60, 80, 170, 31), (215, 30, 72, 165, 32), (-230, -150, 55, 190, 33),
                            (240, -170, 50, 180, 34), (-160, 250, 120, 180, 35), (190, 260, 115, 180, 36)]:
        _peak(m, x, y, h, r, seed=s, base_z=-6, rings=16, segs=30, snow_line=9.0, sharp=1.25)
    return m


# ---------- clouds ----------
def build_clouds():
    import random
    from meshkit import T, Sc
    rng = random.Random(5)
    m = Mesh()
    top, bot = hexc("#ffffff"), hexc("#c7d6ea")

    def cloud(cx, cy, cz, size, n):
        for i in range(n):
            ox = rng.uniform(-1, 1) * size * 1.6
            oy = rng.uniform(-1, 1) * size * 0.9
            oz = rng.uniform(0, 0.45) * size * (1 - abs(ox) / (size * 1.7))
            r = size * rng.uniform(0.45, 0.85) * (1 - 0.35 * abs(ox) / (size * 1.6))
            m.blob(r, top, M=T(cx + ox, cy + oy, cz + oz), rng=rng, sub=1, squash=(1.25, 1.0, 0.62),
                   lumpy=0.12, col_top=top, col_bot=bot)

    mx, my, mh, _ = MOUNTAIN
    for k in range(9):                               # a torn ring around the summit
        a = k / 9 * math.tau + rng.uniform(-0.2, 0.2)
        if rng.random() < 0.25:
            continue
        d = rng.uniform(120, 190)
        cloud(mx + math.cos(a) * d, my + math.sin(a) * d * 0.8, mh * rng.uniform(0.5, 0.62), rng.uniform(28, 46), 7)
    for k in range(34):                              # fair-weather cumulus
        a = rng.uniform(0, math.tau)
        d = rng.uniform(380, 1300)
        cloud(math.cos(a) * d, math.sin(a) * d, rng.uniform(230, 420), rng.uniform(30, 70), rng.randint(5, 9))
    return m
