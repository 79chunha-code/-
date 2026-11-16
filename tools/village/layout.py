"""Where everything stands: houses on their terraces, the plaza with its stage, walls, stairs, trees."""
import math
import random
from mathutils import Vector

import world
import house
import props
import nature
from meshkit import Mesh, hexc, mix, shade, jit, smoothstep, T, R
from house import quad_auto, wall_matrix, wbox, STONE, ROOF_SLATE

H = world.height
VCOL = "village_vcol"


def site(xr, v):
    """Terrace-space (offset from the street, v) -> world (x, y)."""
    x = xr + world.street_x(v)
    return x, v + world.curve(x)


def lane_yaw(x):
    return math.degrees(math.atan(5.0 / 28.0 * math.cos(x / 28.0) + 2.0 / 11.0 * math.cos(x / 11.0 + 1.0)))


FACE = {"S": 0.0, "N": 180.0, "E": 90.0, "W": -90.0}

# name, xr, v, facing, spec
HOUSES = [
    # terrace 0: by the entrance
    ("Inn", 20, -61.5, "S", dict(seed=21, w=10.5, d=7.0, floors=2, sign="inn", chimneys=2, accent=hexc("#3d5d8c"))),
    ("Farmhouse", -22, -62, "S", dict(seed=22, w=8.6, d=6.4, floors=1, pitch=1.38, moss=0.4)),
    ("Barn", -40, -80, "N", dict(seed=23, w=8.0, d=6.2, floors=1, pitch=1.3, win_prob=0.15, chimneys=0,
                                 plaster=hexc("#b08a5e"), door_w=1.9, door_h=2.3, base_h=0.3)),
    # terrace 1
    ("Rota_House", -21, -27.2, "S", dict(seed=5, w=6.4, d=5.2, floors=1, pitch=1.42, accent=hexc("#2f6f7a"),
                                         plaster=hexc("#f3ead8"), roof=hexc("#b85a3c"))),
    ("House_A", -38, -27, "S", dict(seed=31, w=7.4, d=5.8, floors=2)),
    ("Bakery", 15, -27, "S", dict(seed=32, w=8.2, d=6.0, floors=2, sign="bakery", chimneys=2)),
    ("House_B", 33.5, -27.3, "S", dict(seed=33, w=6.4, d=5.4, floors=1, door_wall="gable", pitch=1.35)),
    ("House_C", -29, -43.2, "N", dict(seed=34, w=7.0, d=5.6, floors=2)),
    ("House_D", 28, -43.2, "N", dict(seed=35, w=7.6, d=5.8, floors=2)),
    # terrace 2: around the plaza
    ("Shop", -23, -5, "E", dict(seed=41, w=7.6, d=6.0, floors=2, sign="shop")),
    ("House_E", -38, 6, "S", dict(seed=42, w=7.0, d=5.6, floors=2)),
    ("House_F", 27.5, 6.5, "S", dict(seed=43, w=8.0, d=6.0, floors=2)),
    ("House_G", 31, -11, "N", dict(seed=44, w=6.8, d=5.5, floors=1, pitch=1.36)),
    # terrace 3
    ("House_H", -36, 45, "S", dict(seed=51, w=7.2, d=5.8, floors=2)),
    ("House_I", -16, 45.2, "S", dict(seed=52, w=6.2, d=5.3, floors=1, door_wall="gable", pitch=1.4)),
    ("Smithy", 14, 45, "S", dict(seed=53, w=8.0, d=6.0, floors=2, sign="smith", stone_ground=True, chimneys=2)),
    ("House_J", 33, 45.2, "S", dict(seed=54, w=7.0, d=5.6, floors=2)),
    ("House_K", 23, 29.3, "N", dict(seed=55, w=6.6, d=5.4, floors=1, pitch=1.36)),
    ("House_L", -26, 29.3, "N", dict(seed=56, w=7.2, d=5.6, floors=2)),
    # terrace 4: the last houses before the mountain
    ("Caelum_House", 19, 70.0, "S", dict(seed=9, w=7.0, d=5.6, floors=1, pitch=1.5, moss=0.75, lean=1.8,
                                         plaster=hexc("#e3d6bb"), roof=hexc("#8f4a36"), accent=hexc("#3f6fb5"))),
    ("House_M", -21, 70.0, "S", dict(seed=61, w=7.0, d=5.6, floors=2)),
]


class Scene:
    def __init__(self):
        self.rng = random.Random(7)
        self.out = {}
        self.occ = []                     # (x, y, r): keep trees and grass out of here

    def mesh(self, name):
        if name not in self.out:
            self.out[name] = (Mesh(), VCOL)
        return self.out[name][0]

    def free(self, x, y, r=0.0):
        return all((x - ox) ** 2 + (y - oy) ** 2 > (orr + r) ** 2 for ox, oy, orr in self.occ)


def frame(x, y, yaw, z=None, dz=0.0):
    return T(x, y, (H(x, y) if z is None else z) + dz) @ R("Z", yaw)


