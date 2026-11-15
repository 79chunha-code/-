"""화원태왕타운 텍스처 생성기 v2 (PIL + numpy).

모든 텍스처는 코드로 그린다. 실제 사진은 쓰지 않는다.
건물/바닥 텍스처는 세 장이 한 묶음이다.
  <이름>.png      색 (albedo)
  <이름>_orm.png  G = 거칠기 (glTF metallicRoughness 규칙)
  <이름>_n.png    노멀맵 (높이맵에서 계산)

실행: python3 textures.py <출력 폴더>
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "textures"
os.makedirs(OUT, exist_ok=True)
rng = random.Random(2026)
nrng = np.random.default_rng(2026)

# ------------------------------------------------------------------ 색
WHITE = (228, 230, 232)
LGRAY = (192, 196, 202)
MGRAY = (146, 151, 160)
DGRAY = (96, 101, 112)
NAVY = (30, 42, 88)
NAVY_D = (22, 31, 68)
FRAME_W = (236, 238, 238)
FRAME_D = (74, 78, 84)
CURTAINS = [(214, 210, 198), (232, 228, 220), (196, 204, 208), (206, 196, 176), (180, 186, 190)]

FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# ------------------------------------------------------------------ 노이즈
def tile_noise(size, cells, seed):
    """이어 붙여도 경계가 안 보이는 값 노이즈 (0..1)."""
    g = np.random.default_rng(seed).random((cells, cells)).astype(np.float32)
    g = np.pad(g, 2, mode="wrap")
    im = Image.fromarray((g * 255).astype(np.uint8)).resize(
        (size * (cells + 4) // cells, size * (cells + 4) // cells), Image.BICUBIC)
    off = size * 2 // cells
    a = np.asarray(im, dtype=np.float32)[off:off + size, off:off + size] / 255.0
    return a


def fbm(size, base=4, octaves=4, seed=0):
    a = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        a += tile_noise(size, base * (2 ** o), seed + o * 17) * amp
        tot += amp
        amp *= 0.5
    a /= tot
    return (a - a.min()) / (a.max() - a.min() + 1e-6)


def normal_from_height(h, strength=2.0):
    """h: 0..1 float 배열 -> RGB 노멀맵 이미지."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    ln = np.sqrt(dx * dx + dy * dy + nz * nz)
    n = np.stack([-dx / ln, dy / ln, nz / ln], -1)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB")


