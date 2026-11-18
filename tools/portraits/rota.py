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
    "e": (28, 44, 112),     # iris dark (top and pupil)
    "E": (58, 104, 200),    # iris
    "F": (130, 186, 240),   # iris light (bottom)
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
    # left eye, outer corner on the left; "." keeps whatever is underneath.
    # After the drawing: a long upper lid, a tall iris with a small pupil, a short lower lid, no ring around the eye.
    # the eye after channel's MVs: a thick upper lid that runs past the eye and ends in a little flick,
    # an iris that fills the eye with its top tucked under the lid, a light spot low in the iris,
    # white only at the sides, and a short lower line at the outer corner
    "base": [
        "KK.KKKKKKK.",
        ".KKKKKKKKKK",
        "..WeeeeeeW.",
        "..WEEeeEEW.",
        "K.WEEFFEEW.",
        ".K.WEEEEW..",
        "...........",
    ],
    "smile": [
        "...........",
        "...........",
        "...KKKKKK..",
        "..K......K.",
        ".K........K",
        "...........",
        "...........",
    ],
    "fear": [
        ".KKKKKKKKK.",
        ".KWWWWWWWW.",
        "..WWWWWWWW.",
        "..WWWeEWWW.",
        "..WWWEEWWW.",
        "..WWWWWWW..",
        "...KKKKKK..",
    ],
}
BROWS = {"base": [], "smile": [], "fear": [(1, -2, "KK"), (3, -1, "KK")]}
MOUTHS = {
    "base": ["KKKK", "KnnK", ".KK."],
    "smile": ["KKKKKKK", "KnnnnnK", ".KnnnK.", "..KKK.."],
    "fear": [".KK.", "KnnK", ".KK."],
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
    poly(g, [(9.5, 24), (10.5, 13), (14, 7), (20, 3.5), (28, 2), (36, 3.5), (42, 7), (45.5, 13), (46.5, 24), (46, 35), (42, 38), (14, 38), (10, 35)], "H")
    # ears
    for x0, d in ((13, 1), (43, -1)):
        poly(g, [(x0, 24), (x0 + 3 * d, 23.5), (x0 + 3.5 * d, 31), (x0 + 1.5 * d, 31.5)] if d > 0 else
             [(x0 - 3.5, 23.5), (x0, 24), (x0 - 1.5, 31.5), (x0 - 3.5, 31)], "S")
    g[27][14] = "T"; g[28][14] = "T"; g[27][41] = "T"; g[28][41] = "T"
    # ---------- face: narrow chin ----------
    poly(g, [(12.5, 17), (43.5, 17), (43.5, 29), (41, 35), (35, 39.5), (28, 41), (21, 39.5), (15, 35), (12.5, 29)], "S")
    poly(g, [(12.5, 17), (43.5, 17), (43.5, 20.5), (12.5, 20.5)], "T")     # shade under the fringe
    poly(g, [(12.5, 28), (14, 28), (16, 34.5), (15, 34.5)], "T")
    poly(g, [(23.5, 39), (28, 40.5), (32.5, 39), (32.5, 40), (28, 41.5), (23.5, 40)], "T")
    for x, y in ((16, 34), (17, 34), (18, 34), (38, 34), (39, 34), (40, 34)):
        g[y][x] = "b"
    # ---------- fringe: spiky strands, one long lock falling between the eyes ----------
    poly(g, [(11, 18), (13.5, 11), (20, 6), (36, 6), (42.5, 11), (45, 18), (45, 20), (11, 20)], "H")
    strands = [((11, 19), (14, 12), (14.5, 24)), ((13.5, 19), (17, 12), (17.5, 25)), ((16.5, 19), (19.5, 12), (20.5, 24)),
               ((26, 18), (29, 10), (28.5, 25)), ((28.5, 18), (32, 10), (32, 26)), ((31.5, 18), (35, 10), (35.5, 25.5)),
               ((34.5, 18), (38, 11), (38.5, 25)), ((37.5, 19), (41, 12), (41.5, 24)), ((40.5, 19), (44, 12), (44, 23))]
    for a, b, c in strands:
        poly(g, [a, b, c], "H")
    poly(g, [(20, 20.5), (23.5, 11), (26.5, 20.5)], "S")                   # the part: forehead showing through
    poly(g, [(21, 20.5), (23.5, 14), (26, 20.5)], "S")
    poly(g, [(9.5, 18), (13.5, 18), (14, 33), (12.5, 38), (10, 34)], "H")    # side locks to the jaw, outside the cheeks
    poly(g, [(42.5, 18), (46.5, 18), (46, 34), (43.5, 38), (42, 33)], "H")
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
    ey = 25
    stamp(g, 14, ey, EYES[face])
    stamp(g, 31, ey, mirror(EYES[face]))
    for x_in, dy, row in BROWS[face]:
        y = ey - 2 + dy
        for k, ch in enumerate(row):
            for xx in (23 - x_in - k, 33 + x_in + k):
                if g[y][xx] in SKIN:
                    g[y][xx] = ch
    m = MOUTHS[face]
    stamp(g, 28 - len(m[0]) // 2, 35, m)
    if face == "fear":                                                   # a bead of sweat
        stamp(g, 41, 19, ["..K..", ".KWK.", "KWWFK", "KWFFK", ".KKK."])
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