# ---------------------------------------------------------------- buildings
def place_houses(S):
    info = {}
    for name, xr, v, face, spec in HOUSES:
        x, y = site(xr, v)
        yaw = FACE[face] + lane_yaw(x)
        hm, hi = house.build_house(**spec)
        if spec.get("door_wall") == "gable":
            yaw += 90.0
        M = frame(x, y, yaw, dz=-0.05)
        S.mesh(name).merge(hm, M=M)
        S.occ.append((x, y, max(spec["w"], spec["d"]) / 2 + 1.6))
        info[name] = dict(x=x, y=y, yaw=yaw, M=M, spec=spec, face=face)
    return info


def place_hall(S):
    rng = random.Random(77)
    x, y = site(-11.0, 13.3)
    yaw = lane_yaw(x)
    hm, hi = house.build_house(seed=70, w=13.0, d=8.2, floors=2, h1=3.3, h2=2.8, base_h=0.7, pitch=1.12, roof=ROOF_SLATE,
                               plaster=hexc("#f1e6cf"), accent=hexc("#3f6fb5"), stone_ground=True, chimneys=2, door_w=1.9,
                               door_h=2.6, lean=0.5, moss=0.12, win_prob=0.8, door_col=hexc("#3f6fb5"))
    M = frame(x, y, yaw, dz=-0.05)
    m = S.mesh("Village_Hall")
    m.merge(hm, M=M)
    tw = props.tower(rng, hexc("#f1e6cf"))
    Mt = M @ T(13.0 / 2 + 2.0, -8.2 / 2 + 2.0, -0.3)
    m.merge(tw, M=Mt)
    for dx in (-3.6, 3.6):                              # sky-blue banners either side of the door
        p = M @ Vector((dx, -8.2 / 2 - 0.5, 0.7 + 3.3 + 2.4))
        nrm = M.to_3x3() @ Vector((0, -1, 0))
        props.banner(m, p, nrm, 1.0, 3.0, props.SKY_BLUE, rng)
    S.occ.append((x, y, 8.5))
    tx, ty, _ = Mt @ Vector((0, 0, 0))
    S.occ.append((tx, ty, 3.6))
    return dict(M=M, tower=Mt)


def place_stage(S):
    rng = random.Random(88)
    x, y = site(12.4, -2.0)
    yaw = -90 + lane_yaw(x)
    M = frame(x, y, yaw, dz=-0.03)
    S.mesh("Shadow_Stage").merge(props.stage(rng), M=M)
    S.occ.append((x, y, 5.2))
    bm = S.mesh("Props")
    for row in range(4):                                # benches facing the stage
        for k in (-1, 1):
            bx, by = site(6.6 - row * 1.45, -2.0 + k * 1.85)
            props.bench(bm, frame(bx, by, yaw + 0 + rng.uniform(-3, 3)) @ R("Z", 0), L=3.0, rng=rng)
    return M


def place_gates(S):
    rng = random.Random(99)
    gy = world.GATE_Y
    gx = world.street_x(gy)
    Mg = frame(gx, gy, 0, dz=0.0)
    S.mesh("Mountain_Gate").merge(props.mountain_gate(rng), M=Mg)
    S.occ.append((gx, gy, 4.0))
    ey = -99.0
    ex = world.street_x(ey)
    S.mesh("Entry_Arch").merge(props.entry_arch(rng), M=frame(ex, ey, 0))
    S.occ.append((ex, ey, 4.0))


# ---------------------------------------------------------------- stonework
def retaining_walls(S):
    rng = random.Random(123)
    m = S.mesh("Stonework")
    for c, z0, z1 in world.BANKS:
        def pt(x, dv=-0.75):
            return x, c + dv + world.curve(x)
        rows = max(3, int(round((z1 - z0 + 0.4) / 0.62)))
        for k in range(rows):
            x = -53.0 + (0.6 if k % 2 else 0.0)
            while x < 53.0:
                w = rng.uniform(0.95, 1.7)
                xa, xb = x, x + w
                x = xb
                xm = (xa + xb) / 2
                ya, yb = pt(xa)[1], pt(xb)[1]
                ym = (ya + yb) / 2
                if abs(xm - world.street_x(ym)) < 3.4 + w / 2:
                    continue
                zl = H(xm, c - 0.9 + world.curve(xm))
                zh = H(xm, c + 0.9 + world.curve(xm))
                if zh - zl < 0.9:
                    continue
                u = Vector((xb - xa, yb - ya, 0)).normalized()
                n = Vector((u.y, -u.x, 0))
                zb = zl - 0.45
                ch = (zh - zb) / rows
                Mw = wall_matrix((xa, ya, zb + k * ch), u, n)
                col = jit(rng.choice(STONE), 0.11, rng)
                if rng.random() < 0.16:
                    col = mix(col, hexc("#7f9a5a"), rng.uniform(0.25, 0.55))      # mossy stone
                L = math.hypot(xb - xa, yb - ya)
                if k < rows - 1:
                    wbox(m, Mw, 0.015, L - 0.015, 0.012, ch, -0.3, rng.uniform(0.0, 0.07), col, grad=0.84, faces="yZ")
                else:                                    # cap course runs back to the upper ground
                    wbox(m, Mw, 0.015, L - 0.015, 0.012, ch + 0.03, -1.5, rng.uniform(0.04, 0.1), col, grad=0.9, faces="yZ",
                         top=shade(col, 1.08))
                    if rng.random() < 0.55:              # a broken line of parapet stones
                        pc = jit(rng.choice(STONE), 0.11, rng)
                        wbox(m, Mw, 0.05, L - 0.05, ch + 0.03, ch + 0.03 + rng.uniform(0.28, 0.45), -0.42, 0.05, pc, grad=0.9,
                             faces="xXyYZ", top=shade(pc, 1.1))


