# -*- coding: utf-8 -*-
"""UD-Q4_K_XL 下载校验：按 setup.py 的 UNSLOTH_SHARDS 钉死 size + sha256 逐个核对。"""
import hashlib, os, sys, time, json

SRC = r'D:\idm\Strata-UDQ4KXL'
PIN = {
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf':
        (10946624, '4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082'),
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf':
        (49859583136, '3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9'),
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf':
        (49376141504, '56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3'),
    'Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf':
        (12087983520, '753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a'),
}
OK = []
for n, (sz, sha) in PIN.items():
    p = os.path.join(SRC, n)
    if not os.path.exists(p):
        print('MISSING      %s' % n); OK.append(False); continue
    have = os.path.getsize(p)
    if have != sz:
        print('SIZE BAD     %s  have=%d need=%d (diff %d)' % (n, have, sz, have - sz)); OK.append(False); continue
    t0 = time.time()
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    dt = time.time() - t0
    good = h.hexdigest() == sha
    print('%-6s %-52s %6.2f GB  sha256 %s  (%.0f MB/s)'
          % ('OK' if good else 'SHA BAD', n, sz / 1e9, 'match' if good else h.hexdigest()[:16],
             sz / 1048576 / max(dt, .01)))
    OK.append(good)

print()
tot = sum(PIN[n][0] for n in PIN)
print('TOTAL %.2f GB  ALL_OK=%s' % (tot / 1e9, all(OK)))
if not all(OK):
    sys.exit(2)
