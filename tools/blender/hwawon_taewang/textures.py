"""화원태왕타운 외벽/바닥 텍스처 생성기 (PIL).

모든 텍스처는 코드로 그린다. 실사 사진은 쓰지 않는다.
실행: python3 textures.py <출력 폴더>
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "textures"
os.makedirs(OUT, exist_ok=True)
rng = random.Random(1995)

WALL = (236, 235, 230)
WALL_SHADE = (214, 213, 207)
SLAB = (222, 221, 215)
MINT = (98, 196, 168)
MINT_DARK = (70, 160, 136)
ORANGE = (236, 160, 60)
FRAME = (226, 228, 228)
GLASS_TOP = (88, 116, 124)
GLASS_BOT = (140, 172, 176)
CURTAINS = [(200, 214, 190), (226, 214, 188), (190, 206, 214), (238, 232, 220), (180, 196, 170)]


class Tile:
    """미터 단위로 그리는 캔버스. 원점은 왼쪽 아래(바닥), y는 위로."""

    def __init__(self, w_m, h_m, w_px, h_px, bg):
        self.w_m, self.h_m = w_m, h_m
        self.im = Image.new("RGB", (w_px, h_px), bg)
        self.d = ImageDraw.Draw(self.im)
        self.sx = w_px / w_m
        self.sy = h_px / h_m

    def box(self, x0, y0, x1, y1):
        h = self.im.height
        return [round(x0 * self.sx), round(h - y1 * self.sy), round(x1 * self.sx) - 1, round(h - y0 * self.sy) - 1]

    def rect(self, x0, y0, x1, y1, fill, outline=None, width=1):
        self.d.rectangle(self.box(x0, y0, x1, y1), fill=fill, outline=outline, width=width)

    def hline(self, x0, x1, y, fill, t=0.03):
        self.rect(x0, y - t / 2, x1, y + t / 2, fill)

    def vline(self, x, y0, y1, fill, t=0.04):
        self.rect(x - t / 2, y0, x + t / 2, y1, fill)

    def glass(self, x0, y0, x1, y1, curtain=None):
        bx = self.box(x0, y0, x1, y1)
        hgt = max(1, bx[3] - bx[1])
        for i in range(hgt + 1):
            t = i / hgt
            c = tuple(int(GLASS_TOP[k] * (1 - t) + GLASS_BOT[k] * t) for k in range(3))
            self.d.line([(bx[0], bx[1] + i), (bx[2], bx[1] + i)], fill=c)
        if curtain:
            cw = (x1 - x0) * rng.uniform(0.25, 0.45)
            side = rng.random() < 0.5
            cx0, cx1 = (x0, x0 + cw) if side else (x1 - cw, x1)
            self.rect(cx0, y0, cx1, y1, curtain)
        # 반사광 사선
        for _ in range(2):
            sx = rng.uniform(x0, x1)
            self.d.line([(round(sx * self.sx), bx[3]), (round((sx + 0.4) * self.sx), bx[1])], fill=(170, 196, 200), width=2)

    def window(self, x0, y0, x1, y1, panes=2, curtain=None, frame=FRAME, grill=False):
        self.rect(x0 - 0.06, y0 - 0.06, x1 + 0.06, y1 + 0.06, WALL_SHADE)
        self.glass(x0, y0, x1, y1, curtain)
        self.rect(x0, y0, x1, y1, None, outline=frame, width=3)
        for i in range(1, panes):
            self.vline(x0 + (x1 - x0) * i / panes, y0, y1, frame, 0.05)
        if grill:
            n = max(3, int((x1 - x0) / 0.12))
            for i in range(1, n):
                self.vline(x0 + (x1 - x0) * i / n, y0, y1, (245, 245, 245), 0.025)
            self.hline(x0, x1, (y0 + y1) / 2, (245, 245, 245), 0.03)

    def save(self, name):
        self.im.save(os.path.join(OUT, name))


def front_tile(ground=False):
    """남향(발코니) 면, 한 세그먼트 = 2세대(16m) x 1층(2.7m)."""
    t = Tile(16.0, 2.7, 1024, 256, WALL)
    for u, accent in ((0.0, MINT), (8.0, ORANGE)):
        # 세대 경계 색 띠
        t.rect(u, 0, u + 0.35, 2.7, accent)
        t.rect(u + 7.65, 0, u + 8.0, 2.7, MINT if accent is ORANGE else ORANGE)
        # 발코니 난간벽
        t.rect(u + 0.35, 0, u + 7.65, 0.95, (243, 242, 238))
        t.hline(u + 0.35, u + 7.65, 0.95, WALL_SHADE, 0.05)
        # 발코니 창 (거실 넓게, 방 좁게)
        t.window(u + 0.55, 1.0, u + 4.55, 2.35, panes=4, curtain=rng.choice(CURTAINS), grill=ground)
        t.window(u + 4.85, 1.0, u + 7.45, 2.35, panes=2, curtain=rng.choice(CURTAINS), grill=ground)
        if ground:
            t.vline(u + 4.7, 0.05, 0.9, WALL_SHADE, 0.05)
    # 층간 슬래브 띠
    t.rect(0, 2.45, 16, 2.7, SLAB)
    t.hline(0, 16, 2.45, (190, 190, 184), 0.03)
    t.save("front_ground.png" if ground else "front.png")


def back_tile(ground=False):
    """북향(복도/계단) 면, 한 세그먼트 = 세대 6.5m + 계단실 3m + 세대 6.5m."""
    t = Tile(16.0, 2.7, 1024, 256, WALL)
    for u, mirror in ((0.0, False), (9.5, True)):
        def x(v):
            return u + (6.5 - v if mirror else v)
        a0, a1 = sorted((x(0.6), x(2.2)))
        t.window(a0, 0.9, a1, 2.15, panes=2, curtain=rng.choice(CURTAINS + [None]), grill=ground)
        b0, b1 = sorted((x(2.9), x(3.5)))
        t.window(b0, 1.65, b1, 2.15, panes=1, grill=ground)
        c0, c1 = sorted((x(4.2), x(5.9)))
        t.window(c0, 0.9, c1, 2.15, panes=2, curtain=rng.choice(CURTAINS + [None]), grill=ground)
        # 실외기 거치대
        d0, d1 = sorted((x(3.6), x(4.1)))
        t.rect(d0, 0.3, d1, 0.8, (205, 205, 200), outline=(180, 180, 175))
    # 계단실 민트 띠
    t.rect(6.5, 0, 9.5, 2.7, MINT)
    t.vline(6.5, 0, 2.7, MINT_DARK, 0.06)
    t.vline(9.5, 0, 2.7, MINT_DARK, 0.06)
    if ground:
        # 공동현관 유리문
        t.rect(6.9, 0, 9.1, 2.35, (90, 96, 100))
        t.glass(7.0, 0.0, 7.98, 2.25)
        t.glass(8.02, 0.0, 9.0, 2.25)
        t.rect(7.0, 0.0, 9.0, 2.25, None, outline=(70, 74, 78), width=4)
        t.vline(8.0, 0, 2.25, (70, 74, 78), 0.06)
        t.rect(7.6, 1.0, 7.85, 1.1, (200, 200, 200))
        t.rect(8.15, 1.0, 8.4, 1.1, (200, 200, 200))
    else:
        t.window(7.45, 1.2, 8.55, 2.1, panes=2, frame=(235, 240, 238))
    t.rect(0, 2.5, 16, 2.7, SLAB)
    t.save("back_ground.png" if ground else "back.png")


def side_tile():
    """측벽, 깊이 12m x 1층."""
    t = Tile(12.0, 2.7, 512, 128, WALL)
    t.window(2.6, 1.15, 3.4, 2.0, panes=1)
    t.window(8.6, 1.15, 9.4, 2.0, panes=1)
    t.vline(0.15, 0, 2.7, WALL_SHADE, 0.06)
    t.vline(11.85, 0, 2.7, WALL_SHADE, 0.06)
    t.rect(0, 2.55, 12, 2.7, SLAB)
    t.save("side.png")


def parapet_tile():
    t = Tile(8.0, 1.0, 512, 64, WALL)
    t.rect(0, 0.55, 8, 0.8, MINT)
    t.hline(0, 8, 0.0, WALL_SHADE, 0.08)
    t.save("parapet.png")


def rooftop_tile():
    t = Tile(4.0, 3.2, 256, 256, WALL)
    t.window(1.5, 1.4, 2.5, 2.3, panes=1)
    t.rect(0, 2.75, 4, 3.2, MINT)
    t.save("rooftop.png")


def shop_tile():
    """상가 1층 점포. 간판은 일부러 글자가 없는 색 판으로만 그린다."""
    t = Tile(24.0, 3.6, 1024, 256, (210, 206, 198))
    signs = [(40, 110, 200), (220, 60, 60), (250, 200, 40), (60, 170, 90)]
    for i, sign in enumerate(signs):
        u = i * 6.0
        t.rect(u + 0.2, 2.75, u + 5.8, 3.45, sign)
        t.rect(u + 0.5, 2.95, u + 5.5, 3.25, tuple(min(255, c + 60) for c in sign))
        t.rect(u + 0.3, 0.0, u + 5.7, 2.6, (70, 76, 80))
        t.glass(u + 0.45, 0.05, u + 3.9, 2.5)
        t.glass(u + 4.1, 0.05, u + 5.55, 2.5)
        t.vline(u + 2.2, 0.05, 2.5, (60, 64, 68), 0.06)
        t.vline(u + 4.0, 0.0, 2.6, (60, 64, 68), 0.1)
    t.save("shop.png")


def noise_tile(name, base, var, size=512, speck=None, blur=1.2):
    im = Image.new("RGB", (size, size), base)
    px = im.load()
    for y in range(size):
        for x in range(size):
            n = rng.randint(-var, var)
            px[x, y] = tuple(max(0, min(255, base[k] + n)) for k in range(3))
    if speck:
        d = ImageDraw.Draw(im)
        for _ in range(size * 3):
            x, y = rng.randrange(size), rng.randrange(size)
            d.point((x, y), fill=rng.choice(speck))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    im.save(os.path.join(OUT, name))
    return im


def paver_tile():
    size = 256
    im = Image.new("RGB", (size, size), (180, 176, 168))
    d = ImageDraw.Draw(im)
    step = 32
    for y in range(0, size, step):
        off = (step // 2) if (y // step) % 2 else 0
        for x in range(-step, size, step * 2):
            c = rng.choice([(196, 188, 176), (188, 182, 172), (176, 150, 140), (200, 196, 186)])
            d.rectangle([x + off + 1, y + 1, x + off + step * 2 - 2, y + step - 2], fill=c)
    im.save(os.path.join(OUT, "paver.png"))


def brick_tile():
    size = 256
    im = Image.new("RGB", (size, size), (200, 192, 180))
    d = ImageDraw.Draw(im)
    bh, bw = 16, 48
    for r, y in enumerate(range(0, size, bh)):
        off = bw // 2 if r % 2 else 0
        for x in range(-bw, size + bw, bw):
            c = rng.choice([(150, 78, 58), (162, 88, 64), (140, 72, 56), (170, 96, 70)])
            d.rectangle([x + off + 1, y + 1, x + off + bw - 2, y + bh - 2], fill=c)
    im.save(os.path.join(OUT, "brick.png"))


def roof_tile():
    size = 256
    im = Image.new("RGB", (size, size), (78, 156, 128))
    d = ImageDraw.Draw(im)
    for i in range(0, size, 64):
        d.line([(i, 0), (i, size)], fill=(68, 140, 114), width=2)
        d.line([(0, i), (size, i)], fill=(68, 140, 114), width=2)
    im.save(os.path.join(OUT, "roof.png"))


if __name__ == "__main__":
    front_tile(False)
    front_tile(True)
    back_tile(False)
    back_tile(True)
    side_tile()
    parapet_tile()
    rooftop_tile()
    shop_tile()
    paver_tile()
    brick_tile()
    roof_tile()
    noise_tile("asphalt.png", (78, 80, 84), 14, speck=[(110, 110, 110), (60, 60, 62)])
    noise_tile("grass.png", (92, 132, 64), 22, speck=[(70, 110, 50), (120, 150, 80)], blur=0.8)
    noise_tile("ground.png", (150, 146, 136), 12, speck=[(120, 116, 108)])
    noise_tile("sand.png", (206, 186, 150), 14, blur=0.8)
    print("textures ->", OUT)