def stairs(S):
    rng = random.Random(321)
    m = S.mesh("Stonework")
    pm = S.mesh("Props")
    for c, z0, z1 in world.BANKS:
        x0 = world.street_x(c)
        for _ in range(3):
            x0 = world.street_x(c + world.curve(x0))
        yc = c + world.curve(x0)
        M = T(x0, yc, 0) @ R("Z", lane_yaw(x0))
        n = int(round((z1 - z0) / 0.19))
        run = 2 * world.STAIR_W / n
        rise = (z1 - z0) / n
        for i in range(n):
            col = jit(STONE[2] if i % 2 else STONE[0], 0.07, rng)
            m.box((4.7, run + 0.03, rise + 0.3), col, M=M @ T(0, -world.STAIR_W + (i + 0.5) * run, z0 + (i + 1) * rise - rise - 0.3),
                  grad=0.8, faces="yZ", top=shade(col, 1.1))
        for sx in (-1, 1):                               # stepped cheek walls
            nb = 5
            for k in range(nb):
                y_a = -world.STAIR_W + k * 2 * world.STAIR_W / nb
                top = z0 + (z1 - z0) * (k + 1) / nb + 0.55
                col = jit(rng.choice(STONE), 0.1, rng)
                m.box((1.15, 2 * world.STAIR_W / nb + 0.02, top - (z0 - 0.6)), col,
                      M=M @ T(sx * 2.9, y_a + world.STAIR_W / nb, z0 - 0.6), grad=0.82, top=shade(col, 1.1))
            for (yy, zz) in ((-world.STAIR_W - 0.45, z0), (world.STAIR_W + 0.45, z1)):   # newel piers with lanterns
                P = M @ T(sx * 2.9, yy, zz - 0.4)
                props.stone_pile(m, 1.0, 1.0, 1.75, rng, M=P)
                m.box((1.2, 1.2, 0.14), shade(STONE[2], 1.08), M=P @ T(0, 0, 1.75), grad=1.0)
                if zz == z1:
                    props.lantern_post(pm, P @ T(0, 0, 1.89) @ R("Z", 90 + 90 * sx), h=2.2, rng=rng)
        S.occ.append((x0, yc, 5.0))


def plaza_paving(S):
    rng = random.Random(55)
    m = S.mesh("Stonework")
    cx, cy = site(0.0, world.PLAZA[1])
    cols = [hexc("#d2c6ae"), hexc("#c4b79f"), hexc("#b9ad98"), hexc("#cfc0a6"), hexc("#b0a694")]

    def hz(x, y):
        return H(x, y) + 0.03

    # the sun-and-sky compass at the heart of the plaza
    star_a, star_b = hexc("#5f7fae"), hexc("#e9dfc6")
    for i in range(16):
        a0, a1, am = i / 16 * math.tau, (i + 1) / 16 * math.tau, (i + 0.5) / 16 * math.tau
        r_tip = 1.55 if i % 2 == 0 else 0.0
        c = star_a if (i // 2) % 2 == 0 else star_b
        p0 = (cx, cy, hz(cx, cy) + 0.012)
        p1 = (cx + math.cos(a0) * 0.62, cy + math.sin(a0) * 0.62, hz(cx, cy) + 0.012)
        p2 = (cx + math.cos(a1) * 0.62, cy + math.sin(a1) * 0.62, hz(cx, cy) + 0.012)
        quad_auto(m, [p0, p1, p2], star_b, (0, 0, 1))
    for i in range(8):
        a = i / 8 * math.tau
        tipr = 1.75 if i % 2 == 0 else 1.25
        c = star_a if i % 2 == 0 else shade(star_a, 1.3)
        w = 0.42
        p0 = (cx + math.cos(a - w) * 0.6, cy + math.sin(a - w) * 0.6, hz(cx, cy) + 0.016)
        p1 = (cx + math.cos(a + w) * 0.6, cy + math.sin(a + w) * 0.6, hz(cx, cy) + 0.016)
        p2 = (cx + math.cos(a) * tipr, cy + math.sin(a) * tipr, hz(cx, cy) + 0.016)
        quad_auto(m, [p0, p1, p2], c, (0, 0, 1), cols=[c, c, shade(c, 0.85)])
    # rings of setts around it
    r = 1.95
    ring_i = 0
    while r < 8.3:
        n = max(8, int(math.tau * r / rng.uniform(0.7, 0.86)))
        off = rng.uniform(0, 1)
        blue_ring = ring_i in (0, 5)
        for k in range(n):
            a0, a1 = (k + off + 0.05) / n * math.tau, (k + off + 0.95) / n * math.tau
            ri, ro = r - 0.33, r + 0.33
            c = jit(hexc("#9fb0c8") if blue_ring else rng.choice(cols), 0.07, rng)
            P = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr) for a, rr in ((a0, ri), (a1, ri), (a1, ro), (a0, ro))]
            quad_auto(m, [(px, py, hz(px, py)) for px, py in P], c, (0, 0, 1))
        r += 0.72
        ring_i += 1
    # the rest of the plaza: an irregular field of flagstones
    cxp, cvp, hx, hv = world.PLAZA
    step = 0.86
    y = cy - hv - 6
    while y < cy + hv + 6:
        x = cx - hx - 3
        row = int(round(y / step))
        while x < cx + hx + 3:
            px = x + (0.43 if row % 2 else 0) + rng.uniform(-0.08, 0.08)
            py = y + rng.uniform(-0.08, 0.08)
            x += step
            if math.hypot(px - cx, py - cy) < 8.55 or world.plaza_mask(px, py) < 0.6:
                continue
            w, d = rng.uniform(0.33, 0.4), rng.uniform(0.33, 0.4)
            a = rng.uniform(-0.2, 0.2)
            c = jit(rng.choice(cols), 0.07, rng)
            P = []
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                qx = px + (sx * w * math.cos(a) - sy * d * math.sin(a))
                qy = py + (sx * w * math.sin(a) + sy * d * math.cos(a))
                P.append((qx, qy, hz(qx, qy)))
            m.add(P, [(0, 1, 2, 3)], [c] * 4)
        y += step


