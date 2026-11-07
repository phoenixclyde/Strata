# -*- coding: utf-8 -*-
"""追加 2026-10-06 日志：MMQ 到底在不在用 + 预填优化杠杆（源码级）"""
import os

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
TXT = """

## [W-Strata-11] 源码级核实：**K-quant 的 MMQ 预填内核在 gfx906 上其实是编进去且生效的** —— 重新定位瓶颈

### 一、推翻了之前那句粗结论
之前说"K-quant 的 prompt kernel 是 CUDA-only，AMD 只能走退化路径"，**在 gfx906 这条路不成立**。证据链：
1. `CMakeLists.txt:62-69`：`STRATA_HIP_GFX906=ON` **会强制 `set(STRATA_ENABLE_CUDA ON)`**
   ⇒ 尽管 gfx906 明确拒绝 `STRATA_ENABLE_HIP`，构建仍走 **CUDA 分支**（`.cu` 源由 `CMakeLists:1245-1253` 改成 `LANGUAGE HIP`，
   配 hip_compat 这层 CUDA→HIP 垫片）
2. 于是 `CMakeLists:1042-1080` 那个 CUDA 分支生效：`STRATA_MMQ_KQUANTS=ON` 把
   **`mmq-instance-q4_k / q5_k / q5_1` 一起编进 `libstrata_mmq.a`**，并**无条件**给 `strata_prefill` 定义
   `STRATA_PREFILL_MMQ=1`（注意：CMakeCache 里 `STRATA_PREFILL_MMQ:BOOL=OFF` 只是那个 **option** 没开，
   它只影响纯 HIP 的 `elseif` 分支；**编译宏是另一个东西**，所以引擎里 MMQ 是开着的）
3. 实测物证：`/src/build-906/libstrata_mmq.a` **10,939,280 B**；`nm -C strata` 里 **180** 个 mmq 符号，
   含 `HIP_vector_type` 的 kernel（即确实以 HIP 编出）
4. 运行期判据 `src/prefill/prefill.cpp:669-690`：
   `const bool on = mmq::built() && (env == nullptr || atoi(env) != 0);` ⇒ **默认开**；
   只有 `mmq::fits(gt,1280) || mmq::fits(dt,N)` 失败才**逐层回退**，并打一条 #420 日志
5. `src/prefill/prefill.cpp:144` 的回退提示原文：
   `strata: prompt kernels: llama.cpp's MMQ has no tile for <type> (<rows> rows) on GPU 0 (cc 9, 65536 bytes of shared memory per block)`
6. **关键**：`serve/server.py:455` 是 `stderr=self.log` —— 引擎 stderr 与 stdout **同写一个日志**。
   而 `/data/*.log` 里 **grep 不到任何 "prompt kernels"/"non-MMQ"/"mmq"** ⇒ **没有发生回退 ⇒ MMQ 在用**

⇒ 结论：**gfx906 单卡上 UD-Q4_K_XL 的预填已经在用 llama.cpp 的 MMQ int8 内核**。467 tok/s 不是"退化路径"的结果。
  （`hip_compat/strata_hip.h:218-221` 也给了支撑：gfx906 有 `v_dot4_i32_i8`，`__dp4a` 被映射到 `__builtin_amdgcn_sdot4`）

### 二、真正的瓶颈候选（下一步按这个顺序查）
1. **CPU 侧 K-quant 专家组不是多 token**：日志原话
   `this CPU has no AVX-512: the expert kernels run on AVX-2 (multi-token for the i-quant gate/up rows)`
   ⇒ 多 token AVX2 内核只覆盖 **i-quant**；K-quant 的 gate/up 落到 ggml 的**单 token** vec_dot。
   `src/kernels/cpu/native_expert.cpp:100-107` 有 `STRATA_KQ256=1`（Q4_K/Q5_1/Q8_0 的多 token AVX2 内核），
   上游注释说"引擎里测不出更快"——**但理由是"窗口的专家组只有 ~1.4 tokens"**，那是**解码**的场景，
   **预填的组是几百~几千 token，这条理由不适用** ⇒ 必须实测
2. **`--pcie-frac`**：`src/program/generate.cpp:1218-1224` —— 它是"每层未命中专家里，GPU 通过 PCIe 读走的比例"。
   自动探测公式 `frac = 0.55 × min(1, gbps/20)`；166 实测 **13.1 GB/s ⇒ 自动降到 0.36**。
   这是**预填的第一号旋钮**（GPU 算得多 vs CPU 池算得多），可显式覆盖扫描
3. **`--pcie-mode auto|dma|kernel|direct`**（generate.cpp:471）
4. **`--pool-workers`**（166 实测默认 21 = 22 核 − 1）、`--prefill` chunk（auto）、`--shared-late`、`--adapt-every`
5. **`--stats` 存在**（"print the per-stage breakdown"）⇒ 拿 per-stage 分解是定位瓶颈的正解
6. 其它 opt-in：`STRATA_IQ_MT_MIN=1`（让每组都走多 token）、`STRATA_NO_IQ4NL`、`STRATA_KQ256`、
   `STRATA_PARTIAL_PIN`、`STRATA_FETCH_THREADS`、`STRATA_STAGER_THREADS/RING`、`STRATA_LOOKAHEAD`

### 三、换 i-quant 打包是"不改代码就能拿"的最大一招
`docs/UNSLOTH_Q4.md:224-249`：**UD-IQ4_XS 是常规选项**（93.7 GB，3 片，sha256 全钉死），
专家格式 = **IQ3_S gate/up + IQ4_XS（一层）+ IQ4_NL down（五层 Q8_0）**，全是 **i-quant**。
文档原话：**"It does not ask on AMD: its experts' formats have prompt kernels there too."**
且 CPU 侧 i-quant 正好吃 multi-token AVX2（`native_expert.cpp:108-113`：IQ4_XS 这种只有 AVX-2 内核的格式，
在**非 AVX-512 的 CPU 上**才启用多 token 内核 —— 166 正是这种 CPU）。
官方在 **Strix Halo（gfx1151，128 GB 统一内存）** 实测：**prompt ~820 tok/s @ 8K 与 64K**（= 我们现在 467 的 1.75×）。

### 四、真要"移植/开发"的三条路（成本递增）
1. 给 HIP 的 `_strata_mmq_types`（CMakeLists:1037）补 K-quant —— 我们现在是靠 CUDA shim 绕过去的，
   **这条路等于已经免费拿到**；纯 HIP 构建（`STRATA_PREFILL_MMQ=ON`）反而拿不到 K-quant
2. 若某类型 tile 装不进 gfx906 的 **64 KB LDS**：需自己写 tile / 调 J 与 shared-memory 布局 —— 真移植工作
3. 给 gfx906 写 **wave64 原生**热内核（hip_compat 头注释里提到这是另一条路，现有做法是"把 CUDA warp 当 wave 的
   逻辑半波"来保数值一致性，代价是浪费一半 lane 的执行槽）
"""
old = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(old.rstrip() + '\n' + TXT)
print('appended, size', os.path.getsize(p), 'B')
