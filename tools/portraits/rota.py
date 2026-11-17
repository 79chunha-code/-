"""로타 대화창 초상화 (도트, 56x56). 표정마다 PNG를 만든다.

사용법: python3 tools/portraits/rota.py <출력 폴더>
"""
import sys
from PIL import Image

W = H = 56
PAL = {
    ".": None,
    "K": (30, 26, 36),      # outline
    "h": (22, 22, 32),      # hair darkest
    "H": (40, 41, 56),      # hair
    "I": (68, 72, 96),      # hair sheen
    "J": (110, 118, 150),   # hair shine
    "s": (255, 235, 218),   # skin light
    "S": (252, 220, 198),   # skin
    "T": (234, 184, 158),   # skin shade
    "U": (208, 146, 124),   # nose
    "b": (247, 168, 156),   # blush
    "W": (255, 255, 255),
    "e": (52, 56, 72),      # iris dark
    "E": (104, 112, 132),   # iris
    "F": (176, 184, 202),   # iris light
    "m": (150, 70, 70),     # mouth
    "n": (214, 104, 104),   # mouth inside
    "c": (248, 246, 240),   # tunic
    "C": (222, 216, 204),   # tunic shade
    "D": (184, 176, 160),   # tunic deep
    "l": (190, 138, 96),    # hood light
    "L": (150, 98, 62),     # hood
    "M": (108, 68, 42),     # hood shade
    "r": (126, 84, 54),     # stitches
    "R": (70, 50, 40),      # strings
}


def blank():
    return [["."] * W for _ in range(H)]


