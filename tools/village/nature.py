"""Trees, bushes, rocks, grass and flowers."""
import math
import random
from mathutils import Vector

from meshkit import Mesh, hexc, mix, shade, jit, T, R, Sc

PINE = [hexc("#2f6b45"), hexc("#3a7a4a"), hexc("#28603f"), hexc("#44845a")]
BARK = hexc("#6b4a35")
LEAFS = [hexc("#5fa044"), hexc("#78b54c"), hexc("#4d8f40"), hexc("#8cc257")]
BLOSSOM = [hexc("#f6c9d8"), hexc("#f9dfe6"), hexc("#f2a9c4")]
AUTUMN = [hexc("#e0a03a"), hexc("#d9742e")]
ROCKS = [hexc("#9a968f"), hexc("#86837f"), hexc("#a8a297")]
GRASS = [hexc("#9bcf5a"), hexc("#7fb84c"), hexc("#b4dc6a")]
FLOWERS = [hexc("#f4f1e8"), hexc("#f2c232"), hexc("#e8554e"), hexc("#d86aa6"), hexc("#8f6fd6"), hexc("#f6f0a0")]


def pine(m, x, y, z, h, rng, lod=0, slim=False):
    col = jit(rng.choice(PINE), 0.1, rng)
    n = 5 if lod else 7
    M = T(x, y, z - 0.2) @ R("Z", rng.uniform(0, 360)) @ R("X", rng.uniform(-3, 3))
    m.cyl(h * 0.035 + 0.05, h * 0.02, h * (0.55 if slim else 0.45), 5 if lod else 7, BARK, M=M, cap=False)
    tiers = 2 if lod else rng.choice((4, 4, 5))
    base = h * (0.34 if slim else 0.2)
    girth = 0.16 if slim else 0.24
    for i in range(tiers):
        t = i / tiers
        r = h * girth * (1 - t * 0.72) * rng.uniform(0.9, 1.1)
        z0 = base + (h - base) * t * 0.9
        th = (h - z0) if i == tiers - 1 else (h - base) / tiers * 1.75
        c0 = shade(col, 0.72 + 0.1 * t)
        c1 = shade(col, 1.0 + 0.22 * t)
        B = M @ T(rng.uniform(-0.03, 0.03) * h, rng.uniform(-0.03, 0.03) * h, z0) @ R("Z", rng.uniform(0, 60))
        m.cone(r, th, n, c0, M=B, col_top=c1)
        ring = [(math.cos(k / n * math.tau) * r, math.sin(k / n * math.tau) * r, 0) for k in range(n)]
        m.add(ring[::-1], [tuple(range(n))], [shade(col, 0.5)] * n, M=B)


def leafy(m, x, y, z, h, rng, palette=None, lod=0):
    pal = palette or LEAFS
    col = jit(rng.choice(pal), 0.08, rng)
    M = T(x, y, z - 0.2) @ R("Z", rng.uniform(0, 360))
    th = h * 0.5
    lean = rng.uniform(-0.12, 0.12)
    m.cyl(h * 0.055, h * 0.04, th * 0.55, 6, shade(BARK, 0.9), M=M, cap=False)
    m.cyl(h * 0.04, h * 0.028, th * 0.55, 6, BARK, M=M @ T(0, 0, th * 0.55) @ R("Y", math.degrees(lean)), cap=False)
    top = M @ Vector((lean * th * 0.5, 0, th))
    n = 3 if lod else rng.choice((6, 7, 8))
    for i in range(n):
        a = i / n * math.tau + rng.uniform(-0.5, 0.5)
        big = i == 0
        rr = h * (rng.uniform(0.24, 0.3) if big else rng.uniform(0.14, 0.22))
        off = 0 if big else h * rng.uniform(0.16, 0.27)
        p = top + Vector((math.cos(a) * off, math.sin(a) * off, h * (0.2 if big else rng.uniform(0.0, 0.3))))
        c = jit(col, 0.09, rng)
        m.blob(rr, c, M=T(*p), rng=rng, sub=0 if lod else 1, squash=(1, 1, 0.84), lumpy=0.13,
               col_top=shade(c, 1.22), col_bot=shade(c, 0.6))


def bush(m, x, y, z, rng, s=1.0, palette=None):
    col = jit(rng.choice(palette or LEAFS), 0.1, rng)
    for i in range(rng.choice((1, 2, 3))):
        r = s * rng.uniform(0.45, 0.75)
        m.blob(r, col, M=T(x + rng.uniform(-0.5, 0.5) * s * (i > 0), y + rng.uniform(-0.5, 0.5) * s * (i > 0), z + r * 0.45),
               rng=rng, sub=1 if s > 0.8 else 0, squash=(1, 1, 0.75), lumpy=0.14, col_top=shade(col, 1.15), col_bot=shade(col, 0.6))


def rock(m, x, y, z, rng, s=1.0):
    c = jit(rng.choice(ROCKS), 0.08, rng)
    v, f = [], []
    sub = Mesh()
    sub.blob(s, c, rng=rng, sub=0, squash=(rng.uniform(0.8, 1.3), rng.uniform(0.8, 1.2), rng.uniform(0.5, 0.8)), lumpy=0.28,
             col_top=shade(c, 1.12), col_bot=shade(c, 0.7))
    # facet it: un-share the verts so it shades flat
    M = T(x, y, z + s * 0.2) @ R("Z", rng.uniform(0, 360))
    for face in sub.f:
        m.add([sub.v[i] for i in face], [tuple(range(len(face)))], [sub.c[i] for i in face], M=M)


def grass_tuft(m, x, y, z, rng, s=1.0):
    c = jit(rng.choice(GRASS), 0.08, rng)
    base = shade(c, 0.7)
    for k in range(3):
        a = rng.uniform(0, math.tau)
        w = 0.07 * s
        hh = rng.uniform(0.28, 0.5) * s
        dx, dy = math.cos(a), math.sin(a)
        p0 = (x - dy * w, y + dx * w, z)
        p1 = (x + dy * w, y - dx * w, z)
        tip = (x + dx * 0.12 * s, y + dy * 0.12 * s, z + hh)
        m.add([p0, p1, tip], [(0, 1, 2)], [base, base, c])
        m.add([p1, p0, tip], [(0, 1, 2)], [base, base, c])


def flower(m, x, y, z, rng, col=None):
    c = col or rng.choice(FLOWERS)
    hh = rng.uniform(0.18, 0.32)
    m.add([(x - 0.012, y, z), (x + 0.012, y, z), (x, y, z + hh)], [(0, 1, 2)], [hexc("#5f9a3f")] * 3)
    m.add([(x + 0.012, y, z), (x - 0.012, y, z), (x, y, z + hh)], [(0, 1, 2)], [hexc("#5f9a3f")] * 3)
    r = rng.uniform(0.05, 0.08)
    m.cone(r, r * 0.9, 5, c, M=T(x, y, z + hh - r * 0.3), col_top=shade(c, 1.1))
