# -*- coding: utf-8 -*-
"""gfx906 构建补丁 v3 —— 专供 Strata v0.1.40.2；幂等 + fail-closed。

与 v2 的差异（依据 2026-10-07 对 v0.1.40.2 源码逐处实测，全部有行号）：
  · H1~H4 **上游已修**，v3 起由「打补丁」改为「**验证**」（验证不过即 fail-closed）：
      H1 include/strata/platform/hip_compat/strata_hip.h
           cudaFuncSetAttribute 已是模板内联函数（0.1.40 起）
      H2 src/kernels/cuda/fused_gr.cu
           fused_gr_read_multi 的 gfx906 STRATA_GR_SPLIT 分支已是 `return false;`
           （上游注释是 "the gfx906 STRATA_GR_SPLIT read: no q8_1 ..."，与我们 v2 写的
             "no q8_1 either; the caller quantizes" **措辞不同、语义相同** ⇒ 不能用 v2 的 already_marker 判）
      H3 src/core/mtp.cpp      已是 `#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`
      H4 src/core/vmm.cpp      同上（`#include <cuda.h>` 的门）
  · H5 CMakeLists.txt **仍需打**：
      src/prefill/moe_mmq.cu:219 在 `#if defined(__HIPCC__) || defined(STRATA_Q6K_EXPERTS)` 下
      调用 mul_mat_q_case<GGML_TYPE_Q6_K>（mmq.cuh 的 extern template，实例由
      template-instances/mmq-instance-q6_k.cu 提供）；而 CMakeLists 的 **CUDA 分支**
      （1268-1273 行）只在 STRATA_Q6K_EXPERTS 时才把 q6_k 加进 _strata_mmq_cuda_types。
      gfx906 = 走 CUDA 分支 + .cu 按 HIP 编译 ⇒ __HIPCC__ 为真 ⇒ 调用在、实例缺
      ⇒ ld.lld: undefined symbol mul_mat_q_case<(ggml_type)14>。
      修法：把该条件放宽到 gfx906（只多编一个 MMQ 实例，不打开 grouped 专家内核）。

用法：  python3 patch_gfx906_402.py                  # 默认 --root /src（容器内）
        python3 patch_gfx906_402.py --root <树根>    # 本地 dry-run / 预检
"""
import argparse, os, sys

ap = argparse.ArgumentParser()
ap.add_argument('--root', default='/src')
ap.add_argument('--quiet', action='store_true')
A = ap.parse_args()
ROOT = A.root

patched, verified, absent, fails = [], [], [], []


def log(*a):
    if not A.quiet:
        print(*a)


