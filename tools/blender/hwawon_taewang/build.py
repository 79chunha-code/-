"""화원태왕타운 아파트 단지 로우폴리 모델 생성 (Blender Python, bpy).

배치는 위성지도/지도에서 읽은 픽셀 좌표(1px = 0.51m)를 미터로 바꿔 쓴다.
X = 동쪽, Y = 북쪽, Z = 위. 단위 m.

실행:
  python3 build.py --tex <텍스처 폴더> --out <출력 폴더> [--render]
"""
import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- 기본 설정
S = 0.51                 # m / px
ORIGIN = (260, 420)      # 기준 픽셀 (단지 가운데쯤)
FLOOR_H = 2.7
BASE_H = 0.6             # 1층 바닥이 지면보다 높은 만큼 (기단)
PARAPET_H = 1.0
rng = random.Random(7058)


def P(px, py):
    return Vector(((px - ORIGIN[0]) * S, -(py - ORIGIN[1]) * S))


def v3(p, z):
    return (p.x, p.y, z)


# ---------------------------------------------------------------- 동 데이터
# a, b: 건물 긴 축의 양 끝(px). segs: 계단실 단위 개수. floors: 세그먼트별 층수.
# front: 발코니(앞)면이 대략 향하는 방향. offs: 세그먼트별 앞뒤 엇갈림(m).
BUILDINGS = [
    dict(no="101", a=(258, 523.5), b=(445, 523.5), depth=13.0, segs=6,
         floors=[18, 18, 18, 18, 18, 12], front=(0, -1), back_parking=True),
    dict(no="102", a=(120, 535), b=(212, 535), depth=11.5, segs=3,
         floors=[18] * 3, front=(0, -1), back_parking=True),
    dict(no="103", a=(227, 398), b=(227, 490), depth=11.5, segs=3,
         floors=[18] * 3, front=(1, 0), back_parking=True),
    dict(no="104", a=(446, 480), b=(514, 480), depth=13.0, segs=2,
         floors=[18] * 2, front=(0, -1), back_parking=True),
    dict(no="105", a=(322, 340), b=(437, 437), depth=11.5, segs=5,
         floors=[18] * 5, front=(-0.6, -0.8), back_parking=False),
    dict(no="106", a=(240, 273), b=(322, 343), depth=11.5, segs=3,
         floors=[18] * 3, front=(-0.6, -0.8), back_parking=False),
    dict(no="107", a=(163, 266), b=(235, 260), depth=10.0, segs=2,
         floors=[18] * 2, front=(0, -1), back_parking=False),
    dict(no="108", a=(68, 445), b=(160, 283), depth=10.0, segs=6,
         floors=[18] * 6, front=(0.9, -0.3), back_parking=False,
         offs=[0.0, 0.0, 1.6, 1.6, 3.2, 3.2]),
    dict(no="109", a=(94, 460), b=(94, 530), depth=10.0, segs=2,
         floors=[11, 11], front=(1, 0), back_parking=True),
]

BOUNDARY = [(50, 588), (48, 450), (105, 300), (150, 215), (215, 200), (250, 215),
            (470, 440), (522, 470), (522, 588)]


# ---------------------------------------------------------------- 유틸
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


TEX_DIR = None
_mats = {}


