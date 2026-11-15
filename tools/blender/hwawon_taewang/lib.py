"""공용 도구: 좌표, 재질, 메시 빌더."""
import math
import os
import random

import bpy
from mathutils import Vector

S = 0.51                 # m / px (지도 캡처 축척)
ORIGIN = (260, 420)      # 기준 픽셀
rng = random.Random(7058)

TEX_DIR = ""
_mats = {}


def P(px, py):
    """지도 픽셀 -> 미터 (X 동쪽, Y 북쪽)."""
    return Vector(((px - ORIGIN[0]) * S, -(py - ORIGIN[1]) * S))


# 네이버 거리뷰 지점(경도, 위도)을 같은 좌표로. 정문 지점을 기준으로 맞췄다.
_GEO_REF = (128.4912501, 35.8020918, 238, 584)


def geo(lon, lat):
    dx = (lon - _GEO_REF[0]) * 90290.0
    dy = (lat - _GEO_REF[1]) * 110950.0
    return P(_GEO_REF[2], _GEO_REF[3]) + Vector((dx, dy))


def v3(p, z):
    return (p.x, p.y, z)


def perp(u):
    return Vector((-u.y, u.x))


def srgb(rgb):
    out = []
    for c in rgb:
        c = c / 255.0
        out.append(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92)
    return out