def poly(g, pts, c):
    n = len(pts)
    ys = [p[1] for p in pts]
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
        sy = y + 0.5
        xs = []
        for i in range(n):
            x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % n]
            if (y1 <= sy < y2) or (y2 <= sy < y1):
                xs.append(x1 + (sy - y1) / (y2 - y1) * (x2 - x1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(max(0, round(xs[i])), min(W, round(xs[i + 1]))):
                g[y][x] = c


def stamp(g, x0, y0, rows, keep="."):
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != keep:
                g[y0 + dy][x0 + dx] = ch


def outline(g, inside_of=None):
    src = [r[:] for r in g]
    for y in range(H):
        for x in range(W):
            if src[y][x] != ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and 0 <= yy < H and src[yy][xx] != ".":
                    g[y][x] = "K"
                    break


# ---------- eyes (left eye as drawn; the right eye is mirrored) ----------
EYES = {
    "base": [
        "..KKKKKK.",
        ".KKeeeeKK",
        "KKeeeeeeK",
        ".KEWWEEeK",
        ".KEWWEEEK",
        ".KEEEEFEK",
        ".KFEEFFFK",
        "..KFFFFK.",
        "...KKKK..",
    ],
    "smile": [
        ".........",
        ".........",
        ".........",
        "..KKKKK..",
        ".KK...KK.",
        "KK.....KK",
        ".........",
        ".........",
        ".........",
    ],
    "fear": [
        ".........",
        "..KKKKK..",
        ".KWWWWWK.",
        "KWWeeeWWK",
        "KWWEWEWWK",
        "KWWFFFWWK",
        ".KWWWWWK.",
        "..KKKKK..",
        ".........",
    ],
}
# brows sit on the skin just under the fringe; inner end first
BROWS = {
    "base": [(2, 0, "hhhh")],
    "smile": [(2, -1, "hhhh")],
    "fear": [(3, -1, "hh"), (1, 0, "hh")],
}
MOUTHS = {
    "base": [".KKKKK.", ".KnnnK.", "..KKK.."],
    "smile": ["KKKKKKK", ".KnnnK.", "..KKK.."],
    "fear": ["...K...", "..KnK..", "...K..."],
}
SKIN = set("sSTUb")
HAIR = set("HIJ")


def mirror(rows):
    return [r[::-1] for r in rows]


def portrait(face):
    g = blank()
    # ---------- shoulders: white tunic under a brown hood collar ----------
    poly(g, [(4, 56), (8, 48), (16, 44.5), (40, 44.5), (48, 48), (52, 56)], "c")
    poly(g, [(4, 56), (8, 48), (11, 46.5), (12, 56)], "C")
    poly(g, [(44, 56), (45, 46.5), (48, 48), (52, 56)], "C")
    poly(g, [(23, 36), (33, 36), (33, 46), (23, 46)], "S")                 # neck
    poly(g, [(23, 38), (33, 38), (33, 41), (23, 42)], "T")
    # the hood lies around the neck and dips to a V at the chest
    poly(g, [(12, 46), (18, 41.5), (24, 42.5), (28, 50), (32, 42.5), (38, 41.5), (44, 46), (40, 48.5), (32, 52), (28, 54), (24, 52), (16, 48.5)], "L")
    poly(g, [(16, 48.5), (24, 52), (28, 54), (32, 52), (40, 48.5), (41, 49.5), (32, 53.5), (28, 55.5), (24, 53.5), (15, 49.5)], "M")
    poly(g, [(18, 42.5), (23, 43.5), (20, 45.5)], "l")
    poly(g, [(33, 43.5), (38, 42.5), (36, 45.5)], "l")
    for x0 in (14, 40):                                                    # cross stitches down the front
        for dx, dy in ((0, 0), (2, 0), (1, 1), (0, 2), (2, 2)):
            g[51 + dy][x0 + dx] = "r"
    # ---------- back hair: a round, full cut down to the jaw ----------
    poly(g, [(11.5, 24), (12, 13), (15, 7.5), (20, 4), (28, 2.5), (36, 4), (41, 7.5), (44, 13), (44.5, 24), (44, 34), (40, 37), (16, 37), (12, 34)], "H")
    # ears
    for x0, d in ((13, 1), (43, -1)):
        poly(g, [(x0, 24), (x0 + 3 * d, 23.5), (x0 + 3.5 * d, 31), (x0 + 1.5 * d, 31.5)] if d > 0 else
             [(x0 - 3.5, 23.5), (x0, 24), (x0 - 1.5, 31.5), (x0 - 3.5, 31)], "S")
    g[27][14] = "T"; g[28][14] = "T"; g[27][41] = "T"; g[28][41] = "T"
    # ---------- face: narrow chin ----------
    poly(g, [(15.5, 17), (40.5, 17), (40.5, 29), (38, 34.5), (32.5, 39), (28, 40.5), (23.5, 39), (18, 34.5), (15.5, 29)], "S")
    poly(g, [(15.5, 17), (40.5, 17), (40.5, 22), (15.5, 22)], "T")         # shade under the fringe
    poly(g, [(15.5, 28), (17, 28), (19, 34.5), (18, 34.5)], "T")
    poly(g, [(23.5, 39), (28, 40.5), (32.5, 39), (32.5, 40), (28, 41.5), (23.5, 40)], "T")
    for x, y in ((19, 32), (20, 32), (21, 32), (35, 32), (36, 32), (37, 32)):
        g[y][x] = "b"
    g[32][28] = "U"
    # ---------- fringe: spiky strands, one long lock falling between the eyes ----------
    poly(g, [(13, 18), (15, 11), (21, 6.5), (35, 6.5), (41, 11), (43, 18), (43, 20), (13, 20)], "H")
    strands = [((13, 19), (16, 12), (17.5, 24)), ((16, 19), (20, 11), (22, 25)), ((21, 18), (24, 10), (25.5, 23.5)),
               ((25, 18), (28, 10), (31.5, 30.5)), ((29, 18), (32, 10), (34, 24.5)), ((33, 18), (37, 11), (37.5, 25)),
               ((37, 19), (40, 12), (42.5, 24))]
    for a, b, c in strands:
        poly(g, [a, b, c], "H")
    poly(g, [(12, 18), (15.5, 18), (16.5, 33), (15, 37), (12.5, 33)], "H")  # side locks to the jaw
    poly(g, [(40.5, 18), (44, 18), (43.5, 33), (41, 37), (39.5, 33)], "H")
    poly(g, [(16, 10), (21, 6.5), (29, 5.5), (23, 8.5), (18.5, 12)], "I")  # cool sheen on black hair
    poly(g, [(19.5, 8.5), (24, 6.8), (21, 9.5)], "J")
    poly(g, [(33, 6), (38, 8.5), (40.5, 12.5), (36.5, 9.5)], "I")
    for (x0, y0), (x1, y1) in (((21, 9), (19, 17)), ((27, 8), (27, 16)), ((33, 9), (34, 17))):
        n = max(abs(x1 - x0), abs(y1 - y0))
        for k in range(n + 1):
            g[round(y0 + (y1 - y0) * k / n)][round(x0 + (x1 - x0) * k / n)] = "h"
    # where hair meets skin, the hair darkens so each strand reads
    src = [r[:] for r in g]
    for y in range(H):
        for x in range(W):
            if src[y][x] in HAIR and any(0 <= y + dy < H and 0 <= x + dx < W and src[y + dy][x + dx] in SKIN for dx, dy in ((0, 1),)):
                g[y][x] = "h"
    outline(g)
    # ---------- the face itself ----------
    ey = 24
    stamp(g, 17, ey, EYES[face])
    stamp(g, 30, ey, mirror(EYES[face]))
    for x_in, dy, row in BROWS[face]:
        y = ey - 2 + dy
        for k, ch in enumerate(row):
            for xx in (25 - x_in - k, 30 + x_in + k):
                if g[y][xx] in SKIN:
                    g[y][xx] = ch
    stamp(g, 25, 35, MOUTHS[face])
    if face == "fear":                                                   # a bead of sweat
        stamp(g, 39, 17, ["..K..", ".KWK.", "KWWFK", "KWFFK", ".KKK."])
    return g


def save(g, path, scale=1):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y in range(H):
        for x in range(W):
            c = PAL[g[y][x]]
            if c:
                img.putpixel((x, y), c + (255,))
    if scale > 1:
        img = img.resize((W * scale, H * scale), Image.NEAREST)
    img.save(path)


if __name__ == "__main__":
    out = sys.argv[1]
    for face in ("base", "smile", "fear"):
        save(portrait(face), f"{out}/rota_{face}.png")
        save(portrait(face), f"{out}/rota_{face}_x8.png", 8)
