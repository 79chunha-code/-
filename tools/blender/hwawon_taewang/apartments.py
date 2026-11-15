"""아파트 동 만들기 (2026년 도색 기준: 흰색/회색/남색)."""
import math

from mathutils import Vector

import lib
from lib import P, MeshBuilder, mat_col, mat_tex, perp, rect_pts, rng, v3

FLOOR_H = 2.7
BASE_H = 0.5
PARAPET_H = 1.1
CORE_W = 3.2
CORE_P = 0.9          # 계단실이 뒤로 튀어나온 깊이
TEX_TH = FLOOR_H * 4  # 텍스처 한 장 = 4층

# a, b: 긴 축 양 끝(지도 픽셀). segs: 계단실 단위 수. floors: 단위별 층수.
# front: 발코니 면이 향하는 대략적인 방향. offs: 단위별 앞뒤 엇갈림(m).
BUILDINGS = [
    dict(no="101", a=(258, 523.5), b=(445, 523.5), depth=13.0, segs=6,
         floors=[16, 18, 18, 18, 18, 12], front=(0, -1), scheme="navy", back_parking=True),
    dict(no="102", a=(120, 535), b=(212, 535), depth=11.5, segs=3,
         floors=[16, 18, 18], front=(0, -1), scheme="navy", back_parking=True),
    dict(no="103", a=(227, 398), b=(227, 490), depth=11.5, segs=3,
         floors=[16, 18, 18], front=(1, 0), scheme="gray", back_parking=True),
    dict(no="104", a=(446, 480), b=(514, 480), depth=13.0, segs=2,
         floors=[18, 18], front=(0, -1), scheme="white", back_parking=True),
    dict(no="105", a=(322, 340), b=(437, 437), depth=11.5, segs=5,
         floors=[18, 18, 18, 18, 16], front=(-0.6, -0.8), scheme="white", back_parking=False),
    dict(no="106", a=(240, 273), b=(322, 343), depth=11.5, segs=3,
         floors=[16, 18, 18], front=(-0.6, -0.8), scheme="white", back_parking=False),
    dict(no="107", a=(163, 266), b=(235, 260), depth=10.0, segs=2,
         floors=[16, 18], front=(0, -1), scheme="gray", back_parking=False),
    dict(no="108", a=(68, 445), b=(160, 283), depth=10.0, segs=6,
         floors=[14, 16, 18, 18, 16, 14], front=(0.9, -0.3), scheme="gray", back_parking=False,
         offs=[0.0, 0.0, 1.6, 1.6, 3.2, 3.2]),
    dict(no="109", a=(94, 460), b=(94, 530), depth=10.0, segs=2,
         floors=[9, 11], front=(1, 0), scheme="white", back_parking=True),
]


def materials():
    return dict(
        front=dict(white=mat_tex("Apt_Front_White", "front_white"),
                   navy=mat_tex("Apt_Front_Navy", "front_navy"),
                   gray=mat_tex("Apt_Front_Gray", "front_gray")),
        bay=mat_tex("Apt_Bay", "bay"),
        back=mat_tex("Apt_Back", "back_white"),
        back_base=mat_tex("Apt_Back_Base", "back_base"),
        core=mat_tex("Apt_Core", "core_white"),
        core_base=mat_tex("Apt_Core_Base", "core_base"),
        door=mat_tex("Apt_Core_Door", "core_door"),
        side=mat_tex("Apt_Side", "side_upper"),
        side_base=mat_tex("Apt_Side_Base", "side_base"),
        parapet=mat_tex("Apt_Parapet", "parapet"),
        roof=mat_tex("Roof_Green", "roof_green", normal=0),
        plinth=mat_tex("Concrete", "concrete"),
        lgray=mat_col("Paint_LightGray", (192, 196, 202), 0.8),
        dgray=mat_col("Paint_DarkGray", (90, 95, 106), 0.8),
        navy=mat_col("Paint_Navy", (30, 42, 88), 0.7),
        white=mat_col("Paint_White", (228, 230, 232), 0.8),
        mgray=mat_col("Paint_MidGray", (146, 151, 160), 0.8),
        tile=mat_tex("RoofTile_Blue", "rooftile_blue"),
        steps=mat_tex("Curb", "curb"),
        steel=mat_col("Steel", (150, 154, 160), 0.4, 0.9),
    )