def mat_img(name, file, rough=0.85, metal=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(os.path.join(TEX_DIR, file), check_existing=True)
    tex.image = img
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    _mats[name] = m
    return m


def mat_col(name, rgb, rough=0.8, metal=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    col = [c / 255.0 for c in rgb]
    # sRGB -> linear
    col = [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in col]
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*col, 1.0)
    _mats[name] = m
    return m


class MeshBuilder:
    def __init__(self):
        self.verts, self.faces, self.uvs, self.mats = [], [], [], []

    def add(self, pts, uvs, mat):
        i = len(self.verts)
        self.verts.extend(pts)
        self.faces.append(list(range(i, i + len(pts))))
        self.uvs.append(uvs)
        self.mats.append(mat)

    def build(self, name, collection):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.update()
        uvl = me.uv_layers.new(name="UVMap")
        order = []
        for m in self.mats:
            if m not in order:
                order.append(m)
        for m in order:
            me.materials.append(m)
        for fi, poly in enumerate(me.polygons):
            poly.material_index = order.index(self.mats[fi])
            for k, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uvs[fi][k]
        me.validate()
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        return ob

    # 수직 벽: 바닥 모서리 p0-p1, 바깥 방향 N
    def wall(self, p0, p1, z0, z1, N, mat, tw, th, u0=0.0, v0=0.0):
        r = Vector((-N.y, N.x))
        if (p1 - p0).dot(r) < 0:
            p0, p1 = p1, p0
        L = (p1 - p0).length
        u1 = u0 + L / tw
        v1 = v0 + (z1 - z0) / th
        self.add([v3(p0, z0), v3(p1, z0), v3(p1, z1), v3(p0, z1)],
                 [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat)

    # 수평면 (위로 향함, down=True면 아래로)
    def flat(self, pts, z, mat, tile=4.0, down=False):
        area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                   for i in range(len(pts)))
        if (area < 0) != down:
            pts = list(reversed(pts))
        self.add([v3(p, z) for p in pts], [(p.x / tile, p.y / tile) for p in pts], mat)

    # 회전된 상자 (c 중심, u 긴축 단위벡터)
    def box(self, c, u, sx, sy, z0, z1, side, top, tw=4.0, th=None, bottom=False):
        n = Vector((-u.y, u.x))
        hx, hy = sx / 2, sy / 2
        q = [c - u * hx - n * hy, c + u * hx - n * hy, c + u * hx + n * hy, c - u * hx + n * hy]
        th = th or (z1 - z0)
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            mid = (a + b) / 2
            N = (mid - c).normalized()
            self.wall(a, b, z0, z1, N, side, tw, th)
        self.flat(q, z1, top)
        if bottom:
            self.flat(q, z0, top, down=True)
        return q


def rect_pts(c, u, sx, sy):
    n = Vector((-u.y, u.x))
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


# 나무/소품 배치 충돌 검사용 금지 구역 (사각형 다각형 목록)
BLOCKED = []


def free(p, margin=0.0):
    for poly in BLOCKED:
        c = sum(poly, Vector((0, 0))) / len(poly)
        if margin:
            poly = [c + (q - c) * (1 + margin / max(0.1, (q - c).length)) for q in poly]
        if point_in_poly(p, poly):
            return False
    return True


# ---------------------------------------------------------------- 아파트 동
def build_apartment(bd, col):
    M = dict(
        front=mat_img("Facade_Front", "front.png", 0.7),
        front_g=mat_img("Facade_FrontGround", "front_ground.png", 0.7),
        back=mat_img("Facade_Back", "back.png", 0.75),
        back_g=mat_img("Facade_BackGround", "back_ground.png", 0.75),
        side=mat_img("Facade_Side", "side.png", 0.8),
        parapet=mat_img("Parapet", "parapet.png", 0.8),
        roof=mat_img("Roof_Green", "roof.png", 0.6),
        rooftop=mat_img("RooftopRoom", "rooftop.png", 0.8),
        base=mat_col("Concrete_Base", (150, 150, 146), 0.9),
        cap=mat_col("Concrete_Cap", (226, 226, 220), 0.85),
        canopy=mat_col("Canopy", (230, 232, 228), 0.6),
        steps=mat_col("Steps", (176, 172, 164), 0.9),
    )
    a, b = P(*bd["a"]), P(*bd["b"])
    c = (a + b) / 2
    u = (b - a).normalized()
    L = (b - a).length
    n = Vector((-u.y, u.x))
    if n.dot(Vector(bd["front"])) < 0:
        n = -n
    D = bd["depth"]
    segs = bd["segs"]
    sw = L / segs
    floors = bd["floors"]
    offs = bd.get("offs", [0.0] * segs)

    # 같은 층수/엇갈림끼리 묶어 덩어리(piece) 만들기
    pieces = []
    for i in range(segs):
        if pieces and pieces[-1]["f"] == floors[i] and pieces[-1]["o"] == offs[i]:
            pieces[-1]["k1"] = i + 1
        else:
            pieces.append(dict(k0=i, k1=i + 1, f=floors[i], o=offs[i]))

    mb = MeshBuilder()

    def pt(along, across):
        return c + u * along + n * across

    info = dict(no=bd["no"], c=c, u=u, n=n, L=L, D=D, pieces=[], entrances=[])
    for pi, pc in enumerate(pieces):
        a0 = -L / 2 + pc["k0"] * sw
        a1 = -L / 2 + pc["k1"] * sw
        o = pc["o"]
        top = BASE_H + FLOOR_H * pc["f"]
        fb, bb = D / 2 + o, -D / 2 + o
        FL, FR = pt(a0, fb), pt(a1, fb)
        BL, BR = pt(a0, bb), pt(a1, bb)
        g1 = BASE_H + FLOOR_H
        # 앞면
        mb.wall(FL, FR, 0, BASE_H, n, M["base"], 4.0, 1.0)
        mb.wall(FL, FR, BASE_H, g1, n, M["front_g"], sw, FLOOR_H)
        mb.wall(FL, FR, g1, top, n, M["front"], sw, FLOOR_H)
        # 뒷면
        mb.wall(BL, BR, 0, BASE_H, -n, M["base"], 4.0, 1.0)
        mb.wall(BL, BR, BASE_H, g1, -n, M["back_g"], sw, FLOOR_H)
        mb.wall(BL, BR, g1, top, -n, M["back"], sw, FLOOR_H)
        # 측면
        for (p0, p1, N) in ((BL, FL, -u), (BR, FR, u)):
            mb.wall(p0, p1, 0, BASE_H, N, M["base"], 4.0, 1.0)
            mb.wall(p0, p1, BASE_H, top, N, M["side"], D, FLOOR_H)
        # 파라펫 + 옥상
        outer = [BL, BR, FR, FL]
        inset = 0.25
        inner = [pt(a0 + inset, bb + inset), pt(a1 - inset, bb + inset),
                 pt(a1 - inset, fb - inset), pt(a0 + inset, fb - inset)]
        cc = pt((a0 + a1) / 2, o)
        for i in range(4):
            p0, p1 = outer[i], outer[(i + 1) % 4]
            N = ((p0 + p1) / 2 - cc).normalized()
            mb.wall(p0, p1, top, top + PARAPET_H, N, M["parapet"], 8.0, PARAPET_H)
            q0, q1 = inner[i], inner[(i + 1) % 4]
            mb.wall(q0, q1, top, top + PARAPET_H, -N, M["cap"], 4.0, 1.0)
            mb.flat([p0, p1, q1, q0], top + PARAPET_H, M["cap"])
        mb.flat(inner, top + 0.02, M["roof"], tile=16.0)
        # 계단실 옥탑, 공동현관
        for k in range(pc["k0"], pc["k1"]):
            am = -L / 2 + (k + 0.5) * sw
            rc = pt(am, bb + 3.0)
            mb.box(rc, u, 4.0, 4.6, top, top + 3.2, M["rooftop"], M["roof"], tw=4.0, th=3.2)
            # 현관 캐노피 + 계단
            ec = pt(am, bb - 1.0)
            mb.box(ec, u, 3.2, 2.0, BASE_H + 2.45, BASE_H + 2.7, M["canopy"], M["canopy"], bottom=True)
            mb.box(pt(am, bb - 1.1), u, 3.4, 2.2, 0, BASE_H, M["steps"], M["steps"])
            mb.box(pt(am, bb - 2.45), u, 3.4, 0.5, 0, BASE_H * 0.66, M["steps"], M["steps"])
            mb.box(pt(am, bb - 2.95), u, 3.4, 0.5, 0, BASE_H * 0.33, M["steps"], M["steps"])
            info["entrances"].append((pt(am, bb - 3.5), -n))
        info["pieces"].append(dict(a0=a0, a1=a1, o=o, top=top))
        BLOCKED.append([pt(a0, bb - 3.3), pt(a1, bb - 3.3), pt(a1, fb), pt(a0, fb)])

    ob = mb.build(f"Apt_{bd['no']}", col)
    ob["building_no"] = bd["no"]
    info["obj"] = ob
    return info


def add_building_numbers(infos, col):
    mat = mat_col("Sign_Number", (52, 120, 104), 0.6)
    objs = []
    for info in infos:
        c, u, n = info["c"], info["u"], info["n"]
        ends = ((info["pieces"][0], "a0", -u), (info["pieces"][-1], "a1", u))
        for pc, key, N in ends:
            curve = bpy.data.curves.new(f"num_{info['no']}", "FONT")
            curve.body = info["no"]
            curve.size = 3.6
            curve.extrude = 0.04
            curve.align_x = "CENTER"
            curve.align_y = "CENTER"
            ob = bpy.data.objects.new(f"num_{info['no']}", curve)
            col.objects.link(ob)
            p = c + u * pc[key] + n * pc["o"] + N * 0.06
            ob.location = (p.x, p.y, pc["top"] - 4.0)
            ob.rotation_euler = (math.radians(90), 0, math.atan2(N.x, -N.y))
            curve.materials.append(mat)
            objs.append(ob)
    # 메시로 변환 후 하나로 합치기
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    bpy.context.view_layer.objects.active.name = "BuildingNumbers"


# ---------------------------------------------------------------- 바닥/도로
def build_ground(infos, col):
    M = dict(
        ground=mat_img("Ground", "ground.png", 0.95),
        asphalt=mat_img("Asphalt", "asphalt.png", 0.9),
        grass=mat_img("Grass", "grass.png", 0.95),
        paver=mat_img("Paver", "paver.png", 0.9),
        curb=mat_col("Curb", (190, 188, 182), 0.9),
        line=mat_col("Paint_White", (240, 240, 236), 0.7),
        yellow=mat_col("Paint_Yellow", (236, 190, 40), 0.7),
        water=mat_col("Water", (70, 96, 84), 0.08),
        path=mat_col("Path_Clay", (196, 164, 132), 0.95),
        wall=mat_col("Wall_Stone", (204, 196, 180), 0.9),
        hedge=mat_col("Hedge", (58, 98, 52), 0.95),
    )
    mb = MeshBuilder()
    poly = [P(*q) for q in BOUNDARY]
    # 바깥 땅
    G = 400
    mb.flat([Vector((-G, -G)), Vector((G, -G)), Vector((G, G)), Vector((-G, G))], -0.02, M["ground"], tile=8.0)
    # 단지 아스팔트
    mb.flat(poly, 0.0, M["asphalt"], tile=8.0)

    # 도로: 남쪽 성화로4길, 서쪽 길, 북동쪽 비슬로497길
    def road(p0, p1, w, z=0.005, center_line=True):
        u = (p1 - p0).normalized()
        L = (p1 - p0).length
        c = (p0 + p1) / 2
        mb.flat(rect_pts(c, u, L, w), z, M["asphalt"], tile=8.0)
        if center_line:
            for i in range(int(L // 6)):
                cc = p0 + u * (i * 6 + 1.5)
                mb.flat(rect_pts(cc, u, 3.0, 0.15), z + 0.01, M["yellow"])

    s0, s1 = P(-150, 597), P(800, 597)
    road(s0, s1, 8.0)
    road(P(30, 640), P(40, 450) , 7.0, center_line=False)
    road(P(40, 450), P(140, 175), 7.0, center_line=False)
    ne0, ne1 = P(250, 215), P(522, 470)
    une = (ne1 - ne0).normalized()
    nne = Vector((une.y, -une.x))  # 북동쪽(바깥) 방향
    if nne.dot(Vector((1, 1))) < 0:
        nne = -nne
    rc0 = ne0 - une * 120 + nne * 8
    rc1 = ne1 + une * 200 + nne * 8
    road(rc0, rc1, 9.0)
    # 하천 (천내천): 둑 잔디, 산책로, 물
    L = (rc1 - rc0).length
    cmid = (rc0 + rc1) / 2
    mb.flat(rect_pts(cmid + nne * 33, une, L, 48), 0.003, M["grass"], tile=8.0)
    mb.flat(rect_pts(cmid + nne * 14, une, L, 3.0), 0.012, M["path"], tile=4.0)
    mb.flat(rect_pts(cmid + nne * 52, une, L, 3.0), 0.012, M["path"], tile=4.0)
    mb.flat(rect_pts(cmid + nne * 33, une, L, 13), -0.6, M["water"], tile=8.0)
    for side in (-1, 1):
        e = cmid + nne * (33 + side * 6.5)
        q = rect_pts(e, une, L, 0.01)
        mb.wall(q[0], q[1], -0.6, 0.003, -nne * side, M["grass"], 8.0, 1.0)

    # 담장 (정문/후문 자리 비움)
    gates = [(P(130, 588), P(258, 588)), (P(445, 413), P(462, 431)), (P(178, 207), P(192, 204))]

    def in_gate(p):
        for g0, g1 in gates:
            d = g1 - g0
            t = (p - g0).dot(d) / d.length_squared
            if -0.02 <= t <= 1.02 and ((g0 + d * t) - p).length < 1.0:
                return True
        return False

    for i in range(len(poly)):
        p0, p1 = poly[i], poly[(i + 1) % len(poly)]
        d = p1 - p0
        L = d.length
        k = max(1, int(L / 2.0))
        uu = d.normalized()
        for j in range(k):
            a = p0 + d * (j / k)
            b = p0 + d * ((j + 1) / k)
            if in_gate((a + b) / 2):
                continue
            mb.box((a + b) / 2, uu, (b - a).length + 0.02, 0.3, 0, 1.2, M["wall"], M["wall"], tw=4.0, th=1.2)
            hc = (a + b) / 2
            inward = Vector((-uu.y, uu.x))
            if not point_in_poly(hc + inward * 1.0, poly):
                inward = -inward
            mb.box(hc + inward * 0.75, uu, (b - a).length + 0.02, 1.0, 0, 0.9, M["hedge"], M["hedge"])

    # 동별 화단(앞), 보도(뒤), 주차(뒤)
    stalls = []
    for info in infos:
        c, u, n, D = info["c"], info["u"], info["n"], info["D"]
        for pc in info["pieces"]:
            a0, a1, o = pc["a0"], pc["a1"], pc["o"]
            am, al = (a0 + a1) / 2, (a1 - a0)
            gc = c + u * am + n * (D / 2 + o + 2.75)
            mb.box(gc, u, al + 1.0, 5.5, 0, 0.15, M["curb"], M["grass"], tw=4.0, th=0.15)
            BLOCKED.append(rect_pts(gc, u, al + 1.0, 5.5))
            info.setdefault("beds", []).append((gc, u, al + 1.0, 5.5))
            sc = c + u * am + n * (-D / 2 + o - 1.0)
            mb.flat(rect_pts(sc, u, al, 2.0), 0.03, M["paver"], tile=4.0)
        if info["back_parking"]:
            o0 = info["pieces"][0]["o"]
            row_c = c + n * (-D / 2 + o0 - 3.6 - 2.5)
            stalls += parking_row(mb, M, row_c, u, info["L"] - 4.0, -n)

    # 중앙 주차장: 105동과 나란한 양면 주차 3줄
    a105, b105 = P(322, 340), P(437, 437)
    u105 = (b105 - a105).normalized()
    sw = Vector((-0.645, -0.764))
    c105 = (a105 + b105) / 2
    for d, Lr in ((21, 44), (35, 46), (49, 34)):
        rc = c105 + sw * d
        stalls += parking_row(mb, M, rc + sw * 2.5, u105, Lr, sw)
        stalls += parking_row(mb, M, rc - sw * 2.5, u105, Lr, -sw)
    # 101동 앞(남쪽) 주차 한 줄
    stalls += parking_row(mb, M, P(352, 560) + Vector((0, 0)), Vector((1, 0)), 80, Vector((0, -1)))

    mb.build("Ground", col)
    return stalls


def parking_row(mb, M, c, u, L, facing):
    """c: 주차칸 줄 중심, u: 줄 방향, facing: 차가 머리를 두는 방향."""
    n = facing.normalized()
    k = int(L // 2.5)
    start = c - u * (k * 2.5 / 2)
    out = []
    for i in range(k + 1):
        p = start + u * (i * 2.5)
        mb.flat(rect_pts(p, n, 5.0, 0.12), 0.02, M["line"])
        if i < k:
            out.append((p + u * 1.25, n))
    mb.flat(rect_pts(c + n * 2.5, u, k * 2.5, 0.12), 0.02, M["line"])
    BLOCKED.append(rect_pts(c, u, k * 2.5, 5.0))
    return out


# ---------------------------------------------------------------- 소품
def make_tree_meshes(col):
    trunk = mat_col("Bark", (92, 70, 54), 0.95)
    pine = mat_col("Leaf_Pine", (44, 82, 52), 0.9)
    leaf = mat_col("Leaf", (86, 140, 64), 0.9)
    leaf2 = mat_col("Leaf_Light", (112, 160, 76), 0.9)
    meshes = []
    for kind in ("pine", "pine", "pine", "round", "round", "round2"):
        if kind == "pine":
            # 살짝 기운 줄기 + 높이마다 옆으로 퍼진 잎 덩어리 (소나무)
            lean = rng.uniform(0.15, 0.35)
            bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.17, depth=4.6, location=(lean * 2.3, 0, 2.3))
            tr = bpy.context.active_object
            tr.rotation_euler = (0, math.atan(lean), 0)
            tr.data.materials.append(trunk)
            parts = [tr]
            tip = Vector((lean * 4.6, 0))
            blobs = [(3.0, 1.0, 1.25), (3.9, 0.85, 1.1), (4.7, 0.7, 0.9), (5.2, 0.4, 0.7)]
            for i, (z, spread, r) in enumerate(blobs):
                ang = rng.uniform(0, 6.28)
                off = Vector((math.cos(ang), math.sin(ang))) * spread * rng.uniform(0.6, 1.2)
                base = tip * (z / 5.0)
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r,
                                                      location=(base.x + off.x, base.y + off.y, z))
                s = bpy.context.active_object
                s.scale = (rng.uniform(1.3, 1.7), rng.uniform(1.1, 1.5), rng.uniform(0.5, 0.65))
                s.rotation_euler = (0, 0, rng.uniform(0, 6.28))
                s.data.materials.append(pine)
                parts.append(s)
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.16, depth=2.6, location=(0, 0, 1.3))
            tr = bpy.context.active_object
            tr.data.materials.append(trunk)
            parts = [tr]
            m = leaf if kind == "round" else leaf2
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=2.2, location=(0, 0, 4.2))
            s = bpy.context.active_object
            s.scale = (1.0, 1.0, 1.15)
            s.data.materials.append(m)
            parts.append(s)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.4, location=(0.9, 0.4, 5.3))
            s2 = bpy.context.active_object
            s2.data.materials.append(m)
            parts.append(s2)
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = tr
        bpy.ops.object.join()
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        ob = bpy.context.active_object
        meshes.append(ob.data)
        bpy.data.objects.remove(ob)
    return meshes


