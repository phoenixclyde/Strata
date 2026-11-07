# -*- coding: utf-8 -*-
"""追加 [W-Strata-24]：0.1.40.1 构建成功（H5 补丁）与镜像验收数据。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-07.md'
TXT = """

## [W-Strata-24] 0.1.40.1 构建**成功** —— 上游的**第二处守卫不一致**（H5），已打补丁

**第二个失败点**（紧接着 W-Strata-23 之后）：
```
ld.lld: error: undefined symbol: void mul_mat_q_case<(ggml_type)14>(ggml_backend_cuda_context&, mmq_args const&, ihipStream_t*)
```
`(ggml_type)14` = **`GGML_TYPE_Q6_K`**（该枚举里 4/5 被移除，所以 Q5_0=6…Q6_K=14，别按印象数）。

**机理（上游 bug，0.1.40 起必现于 gfx906）**：
- `src/prefill/moe_mmq.cu:219` 的判据是 **源码级**：`#if defined(__HIPCC__) || defined(STRATA_Q6K_EXPERTS)` → **HIP 编译就一定调用** `mul_mat_q_case<GGML_TYPE_Q6_K>`
- 而 `CMakeLists.txt:1206` 的 **CUDA 分支只在 `STRATA_Q6K_EXPERTS` 时**才把 `mmq-instance-q6_k.cu` 加进 `strata_mmq`（HIP 分支则 `STRATA_MMQ_KQUANTS` 就加）
- gfx906 = **CUDA 分支 + `.cu` 按 HIP 编译** ⇒ `__HIPCC__` 为真 ⇒ 调用存在、实例缺失
- `mmq.cuh:1571` 的 `DECL_MMQ_CASE` 是 **`extern template`**（显式抑制隐式实例化，实例必须由 `template-instances/mmq-instance-<type>.cu` 提供）⇒ 不编就一定是 undefined symbol

**修法（H5，最小面）**：`if(STRATA_Q6K_EXPERTS)` → `if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)`
—— 只多编**一个 MMQ 实例**，**不**打开 `STRATA_Q6K_EXPERTS` 的 grouped 专家内核（那个会吃显存）。
锚点在 0.1.40.1 命中 1 次（6/8/6 空格缩进，注意别凭印象写 4 空格）；0.1.39 无此构造 ⇒ 补丁器判 N/A（`loose='STRATA_Q6K_EXPERTS'`）。
dry-run：zip **全新解压**树跑两遍 —— run1 `patched=4 skipped=2`（H1 上游已修）、run2 全 skip（幂等）、故意改坏锚点被 FAIL-CLOSED 拦（rc=1）⇒ `ALL_OK`。

**镜像验收（全绿，物证）**：
| 项 | 值 |
|---|---|
| 镜像 | `strata-gfx906:0.1.40.1` **6.55 GB** |
| 二进制 | 24,668,280 B（0.1.39 为 19.4 MB） |
| CMakeCache | `STRATA_HIP_GFX906=ON` / `ENABLE_CUDA=ON` / `MMQ_KQUANTS=ON` / **`Q6K_EXPERTS=OFF`**（正是预期） |
| build.ninja | 含 `mmq-instance-q6_k.cu` |
| **符号** | **`mul_mat_q_case<(ggml_type)14>` 在**；共 13 个实例（7,8,12,13,14,16,17,18,20,21,22,23,42） |
| libstrata_mmq.a | 11,904,186 B（0.1.39 = 10,939,280 ⇒ +965 KB ≈ 一个实例） |
| H1–H5 | 5 处全部目标形态（hip_compat:162 / fused_gr:1743 / mtp:418 / vmm:3 / CMakeLists:1206） |

**[!] 可复制定式**：`mmq.cuh` 用 `extern template` ⇒ **「谁调用」与「谁编实例」必须在同一套判据下**。CMake 的开关（`STRATA_Q6K_EXPERTS`）与 C++ 的宏（`__HIPCC__`）不一致时，症状是**链接期 undefined symbol**，而且**症状不指向任何一方的源码**——这类问题一律先做「把两边的判据抄在一张表上」的对齐，再去改代码。
**成本**：两次构建失败各白跑一遍 apt（~9 min）；修好后走缓存，第 8 步起重跑。**全量 ninja 只要 ~60 s**（22 核），比预想快得多。

**下一步**：三臂对拍 `0.1.39 → 0.1.40.1 → 0.1.39 复测`（同配置、同权重、唯一变量=引擎版本；每臂预热 1 次丢弃 + 重复 3 次取中位与极差）。脚本 `D:\\strata166\\scripts\\_ab_version166.py`，日志 `D:\\strata166\\logs\\ab_version166.txt`。
"""
open(P, 'a', encoding='utf-8').write(TXT)
print('appended, size =', os.path.getsize(P), 'B')
