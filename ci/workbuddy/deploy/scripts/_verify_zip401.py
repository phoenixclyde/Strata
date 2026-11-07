# -*- coding: utf-8 -*-
"""校验 0.1.40.1 源码 zip：结构 + 与 API 单文件逐字节对拍 + 三处补丁锚点是否存在"""
import hashlib, os, sys, zipfile
sys.stdout.reconfigure(encoding='utf-8')

ZIP = r'D:\strata166\transfer\strata-src-0.1.40.1.zip'
FETCH = r'D:\strata166\upstream\v0.1.40.1'
print('zip size =', os.path.getsize(ZIP))

z = zipfile.ZipFile(ZIP)
bad = z.testzip()
print('testzip (None=OK) =', bad)
names = [n for n in z.namelist() if not n.endswith('/')]
roots = sorted({n.split('/', 1)[0] for n in z.namelist()})
print('顶层:', roots)
print('条目数 =', len(names))

# 关键文件
KEY = ['src/core/vmm.cpp', 'src/core/mtp.cpp', 'src/kernels/cuda/fused_gr.cu',
       'include/strata/platform/hip_compat/strata_hip.h', 'CMakeLists.txt',
       'serve/server.py', 'tools/mtp_pack.py', 'docs/AMD_HIP.md', 'setup.py']
print()
print('关键文件存在性:')
for k in KEY:
    hit = [n for n in names if n.endswith('/' + k)]
    print('  %-52s %s' % (k, hit[0] if hit else '**缺失**'))

# 与 API 单文件对拍
print()
print('与 API 单文件逐字节对拍:')
pairs = {
    'include__strata__platform__hip_compat__strata_hip.h': 'include/strata/platform/hip_compat/strata_hip.h',
    'src__kernels__cuda__fused_gr.cu': 'src/kernels/cuda/fused_gr.cu',
    'src__core__mtp.cpp': 'src/core/mtp.cpp',
    'src__core__vmm.cpp': 'src/core/vmm.cpp',
}
for flat, rel in pairs.items():
    fp = os.path.join(FETCH, flat)
    hit = [n for n in names if n.endswith('/' + rel)]
    if not os.path.exists(fp) or not hit:
        print('  %-52s (缺一侧)' % rel); continue
    a = hashlib.md5(open(fp, 'rb').read()).hexdigest()
    b = hashlib.md5(z.read(hit[0])).hexdigest()
    print('  %-52s %s  %s' % (rel, 'SAME' if a == b else '**DIFF**', a[:12]))

# 三处锚点
print()
print('补丁锚点存在性（在 zip 内的真实内容上检查）:')
def member(rel):
    hit = [n for n in names if n.endswith('/' + rel)]
    return z.read(hit[0]).decode('utf-8', 'replace') if hit else ''

t = member('include/strata/platform/hip_compat/strata_hip.h')
print('  H1 已修(内联函数) =', 'inline hipError_t cudaFuncSetAttribute' in t,
      ' | carveout 映射 =', 'cudaFuncAttributePreferredSharedMemoryCarveout' in t)
t = member('src/kernels/cuda/fused_gr.cu')
print('  H2 裸 return; 锚点 =', t.count('        return;\n    }\n#endif'), '次')
t = member('src/core/mtp.cpp')
print('  H3 门锚点 =', t.count('#if !defined(STRATA_USE_HIP)   // (HIP: the default priority)'), '次')
t = member('src/core/vmm.cpp')
print('  H4 门锚点 =', t.count('#if !defined(STRATA_USE_HIP)\n#include <cuda.h>'), '次')