def stepping_stones(S):
    """Worn flat stones set into the street and the mountain path."""
    rng = random.Random(66)
    m = S.mesh("Stonework")
    cols = [hexc("#d6c6a4"), hexc("#cdbb98"), hexc("#dccfb0")]
    y = -128.0
    while y < 150:
        y += rng.uniform(0.45, 0.9) if y < world.GATE_Y else rng.uniform(1.0, 2.0)
        v = world.tv(world.street_x(y), y)
        if any(abs(v - c) < world.STAIR_W + 0.6 for c, _, _ in world.BANKS):
            continue
        for _ in range(2 if y < world.GATE_Y else 1):
            x = world.street_x(y) + rng.uniform(-1.6, 1.6) * (1.0 if y < world.GATE_Y else 0.45)
            if world.plaza_mask(x, y) > 0.3:
                continue
            w, d, a = rng.uniform(0.17, 0.3), rng.uniform(0.14, 0.24), rng.uniform(0, math.pi)
            c = jit(rng.choice(cols), 0.06, rng)
            P = []
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                qx = x + (sx * w * math.cos(a) - sy * d * math.sin(a))
                qy = y + (sx * w * math.sin(a) + sy * d * math.cos(a))
                P.append((qx, qy, H(qx, qy) + 0.02))
            m.add(P, [(0, 1, 2, 3)], [c] * 4)


