# -*- coding: utf-8 -*-
"""看 pinned llama.cpp 里 template-instances 清单、q6_k 实例内容、mmq.cuh 的实例宏与 guard。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

L = r'D:\Strata\src\Strata-0.1.39\third_party\llama.cpp\ggml\src\ggml-cuda'
TI = os.path.join(L, 'template-instances')

print('=' * 74)
print('1) template-instances 清单')
print('=' * 74)
if os.path.isdir(TI):
    for x in sorted(os.listdir(TI)):
        print('  %-40s %6d B' % (x, os.path.getsize(os.path.join(TI, x))))
else:
    print('  !! 无此目录')

print()
print('=' * 74)
print('2) mmq-instance-q6_k.cu 全文')
print('=' * 74)
p = os.path.join(TI, 'mmq-instance-q6_k.cu')
print(open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else '  (不存在)')
print('--- 对照 mmq-instance-q4_k.cu ---')
p2 = os.path.join(TI, 'mmq-instance-q4_k.cu')
print(open(p2, encoding='utf-8', errors='replace').read() if os.path.exists(p2) else '  (不存在)')

print()
print('=' * 74)
print('3) mmq.cuh 里 mul_mat_q_case 定义处 + 实例宏（1530-1600）')
print('=' * 74)
t = open(os.path.join(L, 'mmq.cuh'), encoding='utf-8', errors='replace').read().splitlines()
for i in range(1525, min(len(t), 1600)):
    print('  %-5d %s' % (i + 1, t[i][:150]))

print()
print('=' * 74)
print('4) mmq.cuh 里所有 #if/#ifdef 及其行号（看谁 guard 了实例）')
print('=' * 74)
for i, ln in enumerate(t, 1):
    if re.match(r'\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b', ln):
        print('  %-5d %s' % (i, ln.strip()[:140]))
