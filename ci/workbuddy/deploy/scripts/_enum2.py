# -*- coding: utf-8 -*-
"""从 generate.cpp 枚举全部预填相关选项 + 定位预填分解行打印条件（0.1.40.1）。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:\strata166\tmp\src401_pristine\Strata-0.1.40.1'
GEN = os.path.join(ROOT, 'src', 'program', 'generate.cpp')
g = open(GEN, encoding='utf-8', errors='replace').read()
gl = g.splitlines()

print('=' * 80)
print('1) 选项定义（以 "o." 开头 或 add/register 调用，含预填类关键词）')
print('=' * 80)
KW = ('prefill', 'ple', 'ring', 'thread', 'pool', 'worker', 'vram', 'reserve',
      'chunk', 'adapt', 'shared', 'pcie', 'stats', 'native', 'dense', 'resident')
seen = set()
for i, ln in enumerate(gl, 1):
    s = ln.strip()
    if not s.startswith('o.'):
        continue
    low = s.lower()
    if not any(k in low for k in KW):
        continue
    blk = ' '.join(x.strip() for x in gl[i - 1:i + 3])[:230]
    if blk in seen:
        continue
    seen.add(blk)
    print('  %-6d %s' % (i, blk))

print()
print('=' * 80)
print('2) 预填分解行（"in %d chunks"）的上下文与条件')
print('=' * 80)
for i, ln in enumerate(gl, 1):
    if re.search(r'chunks[,)]|in %d chunks|%d chunks', ln) and 'ms' in ln:
        for j in range(max(0, i - 26), min(len(gl), i + 5)):
            print('  %-6d %s' % (j + 1, gl[j][:165]))
        print('  ' + '-' * 72)
        break

print()
print('=' * 80)
print('3) 所有 "stats" 门与其打印内容')
print('=' * 80)
for i, ln in enumerate(gl, 1):
    if re.search(r'o\.stats|ms_ple|ms_layers|stage-timing', ln):
        print('  %-6d %s' % (i, ln.strip()[:165]))

print()
print('=' * 80)
print('4) PLE 相关旋钮的取值校验（--ple-* 的合法域）')
print('=' * 80)
for i, ln in enumerate(gl, 1):
    if re.search(r'ple_io|ple_inflight|ple_row_cache|ple_delay|ple_rows|ple_direct', ln):
        s = ln.strip()
        if any(k in s for k in ('ok', 'err', 'invalid', 'must', 'range', '<=', '>=', 'at(')):
            print('  %-6d %s' % (i, s[:165]))
