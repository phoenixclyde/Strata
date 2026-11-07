import sys, base64, os, difflib, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'w820'))
from gh import api

pairs = [
    ('src/core/expert_cache.cpp', 'cache'),
    ('docs/AMD_HIP.md', 'amdhip'),
    ('docs/OLDER_GPUS.md', 'older'),
]
for f, short in pairs:
    got = {}
    for tag, sub in (('v0.2.4.2', 'old'), ('v0.2.7', 'new')):
        p = 'albus/w823/%s_%s.txt' % (short, sub)
        if not os.path.exists(p):
            d = api('/repos/Niko1221/Strata/contents/%s?ref=%s' % (f, tag), timeout=240)
            open(p, 'wb').write(base64.b64decode(d['content']))
        got[sub] = open(p, encoding='utf-8', errors='replace').read().splitlines()
    A, B = got['old'], got['new']
    d = [x for x in difflib.unified_diff(A, B, 'old', 'new', n=2, lineterm='')
         if x.startswith(('+', '-')) and not x.startswith(('+++', '---'))]
    print('%-28s %5d -> %5d lines, +-%d' % (f, len(A), len(B), len(d)), flush=True)
    if short != 'cache':
        # 只看含 gfx906 / MI50 的变更行
        g = [x for x in d if re.search(r'gfx906|MI50|Vega', x)]
        print('   gfx906/MI50 相关变更行:', len(g))
        for x in g[:20]:
            print('     ', x[:170])
