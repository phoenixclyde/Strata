import io

P = 'D:/workbuddy_space/strata_ws/deploy/patches/LOCAL_PATCHES.tsv'
raw = io.open(P, encoding='utf-8-sig').read().split('\n')
rows = [l.split('\t') for l in raw if l.strip()]
hdr = rows[0]
body = rows[1:]

COMMIT = {
    'W793': 'c5fd0796',
    'W776': '01e01636',
    'W794': 'b42e4bc0',
    'TEL-PCIE': '46aaaba5',
    'WEB-UI': '7c38cb4e',
    'W830-COMPAT': '923c2118',
    'W831': 'f3d35b86',
}

if 'commit' not in hdr:
    hdr = hdr + ['commit']

out = ['\t'.join(hdr)]
missing = []
for r in body:
    pid = r[0].strip()
    c = COMMIT.get(pid, '')
    if not c:
        missing.append(pid)
    out.append('\t'.join(r + [c]))

io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('rows:', len(out) - 1)
print('cols:', len(hdr))
print('without commit:', missing if missing else 'none')
for l in out[1:]:
    c = l.split('\t')
    print('  %-13s %s  %s' % (c[0], c[-1] or '(none)', c[1][:40]))
