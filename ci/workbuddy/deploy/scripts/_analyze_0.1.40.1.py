# -*- coding: utf-8 -*-
"""分析 v0.1.40.1 的三个 gfx906 构建门（PR #1083）与 dp4a 条件（PR #1084），定位精确锚点"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')

D = r'D:\strata166\upstream\v0.1.40.1'
print(open(os.path.join(D, '_fetch.txt'), encoding='utf-8').read())
print()

def load(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return None
    return open(p, encoding='utf-8', errors='replace').read().splitlines()

def show(lines, lo, hi, tag):
    print('  --- %s  [%d..%d] ---' % (tag, lo, hi))
    for i in range(max(0, lo - 1), min(len(lines), hi)):
        print('   %5d| %s' % (i + 1, lines[i][:170]))

# ================= 1) fused_gr.cu：裸 return; =================
L = load('src__kernels__cuda__fused_gr.cu')
print('=' * 78); print('① fused_gr.cu  (PR #1083 第 1 处)'); print('=' * 78)
if L:
    print('  行数 =', len(L))
    for i, ln in enumerate(L):
        if 'fused_gr_read_multi' in ln:
            print('   :%-5d %s' % (i + 1, ln.strip()[:150]))
    for i, ln in enumerate(L):
        if re.match(r'^\s*return;\s*$', ln):
            lo = max(0, i - 14)
            print('   >>> 命中裸 return; 于 :%d' % (i + 1))
            show(L, lo, i + 3, 'context')
    print('  --- 该函数内的 #if 门 ---')
    s = None
    for i, ln in enumerate(L):
        if 'fused_gr_read_multi' in ln and '(' in ln:
            s = i; break
    if s is not None:
        for i in range(s, min(len(L), s + 80)):
            if L[i].lstrip().startswith('#if') or L[i].lstrip().startswith('#el'):
                print('   :%-5d %s' % (i + 1, L[i].strip()[:140]))
else:
    print('  (文件未取到)')

# ================= 2) mtp.cpp =================
L = load('src__core__mtp.cpp')
print(); print('=' * 78); print('② mtp.cpp  (PR #1083 第 2 处)'); print('=' * 78)
if L:
    print('  行数 =', len(L))
    hits = [i for i, ln in enumerate(L) if 'StreamPriorityRange' in ln or 'StreamCreateWithPriority' in ln]
    for i in hits:
        show(L, i - 12, i + 6, 'stream priority')
    for i, ln in enumerate(L):
        if 'STRATA_USE_HIP' in ln or 'STRATA_HIP_GFX906' in ln:
            print('   :%-5d %s' % (i + 1, ln.strip()[:150]))
else:
    print('  (文件未取到)')

# ================= 3) vmm.cpp =================
L = load('src__core__vmm.cpp')
print(); print('=' * 78); print('③ vmm.cpp  (PR #1083 第 3 处，0.1.40 新增)'); print('=' * 78)
if L:
    print('  行数 =', len(L))
    for i in range(0, min(len(L), 40)):
        print('   %5d| %s' % (i + 1, L[i][:170]))
else:
    print('  (文件未取到)')

# ================= 4) intrinsics.hpp dp4a =================
L = load('include__strata__hip_compat__intrinsics.hpp')
print(); print('=' * 78); print('④ intrinsics.hpp  dp4a 条件（PR #1084）'); print('=' * 78)
if L:
    print('  行数 =', len(L))
    for i, ln in enumerate(L):
        if 'dp4a' in ln.lower() or 'sdot4' in ln or 'sudot4' in ln or 'gfx' in ln:
            print('   :%-5d %s' % (i + 1, ln.strip()[:160]))
else:
    print('  (文件未取到)')
