"""Small mesh-building kit: accumulates vertices, faces and per-vertex colours,
then turns them into one Blender mesh object (few draw calls, mobile friendly)."""
import math
import random
from mathutils import Matrix, Vector


# ---------- colour helpers (authoring in sRGB hex, stored linear) ----------
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexc(h):
    h = h.lstrip("#")
    return tuple(_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shade(c, k):
    return tuple(max(0.0, x * k) for x in c)


def jit(c, amt, rng):
    """Vary brightness (and a touch of warmth) of a colour."""
    k = 1.0 + rng.uniform(-amt, amt)
    w = rng.uniform(-amt, amt) * 0.35
    return (max(0, c[0] * (k + w)), max(0, c[1] * k), max(0, c[2] * (k - w)))


def smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


class Mesh:
    def __init__(self):
        self.v = []       # Vector
        self.c = []       # (r,g,b) linear
        self.f = []       # index tuples
        self.s = []       # smooth flag per face

    # ---- raw ----
    def add(self, verts, faces, cols, smooth=False, M=None):
        base = len(self.v)
        if M is not None:
            verts = [M @ Vector(p) for p in verts]
        else:
            verts = [Vector(p) for p in verts]
        self.v.extend(verts)
        if isinstance(cols, tuple) and len(cols) == 3 and not isinstance(cols[0], tuple):
            cols = [cols] * len(verts)
        self.c.extend(cols)
        for f in faces:
            self.f.append(tuple(base + i for i in f))
            self.s.append(smooth)

    def merge(self, other, M=None, warp=None):
        base = len(self.v)
        for p in other.v:
            q = Vector(warp(p)) if warp else p
            self.v.append(M @ q if M is not None else q.copy())
        self.c.extend(other.c)
        for f in other.f:
            self.f.append(tuple(base + i for i in f))
        self.s.extend(other.s)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)

    # ---- primitives ----
    def quad(self, a, b, c, d, col, col2=None, M=None):
        """a,b = first edge; c,d continue CCW. col2 (optional) applies to c,d."""
        cols = [col, col, col2 or col, col2 or col]
        self.add([a, b, c, d], [(0, 1, 2, 3)], cols, M=M)

    def tri(self, a, b, c, col, M=None):
        self.add([a, b, c], [(0, 1, 2)], [col] * 3, M=M)

    def poly(self, pts, col, M=None):
        self.add(pts, [tuple(range(len(pts)))], [col] * len(pts), M=M)

    def box(self, size, col, M=None, top=None, taper=1.0, grad=0.86, faces="xXyYzZ", off=(0, 0, 0)):
        """Box with origin at bottom-centre (+off). taper scales the top in x/y.
        grad darkens the bottom verts for a grounded, hand-painted look."""
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2]
        ox, oy, oz = off
        t = taper
        P = [(-sx + ox, -sy + oy, oz), (sx + ox, -sy + oy, oz), (sx + ox, sy + oy, oz), (-sx + ox, sy + oy, oz),
             (-sx * t + ox, -sy * t + oy, sz + oz), (sx * t + ox, -sy * t + oy, sz + oz),
             (sx * t + ox, sy * t + oy, sz + oz), (-sx * t + ox, sy * t + oy, sz + oz)]
        lo, hi = shade(col, grad), col
        tcol = top or col
        F = {"y": (0, 1, 5, 4), "X": (1, 2, 6, 5), "Y": (2, 3, 7, 6), "x": (3, 0, 4, 7)}
        for k, idx in F.items():
            if k in faces:
                self.add([P[i] for i in idx], [(0, 1, 2, 3)], [lo, lo, hi, hi], M=M)
        if "Z" in faces:
            self.add([P[4], P[5], P[6], P[7]], [(0, 1, 2, 3)], [tcol] * 4, M=M)
        if "z" in faces:
            self.add([P[3], P[2], P[1], P[0]], [(0, 1, 2, 3)], [lo] * 4, M=M)

    def beam(self, p0, p1, w, d, col, up=(0, 0, 1), M=None, grad=1.0, faces="xXyYzZ"):
        """Box running from p0 to p1 (its local Z), cross-section w (local X) x d (local Y)."""
        p0, p1 = Vector(p0), Vector(p1)
        z = p1 - p0
        L = z.length
        if L < 1e-6:
            return
        z.normalize()
        u = Vector(up)
        if abs(z.dot(u)) > 0.98:
            u = Vector((1, 0, 0))
        x = u.cross(z).normalized()
        y = z.cross(x)
        B = Matrix(((x.x, y.x, z.x, p0.x), (x.y, y.y, z.y, p0.y), (x.z, y.z, z.z, p0.z), (0, 0, 0, 1)))
        self.box((w, d, L), col, M=(M @ B) if M is not None else B, grad=grad, faces=faces)

    def cyl(self, r0, r1, h, n, col, M=None, cap=True, col_top=None, smooth=False, z0=0.0, bottom=False):
        """Tapered n-gon cylinder, base at z0."""
        ct = col_top or col
        ring0 = [(math.cos(i / n * math.tau) * r0, math.sin(i / n * math.tau) * r0, z0) for i in range(n)]
        ring1 = [(math.cos(i / n * math.tau) * r1, math.sin(i / n * math.tau) * r1, z0 + h) for i in range(n)]
        if smooth:
            self.add(ring0 + ring1, [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)],
                     [col] * n + [ct] * n, smooth=True, M=M)
        else:
            for i in range(n):
                j = (i + 1) % n
                self.add([ring0[i], ring0[j], ring1[j], ring1[i]], [(0, 1, 2, 3)], [col, col, ct, ct], M=M)
        if cap and r1 > 1e-4:
            self.add(ring1, [tuple(range(n))], [ct] * n, M=M)
        if bottom:
            self.add(ring0[::-1], [tuple(range(n))], [col] * n, M=M)

    def cone(self, r, h, n, col, M=None, col_top=None, z0=0.0, smooth=False):
        ct = col_top or col
        ring = [(math.cos(i / n * math.tau) * r, math.sin(i / n * math.tau) * r, z0) for i in range(n)]
        apex = (0, 0, z0 + h)
        if smooth:
            self.add(ring + [apex], [(i, (i + 1) % n, n) for i in range(n)], [col] * n + [ct], smooth=True, M=M)
        else:
            for i in range(n):
                self.add([ring[i], ring[(i + 1) % n], apex], [(0, 1, 2)], [col, col, ct], M=M)

    def blob(self, r, col, M=None, rng=None, sub=1, squash=(1, 1, 1), lumpy=0.18, col_top=None, col_bot=None):
        """Lumpy icosphere with shared verts (smooth shaded): foliage, clouds, bushes, rocks."""
        verts, faces = _icosphere(sub)
        rng = rng or random
        out, cols = [], []
        ct = col_top or col
        cb = col_bot or shade(col, 0.72)
        for p in verts:
            k = 1.0 + rng.uniform(-lumpy, lumpy)
            q = (p[0] * r * k * squash[0], p[1] * r * k * squash[1], p[2] * r * k * squash[2])
            out.append(q)
            t = (p[2] + 1) / 2
            cols.append(mix(cb, ct, smoothstep(0.1, 0.9, t)))
        self.add(out, faces, cols, smooth=True, M=M)

    # ---- to Blender ----
    def to_object(self, name, collection=None):
        import bpy
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        me.update()
        me.polygons.foreach_set("use_smooth", self.s)
        attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        flat = []
        for c in self.c:
            flat.extend((c[0], c[1], c[2], 1.0))
        attr.data.foreach_set("color", flat)
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = 0
        ob = bpy.data.objects.new(name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        return ob


_ICO_CACHE = {}


def _icosphere(sub):
    if sub in _ICO_CACHE:
        return _ICO_CACHE[sub]
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    V = [Vector(p).normalized() for p in V]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        cache, F2 = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                V.append(((V[a] + V[b]) / 2).normalized())
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = F2
    res = ([tuple(p) for p in V], F)
    _ICO_CACHE[sub] = res
    return res


def T(x=0, y=0, z=0):
    return Matrix.Translation((x, y, z))


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def Sc(x, y=None, z=None):
    y = x if y is None else y
    z = x if z is None else z
    return Matrix.Diagonal((x, y, z, 1))
