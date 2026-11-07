# -*- coding: utf-8 -*-
"""决定性核实：本地树 vs 官方源码 zip 逐文件哈希比对 + 我额外加进去的东西（排除 llama.cpp / venv）"""
import os, sys, zipfile, hashlib, time
sys.stdout.reconfigure(encoding='utf-8')

LOCAL = r'D:\Strata\src\Strata-0.1.39'
ZIP   = r'D:\strata166\transfer\strata-src-0.1.39.zip'

def h(b): return hashlib.md5(b).hexdigest()

zf = zipfile.ZipFile(ZIP)
entries = [n for n in zf.namelist() if not n.startswith('__MACOSX') and not n.endswith('/')]
print('zip 条目数 =', len(entries))

# ---------- 1) 逐文件哈希：zip 里有、本地也有 → 比内容 ----------
same = diff = missing = 0
diffs = []
for n in entries:
    rel = n.split('/', 1)[-1]
    if not rel:
        continue
    lp = os.path.join(LOCAL, rel.replace('/', os.sep))
    if not os.path.exists(lp):
        missing += 1
        continue
    zb = zf.read(n)
    lb = open(lp, 'rb').read()
    if h(zb) == h(lb):
        same += 1
    else:
        diff += 1
        diffs.append((rel, len(zb), len(lb)))

print()
print('=' * 78)
print('① zip 内文件在本地是否被改动过')
print('=' * 78)
print('  逐字节相同 = %d ； 内容不同 = %d ； 本地缺失 = %d' % (same, diff, missing))
if diffs:
    print('  --- 有差异的文件（这些才是"我改过的源码"）---')
    for rel, zs, ls in diffs[:60]:
        print('    %-70s zip=%d B  local=%d B' % (rel[:70], zs, ls))
else:
    print('  ⇒ **官方 zip 里的每一个文件，在本地都逐字节未改**')

# ---------- 2) 我额外加进去的东西（排除 vendored llama.cpp 与 venv） ----------
znorm = set(n.split('/', 1)[-1] for n in entries)
SKIP = ('third_party/llama.cpp/', '.venv/', '__pycache__/', '.git/')
extra = []
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
    for x in files:
        full = os.path.join(root, x)
        rel = os.path.relpath(full, LOCAL).replace('\\', '/')
        if rel in znorm or rel.startswith(SKIP):
            continue
        try: sz = os.path.getsize(full)
        except Exception: sz = -1
        extra.append((rel, sz, os.path.getmtime(full)))
extra.sort(key=lambda r: -r[2])
print()
print('=' * 78)
print('② 本地有、官方 zip 没有的条目（排除 third_party/llama.cpp 与 .venv）')
print('=' * 78)
print('  条目数 =', len(extra))
for rel, sz, mt in extra:
    print('   %10d B  %s  %s' % (sz, time.strftime('%m-%d %H:%M', time.localtime(mt)), rel[:110]))

# ---------- 3) 补丁脚本的代码部分（去掉 docstring，看它实际动什么） ----------
print()
print('=' * 78)
print('③ 补丁脚本的实际代码（docstring 之后的部分）')
print('=' * 78)
ps = r'D:\strata166\docker\patch_hipcompat.py'
src = open(ps, encoding='utf-8').read()
i = src.find('"""', src.find('"""') + 3)
print(src[i + 3:].strip()[:4000])