def make_car_meshes():
    glass = mat_col("Car_Glass", (40, 48, 56), 0.15)
    tire = mat_col("Car_Tire", (30, 30, 32), 0.9)
    colors = [(236, 236, 234), (236, 236, 234), (180, 182, 186), (180, 182, 186), (30, 32, 36),
              (90, 94, 100), (40, 52, 90), (196, 186, 166)]
    meshes = []
    for i, rgb in enumerate(colors):
        body = mat_col(f"Car_Paint_{i}", rgb, 0.3, 0.3)
        mb = MeshBuilder()
        f = Vector((1, 0))
        mb.box(Vector((0, 0)), f, 4.6, 1.8, 0.28, 0.95, body, body, bottom=True)
        # 캐빈(유리)
        q = rect_pts(Vector((-0.25, 0)), f, 2.5, 1.62)
        qt = rect_pts(Vector((-0.35, 0)), f, 1.8, 1.4)
        for j in range(4):
            a, b = q[j], q[(j + 1) % 4]
            at, bt = qt[j], qt[(j + 1) % 4]
            mb.add([v3(a, 0.95), v3(b, 0.95), v3(bt, 1.42), v3(at, 1.42)],
                   [(0, 0), (1, 0), (1, 1), (0, 1)], glass)
        mb.flat(qt, 1.42, body)
        for sx in (-1.45, 1.45):
            for sy in (-0.82, 0.82):
                mb.box(Vector((sx, sy)), f, 0.66, 0.24, 0.0, 0.62, tire, tire)
        me = bpy.data.meshes.new(f"car_{i}")
        ob = mb.build(f"car_{i}", bpy.context.scene.collection)
        meshes.append(ob.data)
        bpy.data.objects.remove(ob)
    return meshes


