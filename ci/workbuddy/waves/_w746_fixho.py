# -*- coding: utf-8 -*-
"""W709 步29：修交接件 §7 的 BAN 漏网（描述禁用码位时不得写字面量）+ 补产物索引注记 + 推 166
判据同 _w742：① 改后无禁用码位 ② 行数不变且 equal 块逐字节相同
             ③ replace 块每对 (old,new) 满足 new==map(old) 且 old 必含禁用码位
"""
import difflib, hashlib, io, os, shutil, sys, time
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

BANMAP = [('\u21d2', '=>'), ('\u2192', '->'), ('\u2014', '--'), ('\u2013', '-'), ('\u2026', '...'),
          ('\u2265', '>='), ('\u2264', '<='), ('\u2260', '!='), ('\u2212', '-'), ('\u00d7', 'x')]
BANC = [a for a, _ in BANMAP]
HO = r'D:/strata166/W709_HANDOVER.md'
BAKDIR = r'D:/workbuddy/_z_rk81/_bak_w709'
os.makedirs(BAKDIR, exist_ok=True)
TS = time.strftime('%Y%m%d_%H%M%S')


def amap(s):
    for a, b in BANMAP:
        s = s.replace(a, b)
    return s


def prove(o, n, tag):
    assert not any(c in n for c in BANC), 'STILL_BANNED %s' % [hex(ord(c)) for c in BANC if c in n]
    ol, nl = o.split('\n'), n.split('\n')
    assert len(ol) == len(nl), 'LINE_DRIFT'
    ch = 0
    for tg, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ol, nl).get_opcodes():
        if tg == 'equal':
            assert ol[i1:i2] == nl[j1:j2]
            continue
        assert i2 - i1 == j2 - j1
        for a, b in zip(ol[i1:i2], nl[j1:j2]):
            assert any(c in a for c in BANC), 'CHANGED_WITHOUT_BAN: %r' % a[:70]
            assert b == amap(a), 'UNEXPECTED: %r' % a[:70]
            ch += 1
    return ch


raw = open(HO, 'rb').read()
shutil.copy2(HO, os.path.join(BAKDIR, 'handover.bak_%s' % TS))
old = raw.decode('utf-8')
new = amap(old)

# 把 §7 里"写出字面量"的说明改成码位记法（可读性更好，且再断言一次）
fixes = [
    ('含 2 个禁用码位（`3x3` 里的那个乘号被写成 U+00D7', '含 2 个禁用码位（`3x3` 里的乘号被写成 U+00D7'),
    ('含 U+21D2 x1 + U+2014 x12', '含 U+21D2 x1 + U+2014 x12'),
]
for a, b in fixes:
    if a in new:
        new = new.replace(a, b)

ch = prove(old, new, 'handover')
nb = new.encode('utf-8')
assert nb.count(b'\r') == raw.count(b'\r'), 'CR_DRIFT'
open(HO, 'wb').write(nb)
print('交接件: %d -> %d B  改动行=%d  CR=%d  SELF_PROVE_OK' % (len(raw), len(nb), ch, nb.count(b'\r')))

# 追加产物索引注记（提醒 stale 的 verify 捕获件）
ADD = """
> **注（易踩）**：`D:/strata166/params/_verify_w709b.txt` 是**过时的捕获件**（改 TOOL 分支**之前**的
> `PASS=14 / FAIL=1`）。**当前正确读数 `PASS=15 / FAIL=0 / SKIP=1` 在 `D:/workbuddy/_z_rk81/_w736.out.txt`。**
> 若已把 `verify_config.py` 改成带 TOOL 分支的版本，重跑一次即可复现 15/0。
"""
t = io.open(HO, encoding='utf-8').read().rstrip('\n') + '\n' + ADD
bb = t.encode('utf-8')
assert not any(c in t for c in BANC), 'ADD_HAS_BAN'
open(HO, 'wb').write(bb)
b = open(HO, 'rb').read(); tt = b.decode('utf-8')
print('交接件终态 %d B md5=%s CR=%d BAN=%s' % (len(b), hashlib.md5(b).hexdigest(), b.count(b'\r'),
                                             {hex(ord(k)): tt.count(k) for k in BANC if tt.count(k)} or 'CLEAN'))

ok, size, m, _ = _sshutil.push_b64(HO, '/home/albus/strata166/W709_HANDOVER.md')
print('push 166 ok=%s size=%s md5=%s' % (ok, size, m))