def save_set(name, albedo, rough, height=None, nstrength=2.0):
    albedo.save(os.path.join(OUT, name + ".png"))
    r = np.asarray(rough.convert("L"))
    orm = np.zeros((*r.shape, 3), np.uint8)
    orm[..., 0] = 255
    orm[..., 1] = r
    Image.fromarray(orm, "RGB").save(os.path.join(OUT, name + "_orm.png"))
    if height is not None:
        h = np.asarray(height.convert("L").filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255.0
        normal_from_height(h, nstrength).save(os.path.join(OUT, name + "_n.png"))


def weather(albedo, seed, amount=0.10, streak=0.07):
    """얼룩과 빗물 자국. 가로세로로 이어 붙여도 티가 안 난다."""
    w, h = albedo.size
    s = 512
    blot = fbm(s, 3, 4, seed)
    st = tile_noise(s, 64, seed + 5)
    st = np.repeat(st[:1, :], s, axis=0) * 0.6 + np.repeat(tile_noise(s, 128, seed + 9)[:1, :], s, axis=0) * 0.4
    m = 1.0 - amount * blot - streak * np.clip(st - 0.55, 0, 1) * 2.2
    m_img = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    a = np.asarray(albedo, dtype=np.float32) * (np.asarray(m_img, dtype=np.float32)[..., None] / 255.0)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------ 그리기 도구
class Painter:
    """미터 단위로 그린다. 원점은 왼쪽 아래, y는 위. 색/거칠기/높이를 함께 칠한다."""

    def __init__(self, w_m, h_m, w_px, h_px, color, rough=0.85, height=0.5):
        self.w_m, self.h_m = w_m, h_m
        self.a = Image.new("RGB", (w_px, h_px), color)
        self.r = Image.new("L", (w_px, h_px), int(rough * 255))
        self.h = Image.new("L", (w_px, h_px), int(height * 255))
        self.da, self.dr, self.dh = ImageDraw.Draw(self.a), ImageDraw.Draw(self.r), ImageDraw.Draw(self.h)
        self.sx, self.sy = w_px / w_m, h_px / h_m
        self.ox = self.oy = 0.0

    def box(self, x0, y0, x1, y1):
        H = self.a.height
        x0, x1 = x0 + self.ox, x1 + self.ox
        y0, y1 = y0 + self.oy, y1 + self.oy
        return [round(x0 * self.sx), round(H - y1 * self.sy),
                max(round(x0 * self.sx), round(x1 * self.sx) - 1), max(round(H - y1 * self.sy), round(H - y0 * self.sy) - 1)]

    def rect(self, x0, y0, x1, y1, c=None, r=None, h=None):
        b = self.box(x0, y0, x1, y1)
        if c is not None:
            self.da.rectangle(b, fill=c)
        if r is not None:
            self.dr.rectangle(b, fill=int(r * 255))
        if h is not None:
            self.dh.rectangle(b, fill=int(h * 255))

    def hline(self, x0, x1, y, c, t=0.03, **k):
        self.rect(x0, y - t / 2, x1, y + t / 2, c, **k)

    def vline(self, x, y0, y1, c, t=0.04, **k):
        self.rect(x - t / 2, y0, x + t / 2, y1, c, **k)

    def glass(self, x0, y0, x1, y1, style=None):
        """유리창 한 칸. style: None(무작위) / 'dark' / 'curtain' / 'blind' / 'sky'"""
        style = style or rng.choices(["dark", "curtain", "blind", "sky", "half"], [3, 3, 2, 3, 2])[0]
        b = self.box(x0, y0, x1, y1)
        hh = max(1, b[3] - b[1])
        top = (58, 74, 88) if style != "sky" else (120, 150, 176)
        bot = (86, 104, 112) if style != "sky" else (150, 176, 190)
        for i in range(hh + 1):
            t = i / hh
            c = tuple(int(top[k] * (1 - t) + bot[k] * t) for k in range(3))
            self.da.line([(b[0], b[1] + i), (b[2], b[1] + i)], fill=c)
        self.dr.rectangle(b, fill=int(0.08 * 255))
        self.dh.rectangle(b, fill=int(0.30 * 255))
        if style in ("curtain", "half"):
            cc = rng.choice(CURTAINS)
            frac = rng.uniform(0.3, 0.55) if style == "half" else rng.uniform(0.7, 1.0)
            if rng.random() < 0.5:
                self.rect(x0, y0, x0 + (x1 - x0) * frac, y1, cc, r=0.25)
            else:
                self.rect(x1 - (x1 - x0) * frac, y0, x1, y1, cc, r=0.25)
        elif style == "blind":
            cc = rng.choice([(206, 208, 206), (188, 184, 172), (160, 170, 176)])
            drop = rng.uniform(0.4, 1.0)
            yb = y1 - (y1 - y0) * drop
            self.rect(x0, yb, x1, y1, cc, r=0.3)
            n = int((y1 - yb) / 0.06)
            for i in range(n):
                self.hline(x0, x1, yb + i * 0.06, tuple(int(v * 0.86) for v in cc), 0.012)

    def window(self, x0, y0, x1, y1, panes=2, frame=FRAME_W, ft=0.07, style=None, sill=True):
        self.rect(x0 - ft, y0 - ft, x1 + ft, y1 + ft, frame, r=0.45, h=0.58)
        pw = (x1 - x0) / panes
        for i in range(panes):
            self.glass(x0 + i * pw + 0.02, y0 + 0.02, x0 + (i + 1) * pw - 0.02, y1 - 0.02, style)
        for i in range(1, panes):
            self.vline(x0 + i * pw, y0, y1, frame, 0.06, r=0.45, h=0.58)
        if sill:
            self.rect(x0 - ft - 0.04, y0 - ft - 0.05, x1 + ft + 0.04, y0 - ft, tuple(int(v * 0.9) for v in frame), h=0.66)
            # 창틀 아래 물자국
            self.rect(x0 - ft, y0 - ft - 0.5, x0 - ft + 0.04, y0 - ft - 0.05, None)

    def ac_unit(self, x, y):
        self.rect(x, y, x + 0.8, y + 0.55, (214, 216, 214), r=0.5, h=0.8)
        self.rect(x + 0.04, y + 0.04, x + 0.52, y + 0.51, (168, 172, 172), h=0.74)
        b = self.box(x + 0.08, y + 0.08, x + 0.48, y + 0.47)
        self.da.ellipse(b, fill=(92, 96, 98))
        self.rect(x - 0.03, y - 0.05, x + 0.83, y, (150, 152, 152), h=0.7)

    def finish(self, name, seed=1, wamount=0.10, wstreak=0.07, nstrength=2.2):
        save_set(name, weather(self.a, seed, wamount, wstreak), self.r, self.h, nstrength)


CELL_H = 2.7
NV, NR = 4, 4   # 변형 4칸 x 4층


def grid_painter(cell_w, w_px, h_px, color):
    return Painter(cell_w * NV, CELL_H * NR, w_px, h_px, color)


def each_cell(p, cell_w):
    for j in range(NR):
        for i in range(NV):
            p.ox, p.oy = i * cell_w, j * CELL_H
            yield i, j
    p.ox = p.oy = 0.0


# ------------------------------------------------------------------ 아파트 외벽
FRONT_W = 3.7


def front_flat(name, wall, band, pil, seed, slab=None):
    """발코니 면의 평평한 칸 (샷시로 막은 발코니)."""
    p = grid_painter(FRONT_W, 2048, 1024, wall)
    for i, j in each_cell(p, FRONT_W):
        p.rect(0.3, 0.0, FRONT_W, 0.98, band, h=0.56)                      # 난간벽
        p.hline(0.3, FRONT_W, 0.5, tuple(int(v * 0.93) for v in band), 0.015)
        fr = FRAME_W if rng.random() < 0.8 else FRAME_D
        p.window(0.48, 1.06, FRONT_W - 0.18, 2.30, panes=4, frame=fr, sill=False)
        p.rect(0.0, 0.0, 0.3, CELL_H, pil, h=0.62)                          # 세대 경계 기둥
        p.rect(0.0, 2.42, FRONT_W, CELL_H, slab or band, h=0.64)            # 슬래브 띠
        p.hline(0.0, FRONT_W, 2.41, (70, 74, 80), 0.035, h=0.4)
        if rng.random() < 0.3:
            p.ac_unit(rng.uniform(0.5, 2.6), 0.14)
    p.finish(name, seed)


BAY_W = 3.7


def bay(name, band, seed):
    """둥글게 튀어나온 발코니. 둘레를 펼친 그림."""
    p = grid_painter(BAY_W, 2048, 1024, band)
    for i, j in each_cell(p, BAY_W):
        for k in range(1, 4):
            p.hline(0, BAY_W, 0.22 * k, tuple(int(v * 0.94) for v in band), 0.012)
        st = rng.choices(["dark", "curtain", "sky", "half", "blind"], [3, 2, 3, 2, 1])[0]
        fr = FRAME_W if rng.random() < 0.75 else FRAME_D
        p.rect(0.0, 0.94, BAY_W, 2.40, fr, r=0.45, h=0.56)
        n = 5
        pw = BAY_W / n
        for k in range(n):
            p.glass(k * pw + 0.035, 1.0, (k + 1) * pw - 0.035, 2.34, st if rng.random() < 0.7 else None)
        # 난간
        for yy in (1.12, 1.26, 1.40):
            p.hline(0, BAY_W, yy, (58, 62, 70), 0.022, r=0.4, h=0.7)
        p.rect(0.0, 2.42, BAY_W, CELL_H, band, h=0.66)
        p.hline(0.0, BAY_W, 2.41, (70, 74, 80), 0.035, h=0.4)
    p.finish(name, seed)


BACK_W = 6.5


def back(name, wall, stripe, seed, grill=False):
    """복도/계단 쪽 면."""
    p = grid_painter(BACK_W, 2048, 1024, wall)
    for i, j in each_cell(p, BACK_W):
        for (a, b) in ((0.55, 2.55), (4.05, 6.0)):
            p.rect(a, 0, b, CELL_H, stripe)
        p.window(0.8, 0.95, 2.3, 2.15, panes=2)
        p.window(3.0, 1.55, 3.6, 2.15, panes=1, style=rng.choice(["dark", "curtain"]))
        p.window(4.3, 1.05, 5.75, 2.15, panes=2)
        p.hline(0, BACK_W, 2.69, tuple(int(v * 0.86) for v in wall), 0.03, h=0.42)
        if rng.random() < 0.35:
            p.ac_unit(rng.choice([2.62, 3.15]), 0.25)
        if grill and j == 0:
            for (a, b, y0, y1) in ((0.8, 2.3, 0.95, 2.15), (4.3, 5.75, 1.05, 2.15)):
                n = int((b - a) / 0.13)
                for k in range(1, n):
                    p.vline(a + (b - a) * k / n, y0, y1, (230, 232, 232), 0.025, h=0.7)
    p.finish(name, seed)


CORE_W = 3.2


def core(name, wall, seed):
    p = Painter(CORE_W, CELL_H * NR, 256, 1024, wall)
    for j in range(NR):
        p.oy = j * CELL_H
        p.window(0.95, 1.15, 2.25, 2.25, panes=2, style=rng.choice(["dark", "sky", "dark"]))
        p.hline(0, CORE_W, 2.69, tuple(int(v * 0.84) for v in wall), 0.03, h=0.42)
        p.vline(0.06, 0, CELL_H, tuple(int(v * 0.9) for v in wall), 0.05)
        p.vline(CORE_W - 0.06, 0, CELL_H, tuple(int(v * 0.9) for v in wall), 0.05)
    p.oy = 0
    p.finish(name, seed)


def core_door(name, wall, seed):
    p = Painter(CORE_W, CELL_H, 512, 512, wall)
    p.rect(0.45, 0.0, 2.75, 2.3, (60, 64, 70), r=0.4, h=0.6)
    p.glass(0.55, 0.05, 1.56, 2.2, "dark")
    p.glass(1.64, 0.05, 2.65, 2.2, "sky")
    p.vline(1.6, 0, 2.25, (60, 64, 70), 0.08, h=0.62)
    p.rect(1.42, 1.0, 1.52, 1.25, (190, 192, 190), r=0.3, h=0.7)
    p.rect(1.68, 1.0, 1.78, 1.25, (190, 192, 190), r=0.3, h=0.7)
    p.rect(2.82, 1.15, 3.02, 1.5, (40, 44, 48), r=0.3, h=0.66)      # 인터폰
    p.rect(2.85, 1.3, 2.99, 1.46, (120, 160, 200), r=0.1)
    p.finish(name, seed)


SIDE_W = 12.0


def side(name, wall, stripe, seed):
    p = Painter(SIDE_W, CELL_H * NR, 1024, 1024, wall)
    if stripe:
        for a in (4.25, 7.15):
            p.rect(a, 0, a + 0.6, CELL_H * NR, stripe)
    y = 0.0
    while y < CELL_H * NR:
        p.hline(0, SIDE_W, y, tuple(int(v * 0.88) for v in wall), 0.022, h=0.4)
        y += 0.45
    p.finish(name, seed, wamount=0.12, wstreak=0.10)


def parapet(name, wall, cap):
    p = Painter(8.0, 1.1, 512, 64, wall)
    p.rect(0, 0.95, 8, 1.1, cap, h=0.7)
    p.hline(0, 8, 0.02, tuple(int(v * 0.8) for v in wall), 0.04)
    p.finish(name, 31)


# ------------------------------------------------------------------ 바닥/재료
def from_arrays(name, rgb, rough, height=None, nstrength=2.0):
    a = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    r = Image.fromarray(np.clip(rough * 255, 0, 255).astype(np.uint8), "L")
    h = Image.fromarray(np.clip(height * 255, 0, 255).astype(np.uint8), "L") if height is not None else None
    save_set(name, a, r, h, nstrength)


def asphalt():
    s = 1024
    n1, n2 = fbm(s, 4, 5, 3), fbm(s, 64, 3, 9)
    grain = nrng.random((s, s)).astype(np.float32)
    v = 96 + (n1 - 0.5) * 34 + (n2 - 0.5) * 20 + (grain - 0.5) * 24
    rgb = np.stack([v, v + 1, v + 4], -1)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    for _ in range(14):                       # 갈라진 금
        x, y = rng.randrange(s), rng.randrange(s)
        pts = [(x, y)]
        ang = rng.uniform(0, 6.28)
        for _ in range(rng.randint(6, 16)):
            ang += rng.uniform(-0.6, 0.6)
            x += math.cos(ang) * rng.uniform(12, 30)
            y += math.sin(ang) * rng.uniform(12, 30)
            pts.append((x, y))
        d.line(pts, fill=(54, 55, 58), width=rng.choice([1, 1, 2]))
    for _ in range(5):                        # 덧씌운 자국
        x, y = rng.randrange(s - 200), rng.randrange(s - 200)
        w, h = rng.randint(60, 180), rng.randint(40, 120)
        patch = Image.new("RGB", (w, h), (66, 67, 71))
        im.paste(Image.blend(im.crop((x, y, x + w, y + h)), patch, 0.45), (x, y))
    rough = 0.82 + (n2 - 0.5) * 0.2
    from_arrays("asphalt", np.asarray(im, dtype=np.float32), rough, grain * 0.5 + n2 * 0.5, 1.2)


def noise_mat(name, base, var, seed, rough=0.9, cells=6, grain_amt=14, nstrength=1.0):
    s = 512
    n = fbm(s, cells, 5, seed)
    g = nrng.random((s, s)).astype(np.float32)
    rgb = np.stack([base[k] + (n - 0.5) * var + (g - 0.5) * grain_amt for k in range(3)], -1)
    from_arrays(name, rgb, np.full((s, s), rough, np.float32) + (n - 0.5) * 0.1, g * 0.4 + n * 0.6, nstrength)


def grass():
    s = 512
    n, n2 = fbm(s, 5, 5, 21), fbm(s, 48, 3, 22)
    g = nrng.random((s, s)).astype(np.float32)
    r = 70 + (n - 0.5) * 40 + (n2 - 0.5) * 30 + (g - 0.5) * 30
    gr = 112 + (n - 0.5) * 44 + (n2 - 0.5) * 36 + (g - 0.5) * 36
    b = 48 + (n - 0.5) * 24 + (g - 0.5) * 20
    from_arrays("grass", np.stack([r, gr, b], -1), np.full((s, s), 0.95, np.float32), n2 * 0.6 + g * 0.4, 1.5)


def hedge():
    s = 512
    n, n2 = fbm(s, 24, 4, 41), fbm(s, 6, 3, 42)
    g = nrng.random((s, s)).astype(np.float32)
    k = n * 0.7 + g * 0.3
    r = 34 + k * 52 + (n2 - 0.5) * 16
    gr = 62 + k * 78 + (n2 - 0.5) * 20
    b = 26 + k * 34
    from_arrays("hedge", np.stack([r, gr, b], -1), np.full((s, s), 0.9, np.float32), k, 3.0)


def bricks(name, colors, mortar, bw=0.21, bh=0.07, w_m=1.26, h_m=1.26, s=512, lattice=False, seed=1):
    """벽돌 쌓기. lattice=True면 가운데 줄에 구멍(투시형 담장)을 뚫는다."""
    p = Painter(w_m, h_m, s, s, mortar, rough=0.95, height=0.3)
    rows = int(round(h_m / bh))
    cols = int(round(w_m / bw))
    r2 = random.Random(seed)
    for j in range(rows):
        off = (bw / 2) if j % 2 else 0.0
        for i in range(-1, cols + 1):
            x0 = i * bw + off
            c = r2.choice(colors)
            c = tuple(max(0, min(255, v + r2.randint(-8, 8))) for v in c)
            hole = lattice and 4 <= j <= rows - 5 and (i + j) % 2 == 0
            if hole:
                p.rect(x0 + 0.01, j * bh + 0.006, x0 + bw - 0.01, (j + 1) * bh - 0.006, (26, 22, 22), r=1.0, h=0.0)
            else:
                p.rect(x0 + 0.006, j * bh + 0.006, x0 + bw - 0.006, (j + 1) * bh - 0.006, c, r=0.85, h=0.7)
    p.finish(name, seed + 50, wamount=0.14, wstreak=0.05, nstrength=3.0)


def pavers(name, colors, mortar, seed):
    s = 512
    p = Painter(1.6, 1.6, s, s, mortar, rough=0.9, height=0.35)
    r2 = random.Random(seed)
    u = 0.2
    for j in range(8):
        for i in range(-1, 5):
            x0 = i * 0.4 + (0.2 if j % 2 else 0)
            c = r2.choice(colors)
            c = tuple(max(0, min(255, v + r2.randint(-10, 10))) for v in c)
            p.rect(x0 + 0.006, j * u + 0.006, x0 + 0.4 - 0.006, (j + 1) * u - 0.006, c, h=0.65)
    p.finish(name, seed + 60, wamount=0.16, wstreak=0.0, nstrength=2.0)


def rocks(name, seed):
    """강돌을 박은 돌기둥."""
    s = 512
    a = Image.new("RGB", (s, s), (118, 112, 104))
    h = Image.new("L", (s, s), 60)
    da, dh = ImageDraw.Draw(a), ImageDraw.Draw(h)
    r2 = random.Random(seed)
    pal = [(170, 164, 150), (146, 138, 124), (190, 182, 166), (128, 118, 108), (160, 140, 118), (176, 170, 164)]
    placed = []
    for _ in range(900):
        rx, ry = r2.uniform(16, 34), r2.uniform(13, 26)
        x, y = r2.uniform(0, s), r2.uniform(0, s)
        if any((x - px) ** 2 + (y - py) ** 2 < (max(rx, ry) + pr) ** 2 * 0.72 for px, py, pr in placed):
            continue
        placed.append((x, y, max(rx, ry)))
        c = r2.choice(pal)
        c = tuple(max(0, min(255, v + r2.randint(-10, 10))) for v in c)
        for ox in (-s, 0, s):
            for oy in (-s, 0, s):
                bb = [x - rx + ox, y - ry + oy, x + rx + ox, y + ry + oy]
                da.ellipse(bb, fill=c)
                dh.ellipse(bb, fill=200)
                dh.ellipse([bb[0] + rx * 0.3, bb[1] + ry * 0.3, bb[2] - rx * 0.3, bb[3] - ry * 0.3], fill=250)
    a = weather(a, seed, 0.12, 0.0)
    save_set(name, a, Image.new("L", (s, s), 220), h.filter(ImageFilter.GaussianBlur(2.5)), 3.5)


def stone_blocks(name, seed):
    p = Painter(1.2, 0.8, 512, 512, (96, 94, 90), rough=0.9, height=0.3)
    r2 = random.Random(seed)
    for j in range(4):
        x = -r2.uniform(0, 0.3)
        while x < 1.2:
            w = r2.uniform(0.25, 0.45)
            v = r2.randint(132, 176)
            p.rect(x + 0.008, j * 0.2 + 0.008, x + w - 0.008, (j + 1) * 0.2 - 0.008, (v, v - 3, v - 10), h=r2.uniform(0.6, 0.8))
            x += w
    p.finish(name, seed, wamount=0.2, wstreak=0.05, nstrength=3.0)


def roof_tiles(name, base, dark, seed):
    """기와 지붕 (세로 골 + 가로 겹침)."""
    s = 256
    xs = np.arange(s)
    ridge = (np.sin(xs / s * 2 * math.pi * 8) * 0.5 + 0.5)
    rows = ((np.arange(s) / s * 6) % 1.0)
    hgt = ridge[None, :] * 0.7 + (1 - rows)[:, None] * 0.3
    n = fbm(s, 6, 3, seed)
    rgb = np.stack([dark[k] + (base[k] - dark[k]) * hgt + (n - 0.5) * 16 for k in range(3)], -1)
    from_arrays(name, rgb, np.full((s, s), 0.35, np.float32), hgt, 3.0)


def metal_roof(name, base, seed):
    s = 256
    xs = np.arange(s)
    ridge = (np.sin(xs / s * 2 * math.pi * 16) * 0.5 + 0.5)
    n = fbm(s, 4, 4, seed)
    hgt = np.repeat(ridge[None, :], s, 0)
    rgb = np.stack([base[k] * (0.8 + 0.25 * hgt) + (n - 0.5) * 30 for k in range(3)], -1)
    from_arrays(name, rgb, 0.45 + n * 0.2, hgt, 2.0)


def roof_green():
    s = 512
    n, n2 = fbm(s, 4, 5, 71), fbm(s, 24, 3, 72)
    r = 72 + (n - 0.5) * 30 + (n2 - 0.5) * 10
    g = 138 + (n - 0.5) * 36 + (n2 - 0.5) * 14
    b = 112 + (n - 0.5) * 30
    im = Image.fromarray(np.clip(np.stack([r, g, b], -1), 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    for i in range(0, s, 128):
        d.line([(i, 0), (i, s)], fill=(60, 116, 96), width=2)
        d.line([(0, i), (s, i)], fill=(60, 116, 96), width=2)
    save_set("roof_green", im, Image.new("L", (s, s), 150))


def speed_bump():
    p = Painter(3.6, 0.9, 512, 128, (238, 196, 44), rough=0.7)
    for i in range(0, 8, 2):
        p.rect(i * 0.45, 0, (i + 1) * 0.45, 0.9, (236, 236, 230))
    p.finish("speedbump", 91, wamount=0.25, wstreak=0.0, nstrength=0.5)


def booth_wall():
    """경비실 벽 한 면 (창문)과 문 면."""
    p = Painter(6.0, 2.4, 1024, 512, (232, 232, 226))
    p.rect(0, 0, 6.0, 0.75, (150, 84, 64), h=0.6)           # 벽돌 하단
    for j in range(10):
        p.hline(0, 6.0, j * 0.075, (190, 176, 164), 0.012)
    # 창문 면 (0..3)
    p.window(0.35, 0.95, 2.65, 2.0, panes=3, frame=(70, 90, 150), style="dark")
    # 문 면 (3..6)
    p.rect(3.4, 0.0, 4.4, 2.05, (70, 90, 150), h=0.6)
    p.glass(3.5, 0.9, 4.3, 1.95, "dark")
    p.window(4.75, 0.95, 5.7, 2.0, panes=1, frame=(70, 90, 150), style="curtain")
    p.rect(0, 2.25, 6.0, 2.4, (70, 90, 150), h=0.62)
    p.finish("booth", 12)


def text_img(text, size, fg, bg, pad=18, fsize=None):
    f = font(fsize or int(size[1] * 0.62))
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if tw > size[0] - pad * 2:
        f = font(int((fsize or int(size[1] * 0.62)) * (size[0] - pad * 2) / tw))
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size[0] - tw) / 2 - bb[0], (size[1] - th) / 2 - bb[1]), text, font=f, fill=fg)
    return im


