# -*- coding: utf-8 -*-
"""给 flashnext-engine-selection 追加 §7.11：0.1.40 升级路径 + 上游 gfx906 现状 + 快镜像"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\clyde\.workbuddy\skills\flashnext-engine-selection\SKILL.md'
ADD = r'''

### 7.11 [!] 升到 0.1.40 的正确姿势（含上游已修 / 仍缺的清单）

**先查版本，别猜**：`v0.1.39`（2026-10-04 12:32）→ `v0.1.40`（10-06 06:29）→ `v0.1.40.1`（10-06 09:53）。
`STRATA_HIP_GFX906` 的构建完整性**在这几个版本之间变过**，凡遇编译失败先核对版本与下面两张表。

#### A. 上游**已修**（0.1.40 起不需要我们打）
| 处 | 内容 | 证据 |
|---|---|---|
| `hip_compat/strata_hip.h` | `cudaFuncSetAttribute` 由**函数式宏**改为**模板内联函数**（模板逗号不再被预处理器拆参）；并补 `cudaFuncAttributePreferredSharedMemoryCarveout` | 0.1.40 头文件第 158 行注释原文 *"A function, not a macro: the call sites pass kernels as cudaFuncSetAttribute(kernel<A, B, C>, ...)"*；维护者在 PR #808 下回复 **"Merged for 0.1.40 … Thank you."** |
> 我们曾独立踩到并写了补丁（`patch_hipcompat.py`）—— **实为第 4 个独立发现者**（另有 PR #808 / #858 / #839）。
> 破损由 commit `cfd3b72` 于 2026-10-04 引入、10-06 早修好 ⇒ 我们正好落在**约 29 小时的破损窗口**里。
> **不要为它提 PR**（已修 + 重复），正确动作是**升级并把补丁删掉**。

#### B. 上游**仍缺**（0.1.40 起 gfx906 依然编不过，见 PR **#1083**，仍 open）
三处**只 gate 了 `STRATA_USE_HIP`、漏了 `STRATA_HIP_GFX906`**：
1. `src/kernels/cuda/fused_gr.cu`：`bool fused_gr_read_multi` 里 `STRATA_HIP_GFX906`+`if (split_on)` 块中的
   裸 `return;` → 应为 `return false;`（该函数返回 bool；`-Wreturn-mismatch` 下报错）
2. `src/core/mtp.cpp`：`#if !defined(STRATA_USE_HIP)   // (HIP: the default priority)`
   → 追加 `&& !defined(STRATA_HIP_GFX906)`（HIP 无 stream priority）
3. `src/core/vmm.cpp`（**0.1.40 新增的文件**）：`#if !defined(STRATA_USE_HIP)` + `#include <cuda.h>` → 同上追加

#### 现役补丁器：`D:\strata166\docker\patch_gfx906.py`（v2）
4 处改动（H1–H4 = 上表 A 一处 + B 三处），**同时兼容 0.1.39 与 0.1.40.1**，语义：
- 文件**不存在** → N/A（例：0.1.39 没有 `vmm.cpp`，也没有 mtp 的 stream-priority 段）
- 已是目标形态 → skip（幂等）
- 锚点**恰好命中 1 次** → patch
- **其余一律 fail-closed `exit 1`**（绝不做静默替换）
**验证方法**：`_dryrun_patch.py` 对两版树各跑两遍（幂等）+ 故意改坏锚点（应 rc≠0）。
实测结论 `DRY_RUN_RESULT = ALL_OK`。**改任何锚点后都要重跑这个 dry-run。**
Dockerfile 里补丁之后**必须 `grep` 复核每处改动**（打出行号），grep 不中即构建失败 —— 防"静默改了没生效"。

#### [!] 下载 GitHub 源码包：用 `gh-proxy.com` 前缀
| 源 | 实测 |
|---|---|
| `codeload.github.com` | **12~22 KB/s**（限速；15 MB 要半小时） |
| **`https://gh-proxy.com/https://github.com/<...>.zip`** | **1.4~4.2 MB/s** |
| `api.github.com` 直连 / `github.com` 直连 / `ghproxy.net` / `hub.gitmirror.com` / `ghfast.top` | 0（连不上） |
（`api.github.com` 的**元数据**接口本身很快，可用来取单文件、release 资产、PR/issue —— 只有**大文件**要走代理。）

#### 升级前必查的三项（都在 zip 上核，别只看 release note）
1. `CMakeLists.txt` 的 `project(strata VERSION x.y.z)` — 确认版本号
2. **`setup.py` 的 `LLAMA_CPP_COMMIT`** — 若与手头一致就**不必重下**依赖
   （实测 0.1.39 与 0.1.40.1 同为 `3cf03257f219afbe7334045ff7c6a06ac68c627d`）
3. 四个开关仍在：`STRATA_HIP_GFX906` / `STRATA_ENABLE_CUDA` / `STRATA_MMQ_KQUANTS` / `STRATA_PREFILL_MMQ`
   （0.1.40 起 `STRATA_MMQ_KQUANTS` 的语义**扩展到 HIP 的 dense 部分**，flag 依然有意义）
4. zip 与 API 抓到的同名文件**逐字节比对** —— 保证你分析的锚点就是构建用的那棵树

#### 一个上游环境事实（提 PR 前必读）
该仓库会**强推（force-push）main 清理提交历史**：2026-10-06 那次把 `#858`/`#758` 等 PR **自动关闭**
（GitHub 的 "base branch was force-pushed" 事件）。维护者明说 *"It is not a rejection… we port it onto the new
main ourselves and keep you as its author."* ⇒ 提 PR 别指望它一直开着；被自动关 ≠ 被拒。
'''
s = open(p, encoding='utf-8').read()
assert '### 7.11' not in s, '已存在 7.11'
open(p, 'w', encoding='utf-8').write(s.rstrip() + ADD)
b = open(p, 'rb').read()
print('skill updated -> bytes %d chars %d' % (len(b), len(b.decode('utf-8'))))