# ---------------------------------------------------------------- dressing
def dress_plaza(S, hall):
    rng = random.Random(202)
    m = S.mesh("Props")
    v0 = world.PLAZA[1]
    # tall poles at the corners, strung with bunting
    poles = {}
    for key, (xr, dv) in {"SW": (-13.6, -8.4), "SE": (13.8, -8.6), "NE": (13.6, 8.2), "NW": (-13.4, 6.0)}.items():
        x, y = site(xr, v0 + dv)
        z = H(x, y)
        m.cyl(0.13, 0.08, 6.2, 7, house.TIMBER, M=T(x, y, z - 0.3))
        m.box((0.5, 0.5, 0.45), jit(STONE[0], 0.06, rng), M=T(x, y, z - 0.1), grad=0.85)
        m.blob(0.14, hexc("#e0b84a"), M=T(x, y, z + 5.98), sub=0, lumpy=0)
        poles[key] = Vector((x, y, z + 5.75))
        S.occ.append((x, y, 0.8))
    bm = S.mesh("Bunting")
    for a, b in (("SW", "NE"), ("NW", "SE"), ("SW", "SE"), ("NW", "NE"), ("SW", "NW")):
        props.bunting(bm, poles[a], poles[b], rng, sag=1.1 if a + b in ("SWNE", "NWSE") else 0.8)
    tw = hall["tower"] @ Vector((0, -2.3, 9.6))
    props.bunting(bm, tw, poles["NE"], rng, sag=1.3)
    # market stalls along the south edge, facing into the plaza
    for xr, dv, yaw in ((-9.5, -8.0, 180), (-4.6, -8.6, 180), (7.2, -8.4, 180)):
        x, y = site(xr, v0 + dv)
        props.stall(m, frame(x, y, yaw + lane_yaw(x) + rng.uniform(-6, 6)), rng)
        S.occ.append((x, y, 2.2))
        for k in range(rng.randint(2, 4)):
            px, py = x + rng.uniform(-2.4, 2.4), y - rng.uniform(1.3, 2.2)
            Mp = frame(px, py, rng.uniform(0, 360))
            rng.choice((props.barrel, props.crate, props.sack))(m, Mp, rng)
    x, y = site(-13.0, v0 - 3.5)
    props.cart(m, frame(x, y, 25), rng)
    S.occ.append((x, y, 2.0))
    # lantern posts round the square
    for xr, dv in ((-15.3, 1.5), (15.4, 5.0), (-6.0, 9.6), (6.5, -10.2), (-15.2, -6.0)):
        x, y = site(xr, v0 + dv)
        ang = math.degrees(math.atan2(site(0, v0)[1] - y, site(0, v0)[0] - x))
        props.lantern_post(m, frame(x, y, ang), rng=rng)
        S.occ.append((x, y, 0.6))
    # the blossom tree, with a ring bench under it
    x, y = site(8.2, v0 + 15.0)
    tm = S.mesh("Trees")
    nature.leafy(tm, x, y, H(x, y), 9.5, random.Random(4), palette=nature.BLOSSOM)
    S.occ.append((x, y, 2.4))
    for k in range(6):
        a = k / 6 * math.tau
        props.bench(m, frame(x + math.cos(a) * 1.9, y + math.sin(a) * 1.9, math.degrees(a) + 90), L=1.7, rng=rng)
    pm = S.mesh("GroundCover")
    prng = random.Random(8)
    for k in range(70):                                  # fallen petals
        a, rr = prng.uniform(0, math.tau), prng.uniform(0.3, 5.5)
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        s = prng.uniform(0.05, 0.09)
        c = prng.choice(nature.BLOSSOM)
        zz = H(px, py) + 0.045
        pm.add([(px - s, py, zz), (px, py - s, zz), (px + s, py, zz), (px, py + s, zz)], [(0, 1, 2, 3)], [c] * 4)


