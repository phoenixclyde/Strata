# -*- coding: utf-8 -*-
"""拉 v0.1.40 / v0.1.40.1 / v0.1.40.2 的 release note 全文并落盘"""
import sys, os, time, json, io
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

UP = "Niko1221/Strata"
OUT = r"D:/strata166/upstream/relnotes"
os.makedirs(OUT, exist_ok=True)

for tag in ("v0.1.40.2", "v0.1.40.1", "v0.1.40", "v0.1.39"):
    st, b, _ = _gh.api("https://api.github.com/repos/%s/releases/tags/%s" % (UP, tag), timeout=120)
    d = _gh.jload(b) or {}
    print('=== %s  HTTP %s  name=%r  published=%s  body_len=%s' %
          (tag, st, d.get('name'), d.get('published_at'), len(d.get('body') or '')))
    if st != 200:
        print('   raw=%s' % b[:200]); print(); continue
    body = d.get('body') or ''
    p = os.path.join(OUT, tag + '.md')
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    print('   -> %s  (%d B)' % (p, len(body.encode())))
    print()
    time.sleep(0.5)
print('DONE')
