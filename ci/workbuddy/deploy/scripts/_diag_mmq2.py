# -*- coding: utf-8 -*-
"""看清 _strata_mmq 指向哪、q6_k 实例文件内容、以及 llama.cpp mmq.cu/cuh 的 guard。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

A = r'D:\Strata\src\Strata-0.1.39'
B = r'D:\strata166\tmp\src401\Strata-0.1.40.1'

cm = open(os.path.join(B, 'CMakeLists.txt'), encoding='utf-8', errors='replace').read()
print('=' * 74)
print('1) _strata_mmq / _strata_gg 的定义')
print('=' * 74)
for m in re.finditer(r'^\s*set\((_strata_mmq|_strata_gg)\b.*$', cm, re.M):
    print('  ', m.group(0).strip()[:170])

print()
print('=' * 74)
print('2) template-instances 目录清单（0.1.40.1）')
print('=' * 74)
cand = []
for root, d, f in os.walk(B):
    if root.endswith('template-instances'):
        cand.append(root)
        for x in sorted(f):
            p = os.path.join(root, x)
            print('  %-42s %7d B' % (x, os.path.getsize(p)))
        print('  (dir:', root, ')')
if not cand:
    print('  !! 未找到 template-instances 目录')

print()
print('=' * 74)
print('3) mmq-instance-q6_k.cu 全文（若有）')
print('=' * 74)
for root in cand:
    p = os.path.join(root, 'mmq-instance-q6_k.cu')
    if os.path.exists(p):
        print(open(p, encoding='utf-8', errors='replace').read())
    p2 = os.path.join(root, 'mmq-instance-q4_k.cu')
    if os.path.exists(p2):
        print('--- 对照 mmq-instance-q4_k.cu ---')
        print(open(p2, encoding='utf-8', errors='replace').read())

print()
print('=' * 74)
print('4) llama.cpp mmq.cu 前 100 行（看 switch 的 guard）')
print('=' * 74)
p = os.path.join(B, 'third_party/llama.cpp/ggml/src/ggml-cuda/mmq.cu')
t = open(p, encoding='utf-8', errors='replace').read().splitlines()
for i, ln in enumerate(t[:100], 1):
    print('  %-5d %s' % (i, ln[:150]))
