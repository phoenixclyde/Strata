# -*- coding: utf-8 -*-
"""枚举引擎全部与预填相关的选项 + 定位预填分解行的打印条件。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:\strata166\tmp\src401_pristine\Strata-0.1.40.1'
MAIN = os.path.join(ROOT, 'src', 'main.cpp')
GEN = os.path.join(ROOT, 'src', 'program', 'generate.cpp')

print('=' * 80)
print('1) main.cpp 里的选项定义（名字 / 助手里含关键词的）')
print('=' * 80)
t = open(MAIN, encoding='utf-8', errors='replace').read()
KW = ('prefill', 'ple_', 'ple-', 'ple ', 'ring', 'thread', 'pool', 'worker',
      'vram', 'reserve', 'chunk', 'adapt', 'shared', 'pcie', 'stats', 'io_', 'io-')
lines = t.splitlines()
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if not (s.startswith('o.') or 'add_option' in s or s.startswith('// --')):
        continue
    low = s.lower()
    if any(k in low for k in KW):
        # 取该行 + 后 2 行（帮助文本常续行）
        blk = ' '.join(x.strip() for x in lines[i - 1:i + 2])[:250]
        print('  %-5d %s' % (i, blk))

print()
print('=' * 80)
print('2) 预填分解行的打印条件（generate.cpp 里 "in %d chunks" 附近）')
print('=' * 80)
g = open(GEN, encoding='utf-8', errors='replace').read()
gl = g.splitlines()
for i, ln in enumerate(gl, 1):
    if 'chunks' in ln and 'prefill' in ln.lower():
        lo = max(1, i - 30)
        for j in range(lo - 1, min(len(gl), i + 4)):
            print('  %-5d %s' % (j + 1, gl[j][:160]))
        print('  ' + '-' * 70)
        break

print()
print('=' * 80)
print('3) --stats 相关：谁打印 per-stage ms')
print('=' * 80)
for i, ln in enumerate(gl, 1):
    if re.search(r'ms_ple|ms_layers|stats\b', ln):
        print('  %-5d %s' % (i, ln.strip()[:160]))
