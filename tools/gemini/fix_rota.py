# Usage: python3 tools/gemini/fix_rota.py <gemini rota.glb> assets/characters/rota_gemini.glb
"""Gemini rota.glb fix: merge duplicate joint slots per vertex (Blender reads only the last duplicate),
and scale the sword and scabbard to 80% around their origins (grip / scabbard mouth)."""
import json, struct, sys
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
f = bytearray(open(src, 'rb').read())
l = struct.unpack('<I', f[12:16])[0]
j = json.loads(bytes(f[20:20 + l]))
binoff = 20 + l + 8
CT = {5126: np.float32, 5123: np.uint16, 5121: np.uint8}
def view(i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]
    assert not bv.get('byteStride') or bv['byteStride'] == np.dtype(CT[a['componentType']]).itemsize * 4
    off = binoff + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    n = a['count'] * 4
    return np.frombuffer(f, CT[a['componentType']], n, off).reshape(a['count'], 4), off
fixed = 0
for m in j['meshes']:
    for p in m['primitives']:
        if 'JOINTS_0' not in p['attributes']: continue
        W, wo = view(p['attributes']['WEIGHTS_0']); J, jo = view(p['attributes']['JOINTS_0'])
        W2 = W.astype(np.float64).copy(); J2 = J.copy()
        for i in range(len(W)):
            acc = {}
            for k in range(4):
                if W[i, k] > 0: acc[int(J[i, k])] = acc.get(int(J[i, k]), 0) + float(W[i, k])
            if len(acc) < sum(1 for k in range(4) if W[i, k] > 0):
                fixed += 1
            items = sorted(acc.items(), key=lambda x: -x[1])[:4]
            s = sum(w for _, w in items) or 1
            J2[i] = 0; W2[i] = 0
            for k, (jj, w) in enumerate(items): J2[i, k] = jj; W2[i, k] = w / s
        f[wo:wo + W2.nbytes // 2] = W2.astype(np.float32).tobytes()
        f[jo:jo + J2.nbytes] = J2.astype(J.dtype).tobytes()
for n in j['nodes']:
    if n['name'] in ('Rota_Sword', 'Rota_Scabbard'): n['scale'] = [0.8, 0.8, 0.8]
js = json.dumps(j, separators=(',', ':')).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
binchunk = bytes(f[20 + l:])
out = bytearray(b'glTF' + struct.pack('<II', 2, 0))
out += struct.pack('<I', len(js)) + b'JSON' + js + binchunk
out[8:12] = struct.pack('<I', len(out))
open(dst, 'wb').write(out)
print('vertices with duplicate joints merged:', fixed)
