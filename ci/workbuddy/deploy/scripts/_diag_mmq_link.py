# -*- coding: utf-8 -*-
"""定位 mul_mat_q_case 的定义/实例化 guard，并 diff 0.1.39 / 0.1.40.1 的 mmq 构建块。"""
import os, re, sys, difflib
sys.stdout.reconfigure(encoding='utf-8')

A = r'D:\Strata\src\Strata-0.1.39'                      # 0.1.39（能编过）
B = r'D:\strata166\tmp\src401\Strata-0.1.40.1'          # 0.1.40.1（链接失败）
LLAMA = 'third_party/llama.cpp'

print('=' * 74)
print('1) mul_mat_q_case 的定义与显式实例化（llama.cpp 内）')
print('=' * 74)
for rel in ['ggml/src/ggml-cuda/mmq.cuh', 'ggml/src/ggml-cuda/mmq.cu',
            'ggml/src/ggml-cuda/mmq-instance-q6_k.cu', 'ggml/src/ggml-cuda/mmq-instance-q4_k.cu']:
    p = os.path.join(A, LLAMA, rel)
    if not os.path.exists(p):
        print('  [无] %s' % rel)
        continue
    t = open(p, encoding='utf-8', errors='replace').read()
    print('  [有] %-46s %6d B' % (rel, len(t)))
    for i, ln in enumerate(t.splitlines(), 1):
        if 'mul_mat_q_case' in ln or re.match(r'\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b', ln) and 'MMQ' in ln:
            print('        %-5d %s' % (i, ln.strip()[:130]))

print()
print('=' * 74)
print('2) ggml-cuda/mmq-instance-*.cu 文件清单（两版 llama.cpp 相同，仅确认）')
print('=' * 74)

print()
print('=' * 74)
print('3) CMakeLists.txt 里 mmq 相关块 diff（0.1.39 -> 0.1.40.1）')
print('=' * 74)


def mmq_block(root):
    p = os.path.join(root, 'CMakeLists.txt')
    t = open(p, encoding='utf-8', errors='replace').read().splitlines()
    out = []
    for i, ln in enumerate(t, 1):
        if 'MMQ' in ln or 'mmq' in ln or 'strata_mmq' in ln:
            out.append('%5d| %s' % (i, ln))
    return out


a, b = mmq_block(A), mmq_block(B)
print('  0.1.39 命中 %d 行 / 0.1.40.1 命中 %d 行' % (len(a), len(b)))
print('  --- 逐行 diff（去掉行号比对文本）---')


def strip_no(x):
    return re.sub(r'^\s*\d+\| ', '', x)


sa = [strip_no(x) for x in a]
sb = [strip_no(x) for x in b]
for ln in difflib.unified_diff(sa, sb, lineterm='', n=2, fromfile='0.1.39', tofile='0.1.40.1'):
    print('  ' + ln[:175])
