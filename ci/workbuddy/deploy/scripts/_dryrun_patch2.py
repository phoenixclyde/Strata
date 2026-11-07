# -*- coding: utf-8 -*-
"""dry-run：把补丁器 v2（含 H5）对 0.1.39 与 0.1.40.1 两棵树各跑两遍，验「正确 + 幂等 + fail-closed」。
用副本操作，绝不碰原始树。
"""
import os, sys, shutil, subprocess
sys.stdout.reconfigure(encoding='utf-8')

PY = r'C:\Users\clyde\.workbuddy\binaries\python\versions\3.13.12\python.exe'
SCRIPT = r'D:\strata166\docker\patch_gfx906.py'
TMP = r'D:\strata166\tmp'

SRC = {
    '0.1.39': r'D:\Strata\src\Strata-0.1.39',
    '0.1.40.1': r'D:\strata166\tmp\src401\Strata-0.1.40.1',
}

results = {}
for tag, orig in SRC.items():
    work = os.path.join(TMP, 'dryrun_' + tag.replace('.', '_'))
    if os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    print('=' * 74)
    print('### %s  -> 副本 %s' % (tag, work))
    print('=' * 74)
    # 只复制补丁器要用到的文件，省时间（不需要整棵树）
    needed = ['include/strata/platform/hip_compat/strata_hip.h',
              'src/kernels/cuda/fused_gr.cu',
              'src/core/mtp.cpp',
              'src/core/vmm.cpp',
              'CMakeLists.txt']
    for rel in needed:
        s = os.path.join(orig, rel.replace('/', os.sep))
        d = os.path.join(work, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.exists(s):
            shutil.copy2(s, d)
        else:
            print('   (原树缺 %s —— 保持缺失，考补丁器的 N/A 分支)' % rel)

    outs = []
    for run in (1, 2):
        r = subprocess.run([PY, SCRIPT, '--root', work] + (['--quiet'] if run == 2 else []),
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        outs.append((r.returncode, r.stdout, r.stderr))
        if run == 1:
            print('--- run1 rc=%d ---' % r.returncode)
            print(r.stdout)
            if r.stderr.strip():
                print('STDERR:', r.stderr[:400])
        else:
            print('--- run2（幂等）rc=%d  末行=%r ---'
                  % (r.returncode, (r.stdout or r.stderr).strip().splitlines()[-1][:90] if (r.stdout or r.stderr).strip() else ''))
    results[tag] = outs

# fail-closed 验证：故意改坏 CMakeLists 的锚点
print()
print('=' * 74)
print('### fail-closed 验证：把 CMakeLists 的 H5 锚点改坏后应 rc!=0')
print('=' * 74)
work = os.path.join(TMP, 'dryrun_bad')
if os.path.isdir(work):
    shutil.rmtree(work, ignore_errors=True)
for rel in ['CMakeLists.txt', 'src/core/vmm.cpp', 'include/strata/platform/hip_compat/strata_hip.h']:
    s = os.path.join(SRC['0.1.40.1'], rel.replace('/', os.sep))
    d = os.path.join(work, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d)
p = os.path.join(work, 'CMakeLists.txt')
t = open(p, encoding='utf-8').read()
t2 = t.replace('if(STRATA_Q6K_EXPERTS)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md)',
               'if(STRATA_Q6K_EXPERTS_BROKEN)   # mangled')
open(p, 'w', encoding='utf-8', newline='\n').write(t2)
r = subprocess.run([PY, SCRIPT, '--root', work], capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
print('rc =', r.returncode, '(应为非 0)')
print((r.stdout or '')[-700:])
print((r.stderr or '')[-500:])

print()
print('=' * 74)
print('### 汇总')
print('=' * 74)
ok = True
for tag, outs in results.items():
    r1, r2 = outs
    good1 = r1[0] == 0 and 'PATCH_V2_OK' in (r1[1] or '')
    idem = r2[0] == 0
    print('  %-9s run1=%s  run2(幂等)=%s' % (tag, 'OK' if good1 else 'FAIL rc=%d' % r1[0],
                                            'OK' if idem else 'FAIL rc=%d' % r2[0]))
    ok = ok and good1 and idem
fc = r.returncode != 0
print('  坏锚点被拦 = %s' % fc)
print('  DRY_RUN_RESULT = %s' % ('ALL_OK' if (ok and fc) else 'PROBLEM'))
