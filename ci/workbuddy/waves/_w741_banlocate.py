# W709 步26：定位禁用码位（含上下文），并做记忆日志的 delta 扫描
import io, os

BAN = {'\u21d2': '⇒', '\u2192': '→', '\u2014': '—', '\u2013': '–', '\u2026': '…',
       '\u2265': '>=', '\u2264': '<=', '\u2260': '!=', '\u2212': '-', '\u00d7': 'x'}

print('=== 1) PARAM_REGISTER.tsv 的命中行 ===')
p = r'D:/strata166/params/PARAM_REGISTER.tsv'
for i, ln in enumerate(io.open(p, encoding='utf-8').read().splitlines(), 1):
    hit = [hex(ord(k)) for k in BAN if k in ln]
    if hit:
        print('  L%-4d %s' % (i, hit))
        for k in BAN:
            if k in ln:
                j = ln.index(k)
                print('        ...%s...' % ln[max(0, j - 70):j + 70])

print()
print('=== 2) gen_config.py / verify_config.py 的命中行 ===')
for p in [r'D:/strata166/params/gen_config.py', r'D:/strata166/params/verify_config.py']:
    print('  --', os.path.basename(p))
    for i, ln in enumerate(io.open(p, encoding='utf-8').read().splitlines(), 1):
        hit = [hex(ord(k)) for k in BAN if k in ln]
        if hit:
            print('     L%-4d %-22s %s' % (i, hit, ln.strip()[:100]))

print()
print('=== 3) 记忆日志：只扫我本波追加的三段（W709a/W709b/W709c）===')
p = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
t = io.open(p, encoding='utf-8').read()
i = t.find('## W709a')
seg = t[i:] if i > 0 else ''
print('  段字节 =', len(seg.encode()))
for k, name in BAN.items():
    c = seg.count(k)
    if c:
        print('  %s (%s) x%d' % (hex(ord(k)), name, c))
        j = seg.index(k)
        print('      ...%s...' % seg[max(0, j - 80):j + 80].replace('\n', ' | '))
print('  （以上即本波引入的禁用码位；空 = 本波增量洁净）')
