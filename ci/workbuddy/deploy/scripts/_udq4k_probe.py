# -*- coding: utf-8 -*-
"""1) Strata CMake 里与 K-quant / MMQ / gfx906 相关的开关；2) ModelScope 上 unsloth UD-Q4_K_XL 的可下载性。"""
import os, re, json, urllib.request, socket, time

R = r'D:\Strata\src\Strata-0.1.39'
print('=== 1) CMake 开关 ===')
for f in ['CMakeLists.txt', os.path.join('cmake', 'StrataOptions.cmake')]:
    p = os.path.join(R, f)
    if not os.path.exists(p):
        print('  (missing)', f)
        continue
    t = open(p, encoding='utf-8', errors='replace').read()
    print('--', f, len(t), 'chars')
    for m in re.finditer(r'option\(\s*(\w+)\s+"([^"]*)"\s*(\w+)?', t):
        if re.search(r'MMQ|KQUANT|GFX906|HIP|Q4K|KQUANT', m.group(1), re.I):
            print('   option %-28s default=%-5s %s' % (m.group(1), m.group(3) or 'OFF', m.group(2)[:70]))

print()
print('=== 1b) 提到这些开关的地方（含条件逻辑）===')
for root, d, files in os.walk(R):
    if any(x in root for x in ('.git', 'third_party', 'docs', 'bench', 'ref', 'tests')):
        d[:] = []
        continue
    for fn in files:
        if not fn.endswith(('.txt', '.cmake', '.md')):
            continue
        p = os.path.join(root, fn)
        try:
            t = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for kw in ('STRATA_MMQ_KQUANTS', 'STRATA_PREFILL_MMQ', 'STRATA_ORCA_Q4KS_MMQ'):
            if kw in t:
                lines = [l.strip() for l in t.splitlines() if kw in l]
                print('  [%s] %s' % (os.path.relpath(p, R), kw))
                for l in lines[:6]:
                    print('       ', l[:150])

print()
print('=== 2) ModelScope: unsloth/Qwen3.8-Flash-Next-GGUF 的 UD-Q4_K_XL 文件清单 ===')
socket.setdefaulttimeout(30)
UA = {'User-Agent': 'Mozilla/5.0'}
for repo in ['unsloth/Qwen3.8-Flash-Next-GGUF', 'unsloth/Qwen3.8-Flash-Next-UD-Q4_K_XL-GGUF']:
    url = 'https://www.modelscope.cn/api/v1/models/%s/repo/files?Revision=master&Recursive=true' % repo
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            d = json.loads(r.read().decode('utf-8'))
        files = d.get('Data', {}).get('Files', [])
        print('-- %s : %d entries' % (repo, len(files)))
        for x in files:
            nm = x.get('Path', '')
            sz = x.get('Size', 0)
            if sz > 100_000_000 or 'UD-Q4_K_XL' in nm:
                print('   %-72s %8.2f GB' % (nm, sz / 1e9))
    except Exception as e:
        print('-- %s FAIL %s' % (repo, str(e)[:150]))
