# -*- coding: utf-8 -*-
"""gfx906 hip_compat 最小补丁（构建时在容器内执行）。

依据（源码对拍 2026-10-06）：
  A) gfx906 专用的 include/strata/platform/hip_compat/strata_hip.h 把 cudaFuncSetAttribute 写成
     **函数式宏**： #define cudaFuncSetAttribute(fn, attr, val) hipFuncSetAttribute(...)
     而全仓有 16 处调用把**带逗号的模板实参**传进去，例如
         cudaFuncSetAttribute(gr_down_v3_kernel<1, kFusedGrMaxT, false>, ...)
     预处理器不认 <>，会按逗号拆成 5 个实参 -> "too many arguments" -> 宏不展开 ->
     再报 "undeclared identifier 'cudaFuncSetAttribute'"。编译因此失败。
     同仓库 wave32 那套（include/strata/hip_compat/cuda_runtime.h）用的是
     `template <typename Kernel> inline hipError_t cudaFuncSetAttribute(...)`，
     函数实参按 C++ 语法解析，模板逗号不是问题 —— 本补丁照搬该已验证写法。
  B) 该头还缺 `cudaFuncAttributePreferredSharedMemoryCarveout` 映射（wave32 那套有），补上。

这是**唯一**的改动，且仅作用于 gfx906 这一套头文件；不改任何 .cu/.cpp 业务代码。
"""
import sys

P = '/src/include/strata/platform/hip_compat/strata_hip.h'
s = open(P, encoding='utf-8').read()

OLD = ('#define cudaFuncSetAttribute(fn, attr, val) '
       'hipFuncSetAttribute(reinterpret_cast<const void*>(fn), attr, val)')

NEW = '\n'.join([
    'template <typename Kernel>',
    'inline hipError_t cudaFuncSetAttribute(Kernel kernel, hipFuncAttribute attribute, int value) {',
    '    return hipFuncSetAttribute(reinterpret_cast<const void*>(kernel), attribute, value);',
    '}',
])

ALREADY = 'template <typename Kernel>\ninline hipError_t cudaFuncSetAttribute'

if OLD in s:
    s = s.replace(OLD, NEW)
    print('patched: cudaFuncSetAttribute 函数式宏 -> 模板内联函数')
elif ALREADY in s:
    print('already patched: cudaFuncSetAttribute')
else:
    sys.exit('ANCHOR NOT FOUND: cudaFuncSetAttribute 既不是预期宏，也不是已打补丁的形态')

ANC = '#define cudaFuncAttributeMaxDynamicSharedMemorySize hipFuncAttributeMaxDynamicSharedMemorySize'
if 'cudaFuncAttributePreferredSharedMemoryCarveout' not in s:
    if ANC not in s:
        sys.exit('ANCHOR NOT FOUND: cudaFuncAttributeMaxDynamicSharedMemorySize')
    s = s.replace(ANC, ANC + '\n#define cudaFuncAttributePreferredSharedMemoryCarveout '
                             'hipFuncAttributePreferredSharedMemoryCarveout')
    print('patched: + cudaFuncAttributePreferredSharedMemoryCarveout')
else:
    print('already present: cudaFuncAttributePreferredSharedMemoryCarveout')

open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('hip_compat patch done ->', P)
