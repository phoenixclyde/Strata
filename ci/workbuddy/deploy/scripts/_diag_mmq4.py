# -*- coding: utf-8 -*-
"""原文级读取：CMakeLists 的 mmq 块 + llama.cpp mmq.cu 的 guard。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

A = r'D:\Strata\src\Strata-0.1.39'
B = r'D:\strata166\tmp\src401\Strata-0.1.40.1'


def show(path, lo, hi, tag):
    t = open(path, encoding='utf-8', errors='replace').read().splitlines()
    print('=' * 76)
    print('%s   %s   lines %d-%d  (total %d)' % (tag, path.split('Strata-')[-1], lo, hi, len(t)))
    print('=' * 76)
    for i in range(lo - 1, min(hi, len(t))):
        print('%5d| %s' % (i + 1, t[i][:165]))


# 1) 0.1.40.1 的 mmq 块
tb = open(os.path.join(B, 'CMakeLists.txt'), encoding='utf-8', errors='replace').read().splitlines()
idx = [i for i, ln in enumerate(tb, 1) if 'strata_mmq' in ln or 'MMQ_KQUANTS' in ln]
lo = max(1, min(idx) - 12)
hi = max(idx) + 12
show(os.path.join(B, 'CMakeLists.txt'), lo, hi, '[0.1.40.1]')

# 2) 0.1.39 的同名块
ta = open(os.path.join(A, 'CMakeLists.txt'), encoding='utf-8', errors='replace').read().splitlines()
idx2 = [i for i, ln in enumerate(ta, 1) if 'strata_mmq' in ln or 'MMQ_KQUANTS' in ln]
lo2 = max(1, min(idx2) - 8)
hi2 = max(idx2) + 8
show(os.path.join(A, 'CMakeLists.txt'), lo2, hi2, '[0.1.39]')

# 3) llama.cpp mmq.cu 的 guard
L = os.path.join(A, 'third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cu')
t = open(L, encoding='utf-8', errors='replace').read().splitlines()
print('=' * 76)
print('[llama.cpp] mmq.cu 全文件（%d 行）里的所有预处理指令' % len(t))
print('=' * 76)
for i, ln in enumerate(t, 1):
    if re.match(r'\s*#\s*(if|ifdef|ifndef|elif|else|endif|define|include)\b', ln):
        print('%5d| %s' % (i, ln.strip()[:150]))
print()
print('--- mmq.cu 1..30 ---')
for i, ln in enumerate(t[:30], 1):
    print('%5d| %s' % (i, ln[:150]))
print()
print('--- mmq.cu 82..120（switch 之后）---')
for i in range(81, min(120, len(t))):
    print('%5d| %s' % (i + 1, t[i][:150]))
