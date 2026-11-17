"""로타 대화창 초상화 (도트, 56x56). 표정마다 PNG를 만든다.

사용법: python3 tools/portraits/rota.py <출력 폴더>
"""
import sys
from PIL import Image

W = H = 56
PAL = {
    ".": None,
    "K": (43, 29, 36),      # outline
    "h": (59, 43, 47),      # hair dark
    "H": (94, 66, 55),      # hair mid
    "I": (133, 96, 74),     # hair light
    "J": (176, 138, 106),   # hair shine
    "s": (255, 233, 214),   # skin light
    "S": (250, 214, 190),   # skin
    "T": (232, 177, 150),   # skin shade
    "U": (205, 140, 120),   # skin deep shade / nose
    "b": (246, 160, 150),   # blush
    "W": (255, 255, 255),
    "e": (36, 48, 92),      # iris dark
    "E": (70, 118, 186),    # iris
    "F": (140, 196, 240),   # iris light
    "m": (150, 70, 70),     # mouth
    "n": (215, 110, 110),   # mouth inside
    "c": (244, 236, 220),   # tunic
    "C": (214, 199, 170),   # tunic shade
    "D": (170, 150, 122),   # tunic deep
    "l": (163, 205, 240),   # scarf light
    "L": (98, 150, 210),    # scarf
    "M": (60, 100, 166),    # scarf shade
    "r": (107, 74, 51),     # strap
    "R": (78, 52, 36),      # strap dark
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
    "base": ["..KKK.."],
    "smile": [".K...K.", "..KnK.."],
    "fear": ["...K...", "..KnK..", "...K..."],
}
SKIN = set("sSTUb")
HAIR = set("HIJ")


def mirror(rows):
    return [r[::-1] for r in rows]


def portrait(face):
    g = blank()
    # ---------- shoulders: cream tunic, a strap across the chest ----------
    poly(g, [(4, 56), (8, 48), (16, 44.5), (40, 44.5), (48, 48), (52, 56)], "c")
    poly(g, [(4, 56), (8, 48), (12, 46.5), (13, 56)], "C")
    poly(g, [(43, 56), (44, 46.5), (48, 48), (52, 56)], "C")
    poly(g, [(36, 46), (40, 46), (24, 56), (19, 56)], "r")
    poly(g, [(38.5, 46), (40, 46), (24, 56), (22.5, 56)], "R")
    poly(g, [(23, 36), (33, 36), (33, 46), (23, 46)], "S")                 # neck
    poly(g, [(23, 38), (33, 38), (33, 41), (23, 42)], "T")
    # ---------- scarf in the village's sky blue ----------
    poly(g, [(16, 44), (21, 41), (35, 41), (40, 44), (38, 48), (28, 49.5), (18, 48)], "L")
    poly(g, [(18, 46.5), (28, 48), (38, 46.5), (38, 48), (28, 49.5), (18, 48)], "M")
    poly(g, [(20, 42.5), (27, 42), (24, 44)], "l")
    poly(g, [(30, 47), (35, 47), (36, 55), (31, 55)], "L")
    poly(g, [(33.5, 47), (35, 47), (36, 55), (34.5, 55)], "M")
    # ---------- back hair: tufts on top, short at the sides ----------
    poly(g, [(12, 24), (12.5, 13), (15, 8), (18, 5.5), (21, 3.5), (24, 5), (27, 2.5), (31, 4.5), (35, 3), (38, 6), (41, 8.5), (43.5, 13), (44, 24),
             (43, 32), (13, 32)], "H")
    poly(g, [(27, 3.5), (28.5, 0.5), (31, 0), (29.5, 1.5), (29, 4)], "H")    # the one strand that never lies down
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
    # ---------- fringe: strands falling to between the eyes ----------
    poly(g, [(13, 18), (15, 11), (21, 7), (35, 7), (41, 11), (43, 18), (43, 20), (13, 20)], "H")
    strands = [((13, 19), (16, 12), (17.5, 25)), ((16, 19), (20, 11), (21.5, 24.5)), ((20, 18), (24, 10), (26.5, 25.5)),
               ((25, 18), (28, 10), (29, 23)), ((28, 18), (32, 10), (31.5, 25)), ((32, 18), (36, 11), (36.5, 24)),
               ((36, 19), (40, 12), (42.5, 25))]
    for a, b, c in strands:
        poly(g, [a, b, c], "H")
    poly(g, [(12, 18), (15.5, 18), (16, 30), (14, 33), (12.5, 29)], "H")    # side lock in front of the left ear
    poly(g, [(40.5, 18), (44, 18), (43.5, 29), (42, 33), (40, 30)], "H")
    # light on the crown, and a few strand lines
    poly(g, [(16, 10), (21, 6.5), (29, 6), (23, 8.5), (18.5, 12)], "I")
    poly(g, [(19.5, 8.5), (24, 7), (21, 9.5)], "J")
    poly(g, [(33, 6.5), (38, 8.5), (40.5, 12.5), (36.5, 9.5)], "I")
    poly(g, [(28, 1), (30, 0.3), (29, 2)], "I")
    for (x0, y0), (x1, y1) in (((21, 9), (19, 17)), ((27, 8), (26, 16)), ((33, 9), (34, 17))):
        n = max(abs(x1 - x0), abs(y1 - y0))
        for k in range(n + 1):
            g[round(y0 + (y1 - y0) * k / n)][round(x0 + (x1 - x0) * k / n)] = "h"
    # where hair meets skin, the hair darkens so each strand reads
    src = [r[:] for r in g]
    for y in range(H):
        for x in range(W):
            if src[y][x] in HAIR and any(0 <= y + dy < H and 0 <= x + dx < W and src[y + dy][x + dx] in SKIN for dx, dy in ((0, 1), (1, 0), (-1, 0))):
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
        stamp(g, 39, 17, ["..K..", ".KlK.", "KllLK", "KlLLK", ".KKK."])
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
