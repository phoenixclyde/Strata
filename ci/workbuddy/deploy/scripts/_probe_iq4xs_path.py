# -*- coding: utf-8 -*-
"""探测 UD-IQ4_XS 在 ModelScope 上的路径与 revision（并用 size 对上 setup.py 的钉死值）。"""
import os, re, sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

UA = {'User-Agent': 'Mozilla/5.0'}
CR_RE = re.compile(r'bytes\s+(\d+)-(\d+)/(\d+)')
OFF = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# 1) 取 setup.py 里的 HF_REVISIONS（U4/IQ4 那条）
t = open(r'D:\Strata\src\Strata-0.1.39\setup.py', encoding='utf-8', errors='replace').read()
i = t.find('HF_REVISIONS = {')
print('=== HF_REVISIONS ===')
print(t[i:i + 800])
print()

NAME1 = 'Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
WANT = 10946624
BASE = 'https://www.modelscope.cn/models/unsloth/Qwen3.8-Flash-Next-GGUF/resolve/'
CAND = [
    ('master', 'UD-IQ4_XS/'),
    ('master', ''),
    ('master', 'UD-IQ4_XS'),
]
for rev, sub in CAND:
    url = '%s%s/%s%s' % (BASE, rev, sub, NAME1)
    h = dict(UA); h['Range'] = 'bytes=0-0'
    try:
        with OFF.open(urllib.request.Request(url, headers=h), timeout=40) as r:
            cr = r.headers.get('Content-Range')
            n = int(CR_RE.match(cr).group(3)) if cr and CR_RE.match(cr) else None
        print('  %-8s sub=%-12r status=%s total=%s  期望=%d  match=%s'
              % (rev, sub, r.status, n, WANT, n == WANT))
    except Exception as e:
        print('  %-8s sub=%-12r FAIL %s' % (rev, sub, str(e)[:110]))

# 2) 用具体 revision 试（从 HF 的 commit）
for rev in []:
    pass
