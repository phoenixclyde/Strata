import sys, base64, os, difflib, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'w820'))
from gh import api

f = 'src/kernels/cuda/native_mmvq.cu'
os.makedirs('albus/w823', exist_ok=True)
out = {}
for tag, sub in (('v0.2.4.2', 'old'), ('v0.2.7', 'new')):
    p = 'albus/w823/mmvq_%s.cu' % sub
    if not os.path.exists(p):
        d = api('/repos/Niko1221/Strata/contents/%s?ref=%s' % (f, tag), timeout=240)
        raw = base64.b64decode(d['content'])
        open(p, 'wb').write(raw)
        print('saved', p, len(raw), flush=True)
    out[sub] = open(p, encoding='utf-8', errors='replace').read().splitlines()

A, B = out['old'], out['new']
print('lines', len(A), '->', len(B), flush=True)
d = list(difflib.unified_diff(A, B, 'old', 'new', n=4, lineterm=''))
print('diff lines', len(d), flush=True)
hunks = [x for x in d if x.startswith('@@')]
print('hunks', len(hunks), flush=True)
for h in hunks:
    print(h, flush=True)