def place_instances(meshes, items, col, prefix):
    for i, (p, ang, sc) in enumerate(items):
        me = rng.choice(meshes)
        ob = bpy.data.objects.new(f"{prefix}_{i:03d}", me)
        ob.location = (p.x, p.y, 0.0)
        ob.rotation_euler = (0, 0, ang)
        ob.scale = (sc, sc, sc)
        col.objects.link(ob)


def build_props(infos, stalls, col_trees, col_cars, col_props):
    poly = [P(*q) for q in BOUNDARY]
    M = dict(
        brick=mat_img("Brick", "brick.png", 0.9),
        hutroof=mat_col("Roof_Brown", (110, 78, 60), 0.85),
        bluetile=mat_col("Roof_BlueTile", (46, 76, 150), 0.5),
        wood=mat_col("Wood", (150, 104, 66), 0.8),
        sand=mat_img("Sand", "sand.png", 0.95),
        red=mat_col("Play_Red", (226, 64, 52), 0.5),
        yellow=mat_col("Play_Yellow", (250, 200, 40), 0.5),
        blue=mat_col("Play_Blue", (40, 120, 220), 0.5),
        steel=mat_col("Steel", (170, 172, 176), 0.4, 0.8),
        shop=mat_img("Shopfront", "shop.png", 0.6),
        shopwall=mat_img("Shop_Upper", "back.png", 0.8),
        concrete=mat_col("Concrete_Cap", (226, 226, 220), 0.85),
        door=mat_col("Door_Steel", (120, 128, 134), 0.5, 0.4),
    )
    mb = MeshBuilder()

    def hip_roof(c, u, sx, sy, z, h, mat, over=0.5):
        q = rect_pts(c, u, sx + over * 2, sy + over * 2)
        ridge = (sx - sy) / 2 if sx > sy else 0.0
        r0, r1 = c - u * ridge, c + u * ridge
        tops = [r0, r1, r1, r0]
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            ta, tb = tops[i], tops[(i + 1) % 4]
            if (ta - tb).length < 1e-6:
                mb.add([v3(a, z), v3(b, z), v3(ta, z + h)], [(0, 0), (1, 0), (0.5, 1)], mat)
            else:
                mb.add([v3(a, z), v3(b, z), v3(tb, z + h), v3(ta, z + h)], [(0, 0), (1, 0), (1, 1), (0, 1)], mat)
        mb.flat(q, z, mat, down=True)

    # 경비실 / 분리수거장 (벽돌)
    huts = [(P(262, 570), Vector((1, 0)), 4.0, 3.2), (P(185, 410), Vector((0, 1)), 5.0, 3.0),
            (P(300, 470), Vector((0.764, -0.645)), 5.0, 3.0)]
    for c, u, sx, sy in huts:
        mb.box(c, u, sx, sy, 0, 2.6, M["brick"], M["hutroof"], tw=3.0, th=2.6)
        n = Vector((-u.y, u.x))
        mb.box(c + n * (sy / 2 + 0.02), u, 1.0, 0.06, 0, 2.1, M["door"], M["door"])
        hip_roof(c, u, sx, sy, 2.6, 1.1, M["hutroof"])
        BLOCKED.append(rect_pts(c, u, sx + 2, sy + 2))

    # 정자 (파란 기와)
    pc, pu = P(205, 355), Vector((1, 0))
    mb.box(pc, pu, 6.0, 6.0, 0, 0.5, M["wood"], M["wood"])
    for sx in (-2.6, 2.6):
        for sy in (-2.6, 2.6):
            mb.box(pc + Vector((sx, sy)), pu, 0.3, 0.3, 0.5, 3.0, M["wood"], M["wood"])
    hip_roof(pc, pu, 6.0, 6.0, 3.0, 1.8, M["bluetile"], over=0.9)
    BLOCKED.append(rect_pts(pc, pu, 9, 9))

    # 놀이터 (107동 북쪽)
    gc, gu = P(199, 236), Vector((0.995, 0.083))
    mb.box(gc, gu, 18, 9, 0, 0.12, M["wood"], M["sand"])
    gn = Vector((-gu.y, gu.x))
    # 미끄럼틀
    s = gc - gu * 5
    mb.box(s, gu, 2.0, 2.0, 0.12, 1.8, M["yellow"], M["red"])
    for dx in (-0.9, 0.9):
        for dy in (-0.9, 0.9):
            mb.box(s + gu * dx + gn * dy, gu, 0.12, 0.12, 1.8, 2.8, M["blue"], M["blue"])
    hip_roof(s, gu, 2.0, 2.0, 2.8, 0.8, M["red"], over=0.2)
    sl0, sl1 = s + gu * 1.0, s + gu * 4.0
    w = gn * 0.45
    mb.add([v3(sl0 - w, 1.8), v3(sl0 + w, 1.8), v3(sl1 + w, 0.15), v3(sl1 - w, 0.15)],
           [(0, 0), (1, 0), (1, 1), (0, 1)], M["yellow"])
    mb.add([v3(sl1 - w, 0.15), v3(sl1 + w, 0.15), v3(sl0 + w, 1.8), v3(sl0 - w, 1.8)],
           [(0, 0), (1, 0), (1, 1), (0, 1)], M["yellow"])
    # 그네
    sc = gc + gu * 4.5
    for dx in (-2.0, 2.0):
        mb.box(sc + gu * dx, gu, 0.15, 1.6, 0.12, 2.6, M["blue"], M["blue"])
    mb.box(sc, gu, 4.2, 0.15, 2.5, 2.65, M["steel"], M["steel"])
    for dx in (-1.0, 1.0):
        mb.box(sc + gu * dx, gu, 0.5, 0.25, 0.55, 0.62, M["red"], M["red"])
        for ex in (-0.22, 0.22):
            mb.box(sc + gu * (dx + ex), gu, 0.03, 0.03, 0.62, 2.5, M["steel"], M["steel"])
    BLOCKED.append(rect_pts(gc, gu, 20, 11))

    # 상가동 (2층)
    shc, shu = P(180, 576), Vector((1, 0))
    sx, sy = 51.0, 11.0
    q = rect_pts(shc, shu, sx, sy)
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        N = ((a + b) / 2 - shc).normalized()
        long_side = (b - a).length > 20
        mb.wall(a, b, 0, 3.6, N, M["shop"] if long_side else M["concrete"], 24.0, 3.6)
        mb.wall(a, b, 3.6, 7.2, N, M["shopwall"] if long_side else M["concrete"], 16.0, 3.6)
        mb.wall(a, b, 7.2, 8.0, N, M["concrete"], 4.0, 0.8)
    mb.flat(q, 8.0, M["concrete"])
    BLOCKED.append(rect_pts(shc, shu, sx + 2, sy + 2))

    mb.build("Props", col_props)

    # 차
    car_meshes = make_car_meshes()
    car_items = []
    for p, facing in stalls:
        if rng.random() < 0.68:
            ang = math.atan2(facing.y, facing.x) + (math.pi if rng.random() < 0.35 else 0) + rng.uniform(-0.04, 0.04)
            car_items.append((p, ang, 1.0))
    place_instances(car_meshes, car_items, col_cars, "Car")

    # 나무: 화단 위, 담장 안쪽, 빈 땅
    tree_meshes = make_tree_meshes(col_trees)
    BLOCKED_TREES = [b for b in BLOCKED]
    tree_items = []
    for info in infos:
        for gc, u, L, w in info.get("beds", []):
            k = max(1, int(L / 6.5))
            for i in range(k):
                p = gc + u * (-L / 2 + (i + 0.5) * L / k + rng.uniform(-1, 1))
                tree_items.append((p, rng.uniform(0, 6.28), rng.uniform(0.8, 1.15)))
    for i in range(len(poly)):
        p0, p1 = poly[i], poly[(i + 1) % len(poly)]
        d = p1 - p0
        uu = d.normalized()
        inward = Vector((-uu.y, uu.x))
        if not point_in_poly((p0 + p1) / 2 + inward * 2, poly):
            inward = -inward
        k = int(d.length / 7.5)
        for j in range(1, k):
            p = p0 + d * (j / k) + inward * rng.uniform(2.8, 4.0)
            if free(p, 1.0):
                tree_items.append((p, rng.uniform(0, 6.28), rng.uniform(0.8, 1.2)))
    # 단지 밖 하천변 가로수
    ne0, ne1 = P(250, 215), P(522, 470)
    une = (ne1 - ne0).normalized()
    nne = Vector((une.y, -une.x))
    if nne.dot(Vector((1, 1))) < 0:
        nne = -nne
    for side in (13.0, 55.5):
        for j in range(-14, 34):
            p = ne0 + une * (j * 7.0) + nne * (side + rng.uniform(-0.6, 0.6) + 1.8)
            tree_items.append((p, rng.uniform(0, 6.28), rng.uniform(0.9, 1.25)))
    place_instances(tree_meshes, tree_items, col_trees, "Tree")
    return len(car_items), len(tree_items)


