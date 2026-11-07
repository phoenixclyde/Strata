# -*- coding: utf-8 -*-
"""gfx906 构建补丁 v2 —— 覆盖 0.1.39 与 0.1.40.1；幂等 + fail-closed。

语义（重要）：
  · 目标文件**不存在**  → 判「不适用」跳过（例如 0.1.39 没有 src/core/vmm.cpp），不算失败
  · 文件存在 + 已是目标形态 → 跳过（幂等）
  · 文件存在 + 锚点**恰好命中 1 次** → 打补丁
  · 文件存在 + 锚点既不是原文也不是已打形态，或命中次数≠1 → **FAIL-CLOSED，exit 1**
    （绝不做静默替换；这是上一版补丁器就有的纪律，保留）

用法：  python3 patch_gfx906.py                  # 默认 --root /src（容器内）
        python3 patch_gfx906.py --root <树根>    # 本地 dry-run
"""
import argparse, os, sys

ap = argparse.ArgumentParser()
ap.add_argument('--root', default='/src')
ap.add_argument('--quiet', action='store_true')
A = ap.parse_args()
ROOT = A.root

patched, skipped, absent = [], [], []


def log(*a):
    if not A.quiet:
        print(*a)


def hunk(rel, name, old, new, already_marker, loose=None):
    """loose: 该构造在「存在」时必然出现的特征串。
       · 文件不存在 → N/A
       · 已是目标形态 → skip（幂等）
       · 锚点恰好 1 次 → patch
       · loose 给了且文件里根本没有该特征 → N/A（该版本没有这段代码）
       · 其余（锚点次数≠1、或 loose 在但锚点不匹配）→ FAIL-CLOSED
    """
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        log('  [N/A ] %-52s 文件不存在（该版本无此文件）' % (rel + ' :: ' + name))
        absent.append(rel + '::' + name)
        return
    s = open(p, encoding='utf-8').read()
    if already_marker is not None and already_marker in s:
        log('  [skip] %-52s 已是目标形态' % (rel + ' :: ' + name))
        skipped.append(rel + '::' + name)
        return
    n = s.count(old)
    if n == 1:
        s2 = s.replace(old, new)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(s2)
        log('  [patch] %-51s 已改（%d -> %d chars）' % (rel + ' :: ' + name, len(s), len(s2)))
        patched.append(rel + '::' + name)
        return
    if loose is not None and loose not in s:
        log('  [N/A ] %-52s 该版本无此构造（特征串缺失）' % (rel + ' :: ' + name))
        absent.append(rel + '::' + name)
        return
    sys.exit('FAIL-CLOSED: %s :: %s\n  锚点命中 %d 次（应为 1）\n  锚点首行: %r'
             % (rel, name, n, (old.splitlines() or [''])[0]))


print('=== gfx906 构建补丁 v2 · root=%s ===' % ROOT)

# ---------- H1  hip_compat 头 ----------
HDR = 'include/strata/platform/hip_compat/strata_hip.h'
OLD_MACRO = ('#define cudaFuncSetAttribute(fn, attr, val) '
             'hipFuncSetAttribute(reinterpret_cast<const void*>(fn), attr, val)')
NEW_FUNC = '\n'.join([
    'template <typename Kernel>',
    'inline hipError_t cudaFuncSetAttribute(Kernel kernel, hipFuncAttribute attribute, int value) {',
    '    return hipFuncSetAttribute(reinterpret_cast<const void*>(kernel), attribute, value);',
    '}',
])
ANC = ('#define cudaFuncAttributeMaxDynamicSharedMemorySize '
       'hipFuncAttributeMaxDynamicSharedMemorySize')
hunk(HDR, 'cudaFuncSetAttribute 宏 -> 模板内联函数', OLD_MACRO, NEW_FUNC,
     already_marker='inline hipError_t cudaFuncSetAttribute')