def build_apartment(bd, col, M, plates):
    a, b = P(*bd["a"]), P(*bd["b"])
    c = (a + b) / 2
    u = (b - a).normalized()
    L = (b - a).length
    n = perp(u)
    if n.dot(Vector(bd["front"])) < 0:
        n = -n
    D = bd["depth"]
    segs = bd["segs"]
    sw = L / segs
    hw = sw / 2
    floors = bd["floors"]
    offs = bd.get("offs", [0.0] * segs)
    bayc = 3.2                              # 둥근 발코니 폭
    PLAIN = 1.0                             # 세대 사이 색 기둥 폭
    accent = {'white': M['mgray'], 'gray': M['dgray'], 'navy': M['navy']}[bd['scheme']]
    front_mat = M["front"][bd["scheme"]]
    mb = MeshBuilder()

    def pt(along, across):
        return c + u * along + n * across

    def order(p0, p1, N):
        """바깥에서 봤을 때 왼쪽 -> 오른쪽 순서로."""
        r = Vector((-N.y, N.x))
        return (p0, p1) if (p1 - p0).dot(r) >= 0 else (p1, p0)

    info = dict(no=bd["no"], c=c, u=u, n=n, L=L, D=D, pieces=[], entrances=[], beds=[],
                back_parking=bd["back_parking"], sw=sw)

    for k in range(segs):
        f = floors[k]
        o = offs[k]
        a0 = -L / 2 + k * sw
        a1 = a0 + sw
        am = (a0 + a1) / 2
        fb, bb = D / 2 + o, -D / 2 + o
        top = BASE_H + FLOOR_H * f
        nb = 4 if f >= 12 else 3                 # 아래쪽 진회색 층수
        zb = BASE_H + FLOOR_H * nb

        # ---------------- 앞면 (발코니)
        # 한 세대 = [샷시 발코니 칸][둥근 발코니][색 기둥]
        for hh, (h0, h1) in enumerate(((a0, am), (am, a1))):
            f0, f1 = h0, h1 - bayc - PLAIN
            b0, b1 = f1, h1 - PLAIN
            mb.wall(pt(b1, fb), pt(h1, fb), 0, top, n, accent, 2, 2)
            var = rng.randrange(4)
            vrow = rng.randrange(4) / 4
            p0, p1 = order(pt(f0, fb), pt(f1, fb), n)
            mb.wall(p0, p1, 0, BASE_H, n, M["plinth"], 3.0, 3.0)
            mb.wall(p0, p1, BASE_H, top, n, front_mat, 1, TEX_TH, u0=var / 4, v0=vrow, fit_u=0.25)
            # 둥근 발코니
            pts = []
            N_ARC = 7
            for i in range(N_ARC + 1):
                t = i / N_ARC
                bulge = 0.65 * (math.sin(math.pi * t) ** 0.6)
                pts.append(pt(b0 + (b1 - b0) * t, fb + bulge))
            if (pts[-1] - pts[0]).dot(Vector((-n.y, n.x))) < 0:
                pts.reverse()
            var2 = rng.randrange(4)
            mb.strip(pts, BASE_H, top, M["bay"], TEX_TH, var2 / 4, var2 / 4 + 0.25, v0=rng.randrange(4) / 4)
            mb.flat(pts, top, M["white"])
            mb.flat(pts, BASE_H, M["plinth"], down=True)
            # 발코니 뒤 벽 아래쪽 (기단)
            q0, q1 = order(pt(b0, fb), pt(b1, fb), n)
            mb.wall(q0, q1, 0, BASE_H, n, M["plinth"], 3.0, 3.0)

        # ---------------- 뒷면 (계단실 쪽)
        bw = (sw - CORE_W) / 2
        for (h0, h1) in ((a0, a0 + bw), (a1 - bw, a1)):
            var = rng.randrange(4)
            vrow = rng.randrange(4) / 4
            p0, p1 = pt(h0, bb), pt(h1, bb)
            mb.wall(p0, p1, 0, BASE_H, -n, M["plinth"], 3.0, 3.0)
            mb.wall(p0, p1, BASE_H, zb, -n, M["back_base"], 1, TEX_TH, u0=var / 4, v0=0.0, fit_u=0.25)
            mb.wall(p0, p1, zb, top, -n, M["back"], 1, TEX_TH, u0=var / 4, v0=vrow, fit_u=0.25)
        # 계단실 (튀어나온 부분)
        c0, c1 = am - CORE_W / 2, am + CORE_W / 2
        cf = bb - CORE_P
        g1 = BASE_H + FLOOR_H
        mb.wall(pt(c0, cf), pt(c1, cf), 0, BASE_H, -n, M["plinth"], 3.0, 3.0)
        mb.wall(pt(c0, cf), pt(c1, cf), BASE_H, g1, -n, M["door"], 1, FLOOR_H, fit_u=1.0)
        mb.wall(pt(c0, cf), pt(c1, cf), g1, zb, -n, M["core_base"], 1, TEX_TH, v0=0.25, fit_u=1.0)
        mb.wall(pt(c0, cf), pt(c1, cf), zb, top, -n, M["core"], 1, TEX_TH, v0=rng.randrange(4) / 4, fit_u=1.0)
        for (ca, N) in ((c0, -u), (c1, u)):
            mb.wall(pt(ca, cf), pt(ca, bb), 0, zb, N, M["dgray"], 2, 2)
            mb.wall(pt(ca, cf), pt(ca, bb), zb, top, N, M["lgray"], 2, 2)
        # 옥탑 (계단실/엘리베이터 기계실)
        rc = pt(am, bb - CORE_P + 2.6)
        mb.box(rc, u, CORE_W + 0.6, 5.2, top, top + 3.3, M["lgray"], M["roof"])
        mb.box(rc, u, CORE_W + 1.0, 5.6, top + 3.3, top + 3.55, M["white"], M["white"], bottom=True)

        # ---------------- 공동현관: 계단, 캐노피(파란 기와), 동 번호판
        ec = pt(am, cf - 1.3)
        mb.box(ec, u, 3.4, 2.6, 0, BASE_H, M["steps"], M["steps"], tw=2.0, th=2.0)
        for i, hgt in enumerate((0.34, 0.17)):
            mb.box(pt(am, cf - 2.6 - 0.3 * i - 0.15), u, 3.4, 0.3, 0, hgt, M["steps"], M["steps"], tw=2.0, th=2.0)
        for sx in (-1.45, 1.45):
            mb.box(pt(am + sx, cf - 2.2), u, 0.22, 0.22, BASE_H, BASE_H + 2.55, M["white"], M["white"])
        zc = BASE_H + 2.55
        mb.box(pt(am, cf - 1.25), u, 3.6, 2.5, zc, zc + 0.22, M["white"], M["white"], bottom=True)
        mb.hip_roof(pt(am, cf - 1.25), u, 3.6, 2.5, zc + 0.22, 0.75, M["tile"], over=0.35)
        # 번호판 (캐노피 앞)
        pl = plates[bd["no"]]
        pc = pt(am, cf - 2.52)
        l, r = order(pc - u * 0.55, pc + u * 0.55, -n)
        mb.quad3([v3(l, zc - 0.02), v3(r, zc - 0.02), v3(r, zc + 0.36), v3(l, zc + 0.36)], pl)
        info["entrances"].append((pt(am, cf - 4.0), -n))

        # ---------------- 측벽
        for (ae, N) in ((a0, -u), (a1, u)):
            p0, p1 = pt(ae, bb), pt(ae, fb)
            mb.wall(p0, p1, 0, BASE_H, N, M["plinth"], 3.0, 3.0)
            mb.wall(p0, p1, BASE_H, zb, N, M["side_base"], 1, TEX_TH, fit_u=1.0)
            mb.wall(p0, p1, zb, top, N, M["side"], 1, TEX_TH, v0=nb / 4, fit_u=1.0)

        # ---------------- 옥상: 난간벽과 바닥
        outer = [pt(a0, bb), pt(a1, bb), pt(a1, fb), pt(a0, fb)]
        ins = 0.22
        inner = [pt(a0 + ins, bb + ins), pt(a1 - ins, bb + ins), pt(a1 - ins, fb - ins), pt(a0 + ins, fb - ins)]
        cc = pt(am, o)
        for i in range(4):
            p0, p1 = outer[i], outer[(i + 1) % 4]
            N = ((p0 + p1) / 2 - cc).normalized()
            mb.wall(p0, p1, top, top + PARAPET_H, N, M["parapet"], 8.0, PARAPET_H)
            q0, q1 = inner[i], inner[(i + 1) % 4]
            mb.wall(q0, q1, top, top + PARAPET_H, -N, M["lgray"], 4.0, 1.0)
            mb.flat([p0, p1, q1, q0], top + PARAPET_H, M["lgray"])
        mb.flat(inner, top + 0.02, M["roof"], tile=12.0)
        if rng.random() < 0.6:      # 물탱크/설비
            mb.box(pt(am + rng.uniform(-3, 3), o + 2.2), u, 2.4, 2.0, top, top + 1.7, M["lgray"], M["lgray"])

        info["pieces"].append(dict(a0=a0, a1=a1, o=o, top=top, zb=zb))
        lib.block([pt(a0 - 0.5, bb - 4.2), pt(a1 + 0.5, bb - 4.2), pt(a1 + 0.5, fb + 1.2), pt(a0 - 0.5, fb + 1.2)])

    # ---------------- 건물 모서리 남색 기둥
    first, last = info["pieces"][0], info["pieces"][-1]
    for pc_, ae, sgn in ((first, first["a0"], 1), (last, last["a1"], -1)):
        o = pc_["o"]
        for across in (D / 2 + o + 0.12, -D / 2 + o - 0.12):
            mb.box(pt(ae + sgn * 0.5, across), u, 1.0, 0.3, 0, pc_["top"] + PARAPET_H, M["navy"], M["navy"])

    ob = mb.build(f"Apt_{bd['no']}", col)
    ob["building_no"] = bd["no"]
    info["obj"] = ob
    return info


def add_numbers(infos, col):
    """측벽에 큰 동 번호."""
    mat = mat_col("Paint_Number", (236, 238, 240), 0.7)
    objs = []
    for info in infos:
        c, u, n = info["c"], info["u"], info["n"]
        for pc, key, N in ((info["pieces"][0], "a0", -u), (info["pieces"][-1], "a1", u)):
            p = c + u * pc[key] + n * pc["o"] + N * 0.05
            rot = (math.radians(90), 0, math.atan2(N.x, -N.y))
            objs.append(lib.text_mesh(info["no"], 3.0, mat, col, f"num_{info['no']}",
                                      (p.x, p.y, pc["zb"] - 2.0), rot, extrude=0.02))
    lib.join_as_mesh(objs, "BuildingNumbers")
