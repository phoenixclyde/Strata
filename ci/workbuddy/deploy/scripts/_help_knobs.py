# -*- coding: utf-8 -*-
"""抄出关键开关的帮助原文（照着帮助写参数，不凭印象）。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:\strata166\tmp\src401_pristine\Strata-0.1.40.1'
GEN = os.path.join(ROOT, 'src', 'program', 'generate.cpp')
gl = open(GEN, encoding='utf-8', errors='replace').read().splitlines()

WANT = ['--prefill', '--no-split-rows', '--no-prefill-borrow', '--vram-reserve',
        '--shared-late', '--pool-workers', '--tokens', '--stats', '--stage-timing',
        '--max-tokens', '--generate', '--serve', '--ple-', '--ngram', '--draft']


def block_at(i):
    """从帮助行 i 起，收集连续的 C 字符串续行。"""
    out = []
    j = i
    while j < len(gl) and (gl[j].strip().startswith('"') or 'std::fprintf' in gl[j] or 'printf(' in gl[j]):
        s = gl[j].strip()
        m = re.findall(r'"([^"]*)"', s)
        if m:
            out.append(''.join(m))
        else:
            out.append(s[:120])
        j += 1
        if len(out) > 6:
            break
    return out


print('=' * 82)
print('帮助文本（按开关名定位）')
print('=' * 82)
for i, ln in enumerate(gl, 1):
    s = ln.strip()
    if not s.startswith('"'):
        continue
    for w in WANT:
        if s.startswith('"' + w) or ('"  ' + w) in s or w in s and s.lstrip('"').startswith(w):
            blk = block_at(i - 1)
            txt = ' '.join(blk)[:300]
            print('\n  [%s]  行 %d' % (w, i))
            print('    ' + txt)
            break

print()
print('=' * 82)
print('选项解析点（确认这些开关真的被解析）')
print('=' * 82)
for i, ln in enumerate(gl, 1):
    for w in ['--no-split-rows', '--no-prefill-borrow', '--vram-reserve-later-mib',
              '--shared-late', '--pool-workers', '--stage-timing', '--stats']:
        if 'a == "%s"' % w in ln:
            print('  %-26s -> 行 %d' % (w, i))