def _read(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    return open(p, encoding='utf-8').read()


def verify(rel, name, needles, forbid=()):
    """H1~H4 用：断言上游已是目标形态；不满足则记 FAIL（最后 fail-closed）。"""
    s = _read(rel)
    if s is None:
        log('  [FAIL] %-56s 文件不存在（该版本应有此文件）' % (rel + ' :: ' + name))
        fails.append(rel + '::' + name)
        return
    for nd in needles:
        if nd not in s:
            log('  [FAIL] %-56s 缺特征: %r' % (rel + ' :: ' + name, nd[:64]))
            fails.append(rel + '::' + name)
            return
    for nd in forbid:
        if nd in s:
            log('  [FAIL] %-56s 仍含旧形态: %r' % (rel + ' :: ' + name, nd[:64]))
            fails.append(rel + '::' + name)
            return
    log('  [ok  ] %-56s 上游已修（验证通过）' % (rel + ' :: ' + name))
    verified.append(rel + '::' + name)


def hunk(rel, name, old, new, already_marker, loose=None):
    """H5 用：文件不存在→N/A；已目标形态→skip；锚点恰 1 次→patch；其余→FAIL-CLOSED。"""
    s = _read(rel)
    if s is None:
        log('  [N/A ] %-56s 文件不存在' % (rel + ' :: ' + name))
        absent.append(rel + '::' + name)
        return
    if already_marker is not None and already_marker in s:
        log('  [skip] %-56s 已是目标形态' % (rel + ' :: ' + name))
        verified.append(rel + '::' + name)
        return
    n = s.count(old)
    if n == 1:
        s2 = s.replace(old, new)
        with open(os.path.join(ROOT, rel), 'w', encoding='utf-8', newline='\n') as f:
            f.write(s2)
        log('  [patch] %-55s 已改（%d -> %d chars）' % (rel + ' :: ' + name, len(s), len(s2)))
        patched.append(rel + '::' + name)
        return
    if loose is not None and loose not in s:
        log('  [N/A ] %-56s 该版本无此构造（特征串缺失）' % (rel + ' :: ' + name))
        absent.append(rel + '::' + name)
        return
    log('  [FAIL] %-56s 锚点命中 %d 次（应为 1）；首行 %r'
        % (rel + ' :: ' + name, n, (old.splitlines() or [''])[0][:64]))
    fails.append(rel + '::' + name)


print('=== gfx906 构建补丁 v3 (0.1.40.2) · root=%s ===' % ROOT)

# ---------- H1~H4：验证上游已修 ----------
verify('include/strata/platform/hip_compat/strata_hip.h',
       'H1 cudaFuncSetAttribute 模板内联函数',
       ['inline hipError_t cudaFuncSetAttribute',
        'cudaFuncAttributePreferredSharedMemoryCarveout'])

verify('src/kernels/cuda/fused_gr.cu',
       'H2 fused_gr_read_multi 返回 false（gfx906 split 分支）',
       ['STRATA_HIP_GFX906',
        'the gfx906 STRATA_GR_SPLIT read'],          # 上游 0.1.40.2 的注释（已修标志）
       forbid=['        return;\n    }\n#endif'])      # v2 的锚点 = 裸 return 的「未修」形态

verify('src/core/mtp.cpp',
       'H3 mtp.cpp stream-priority 门含 GFX906',
       ['#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)',
        'cudaDeviceGetStreamPriorityRange'])

verify('src/core/vmm.cpp',
       'H4 vmm.cpp <cuda.h> 门含 GFX906',
       ['#if !defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)',
        '#include <cuda.h>'])

# ---------- H5：仍必须打 ----------
CM = 'CMakeLists.txt'
hunk(CM, 'H5 CUDA 分支 q6_k 实例门 加 OR STRATA_HIP_GFX906',
     '      if(STRATA_Q6K_EXPERTS)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md)\n'
     '        list(APPEND _strata_mmq_cuda_types q6_k)\n'
     '      endif()',
     '      if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md),\n'
     '        list(APPEND _strata_mmq_cuda_types q6_k)    #   and gfx906: moe_mmq.cu calls it under __HIPCC__\n'
     '      endif()',
     already_marker='STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906',
     loose='STRATA_Q6K_EXPERTS')

# ---------- H6  strata_hip.h：补 cudaEventBlockingSync 映射（0.1.40.2 新增用法，上游漏了）----------
#   src/prefill/prefill.cpp:399 用 `cudaEventDisableTiming | cudaEventBlockingSync` 建 event。
#   wave32 那套头 include/strata/hip_compat/cuda_runtime.h:39 **早有**
#       #define cudaEventBlockingSync hipEventBlockingSync
#   但 gfx906 专用头 strata_hip.h 只有 cudaEventDisableTiming / cudaEventDefault，**独缺这一个**
#   ⇒ clang: error: use of undeclared identifier 'cudaEventBlockingSync'（2026-10-07 首次构建失败点）
#   上游修 H1（cudaFuncSetAttribute）时漏了同文件的这一条 ⇒ 与技能 §7.2 的 H1 同族问题。
#   [审计依据] 全树对比两个头的 cuda* define 后，只差 cudaEventBlockingSync 与
#   cudaDevAttrIntegrated；后者已被上游 `#if ... && !defined(STRATA_HIP_GFX906)` 正确 gate（expert_cache.cpp:31），
#   故只补前者。
hunk('include/strata/platform/hip_compat/strata_hip.h', 'H6 补 cudaEventBlockingSync 映射',
     '#define cudaEventDisableTiming hipEventDisableTiming\n'
     '#define cudaEventDefault hipEventDefault',
     '#define cudaEventDisableTiming hipEventDisableTiming\n'
     '#define cudaEventBlockingSync hipEventBlockingSync\n'
     '#define cudaEventDefault hipEventDefault',
     already_marker='#define cudaEventBlockingSync hipEventBlockingSync')

print()
print('=== 汇总  patched=%d  verified=%d  not_applicable=%d  failed=%d ==='
      % (len(patched), len(verified), len(absent), len(fails)))
for x in patched:
    print('   patched  :', x)
for x in verified:
    print('   verified :', x)
for x in absent:
    print('   N/A      :', x)
for x in fails:
    print('   FAILED   :', x)

if fails:
    sys.exit('FAIL-CLOSED: %d 处未达预期（上游可能又改了形态，先人工核）' % len(fails))
if not patched and not verified:
    sys.exit('FAIL-CLOSED: 一处都没命中 —— 检查 --root 指向的树')
print('PATCH_V3_OK')
