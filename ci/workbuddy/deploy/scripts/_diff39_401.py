# -*- coding: utf-8 -*-
"""对比 0.1.39 与 0.1.40.1 在 mtp.cpp / vmm.cpp / fuse_gr 三处的差异，定 H3/H4 语义"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

S39 = r'D:\Strata\src\Strata-0.1.39'
S401 = r'D:\strata166\upstream\v0.1.40.1'

def rd(base, rel, flat=None):
    p = os.path.join(base, (flat or rel).replace('/', os.sep))
    if not os.path.exists(p):
        return None
    return open(p, encoding='utf-8', errors='replace').read().splitlines()

print('=' * 78); print('① mtp.cpp：0.1.39 vs 0.1.40.1'); print('=' * 78)
a = rd(S39, 'src/core/mtp.cpp')
b = rd(S401, '', 'src__core__mtp.cpp')
for tag, L in (('0.1.39', a), ('0.1.40.1', b)):
    if L is None:
        print('  %-9s (缺)' % tag); continue
    syms = [i + 1 for i, x in enumerate(L) if 'StreamPriorityRange' in x or 'StreamCreateWithPriority' in x]
    gates = [i + 1 for i, x in enumerate(L) if x.strip().startswith('#if') and 'STRATA_USE_HIP' in x]
    print('  %-9s 行数=%-5d priority 调用@%s  含 STRATA_USE_HIP 的 #if @%s' % (tag, len(L), syms, gates))
    for i in syms[:3]:
        for j in range(max(0, i - 5), min(len(L), i + 2)):
            print('      %5d| %s' % (j + 1, L[j][:150]))
        print('      ---')

print(); print('=' * 78); print('② vmm.cpp：0.1.39 有没有这个文件'); print('=' * 78)
p39 = os.path.join(S39, 'src', 'core', 'vmm.cpp')
print('  0.1.39 src/core/vmm.cpp exists =', os.path.exists(p39))
print('  0.1.39 src/core/ 下文件:')
d = os.path.join(S39, 'src', 'core')
if os.path.isdir(d):
    for x in sorted(os.listdir(d))[:40]:
        print('     ', x)

print(); print('=' * 78); print('③ hip_compat 头里有没有映射 StreamPriorityRange / CreateWithPriority'); print('=' * 78)
for tag, p in (('0.1.39', os.path.join(S39, 'include', 'strata', 'platform', 'hip_compat', 'strata_hip.h')),
               ('0.1.40.1', os.path.join(S401, 'include__strata__platform__hip_compat__strata_hip.h'))):
    t = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
    print('  %-9s StreamPriorityRange=%s  CreateWithPriority=%s' %
          (tag, 'cudaDeviceGetStreamPriorityRange' in t, 'cudaStreamCreateWithPriority' in t))
    for ln in t.splitlines():
        if 'StreamPriority' in ln or 'CreateWithPriority' in ln:
            print('        ', ln.strip()[:140])

print(); print('=' * 78); print('④ fused_gr.cu 的裸 return; 在 0.1.39 是否存在'); print('=' * 78)
for tag, p in (('0.1.39', os.path.join(S39, 'src', 'kernels', 'cuda', 'fused_gr.cu')),
               ('0.1.40.1', os.path.join(S401, 'src__kernels__cuda__fused_gr.cu'))):
    if not os.path.exists(p):
        print('  %-9s (缺)' % tag); continue
    t = open(p, encoding='utf-8', errors='replace').read()
    print('  %-9s 锚点 "        return;\\n    }\\n#endif" 命中 = %d' % (tag, t.count('        return;\n    }\n#endif')))

print(); print('=' * 78); print('⑤ 0.1.40.1 整包下载状态'); print('=' * 78)
zp = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
print('  zip exists=%s size=%s' % (os.path.exists(zp), os.path.getsize(zp) if os.path.exists(zp) else '-'))
lg = r'D:\strata166\logs\_dl_0.1.40.1.txt'
print(open(lg, encoding='utf-8', errors='replace').read()[-800:] if os.path.exists(lg) else '(无日志)')
