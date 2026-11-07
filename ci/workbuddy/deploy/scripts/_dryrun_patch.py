# -*- coding: utf-8 -*-
"""dry-run 验证 patch_gfx906.py：对 0.1.39 与 0.1.40.1 两棵树各跑两遍（验幂等 + fail-closed）"""
import os, shutil, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

PY = r'C:\Users\clyde\.workbuddy\binaries\python\versions\3.13.12\python.exe'
PATCH = r'D:\strata166\docker\patch_gfx906.py'
SRC39 = r'D:\Strata\src\Strata-0.1.39'
FETCH = r'D:\strata166\upstream\v0.1.40.1'
BASE = r'D:\strata166\upstream\_dryrun'

MAP401 = {
    'include__strata__platform__hip_compat__strata_hip.h': 'include/strata/platform/hip_compat/strata_hip.h',
    'src__kernels__cuda__fused_gr.cu': 'src/kernels/cuda/fused_gr.cu',
    'src__core__mtp.cpp': 'src/core/mtp.cpp',
    'src__core__vmm.cpp': 'src/core/vmm.cpp',
}
MAP39 = ['include/strata/platform/hip_compat/strata_hip.h',
         'src/kernels/cuda/fused_gr.cu',
         'src/core/mtp.cpp']

def build_tree(name, kind):
    root = os.path.join(BASE, name)
    if os.path.exists(root):
        shutil.rmtree(root)
    if kind == '401':
        for flat, rel in MAP401.items():
            sp = os.path.join(FETCH, flat)
            dp = os.path.join(root, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copy2(sp, dp)
    else:
        for rel in MAP39:
            sp = os.path.join(SRC39, rel.replace('/', os.sep))
            dp = os.path.join(root, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copy2(sp, dp)
    return root

def run(root, label):
    print('-' * 74)
    print('>>> %s   [root=%s]' % (label, root))
    r = subprocess.run([PY, PATCH, '--root', root], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    print(r.stdout.rstrip())
    if r.stderr.strip():
        print('  [stderr]', r.stderr.strip()[:400])
    print('  rc =', r.returncode)
    return r.returncode

ok = True
for kind, label in [('39', 'v0.1.39 树'), ('401', 'v0.1.40.1 树')]:
    root = build_tree('t' + kind, kind)
    rc1 = run(root, label + ' 第 1 遍')
    rc2 = run(root, label + ' 第 2 遍（幂等检查）')
    if rc1 != 0:
        ok = False
    if rc2 != 0:
        ok = False
        print('  [!] 第 2 遍非 0 —— 幂等失败')

# 反向测试：故意把锚点改坏，应 FAIL-CLOSED
print('-' * 74)
print('>>> 反向测试：把 fused_gr.cu 的锚点改坏，期望 rc != 0')
root = build_tree('tbad', '401')
p = os.path.join(root, 'src', 'kernels', 'cuda', 'fused_gr.cu')
s = open(p, encoding='utf-8').read().replace('        return;\n    }\n#endif', '        return true;\n    }\n#endif')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
rc = run(root, '坏锚点')
if rc == 0:
    ok = False
    print('  [!] 坏锚点竟然通过了 —— fail-closed 失效！')
else:
    print('  [OK] 坏锚点被拦下（rc=%d），fail-closed 生效' % rc)

print()
print('=' * 74)
print('DRY_RUN_RESULT =', 'ALL_OK' if ok else 'FAILED')
