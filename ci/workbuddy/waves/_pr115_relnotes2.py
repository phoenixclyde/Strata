# -*- coding: utf-8 -*-
"""补拉 release note（走 releases 列表端点，实测该端点稳定）+ 落盘"""
import sys, os, io, time
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

UP = "Niko1221/Strata"
OUT = r"D:/strata166/upstream/relnotes"
os.makedirs(OUT, exist_ok=True)

st, b, _ = _gh.api("https://api.github.com/repos/%s/releases?per_page=8" % UP, timeout=150)
print('list HTTP %s' % st)
rels = _gh.jload(b) or []
if not isinstance(rels, list):
    print(b[:400]); raise SystemExit(1)
for r in rels:
    tag = r.get('tag_name'); body = r.get('body') or ''
    p = os.path.join(OUT, tag + '.md')
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    print('  %-12s published=%s  body=%6d B -> %s' % (tag, r.get('published_at'), len(body.encode()), os.path.basename(p)))
print()
print('=== v0.1.40.2 全文 ===')
p = os.path.join(OUT, 'v0.1.40.2.md')
print(io.open(p, encoding='utf-8').read() if os.path.isfile(p) else 'MISSING')
