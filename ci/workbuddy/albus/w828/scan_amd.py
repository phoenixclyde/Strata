import json
import re

BASE = 'D:/workbuddy_space/strata_ws/albus/w828/'
files = json.load(open(BASE + 'compare_0271_028.json', encoding='utf-8'))

KW = re.compile(r'HIP|AMD|amd|gfx|ROCM|rocm|__HIP|hip', re.I)

rows = []
for f in files:
    patch = f.get('patch') or ''
    hits = [l for l in patch.split('\n') if l[:1] in '+-' and KW.search(l)]
    rows.append((f['filename'], f['additions'], f['deletions'], len(hits), len(patch)))

print('%-58s %5s %5s %5s %7s' % ('file', '+', '-', 'amdln', 'patch'))
for r in sorted(rows, key=lambda x: (-x[3], x[0])):
    if r[3] > 0:
        print('%-58s %5d %5d %5d %7d' % r)

print()
print('=== no-patch files (likely binary/huge) ===')
for r in rows:
    if r[4] == 0:
        print('  ', r[0], r[1], r[2])

print()
print('=== engine files with amd lines ===')
for r in rows:
    if r[3] > 0 and (r[0].startswith(('src/', 'include/')) or r[0] == 'CMakeLists.txt'):
        print(r[0], r[3])
