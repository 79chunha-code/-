"""Re-encode the opaque PNG textures inside a .glb as JPEG (alpha textures stay PNG), so models stay light on phones.

    python3 tools/gemini/jpeg_textures.py in.glb out.glb [quality]
"""
import io, json, struct, sys
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
q = int(sys.argv[3]) if len(sys.argv) > 3 else 85
f = open(src, 'rb').read()
l = struct.unpack('<I', f[12:16])[0]
j = json.loads(f[20:20 + l])
b = f[20 + l + 8:]
img_views = {im['bufferView']: k for k, im in enumerate(j.get('images', []))}
new_views, out = [], bytearray()
for vi, bv in enumerate(j['bufferViews']):
    o = bv.get('byteOffset', 0)
    data = b[o:o + bv['byteLength']]
    if vi in img_views:
        im = j['images'][img_views[vi]]
        I = Image.open(io.BytesIO(data))
        if I.mode == 'RGB' or (I.mode == 'RGBA' and I.getchannel('A').getextrema()[0] == 255):
            buf = io.BytesIO(); I.convert('RGB').save(buf, 'JPEG', quality=q, optimize=True)
            if buf.tell() < len(data):
                data = buf.getvalue(); im['mimeType'] = 'image/jpeg'
    while len(out) % 4: out.append(0)
    nb = dict(bv); nb['byteOffset'] = len(out); nb['byteLength'] = len(data)
    out += data; new_views.append(nb)
while len(out) % 4: out.append(0)
j['bufferViews'] = new_views
j['buffers'] = [{'byteLength': len(out)}]
js = json.dumps(j, separators=(',', ':')).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
g = bytearray(b'glTF' + struct.pack('<II', 2, 0))
g += struct.pack('<I', len(js)) + b'JSON' + js
g += struct.pack('<I', len(out)) + b'BIN\x00' + out
g[8:12] = struct.pack('<I', len(g))
open(dst, 'wb').write(g)
print(src, len(f), '->', dst, len(g))
