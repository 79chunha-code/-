"""갈무리(Galmuri) 비트맵 글꼴(BDF)을 게임이 바로 읽는 font.js로 바꾼다.

사용법:
    npm pack galmuri && tar xzf galmuri-*.tgz
    python3 tools/font/build_font.py package/dist game/demo/font.js

글꼴: Galmuri (c) Lee Minseo, SIL Open Font License 1.1.
담는 글자: ASCII, 자주 쓰는 문장부호와 기호, KS X 1001 완성형 한글 2,350자.
글자마다 "머리 5글자(전진폭, 너비, 높이, x오프셋+8, y오프셋+8을 chr(48+값)으로) + 비트맵 base64" 한 덩이.
"""
import base64
import json
import sys

EXTRA = "“”‘’…·—–~♪★☆※→←↑↓▶◀▲▼♥♡◆◇■□●○×÷°「」『』〈〉《》ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅓㅗㅜㅡㅣ"


def charset():
    cs = [chr(c) for c in range(32, 127)]
    cs += list(EXTRA)
    for lead in range(0xB0, 0xC9):
        for trail in range(0xA1, 0xFF):
            try:
                cs.append(bytes([lead, trail]).decode("euc-kr"))
            except UnicodeDecodeError:
                pass
    return cs


def parse_bdf(path):
    glyphs, props = {}, {}
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            k = p[0]
            if k in ("FONT_ASCENT", "FONT_DESCENT"):
                props[k] = int(p[1])
            elif k == "ENCODING":
                cur = {"cp": int(p[1]), "rows": []}
            elif k == "DWIDTH" and cur is not None:
                cur["adv"] = int(p[1])
            elif k == "BBX" and cur is not None:
                cur["w"], cur["h"], cur["x"], cur["y"] = map(int, p[1:5])
            elif k == "BITMAP":
                cur["in"] = True
            elif k == "ENDCHAR":
                glyphs[cur["cp"]] = cur
                cur = None
            elif cur is not None and cur.get("in"):
                cur["rows"].append(p[0])
    return props, glyphs


def pack(g):
    w, h = g["w"], g["h"]
    bits = []
    for row in g["rows"][:h]:
        v = int(row, 16)
        n = len(row) * 4
        bits += [(v >> (n - 1 - i)) & 1 for i in range(w)]
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i >> 3] |= 0x80 >> (i & 7)
    head = "".join(chr(48 + v) for v in (g["adv"], w, h, g["x"] + 8, g["y"] + 8))
    return head + base64.b64encode(bytes(out)).decode().rstrip("=")


def build(path):
    props, glyphs = parse_bdf(path)
    chars, recs = [], []
    for ch in charset():
        g = glyphs.get(ord(ch))
        if g is None:
            continue
        chars.append(ch)
        recs.append(pack(g))
    return {"asc": props["FONT_ASCENT"], "desc": props["FONT_DESCENT"], "chars": "".join(chars), "data": " ".join(recs)}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    fonts = {"f11": build(src + "/Galmuri11.bdf"), "f9": build(src + "/Galmuri9.bdf")}
    with open(dst, "w", encoding="utf-8") as f:
        f.write("// 자동 생성 파일: tools/font/build_font.py. 글꼴: Galmuri (c) Lee Minseo, SIL OFL 1.1\n")
        f.write("window.GAME_FONTS = " + json.dumps(fonts, ensure_ascii=False, separators=(",", ":")) + ";\n")
    for k, v in fonts.items():
        print(k, len(v["chars"]), "글자", len(v["data"]) // 1024, "KB")


main()
