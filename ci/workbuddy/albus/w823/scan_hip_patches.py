import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'w820'))
from gh import api

pat = re.compile(r'__HIPCC__|STRATA_HIP_GFX906|HIP|gfx906|hipError|hipMalloc|rocblas|rocBLAS')
rows = []
for page in (1, 2):
    d = api('/repos/Niko1221/Strata/compare/v0.2.4.2...v0.2.7?per_page=100&page=%d' % page, timeout=240)
    fs = d.get('files') or []
    print('page', page, 'files', len(fs), 'total_commits', d.get('total_commits'), flush=True)
    if not fs:
        break
    rows += fs

eng = [f for f in rows if f['filename'].startswith(('src/', 'include/', 'cmake/'))]
print('engine files', len(eng), 'of', len(rows), flush=True)

hit = []
for f in eng:
    p = f.get('patch') or ''
    added = [l for l in p.splitlines() if l.startswith('+') and not l.startswith('+++')]
    removed = [l for l in p.splitlines() if l.startswith('-') and not l.startswith('---')]
    ah = [l for l in added if pat.search(l)]
    rh = [l for l in removed if pat.search(l)]
    if ah or rh:
        hit.append((f['filename'], len(added), len(ah), len(rh), ah[:4], rh[:4]))

print()
print('=== 补丁里出现 HIP/gfx906 关键字的引擎文件：%d ===' % len(hit))
for fn, na, ah, rh, a, r in sorted(hit, key=lambda x: -(x[2] + x[3])):
    print('\n%-56s +%d 行, HIP 命中 +%d/-%d' % (fn, na, ah, rh))
    for l in a:
        print('   +', l[1:].strip()[:150])
    for l in r:
        print('   -', l[1:].strip()[:150])

json.dump([{k: v for k, v in f.items() if k != 'patch'} for f in rows],
          open('albus/w823/cmp_files.json', 'w'), ensure_ascii=False)