hunk(HDR, '补 cudaFuncAttributePreferredSharedMemoryCarveout', ANC,
     ANC + '\n#define cudaFuncAttributePreferredSharedMemoryCarveout '
           'hipFuncAttributePreferredSharedMemoryCarveout',
     already_marker='cudaFuncAttributePreferredSharedMemoryCarveout')

# ---------- H2  fused_gr.cu（#1083 第 1 项）----------
FG = 'src/kernels/cuda/fused_gr.cu'
hunk(FG, 'fused_gr_read_multi 裸 return; -> return false;',
     '        return;\n    }\n#endif',
     '        return false;   // no q8_1 either; the caller quantizes (same contract as the v3 read)\n'
     '    }\n#endif',
     already_marker='no q8_1 either; the caller quantizes')

# ---------- H3  mtp.cpp（#1083 第 2 项）----------
MTP = 'src/core/mtp.cpp'
hunk(MTP, 'mtp.cpp stream-priority 门补 STRATA_HIP_GFX906',
     '#if !defined(STRATA_USE_HIP)   // (HIP: the default priority)',
     '#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)   '
     '// (HIP and gfx906: the default priority)',
     already_marker='&& !defined(STRATA_HIP_GFX906)   // (HIP and gfx906: the default priority)',
     loose='cudaDeviceGetStreamPriorityRange')

# ---------- H4  vmm.cpp（#1083 第 3 项，0.1.40 新增）----------
VMM = 'src/core/vmm.cpp'
hunk(VMM, 'vmm.cpp <cuda.h> 门补 STRATA_HIP_GFX906',
     '#if !defined(STRATA_USE_HIP)\n#include <cuda.h>',
     '#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)\n#include <cuda.h>',
     already_marker='&& !defined(STRATA_HIP_GFX906)\n#include <cuda.h>',
     loose='#include <cuda.h>')

# ---------- H5  CMakeLists.txt（上游 0.1.40 的守卫不一致，gfx906 上必然链接失败）----------
#   moe_mmq.cu:219 用 `#if defined(__HIPCC__) || defined(STRATA_Q6K_EXPERTS)` 决定是否调用
#   mul_mat_q_case<GGML_TYPE_Q6_K>（mmq.cuh 是 extern template，实例必须由 mmq-instance-q6_k.cu 提供）。
#   但 CMake 的 **CUDA 分支**只在 STRATA_Q6K_EXPERTS 时才把该实例加进 strata_mmq（HIP 分支则有
#   STRATA_MMQ_KQUANTS 就加）。gfx906 = CUDA 分支 + .cu 按 HIP 编译 ⇒ __HIPCC__ 为真 ⇒ 调用存在、
#   实例缺失 ⇒ ld.lld: undefined symbol mul_mat_q_case<(ggml_type)14>。
#   修法：把条件放宽到 gfx906（只多编一个 MMQ 实例，不打开 STRATA_Q6K_EXPERTS 的 grouped 专家内核）。
CM = 'CMakeLists.txt'
hunk(CM, 'CUDA 分支 q6_k 实例门 加 OR STRATA_HIP_GFX906',
     '      if(STRATA_Q6K_EXPERTS)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md)\n'
     '        list(APPEND _strata_mmq_cuda_types q6_k)\n'
     '      endif()',
     '      if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md),\n'
     '        list(APPEND _strata_mmq_cuda_types q6_k)    #   and gfx906: moe_mmq.cu calls it under __HIPCC__\n'
     '      endif()',
     already_marker='STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906',
     loose='STRATA_Q6K_EXPERTS')

print()
print('=== 汇总  patched=%d  skipped=%d  not_applicable=%d ===' % (len(patched), len(skipped), len(absent)))
for x in patched: print('   patched :', x)
for x in skipped: print('   already :', x)
for x in absent:  print('   N/A     :', x)
if not patched and not skipped:
    sys.exit('FAIL-CLOSED: 一处都没命中也没跳过 —— 检查 --root 指向的树是否正确')
print('PATCH_V2_OK')
