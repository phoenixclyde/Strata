# -*- coding: utf-8 -*-
"""本机校验 UD-IQ4_XS 三片 sha256（对照 setup.py 的钉死值）。"""
import hashlib, os, sys, time
sys.stdout.reconfigure(encoding='utf-8')

D = r'D:\idm\Strata-UDIQ4XS'
PIN = {
    'Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf':
        (10946624, '5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4'),
    'Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf':
        (49835229856, '577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7'),
    'Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf':
        (43836407744, 'd4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833'),
}

allok = True
tot = 0
for name, (want_sz, want_sha) in PIN.items():
    p = os.path.join(D, name)
    print('=' * 72)
    print(name)
    if not os.path.exists(p):
        print('  !! 不存在'); allok = False; continue
    sz = os.path.getsize(p)
    tot += sz
    print('  size %d  (期望 %d)  %s' % (sz, want_sz, 'OK' if sz == want_sz else 'MISMATCH'))
    if sz != want_sz:
        allok = False
        continue
    h = hashlib.sha256()
    t0 = time.time()
    with open(p, 'rb') as f:
        while True:
            b = f.read(32 << 20)
            if not b:
                break
            h.update(b)
    got = h.hexdigest()
    ok = got == want_sha
    allok = allok and ok
    print('  sha256 %s  %s  (%.0fs)' % (got[:32] + '...', 'match' if ok else 'MISMATCH', time.time() - t0))
    if not ok:
        print('  期望   %s' % want_sha)

print()
print('TOTAL %.3f GB   期望 93.683 GB   ALL_OK=%s' % (tot / 1e9, allok))