def dress_houses(S, info):
    rng = random.Random(404)
    m = S.mesh("Props")
    gm = S.mesh("GroundCover")
    tm = S.mesh("Trees")
    for name, hi in info.items():
        sp = hi["spec"]
        w, d = sp["w"], sp["d"]
        gable = sp.get("door_wall") == "gable"
        Mh = hi["M"] @ (R("Z", -90) if gable else R("Z", 0))        # frame with the door on -Y
        fw, fd = (d, w) if gable else (w, d)

        def loc(a, b):
            p = Mh @ Vector((a, b, 0))
            return p.x, p.y

        # things leaning against the walls
        for k in range(rng.randint(2, 4)):
            side = rng.choice((-1, 1))
            a, b = side * (fw / 2 + rng.uniform(0.6, 1.1)), rng.uniform(-fd / 2, fd / 2)
            x, y = loc(a, b)
            if not S.free(x, y, -1.0) and False:
                continue
            kind = rng.random()
            if kind < 0.4:
                props.barrel(m, frame(x, y, rng.uniform(0, 360)), rng)
            elif kind < 0.65:
                props.crate(m, frame(x, y, rng.uniform(0, 90)), rng, s=rng.uniform(0.55, 0.8))
            else:
                nature.bush(tm, x, y, H(x, y), rng, s=rng.uniform(0.7, 1.1))
        # flowers and tufts along the front
        for k in range(rng.randint(8, 14)):
            a = rng.uniform(-fw / 2, fw / 2)
            if abs(a) < 1.2:
                continue
            x, y = loc(a, -fd / 2 - rng.uniform(0.5, 1.3))
            if rng.random() < 0.6:
                nature.flower(gm, x, y, H(x, y), rng)
            else:
                nature.grass_tuft(gm, x, y, H(x, y), rng, s=0.9)
        # worn doorstep path to the lane
        for k in range(1, 5):
            x, y = loc(rng.uniform(-0.25, 0.25), -fd / 2 - 1.2 - k * 0.85)
            if world.path_mask(x, y) > 0.5 or world.plaza_mask(x, y) > 0.5:
                break
            s, a = rng.uniform(0.2, 0.3), rng.uniform(0, math.pi)
            c = jit(hexc("#d3c4a3"), 0.07, rng)
            P = [(x + math.cos(a + q) * s, y + math.sin(a + q) * s * 0.8) for q in (0.3, 1.9, 3.3, 4.8)]
            S.mesh("Stonework").add([(px, py, H(px, py) + 0.035) for px, py in P], [(0, 1, 2, 3)], [c] * 4)

    # --- Rota's house: a garden, washing on the line, and a training dummy
    hi = info["Rota_House"]
    Mh = hi["M"]
    sp = hi["spec"]

    def rl(a, b):
        p = Mh @ Vector((a, b, 0))
        return p.x, p.y

    g0, g1 = rl(-sp["w"] / 2 - 4.6, -sp["d"] / 2 - 0.3), rl(-sp["w"] / 2 - 0.6, -sp["d"] / 2 - 0.3)
    g2, g3 = rl(-sp["w"] / 2 - 0.6, -sp["d"] / 2 - 4.2), rl(-sp["w"] / 2 - 4.6, -sp["d"] / 2 - 4.2)
    props.fence(m, [g1, g0, g3, g2], H, rng, h=0.85)
    for r in range(4):                                             # vegetable rows
        for k in range(7):
            x, y = rl(-sp["w"] / 2 - 4.1 + k * 0.5, -sp["d"] / 2 - 1.0 - r * 0.85)
            c = [hexc("#6fae4a"), hexc("#8fc25a"), hexc("#4f9440"), hexc("#a7cf5e")][r]
            tm.blob(0.2, jit(c, 0.1, rng), M=T(x, y, H(x, y) + 0.12), rng=rng, sub=0, squash=(1, 1, 0.8), lumpy=0.15)
            if r == 1 and k % 2 == 0:
                tm.blob(0.09, hexc("#e8554e"), M=T(x + 0.1, y, H(x, y) + 0.28), rng=rng, sub=0, lumpy=0.05)
    a, b = rl(sp["w"] / 2 + 1.0, -1.5), rl(sp["w"] / 2 + 4.6, -2.2)
    props.laundry(m, (a[0], a[1], H(*a)), (b[0], b[1], H(*b)), rng)
    dx, dy = rl(2.6, -sp["d"] / 2 - 3.4)
    dz = H(dx, dy)
    Md = T(dx, dy, dz) @ R("Z", hi["yaw"] + 20)                    # training dummy: Rota means to be a hero
    m.cyl(0.07, 0.06, 1.75, 6, house.TIMBER_DK, M=Md)
    m.beam(Md @ Vector((-0.55, 0, 1.3)), Md @ Vector((0.55, 0, 1.3)), 0.07, 0.07, house.TIMBER_DK)
    m.blob(0.3, hexc("#cdb98c"), M=Md @ T(0, 0, 1.05), rng=rng, sub=1, squash=(1, 0.8, 1.3), lumpy=0.06)
    m.blob(0.19, hexc("#d8c79c"), M=Md @ T(0, 0, 1.72), rng=rng, sub=1, lumpy=0.05)
    m.cyl(0.21, 0.17, 0.2, 8, hexc("#77767e"), M=Md @ T(0, 0, 1.78))            # pot for a helmet
    m.beam(Md @ Vector((0.55, -0.02, 1.3)), Md @ Vector((1.05, -0.3, 0.75)), 0.05, 0.03, props.WOOD_LT)   # wooden sword
    m.beam(Md @ Vector((0.5, -0.1, 1.2)), Md @ Vector((0.64, 0.06, 1.34)), 0.04, 0.04, props.WOOD)
    S.occ.append((dx, dy, 1.2))

    # --- Caelum's house: kept as it was. An old tree, a child's swing, a stone with flowers.
    hi = info["Caelum_House"]
    Mh = hi["M"]
    sp = hi["spec"]

    def cl(a, b):
        p = Mh @ Vector((a, b, 0))
        return p.x, p.y

    tx, ty = cl(sp["w"] / 2 + 4.6, -1.0)
    tz = H(tx, ty)
    trng = random.Random(12)
    nature.leafy(tm, tx, ty, tz, 8.5, trng, palette=[hexc("#5d9a48")])
    S.occ.append((tx, ty, 2.0))
    br0 = Vector((tx - 0.4, ty - 0.2, tz + 3.9))
    br1 = Vector((tx - 2.9, ty - 1.3, tz + 4.3))
    m.beam(br0, br1, 0.2, 0.2, nature.BARK)
    along = (br1 - br0).normalized()
    s0, s1 = br0 + along * 1.5, br0 + along * 2.3
    seat0, seat1 = s0 + Vector((0.05, 0.1, -3.2)), s1 + Vector((0.05, 0.1, -3.2))
    for a, b in ((s0, seat0), (s1, seat1)):
        m.beam(a, b, 0.025, 0.025, hexc("#b9a47a"), grad=1.0, faces="xXyY")
    m.beam(seat0 - along * 0.12, seat1 + along * 0.12, 0.3, 0.05, props.WOOD, grad=1.0)
    sx, sy = cl(-1.8, -sp["d"] / 2 - 3.0)
    sz = H(sx, sy)
    Ms = T(sx, sy, sz - 0.15) @ R("Z", hi["yaw"] + 8)
    c = hexc("#9a968f")
    m.box((0.75, 0.3, 1.25), c, M=Ms, taper=0.8, grad=0.85, top=shade(c, 1.1))
    m.box((1.1, 0.6, 0.2), shade(c, 0.9), M=Ms, grad=0.9)
    ring = [Ms @ Vector((math.cos(a) * 0.17, -0.155, 0.9 + math.sin(a) * 0.17)) for a in [i / 10 * math.tau for i in range(10)]]
    quad_auto(m, ring, hexc("#5f7fae"), Ms.to_3x3() @ Vector((0, -1, 0)))
    for k in range(9):
        fx, fy = sx + rng.uniform(-0.7, 0.7), sy + rng.uniform(-0.75, -0.3)
        nature.flower(gm, fx, fy, H(fx, fy), rng, col=rng.choice([hexc("#f4f1e8"), hexc("#8fb4e8"), hexc("#f6f0a0")]))
    S.occ.append((sx, sy, 1.0))
    p = Mh @ Vector((2.2, -sp["d"] / 2 - 0.22, 3.0))
    props.banner(S.mesh("Caelum_House"), p, Mh.to_3x3() @ Vector((0, -1, 0)), 0.7, 1.5, props.SKY_BLUE, rng)