# ---------------------------------------------------------------- 렌더
def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.1
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    # 지나치게 맑고 밝은 하늘: 위는 파랗고 지평선은 거의 흰색
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.82, 0.90, 1.0, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.25, 0.52, 0.95, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(1.5)
    sun_d.color = (1.0, 0.97, 0.92)
    sun = bpy.data.objects.new("Sun", sun_d)
    sun.rotation_euler = (math.radians(40), 0, math.radians(30))
    sc.collection.objects.link(sun)


def camera(name, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 2000
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- 메인
def main():
    global TEX_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--render", default="")
    ap.add_argument("--samples", type=int, default=48)
    args = ap.parse_args(sys.argv[1:])
    TEX_DIR = os.path.abspath(args.tex)
    os.makedirs(args.out, exist_ok=True)

    clear_scene()
    sc = bpy.context.scene
    cols = {}
    for nm in ("Buildings", "Ground", "Props", "Trees", "Cars"):
        cols[nm] = bpy.data.collections.new(nm)
        sc.collection.children.link(cols[nm])

    infos = [build_apartment(bd, cols["Buildings"]) for bd in BUILDINGS]
    for info, bd in zip(infos, BUILDINGS):
        info["back_parking"] = bd["back_parking"]
    add_building_numbers(infos, cols["Buildings"])
    stalls = build_ground(infos, cols["Ground"])
    ncars, ntrees = build_props(infos, stalls, cols["Trees"], cols["Cars"], cols["Props"])
    print(f"buildings={len(infos)} stalls={len(stalls)} cars={ncars} trees={ntrees}")

    # 게임에서 쓸 기준점: 공동현관 위치
    for info in infos:
        for i, (p, d) in enumerate(info["entrances"]):
            e = bpy.data.objects.new(f"Entrance_{info['no']}_{i + 1}", None)
            e.location = (p.x, p.y, 0)
            e.rotation_euler = (0, 0, math.atan2(d.y, d.x))
            e.empty_display_size = 0.5
            cols["Props"].objects.link(e)

    blend = os.path.join(args.out, "hwawon_taewang.blend")
    glb = os.path.join(args.out, "hwawon_taewang.glb")
    bpy.ops.file.pack_all()  # 텍스처를 .blend 안에 넣어서 어디서 열어도 깨지지 않게
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(glb), export_format="GLB", export_apply=True)
    print("saved", blend, glb)

    if args.render:
        setup_render()
        sc.cycles.samples = args.samples
        rd = args.render
        os.makedirs(rd, exist_ok=True)
        views = {
            "aerial": (camera("Cam_Aerial", (-150, -175, 120), (15, -5, 10), lens=30), 1600, 900),
            "top": (camera("Cam_Top", (8, 5, 300), (8, 5.01, 0), ortho=255), 1200, 1200),
            "street_lot": (camera("Cam_Street", (8, -36, 1.6), (40, 28, 14), lens=24), 1600, 900),
            "gate": (camera("Cam_Gate", (-1, -92, 1.6), (12, -30, 12), lens=24), 1600, 900),
            "courtyard": (camera("Cam_Courtyard", (-36, 16, 1.6), (-8, 6, 12), lens=24), 1600, 900),
        }
        only = os.environ.get("VIEWS")
        for k, (cam, w, h) in views.items():
            if only and k not in only.split(","):
                continue
            render(cam, os.path.abspath(os.path.join(rd, f"{k}.png")), w, h)
            print("rendered", k)


if __name__ == "__main__":
    main()
