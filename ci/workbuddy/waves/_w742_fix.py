# -*- coding: utf-8 -*-
"""W709 步27b：清禁用码位（自证判据改为「逐行对齐 + 改动行必原含禁用码位」）

为什么改判据：首版用「反向 undo 必须逐字节等于原文」——但 `-` 的反向映射不唯一
（`-` 可能来自 `–`/`−`），undo 会把所有连字符变成减号 => 断言必然失败。
**是判据本身有缺陷，不是文件有问题。**

现在的自证（三条，全部逐行可核）：
  1) 改后**无任何禁用码位**；
  2) **行数不变**，且 `equal` 块逐行**字节相同**；
  3) `replace` 块里：每一对 (old,new) 满足 `new == 对 old 施加同一张替换表`，
     且 **old 行必含至少一个禁用码位**（=> 不存在「无故改动」的行）。
"""
import difflib, hashlib, io, os, shutil, sys, time

BANMAP = [('\u21d2', '=>'), ('\u2192', '->'), ('\u2014', '--'), ('\u2013', '-'), ('\u2026', '...'),
          ('\u2265', '>='), ('\u2264', '<='), ('\u2260', '!='), ('\u2212', '-'), ('\u00d7', 'x')]
BANC = [a for a, _ in BANMAP]
BAKDIR = r'D:/workbuddy/_z_rk81/_bak_w709'
os.makedirs(BAKDIR, exist_ok=True)
TS = time.strftime('%Y%m%d_%H%M%S')


def apply_map(s):
    for a, b in BANMAP:
        s = s.replace(a, b)
    return s


def selfprove(old_text, new_text, tag, region=None):
    if region is not None:
        a, b = old_text[region[0]:region[1]], new_text[region[0]:region[1]]
    else:
        a, b = old_text, new_text
    assert not any(c in b for c in BANC), 'STILL_BANNED %s: %s' % (tag, [hex(ord(c)) for c in BANC if c in b])
    ol, nl = a.split('\n'), b.split('\n')
    assert len(ol) == len(nl), 'LINE_COUNT_DRIFT %s %d->%d' % (tag, len(ol), len(nl))
    changed = 0
    for tg, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ol, nl).get_opcodes():
        if tg == 'equal':
            assert ol[i1:i2] == nl[j1:j2], 'EQUAL_BLOCK_DRIFT %s' % tag
            continue
        assert i2 - i1 == j2 - j1, 'BLOCK_LEN_DRIFT %s' % tag
        for o, n in zip(ol[i1:i2], nl[j1:j2]):
            assert any(c in o for c in BANC), 'CHANGED_LINE_WITHOUT_BAN %s: %r' % (tag, o[:80])
            assert n == apply_map(o), 'UNEXPECTED_CHANGE %s: %r -> %r' % (tag, o[:60], n[:60])
            changed += 1
    return changed


def fix_whole(path, tag):
    raw = open(path, 'rb').read()
    shutil.copy2(path, os.path.join(BAKDIR, '%s.%s.bak_%s' % (tag, os.path.basename(path), TS)))
    old = raw.decode('utf-8')
    new = apply_map(old)
    if old == new:
        print('  %-30s 无需修改' % os.path.basename(path)); return
    n = selfprove(old, new, tag)
    nb = new.encode('utf-8')
    assert nb.count(b'\r') == raw.count(b'\r'), 'CR_DRIFT'
    open(path, 'wb').write(nb)
    print('  %-30s %s: %d->%d B  CR=%d  改动行=%d  SELF_PROVE_OK' % (
        os.path.basename(path), tag, len(raw), len(nb), nb.count(b'\r'), n))


def fix_tail(path, anchor, tag):
    raw = open(path, 'rb').read()
    shutil.copy2(path, os.path.join(BAKDIR, '%s.%s.bak_%s' % (tag, os.path.basename(path), TS)))
    old = raw.decode('utf-8')
    i = old.find(anchor)
    assert i > 0, 'ANCHOR_NOT_FOUND'
    seg_old = old[i:]
    seg_new = apply_map(seg_old)
    n = selfprove(seg_old, seg_new, tag)
    new = old[:i] + seg_new
    nb = new.encode('utf-8')
    # 前缀（锚点之前）必须逐字节不变
    p = len(old[:i].encode('utf-8'))
    assert nb[:p] == raw[:p], 'PREFIX_CHANGED'
    assert nb.count(b'\r') == raw.count(b'\r'), 'CR_DRIFT'
    open(path, 'wb').write(nb)
    print('  %-30s %s 增量段: 改动行=%d  前缀逐字节不变  CR=%d  SELF_PROVE_OK' % (
        os.path.basename(path), tag, n, nb.count(b'\r')))


if __name__ == '__main__':
    print('=== A/B) 工件 ===')
    fix_whole(r'D:/strata166/params/PARAM_REGISTER.tsv', 'register')
    fix_whole(r'D:/strata166/params/gen_config.py', 'genconfig')
    fix_whole(r'D:/strata166/params/verify_config.py', 'verifier')
    print('=== C) 记忆日志的增量段（## W709a 起）===')
    fix_tail(r'D:/workbuddy/.workbuddy/memory/2026-10-08.md', '## W709a', 'memory')
    print('=== D) 本机补 evidence 副本 ===')
    src = r'D:/workbuddy/_z_rk81/_w709_calib_out.json'
    dst = r'D:/strata166/params/evidence/w709_calib_out.json'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    b = open(dst, 'rb').read()
    print('  %d B md5=%s' % (len(b), hashlib.md5(b).hexdigest()))
    print()
    print('=== 复验 ===')
    for p in [r'D:/strata166/params/PARAM_REGISTER.tsv', r'D:/strata166/params/gen_config.py',
              r'D:/strata166/params/verify_config.py', r'D:/workbuddy/.workbuddy/memory/2026-10-08.md']:
        b = open(p, 'rb').read(); t = b.decode('utf-8', 'replace')
        ban = {hex(ord(k)): t.count(k) for k in BANC if t.count(k)}
        print('  %-30s %8d B md5=%s CR=%3d BAN=%s' % (os.path.basename(p), len(b), hashlib.md5(b).hexdigest()[:16], b.count(b'\r'), ban or 'CLEAN'))