def dress_edges(S):
    """Entrance road, fields, the first stretch of the mountain path."""
    rng = random.Random(505)
    m = S.mesh("Props")
    gm = S.mesh("GroundCover")
    # fields south of the village
    for (xa, xb, ya, yb, kind) in ((-52, -12, -150, -108, "wheat"), (12, 50, -146, -110, "greens")):
        rows = int((xb - xa) / 1.3)
        for r in range(rows):
            x0 = xa + r * 1.3
            if kind == "wheat":
                c = jit(hexc("#e2c35a") if r % 2 else hexc("#d4b048"), 0.05, rng)
                seg = 10
                for k in range(seg):
                    y0, y1 = ya + (yb - ya) * k / seg, ya + (yb - ya) * (k + 1) / seg
                    P = [(x0, y0), (x0 + 0.95, y0), (x0 + 0.95, y1), (x0, y1)]
                    top = [(px, py, H(px, py) + 0.62) for px, py in P]
                    bot = [(px, py, H(px, py)) for px, py in P]
                    gm.add(top, [(0, 1, 2, 3)], [c] * 4)
                    for i, j in ((0, 3), (2, 1)):
                        quad_auto(gm, [bot[i], bot[j], top[j], top[i]], shade(c, 0.75), (-1 if i == 0 else 1, 0, 0),
                                  cols=[shade(c, 0.6)] * 2 + [c] * 2)
            else:
                y = ya
                while y < yb:
                    x = x0 + rng.uniform(-0.1, 0.1)
                    gm.blob(0.26, jit(hexc("#6fae4a") if r % 3 else hexc("#8f6fb6"), 0.1, rng), M=T(x, y, H(x, y) + 0.12), rng=rng,
                            sub=0, squash=(1, 1, 0.75), lumpy=0.15)
                    y += 1.25
        props.fence(m, [(xa - 1, ya - 1), (xb + 1, ya - 1), (xb + 1, yb + 1), (xa - 1, yb + 1), (xa - 1, ya - 1)], H, rng)
        S.occ.append(((xa + xb) / 2, (ya + yb) / 2, max(xb - xa, yb - ya) / 2 + 2))
    for (x, y) in ((-30, -100), (-33, -101.5), (-31.5, -102.8), (48, -104)):
        props.hay_bale(m, frame(x, y, rng.uniform(0, 180)), rng)
    bx, by = site(-33.0, -74.0)
    props.cart(m, frame(bx, by, 200), rng)
    S.occ.append((bx, by, 2.0))
    # roadside fences leading up to the arch
    for sx in (-1, 1):
        pts = [(world.street_x(y) + sx * 4.2, y) for y in range(-150, -101, 6)]
        props.fence(m, pts, H, rng, h=0.9)
    # the mountain path: cairns, and poles strung with sky-blue pennants
    y = world.GATE_Y + 9
    k = 0
    while y < 150:
        x = world.street_x(y)
        sx = 1 if k % 2 else -1
        cx, cy = x + sx * 2.3, y
        cz = H(cx, cy)
        for i in range(4):
            r = 0.34 - i * 0.07
            nature.rock(m, cx + rng.uniform(-0.04, 0.04), cy + rng.uniform(-0.04, 0.04), cz + i * 0.3 - 0.05, rng, s=r)
        y += rng.uniform(10, 15)
        k += 1
    bm = S.mesh("Bunting")
    prev = None
    for y in (world.GATE_Y + 6, world.GATE_Y + 20, world.GATE_Y + 36):
        pair = []
        for sx in (-1, 1):
            x = world.street_x(y) + sx * 2.6
            z = H(x, y)
            m.cyl(0.08, 0.05, 4.2, 6, house.TIMBER, M=T(x, y, z - 0.3))
            pair.append(Vector((x, y, z + 3.8)))
            S.occ.append((x, y, 0.5))
        _blue_bunting(bm, pair[0], pair[1], rng)
        prev = pair


def _blue_bunting(m, a, b, rng):
    old = props.BUNTING
    props.BUNTING = [props.SKY_BLUE, props.CLOTH, hexc("#8fb4e8"), props.CLOTH]
    props.bunting(m, a, b, rng, sag=0.6)
    props.BUNTING = old


