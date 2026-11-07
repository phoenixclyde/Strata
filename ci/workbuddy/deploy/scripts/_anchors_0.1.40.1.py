# -*- coding: utf-8 -*-
"""精读 0.1.40.1 的三处锚点周边 + dp4a 现状，为 v2 补丁定稿"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
D = r'D:\strata166\upstream\v0.1.40.1'

def L(n): return open(os.path.join(D, n), encoding='utf-8', errors='replace').read().splitlines()
def dump(lines, lo, hi, tag):
    print('  --- %s [%d..%d] ---' % (tag, lo, hi))
    for i in range(lo - 1, min(len(lines), hi)):
        print('  %5d| %s' % (i + 1, lines[i][:165]))

f = L('src__kernels__cuda__fused_gr.cu')
print('=' * 78); print('① fused_gr.cu：围住 :1743 的那层 #if 是什么'); print('=' * 78)
# 向上找最近的未闭合 #if
depth = 0; opens = []
for i in range(1742, -1, -1):
    s = f[i].strip()
    if s.startswith('#endif'): depth += 1
    elif s.startswith('#if'):
        if depth == 0:
            opens.append((i + 1, s))
            break
        depth -= 1
print('  最近的未闭合 #if ->', opens)
for lo, hi in [(1700, 1750), (1600, 1625)]:
    dump(f, lo, hi, 'fused_gr.cu')

print(); print('=' * 78); print('② mtp.cpp :418 门'); print('=' * 78)
m = L('src__core__mtp.cpp')
dump(m, 415, 425, 'mtp.cpp')
print('  全文件里 `#if !defined(STRATA_USE_HIP)` 出现次数 =',
      sum(1 for x in m if x.strip().startswith('#if !defined(STRATA_USE_HIP)')))
for i, x in enumerate(m):
    if x.strip().startswith('#if !defined(STRATA_USE_HIP)'):
        print('    :%-5d %s' % (i + 1, x.strip()[:120]))

print(); print('=' * 78); print('③ vmm.cpp 全文（164 行，看 #else 分支）'); print('=' * 78)
v = L('src__core__vmm.cpp')
dump(v, 1, 12, 'head')
print('  ...')
for i, x in enumerate(v):
    if x.strip().startswith('#el') or x.strip().startswith('#endif') or x.strip().startswith('#if'):
        print('  %5d| %s' % (i + 1, x.strip()[:150]))
dump(v, 150, 164, 'tail')

print(); print('=' * 78); print('④ intrinsics.hpp：dp4a 条件（#1084）'); print('=' * 78)
it = L('include__strata__hip_compat__intrinsics.hpp')
for i, x in enumerate(it):
    if 'sdot4' in x or 'sudot4' in x or 'gfx' in x.lower() or 'dp4a' in x.lower():
        print('  %5d| %s' % (i + 1, x.strip()[:165]))