# ------------------------------------------------------------------ 재질
def _img(file, noncolor=False):
    img = bpy.data.images.load(os.path.join(TEX_DIR, file), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    return img


def mat_tex(name, base=None, rough=0.85, metal=0.0, alpha=False, normal=1.0, double=False):
    """텍스처 재질. <base>.png, 있으면 <base>_orm.png / <base>_n.png 도 연결."""
    if name in _mats:
        return _mats[name]
    base = base or name
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _img(base + ".png")
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if os.path.exists(os.path.join(TEX_DIR, base + "_orm.png")):
        orm = nt.nodes.new("ShaderNodeTexImage")
        orm.image = _img(base + "_orm.png", True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    if normal and os.path.exists(os.path.join(TEX_DIR, base + "_n.png")):
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = _img(base + "_n.png", True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(nimg.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if alpha:
        # 알파를 0/1로 잘라서 glTF에서 MASK(잘라내기) 방식으로 나가게 한다
        mth = nt.nodes.new("ShaderNodeMath")
        mth.operation = "GREATER_THAN"
        mth.inputs[1].default_value = 0.5
        nt.links.new(tex.outputs["Alpha"], mth.inputs[0])
        nt.links.new(mth.outputs[0], bsdf.inputs["Alpha"])
        try:
            m.blend_method = "CLIP"
        except Exception:
            pass
    if double or alpha:
        m.use_backface_culling = False
    else:
        m.use_backface_culling = True
    _mats[name] = m
    return m


def mat_col(name, rgb, rough=0.8, metal=0.0, emission=0.0, alpha=1.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    col = srgb(rgb)
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
    m.diffuse_color = (*col, 1.0)
    _mats[name] = m
    return m


# ------------------------------------------------------------------ 메시 빌더
class MeshBuilder:
    def __init__(self):
        self.verts, self.faces, self.uvs, self.mats = [], [], [], []

    def add(self, pts, uvs, mat):
        i = len(self.verts)
        self.verts.extend(pts)
        self.faces.append(list(range(i, i + len(pts))))
        self.uvs.append(uvs)
        self.mats.append(mat)

    def build(self, name, collection=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        uvl = me.uv_layers.new(name="UVMap")
        order = []
        for m in self.mats:
            if m not in order:
                order.append(m)
        idx = {m: i for i, m in enumerate(order)}
        for m in order:
            me.materials.append(m)
        for fi, poly in enumerate(me.polygons):
            poly.material_index = idx[self.mats[fi]]
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uvs[fi][k]
        me.update()
        if collection is None:
            return me
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        return ob

    # 수직 벽. 바깥 방향 N 기준으로 감는 방향과 UV를 정한다.
    def wall(self, p0, p1, z0, z1, N, mat, tw, th, u0=0.0, v0=0.0, fit_u=None):
        r = Vector((-N.y, N.x))
        if (p1 - p0).dot(r) < 0:
            p0, p1 = p1, p0
        L = (p1 - p0).length
        u1 = u0 + (fit_u if fit_u is not None else L / tw)
        v1 = v0 + (z1 - z0) / th
        self.add([v3(p0, z0), v3(p1, z0), v3(p1, z1), v3(p0, z1)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat)

    # 여러 점을 잇는 수직 띠 (곡면 발코니 등). pts는 바깥에서 봤을 때 왼쪽->오른쪽 순서.
    def strip(self, pts, z0, z1, mat, th, u0, u1, v0=0.0):
        lens = [0.0]
        for a, b in zip(pts, pts[1:]):
            lens.append(lens[-1] + (b - a).length)
        tot = lens[-1]
        vv1 = v0 + (z1 - z0) / th
        for i in range(len(pts) - 1):
            ua = u0 + (u1 - u0) * lens[i] / tot
            ub = u0 + (u1 - u0) * lens[i + 1] / tot
            self.add([v3(pts[i], z0), v3(pts[i + 1], z0), v3(pts[i + 1], z1), v3(pts[i], z1)],
                     [(ua, v0), (ub, v0), (ub, vv1), (ua, vv1)], mat)

    def flat(self, pts, z, mat, tile=4.0, down=False):
        area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                   for i in range(len(pts)))
        if (area < 0) != down:
            pts = list(reversed(pts))
        self.add([v3(p, z) for p in pts], [(p.x / tile, p.y / tile) for p in pts], mat)

    def quad3(self, pts3, mat, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
        self.add([tuple(p) for p in pts3], list(uvs), mat)

    def box(self, c, u, sx, sy, z0, z1, side, top, tw=4.0, th=None, bottom=False):
        q = rect_pts(c, u, sx, sy)
        th = th or (z1 - z0)
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            N = ((a + b) / 2 - c).normalized()
            self.wall(a, b, z0, z1, N, side, tw, th)
        self.flat(q, z1, top)
        if bottom:
            self.flat(q, z0, top, down=True)
        return q

    def prism(self, poly, z0, z1, side, top, tw=4.0, th=None):
        c = sum(poly, Vector((0, 0))) / len(poly)
        th = th or (z1 - z0)
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            N = perp(b - a)
            if N.dot((a + b) / 2 - c) < 0:
                N = -N
            self.wall(a, b, z0, z1, N.normalized(), side, tw, th)
        self.flat(poly, z1, top)

    def hip_roof(self, c, u, sx, sy, z, h, mat, over=0.5, tile=1.2):
        """모임지붕/우진각지붕."""
        q = rect_pts(c, u, sx + over * 2, sy + over * 2)
        ridge = max(0.0, (sx - sy) / 2)
        r0, r1 = c - u * ridge, c + u * ridge
        tops = [r0, r1, r1, r0]
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            ta, tb = tops[i], tops[(i + 1) % 4]
            L = (b - a).length / tile
            sl = math.hypot(h, (sy / 2 + over)) / tile
            if (ta - tb).length < 1e-6:
                self.add([v3(a, z), v3(b, z), v3(ta, z + h)], [(0, 0), (L, 0), (L / 2, sl)], mat)
            else:
                d = ((b - a).length - (tb - ta).length) / 2 / tile
                self.add([v3(a, z), v3(b, z), v3(tb, z + h), v3(ta, z + h)],
                         [(0, 0), (L, 0), (L - d, sl), (d, sl)], mat)
        self.flat(q, z, mat, down=True)

    def cyl(self, c, r, z0, z1, mat, n=8, cap=True, r1=None):
        """수직 원기둥(또는 원뿔대)."""
        r1 = r if r1 is None else r1
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            p0 = c + Vector((math.cos(a0), math.sin(a0))) * r
            p1 = c + Vector((math.cos(a1), math.sin(a1))) * r
            q0 = c + Vector((math.cos(a0), math.sin(a0))) * r1
            q1 = c + Vector((math.cos(a1), math.sin(a1))) * r1
            self.add([v3(p0, z0), v3(p1, z0), v3(q1, z1), v3(q0, z1)],
                     [(i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, 1), (i / n, 1)], mat)
        if cap:
            self.flat([c + Vector((math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))) * r1
                       for i in range(n)], z1, mat)

    def ball(self, c, z, r, mat, n=10, rings=5):
        """공 (가로등 갓 등). c: 바닥 좌표, z: 중심 높이."""
        for j in range(rings):
            t0, t1 = math.pi * j / rings - math.pi / 2, math.pi * (j + 1) / rings - math.pi / 2
            self.cyl(c, r * math.cos(t0), z + r * math.sin(t0), z + r * math.sin(t1), mat, n=n, cap=False,
                     r1=r * math.cos(t1))

    def tube(self, a3, b3, r, mat, n=6):
        """두 점을 잇는 가는 관 (난간, 전선 등)."""
        a, b = Vector(a3), Vector(b3)
        d = (b - a)
        if d.length < 1e-6:
            return
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = d.cross(x).normalized()
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            o0 = (x * math.cos(a0) + y * math.sin(a0)) * r
            o1 = (x * math.cos(a1) + y * math.sin(a1)) * r
            self.add([tuple(a + o1), tuple(a + o0), tuple(b + o0), tuple(b + o1)],
                     [(0, 0), (1, 0), (1, 1), (0, 1)], mat)


def rect_pts(c, u, sx, sy):
    n = perp(u)
    hx, hy = sx / 2, sy / 2
    return [c - u * hx - n * hy, c + u * hx - n * hy, c + u * hx + n * hy, c - u * hx + n * hy]


def point_in_poly(p, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        a, b = poly[i], poly[j]
        if (a.y > p.y) != (b.y > p.y):
            x = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if p.x < x:
                inside = not inside
        j = i
    return inside


# 나무/소품 배치 때 피할 구역 (다각형 목록)
BLOCKED = []
PLANTERS = []   # (중심, 윗면 높이)


def block(poly):
    BLOCKED.append(poly)


def is_free(p, margin=0.0):
    for poly in BLOCKED:
        if margin:
            c = sum(poly, Vector((0, 0))) / len(poly)
            poly = [c + (q - c) * (1 + margin / max(0.1, (q - c).length)) for q in poly]
        if point_in_poly(p, poly):
            return False
    return True


def instance(mesh, col, name, p, ang=0.0, scale=1.0, z=0.0):
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (p.x, p.y, z)
    ob.rotation_euler = (0, 0, ang)
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    ob.scale = scale
    col.objects.link(ob)
    return ob


def text_mesh(body, size, mat, col, name, loc, rot, extrude=0.02, font_path=None):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = extrude
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    if font_path and os.path.exists(font_path):
        curve.font = bpy.data.fonts.load(font_path, check_existing=True)
    curve.materials.append(mat)
    ob = bpy.data.objects.new(name, curve)
    col.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def join_as_mesh(objs, name):
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target="MESH")
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob
