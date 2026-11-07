# -*- coding: utf-8 -*-
"""核实：我到底改了哪些 Strata 源码/文件（对本地树 vs 构建上下文 zip 做逐文件比对）"""
import os, sys, zipfile, hashlib, time
sys.stdout.reconfigure(encoding='utf-8')

LOCAL = r'D:\Strata\src\Strata-0.1.39'
ZIP   = r'D:\strata166\transfer\strata-src-0.1.39.zip'

def md5(b): return hashlib.md5(b).hexdigest()

print('=' * 78)
print('① 本地源码树里那处「必打补丁」的文件，现在是宏还是内联函数？')
print('=' * 78)
f = os.path.join(LOCAL, 'include', 'strata', 'platform', 'hip_compat', 'strata_hip.h')
t = open(f, encoding='utf-8', errors='replace').read()
lines = t.splitlines()
for i, ln in enumerate(lines, 1):
    if 'cudaFuncSetAttribute' in ln or 'cudaFuncAttributePreferredSharedMemoryCarveout' in ln:
        print('  本地 :%-4d %s' % (i, ln.strip()[:150]))
print('  -> 判读：出现 "#define cudaFuncSetAttribute(" = 仍是未打补丁的宏；出现 "inline hipError_t cudaFuncSetAttribute" = 已被打补丁')
print('  本地 md5 =', md5(t.encode('utf-8')), ' size =', os.path.getsize(f))

print()
print('=' * 78)
print('② 构建上下文 zip 里的同一文件（= 166 上 docker build 用的那一份）')
print('=' * 78)
zf = zipfile.ZipFile(ZIP)
names = [n for n in zf.namelist() if n.endswith('platform/hip_compat/strata_hip.h')]
print('  zip 内命中路径:', names)
if names:
    zt = zf.read(names[0]).decode('utf-8', 'replace')
    for i, ln in enumerate(zt.splitlines(), 1):
        if 'cudaFuncSetAttribute' in ln or 'cudaFuncAttributePreferredSharedMemoryCarveout' in ln:
            print('  zip  :%-4d %s' % (i, ln.strip()[:150]))
    print('  zip md5 =', md5(zt.encode('utf-8')))
    print('  两侧是否逐字节相同 =>', md5(zt.encode('utf-8')) == md5(t.encode('utf-8')))

print()
print('=' * 78)
print('③ 本地树整体：哪些文件不在 zip 里（= 我加进去的东西）')
print('=' * 78)
znorm = set(n.split('/', 1)[-1] for n in zf.namelist() if '/' in n)
extra = []
for root, dirs, files in os.walk(LOCAL):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
    for x in files:
        full = os.path.join(root, x)
        rel = os.path.relpath(full, LOCAL).replace('\\', '/')
        if rel not in znorm:
            try: sz = os.path.getsize(full)
            except Exception: sz = -1
            extra.append((rel, sz, os.path.getmtime(full)))
extra.sort(key=lambda r: -r[2])
print('  不在 zip 里的条目数 =', len(extra))
for rel, sz, mt in extra[:40]:
    print('   %8d B  %s  %s' % (sz, time.strftime('%m-%d %H:%M', time.localtime(mt)), rel[:110]))

print()
print('=' * 78)
print('④ 补丁脚本本体（它到底改什么，逐行）')
print('=' * 78)
ps = r'D:\strata166\docker\patch_hipcompat.py'
if os.path.exists(ps):
    print(open(ps, encoding='utf-8').read())
else:
    print('  (不存在)')
