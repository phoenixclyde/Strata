# -*- coding: utf-8 -*-
"""本地复现 docker build 第 8 步（补丁 + grep 复核），定位失败的确切命令。"""
import os, sys, shutil, zipfile, subprocess

sys.stdout.reconfigure(encoding='utf-8')

ZIP = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
ROOT = r'D:\strata166\tmp\src401'
SCRIPT = r'D:\strata166\docker\patch_gfx906.py'
PY = r'C:\Users\clyde\.workbuddy\binaries\python\versions\3.13.12\python.exe'

if os.path.isdir(ROOT):
    shutil.rmtree(ROOT, ignore_errors=True)
os.makedirs(ROOT, exist_ok=True)

z = zipfile.ZipFile(ZIP)
z.extractall(ROOT)
inner = os.path.join(ROOT, os.listdir(ROOT)[0])
print('inner =', inner)

# --- 1) 跑补丁脚本（与容器内完全同一文件）---
print('=' * 70)
print('STEP A: python3 patch_gfx906.py --root <tree>')
print('=' * 70)
r = subprocess.run([PY, SCRIPT, '--root', inner], capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
print('rc =', r.returncode)
print('--- stdout ---')
print(r.stdout)
print('--- stderr ---')
print(r.stderr)

# --- 2) 复核：容器里那 4 条 grep（用 Git Bash 的 grep 语义跑）---
print('=' * 70)
print('STEP B: 复核 grep')
print('=' * 70)
checks = [
    ('inline hipError_t cudaFuncSetAttribute',
     os.path.join(inner, 'include/strata/platform/hip_compat/strata_hip.h')),
    ('return false;   // no q8_1 either',
     os.path.join(inner, 'src/kernels/cuda/fused_gr.cu')),
    ('STRATA_HIP_GFX906)   // (HIP and gfx906',
     os.path.join(inner, 'src/core/mtp.cpp')),
    ('STRATA_HIP_GFX906)',
     os.path.join(inner, 'src/core/vmm.cpp')),
]
for needle, path in checks:
    ex = os.path.exists(path)
    if not ex:
        print('  FILE-MISSING  %s' % path)
        continue
    n = 0
    for i, ln in enumerate(open(path, encoding='utf-8', errors='replace').read().splitlines(), 1):
        if needle in ln:
            n += 1
            if n <= 2:
                print('  HIT %s:%d  %s' % (os.path.basename(path), i, ln.strip()[:110]))
    print('  -> %-46s hits=%d  (%s)' % (os.path.basename(path), n, needle[:40]))

# --- 3) 相关文件是否真在预期路径 ---
print('=' * 70)
print('STEP C: 路径盘点')
print('=' * 70)
for rel in ['include/strata/platform/hip_compat/strata_hip.h',
            'src/kernels/cuda/fused_gr.cu',
            'src/core/mtp.cpp',
            'src/core/vmm.cpp',
            'data/expert-profile.bin']:
    p = os.path.join(inner, rel)
    print('  %-58s %s' % (rel, ('OK %d B' % os.path.getsize(p)) if os.path.exists(p) else 'MISSING'))