SIGN_WORDS = ["태권도", "미용실", "수학학원", "피아노", "세탁", "부동산", "헬스 PT", "치킨", "약국", "분식",
              "종합장식", "철물", "꽃집", "카페", "마트", "반찬", "문구", "안경", "떡집", "정육점", "영어교습소", "인테리어"]
SIGN_COLS = [((250, 214, 40), (30, 30, 30)), ((36, 70, 170), (255, 255, 255)), ((210, 40, 46), (255, 255, 255)),
             ((250, 250, 250), (30, 60, 150)), ((30, 120, 70), (255, 255, 255)), ((30, 30, 34), (250, 220, 60)),
             ((240, 120, 30), (255, 255, 255)), ((120, 60, 150), (255, 255, 255))]


def shop_tiles():
    """상가 1층(가게 앞)과 위층. 가로 24m = 가게 4칸."""
    r2 = random.Random(77)
    words = SIGN_WORDS[:]
    r2.shuffle(words)
    wi = 0
    for name, upper in (("shop_gf", False), ("shop_up", True)):
        p = Painter(24.0, 3.6, 2048, 512, (200, 194, 184))
        for i in range(4):
            u = i * 6.0
            if not upper:
                p.rect(u + 0.25, 0.0, u + 5.75, 2.55, (58, 62, 66), h=0.55)
                p.glass(u + 0.4, 0.08, u + 2.1, 2.45, rng.choice(["dark", "sky"]))
                p.glass(u + 2.25, 0.08, u + 3.95, 2.45, rng.choice(["dark", "curtain"]))
                p.glass(u + 4.15, 0.08, u + 5.6, 2.45, "dark")
                # 유리에 붙은 시트지
                for k in range(3):
                    cc = r2.choice([(240, 240, 240), (250, 220, 60), (220, 50, 50), (40, 90, 200)])
                    x0 = u + r2.uniform(0.5, 4.8)
                    p.rect(x0, r2.uniform(0.3, 1.4), x0 + r2.uniform(0.4, 1.0), r2.uniform(1.6, 2.3), cc, r=0.3)
                if r2.random() < 0.6:         # 차양
                    ac = r2.choice([(36, 70, 150), (180, 40, 40), (40, 110, 70), (230, 230, 230)])
                    p.rect(u + 0.2, 2.45, u + 5.8, 2.75, ac, h=0.75)
                    for k in range(14):
                        if k % 2:
                            p.rect(u + 0.2 + k * 0.4, 2.45, u + 0.6 + k * 0.4, 2.75, (240, 240, 236), h=0.75)
            else:
                p.window(u + 0.6, 1.0, u + 2.6, 2.4, panes=2)
                p.window(u + 3.4, 1.0, u + 5.4, 2.4, panes=2)
            bg, fg = r2.choice(SIGN_COLS)
            y0, y1 = (2.8, 3.5) if not upper else (2.65, 3.3)
            word = words[wi % len(words)]
            wi += 1
            sw = int(5.5 * p.sx)
            sh = int((y1 - y0) * p.sy)
            sim = text_img(word, (sw, sh), fg, bg)
            b = p.box(u + 0.25, y0, u + 5.75, y1)
            p.a.paste(sim.resize((b[2] - b[0] + 1, b[3] - b[1] + 1)), (b[0], b[1]))
            p.rect(u + 0.25, y0, u + 5.75, y1, None, r=0.35, h=0.72)
            if upper and r2.random() < 0.7:   # 세로 돌출 간판
                bg2, fg2 = r2.choice(SIGN_COLS)
                p.rect(u + 2.85, 0.6, u + 3.15, 2.5, bg2, r=0.35, h=0.8)
        p.finish(name, 80 + int(upper), wamount=0.12, wstreak=0.08)


def warehouse_wall():
    p = Painter(12.0, 6.0, 1024, 512, (206, 204, 196))
    p.rect(0, 0, 12, 0.9, (150, 148, 142))
    p.rect(4.2, 0.0, 7.4, 3.2, (150, 156, 160), r=0.5, h=0.4)        # 셔터
    for k in range(20):
        p.hline(4.2, 7.4, k * 0.16, (120, 126, 130), 0.02)
    p.rect(9.2, 0.0, 10.1, 2.0, (110, 70, 60), h=0.42)                # 쪽문
    p.window(1.0, 3.6, 2.4, 4.6, panes=2, frame=(120, 120, 116), style="dark")
    p.finish("warehouse", 55, wamount=0.30, wstreak=0.30)


def tower_wall():
    """멀리 보이는 고층 아파트 (4층 x 12m 한 칸)."""
    p = Painter(12.0, 11.2, 512, 512, (232, 232, 230))
    for j in range(4):
        y = j * 2.8
        p.rect(0, y + 2.5, 12, y + 2.8, (212, 214, 216))
        for (a, b) in ((0.6, 3.4), (4.0, 5.6), (6.4, 8.0), (8.6, 11.4)):
            p.rect(a, y + 0.9, b, y + 2.3, (240, 242, 242))
            p.glass(a + 0.06, y + 0.96, b - 0.06, y + 2.24, rng.choice(["dark", "sky", "sky"]))
    p.rect(5.7, 0, 6.3, 11.2, (120, 126, 136))
    p.finish("tower", 66, wamount=0.05, wstreak=0.03)


# ------------------------------------------------------------------ 잎 (투명)
def foliage(name, kind, seed):
    """나뭇잎 뭉치 한 장 (RGBA). kind: pine / leaf / meta"""
    s = 512
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r2 = random.Random(seed)
    cx = cy = s / 2
    for _ in range(46):                         # 안쪽 그늘 (잎이 빽빽해 보이게)
        ang = r2.uniform(0, 6.28)
        rad = (r2.random() ** 0.7) * s * 0.34
        x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * 0.85
        rr = r2.uniform(34, 70)
        dc = (20, 44, 28) if kind == "pine" else ((30, 62, 26) if kind == "leaf" else (44, 80, 34))
        d.ellipse([x - rr, y - rr * 0.8, x + rr, y + rr * 0.8], fill=(*dc, 255))
    if kind == "pine":
        for _ in range(420):                    # 솔잎 다발
            ang = r2.uniform(0, 6.28)
            rad = (r2.random() ** 0.6) * s * 0.44
            x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * 0.8
            g = r2.randint(52, 104)
            base = (r2.randint(22, 44), g, r2.randint(30, 52))
            for _ in range(16):
                a2 = r2.uniform(0, 6.28)
                ln = r2.uniform(10, 24)
                d.line([(x, y), (x + math.cos(a2) * ln, y + math.sin(a2) * ln)],
                       fill=(*[max(0, min(255, c + r2.randint(-12, 14))) for c in base], 255), width=2)
    else:
        n = 1500 if kind == "leaf" else 2200
        for _ in range(n):
            ang = r2.uniform(0, 6.28)
            rad = (r2.random() ** 0.55) * s * 0.46
            x, y = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad * 0.9
            shade = 0.55 + 0.45 * (1 - y / s) + r2.uniform(-0.12, 0.12)
            if kind == "leaf":
                c = (int(58 * shade), int(118 * shade), int(44 * shade))
                rr = r2.uniform(5, 10)
                a2 = r2.uniform(0, 3.14)
                d.ellipse([x - rr, y - rr * 0.6, x + rr, y + rr * 0.6], fill=(*c, 255))
            else:
                c = (int(80 * shade), int(140 * shade), int(54 * shade))
                a2 = r2.uniform(0, 6.28)
                ln = r2.uniform(8, 16)
                d.line([(x, y), (x + math.cos(a2) * ln, y + math.sin(a2) * ln)], fill=(*c, 255), width=2)
    im.save(os.path.join(OUT, name + ".png"))


def bark():
    s = 256
    n = fbm(s, 8, 4, 33)
    st = np.repeat(tile_noise(s, 32, 34)[:1, :], s, 0)
    k = n * 0.5 + st * 0.5
    rgb = np.stack([70 + k * 60, 52 + k * 44, 40 + k * 34], -1)
    from_arrays("bark", rgb, np.full((s, s), 0.95, np.float32), k, 3.0)
    rgb2 = np.stack([104 + k * 50, 70 + k * 36, 54 + k * 30], -1)   # 소나무 (붉은 껍질)
    from_arrays("bark_pine", rgb2, np.full((s, s), 0.95, np.float32), k, 3.0)


def road_text(name, text, size=(512, 256)):
    """바닥 글씨 (투명 배경)."""
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(int(size[1] * 0.8))
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((size[0] - (bb[2] - bb[0])) / 2 - bb[0], (size[1] - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f,
           fill=(240, 238, 228, 235))
    a = np.asarray(im).copy()
    wear = fbm(size[0], 24, 3, 5)[:size[1], :size[0]]
    a[..., 3] = (a[..., 3] * np.clip(0.55 + wear * 0.6, 0, 1)).astype(np.uint8)
    Image.fromarray(a, "RGBA").save(os.path.join(OUT, name + ".png"))


def sign_plate(name, text, bg, fg, size=(256, 96)):
    text_img(text, size, fg, bg).save(os.path.join(OUT, name + ".png"))


if __name__ == "__main__":
    # 아파트 외벽: 2026년 도색 (흰색/회색/남색)
    front_flat("front_white", WHITE, WHITE, MGRAY, 1)
    front_flat("front_navy", NAVY, NAVY, NAVY_D, 2, slab=WHITE)
    front_flat("front_gray", LGRAY, LGRAY, DGRAY, 3, slab=WHITE)
    bay("bay", WHITE, 4)
    back("back_white", WHITE, LGRAY, 5)
    back("back_base", DGRAY, (86, 91, 102), 6, grill=True)
    core("core_white", LGRAY, 7)
    core("core_base", (86, 91, 102), 8)
    core_door("core_door", (86, 91, 102), 9)
    side("side_upper", LGRAY, MGRAY, 10)
    side("side_base", DGRAY, None, 11)
    parapet("parapet", WHITE, MGRAY)
    # 바닥과 재료
    asphalt()
    noise_mat("concrete", (176, 174, 168), 22, 13, 0.9)
    noise_mat("dirt", (112, 112, 108), 22, 14, 0.95)
    noise_mat("curb", (186, 184, 178), 18, 15, 0.85)
    noise_mat("stucco_white", (226, 226, 220), 10, 16, 0.85, cells=12)
    grass()
    hedge()
    roof_green()
    bricks("brick", [(150, 74, 56), (162, 84, 62), (138, 66, 52), (170, 92, 68)], (188, 180, 168), seed=1)
    bricks("brick_lattice", [(150, 74, 56), (162, 84, 62), (138, 66, 52), (170, 92, 68)], (188, 180, 168),
           lattice=True, seed=2)
    pavers("paver_red", [(170, 96, 84), (156, 86, 76), (182, 108, 94), (150, 90, 82)], (120, 104, 96), 3)
    pavers("paver_gray", [(168, 166, 160), (150, 150, 146), (182, 180, 174)], (112, 110, 106), 4)
    rocks("rock", 5)
    stone_blocks("stoneblock", 6)
    roof_tiles("rooftile_blue", (60, 96, 190), (22, 40, 104), 7)
    roof_tiles("rooftile_dark", (120, 70, 62), (62, 36, 34), 8)
    metal_roof("metal_blue", (58, 110, 190), 9)
    metal_roof("metal_gray", (150, 154, 158), 10)
    speed_bump()
    booth_wall()
    shop_tiles()
    warehouse_wall()
    tower_wall()
    bark()
    foliage("fol_pine", "pine", 1)
    foliage("fol_pine2", "pine", 2)
    foliage("fol_leaf", "leaf", 3)
    foliage("fol_leaf2", "leaf", 4)
    foliage("fol_meta", "meta", 5)
    road_text("txt_slow", "천천히")
    road_text("txt_kids", "어린이보호")
    for no in range(101, 110):
        sign_plate(f"plate_{no}", str(no), (40, 80, 170), (255, 255, 255))
    print("textures ->", OUT)
