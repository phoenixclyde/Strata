# -*- coding: utf-8 -*-
"""从 0.1.40.1 zip 里读它钉的 llama.cpp commit 与其它常量，判断是否要重下依赖"""
import re, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')
Z = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
z = zipfile.ZipFile(Z)
names = z.namelist()

def member(rel):
    hit = [n for n in names if n.endswith('/' + rel)]
    return z.read(hit[0]).decode('utf-8', 'replace') if hit else ''

s = member('setup.py')
print('setup.py 行数 =', len(s.splitlines()))
print()
print('=== 含 llama / commit / zip / tar 的常量行 ===')
for ln in s.splitlines():
    if re.search(r'(LLAMA|llama\.cpp|commit|3cf0325|ZIP\b|TARBALL)', ln) and ('=' in ln or 'http' in ln):
        t = ln.strip()
        if len(t) < 200 and re.search(r'(LLAMA|commit|3cf0325|http)', t):
            print('  ', t[:190])
print()
print('=== 版本 / 模型常量 ===')
for ln in s.splitlines():
    if re.match(r'^\s*(VERSION|STRATA_VERSION|DEFAULT_MODEL|MODELS)\b', ln) or 'version' in ln.lower() and '=' in ln and len(ln) < 120:
        print('  ', ln.strip()[:160])
print()
print('=== requirements.txt（看 python 依赖有无变化）===')
print(member('requirements.txt')[:800])
print()
print('=== serve/ 目录文件数 ===')
print('  serve/*.py :', len([n for n in names if '/serve/' in n and n.endswith('.py')]))
print()
print('=== CMakeLists 里 gfx906 / MMQ 相关仍在否 ===')
c = member('CMakeLists.txt')
for pat in ['STRATA_HIP_GFX906', 'STRATA_MMQ_KQUANTS', 'STRATA_PREFILL_MMQ', '_strata_mmq_types']:
    print('  %-24s 出现 %d 次' % (pat, c.count(pat)))