# ---------------------------------------------------------------- nature
def plant(S):
    rng = random.Random(909)
    tm = S.mesh("Trees")
    fm = S.mesh("Forest")
    gm = S.mesh("GroundCover")
    rm = S.mesh("Props")
    # forest: thick on the valley sides and above the gate, thinning toward the village
    n_forest = 0
    y = -235.0
    while y < 205:
        x = -180.0
        while x < 180:
            px, py = x + rng.uniform(-3.2, 3.2), y + rng.uniform(-3.2, 3.2)
            x += 8.5
            v = world.tv(px, py)
            side = abs(px) - world.VILLAGE_HALF_W
            dens = smoothstep(-2, 16, side) * 0.85
            dens = max(dens, smoothstep(world.GATE_Y + 8, world.GATE_Y + 30, v) * 0.8)
            dens = max(dens, smoothstep(-150, -175, v) * 0.5)
            if abs(px - world.street_x(py)) < 6.5 and py > world.GATE_Y:
                dens = 0
            if abs(px - world.street_x(py)) < 7 and py < -100:
                dens = 0
            dens *= 0.75 + 0.5 * world.fbm(px, py, 0.02, 2)
            if rng.random() > dens or not S.free(px, py, 2.0):
                continue
            pz = H(px, py)
            far = math.hypot(px, py - 0) > 135
            hh = rng.uniform(7.5, 14.0)
            if rng.random() < 0.14 and not far:
                nature.leafy(fm, px, py, pz, hh * 0.75, rng, palette=nature.LEAFS + (nature.AUTUMN if rng.random() < 0.25 else []))
            else:
                nature.pine(fm, px, py, pz, hh, rng, lod=1 if far else 0)
            n_forest += 1
        y += 7.0
    # trees inside the village, between the houses
    spots = [(-47, -62), (40, -66), (4.5, -75), (-9, -30), (44, -31), (-46, -40), (8, -45), (-30, 15), (42, -3),
             (18, 16), (-46, 44), (3.5, 30), (44, 33), (-6, 47), (-34, 62), (6, 66), (35, 62), (-48, 12)]
    for i, (xr, v) in enumerate(spots):
        x, y = site(xr, v)
        if not S.free(x, y, 1.5):
            continue
        pal = nature.AUTUMN if i in (4, 11) else (nature.BLOSSOM if i == 8 else None)
        nature.leafy(tm, x, y, H(x, y), rng.uniform(6.0, 9.0), rng, palette=pal)
        S.occ.append((x, y, 1.6))
    # bushes along the tops of the terrace walls
    for c, z0, z1 in world.BANKS:
        x = -50.0
        while x < 50:
            x += rng.uniform(3.0, 8.0)
            y = c + 2.2 + world.curve(x) + rng.uniform(-0.3, 0.6)
            if abs(x - world.street_x(y)) < 5 or not S.free(x, y, 0.8):
                continue
            nature.bush(tm, x, y, H(x, y), rng, s=rng.uniform(0.6, 1.0))
    # rocks on the wild ground
    for k in range(70):
        x, y = rng.uniform(-150, 150), rng.uniform(-200, 190)
        if abs(x) < world.VILLAGE_HALF_W + 2 and -100 < y < world.GATE_Y + 4:
            continue
        if not S.free(x, y, 1.0):
            continue
        nature.rock(rm, x, y, H(x, y), rng, s=rng.uniform(0.4, 1.5))
    # grass and wild flowers
    for k in range(4200):
        x, y = rng.uniform(-60, 60), rng.uniform(-112, 100)
        if world.path_mask(x, y) > 0.12 or world.plaza_mask(x, y) > 0.05 or not S.free(x, y, -0.6):
            continue
        nature.grass_tuft(gm, x, y, H(x, y), rng, s=rng.uniform(0.8, 1.3))
    for k in range(90):                                  # flowers grow in drifts
        cx, cy = rng.uniform(-58, 58), rng.uniform(-108, 98)
        if world.path_mask(cx, cy) > 0.05 or world.plaza_mask(cx, cy) > 0.05 or not S.free(cx, cy, 0.5):
            continue
        col = rng.choice(nature.FLOWERS)
        for i in range(rng.randint(5, 11)):
            x, y = cx + rng.gauss(0, 0.8), cy + rng.gauss(0, 0.8)
            if world.path_mask(x, y) > 0.2:
                continue
            nature.flower(gm, x, y, H(x, y), rng, col=col if rng.random() < 0.8 else None)
    return n_forest


def build_all():
    S = Scene()
    info = place_houses(S)
    hall = place_hall(S)
    place_stage(S)
    place_gates(S)
    retaining_walls(S)
    stairs(S)
    plaza_paving(S)
    stepping_stones(S)
    dress_plaza(S, hall)
    dress_houses(S, info)
    dress_edges(S)
    n = plant(S)
    print("FOREST TREES", n)
    return S.out
