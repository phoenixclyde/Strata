# -*- coding: utf-8 -*-
"""精筛：本地树里真正由我加入的条目（排除 engine/ 与 llama.cpp/ 与 .venv/）+ 补丁脚本代码"""
import os, sys, zipfile, time
sys.stdout.reconfigure(encoding='utf-8')

LOCAL = r'D:\Strata\src\Strata-0.1.39'
ZIP   = r'D:\strata166\transfer\strata-src-0.1.39.zip'
zf = zipfile.ZipFile(ZIP)
znorm = set(n.split('/', 1)[-1] for n in zf.namelist() if not n.endswith('/'))
SKIP = ('third_party/llama.cpp/', '.venv/', '__pycache__/', '.git/', 'engine/')

extra = []
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
    for x in files:
        full = os.path.join(root, x)
        rel = os.path.relpath(full, LOCAL).replace('\\', '/')
        if rel in znorm or rel.startswith(SKIP):
            continue
        extra.append((rel, os.path.getsize(full), os.path.getmtime(full)))
extra.sort(key=lambda r: -r[2])

print('=' * 78)
print('本地有、官方 zip 没有、且不属于 engine/llama.cpp/.venv 的条目：%d 个' % len(extra))
print('=' * 78)
for rel, sz, mt in extra:
    print('  %10d B  %s  %s' % (sz, time.strftime('%m-%d %H:%M', time.localtime(mt)), rel[:120]))

print()
print('=' * 78)
print('补丁脚本的实际代码（docstring 之后）')
print('=' * 78)
src = open(r'D:\strata166\docker\patch_hipcompat.py', encoding='utf-8').read()
d1 = src.find('"""'); d2 = src.find('"""', d1 + 3)
print(src[d2 + 3:].strip())

print()
print('=' * 78)
print('Dockerfile 全文（看补丁在哪一步、是否还有别的改动）')
print('=' * 78)
print(open(r'D:\strata166\docker\Dockerfile', encoding='utf-8').read())
