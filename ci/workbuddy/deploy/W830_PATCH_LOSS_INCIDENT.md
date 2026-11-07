# W830 · 本地补丁丢失事故：清点、恢复、防复发

## AUDIT12 更正摘要（2026-10-31）

> 已过 AUDIT12。本文件一处**假绿**已更正：`WEB-UI` 当时判"没丢"，是因为标记用了 **上游自带** 的 `saveApiKey`；
> 部署的 `app.js` 与上游 v0.2.8 字节相同，真正缺的是 **PCIe 卡的 `· peak NN MB/s` 4 行**（已由 W831 补回）。
> 另外 §5 的 `1206→843` 是**单次复核读数**，结论以 §6 的 **1190→915 ms**（ABBA 各两轮）为准。
> 门禁本身也因此修过：标记改用 `ALBUS-*` 前缀，并同时校验 tree / image / served 三处。



> 触发：机主发现"生产把以前没有提交上游的补丁丢了"。本文是回溯昨晚至今天的全部轮次后的机械清点与处置记录。
> 一句话结论：**丢了两处代码补丁 + 一处 serve 补丁 + 一处 Web 补丁的 4 行；已全部找回、重编、上生产并逐项验证；根因是"整文件覆盖式升级 + 没有补丁清单"，已加门禁。**

## 1 结论（先看这个）

| 项 | 状态 | 证据 |
|---|---|---|
| `CMakeLists.txt` 的 **W793**（gfx906 接 rocBLAS） | **曾丢**，已恢复并生效 | configure 在 `CMakeLists.txt:213` 找到 `/opt/rocm/lib/cmake/rocblas`；构建里 `rocblas_state_ ... not used` 警告**归零** |
| `CMakeLists.txt` 的 **W776**（dflash2 只给一个文件加 `STRATA_USE_HIP`） | **曾丢**，已恢复并生效 | `build-028r/build.ninja` 里 dflash2.cpp 的 DEFINES 含 `-DSTRATA_USE_HIP=1`，且全树只有这一个文件带它 |
| `serve/telemetry.py` 的 **TEL-PCIE**（AMD PCIe 带宽采样 + FRU/容量一致性） | **更早就丢了**（10-27 升 0.1.53 时），已恢复 | `/metrics` 里重新出现 `gpu_pcie_rx_mb: 60.65` |
| `serve/web/app.js` 的 **WEB-UI** | **丢了 4 行，已由 W831 补回** | 部署的 `app.js` 与上游 v0.2.8 **字节相同**（md5 `9fed14d1…`）；`saveApiKey`/`tab-btn-images` 是**上游自带**的词，当时据此判"没丢"是**假绿**（AUDIT12 更正）。真缺的是 PCIe 卡的 `· peak NN MB/s` |
| `src/kernels/cuda/qsa_decode_attn.cu` 的 **W794**（swizzle/reduce12 接受 k8v4） | 没丢 | 标记在树里，且是唯一"与上游不同"的编译文件 |
| 我们自加的约 2800 个本地文件（third_party 等） | 一个没丢 | `third_party` 实测 2832 个文件；按 7973−5205 / 8002−5229 算是 2768/2773，原文 2824 无法精确复现（AUDIT12） |

**影响面**：昨晚的覆盖只伤到 1 个文件（`CMakeLists.txt`），但那条 `CMakeLists.txt` 里同时住着 **2 个补丁**。
其中 W793 让 `STRATA_ROCBLAS_TUNING` 从"死开关"变回生效——**这是一个性能项，不只是洁癖**。

## 2 怎么查的（可复现）

不看记忆、不看日志，直接做三方机械比对：

1. 取上游两个 tag 的逐文件 blob SHA：`v0.2.7.1`（5205 文件）、`v0.2.8`（5229 文件）。
2. 算 `src0271`（0.1.53 树，7973 文件）与 `src028`（0.1.54 树，8002 文件）每个文件的 git blob sha1。
3. 分类：**本地 ≠ 上游 0.2.7.1 ⇒ 这是我们的改动**；再看它在 `src028` 里是否被换成了上游 0.2.8 的版本。

结果：**94 个文件是我们的改动；74 个保住，20 个被覆盖**。再对 20 个逐个 diff 内容分类：

- **19 个是"我们的树本来就比 tag 旧"**（README/INSTALL/metal/dsv41 等，diff 全是负数行）——被"覆盖"其实是被升级，不是丢补丁。
- **1 个是 `CMakeLists.txt`，+18/−1，里面有三处标记**：`W717`（记录用）、`W776`、`W793`。

另外用"标记全库扫"交叉验证：整个树里带 `W7xx/W8xx` 标记的文件只有 **2 个**——
`CMakeLists.txt`（3 处标记；**发现时 0 处、恢复后 2 处** —— AUDIT12 更正）和 `qsa_decode_attn.cu`（W794，在）。

## 3 丢的三样东西，各自是什么

### W793 —— gfx906 分支从未接上 rocBLAS（性能项）
0.2.8 的 `CMakeLists.txt` 里，gfx906 走一条独立分支，只 `find_package(hip/hipblas)`，
**从不 include `cmake/hip_backend.cmake`**，于是 `STRATA_ROCBLAS_AVAILABLE` 永不定义 ⇒
`gemm.cu` 里整段 `#if defined(__HIPCC__) && defined(STRATA_ROCBLAS_AVAILABLE)` 被编掉 ⇒
我们生产一直设着的 `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.5.0.txt` **读都没被读**。

复现证据（构建日志原文）：
```
/src/include/strata/prefill/gemm.hpp:96:11: warning: private field 'rocblas_state_' is not used
   96 |     void* rocblas_state_ = nullptr;   // HIP: the rocBLAS solution table of f16_inplace (STRATA_ROCBLAS_TUNING)
```
恢复后同一条编译不再报警。

### W776 —— gfx906 上 dflash2 编错了分支（正确性项，当前未被使用）
`dflash2.cpp` 用 `STRATA_USE_HIP` 切换两处行为：流的优先级、fork（双流）默认值。
gfx906 不定义这个宏 ⇒ 走 CUDA 分支 ⇒ **默认开高优先级流 + 默认开 fork**；
而上游对 HIP 的默认恰恰相反（代码注释写着 HIP 上实测更差）。
我们当前没用 `--draft dflash2`，所以**没有实时性能影响**，但这是一个"哪天开 DF2 就踩"的雷。
昨晚我为了让它编过，在 `hip_compat/strata_hip.h` 里补了两个宏——那是**在错误分支上打的补丁**，
正确做法就是这条 W776（把宏限定到这一个文件，让它走 HIP 分支）。两处现在共存，互不冲突。

### TEL-PCIE —— AMD PCIe 带宽采样（更早就没了）
`serve/telemetry.py` 里我们的五处改动（`BW_REFRESH_S`、`_Amd.bw()`、独立采样线程、`sample()` 注入
`gpu_pcie_rx_mb`、`name()` 的 FRU/容量一致性校验）。这份补丁的产物停在 10-22，
而树里现在的 `telemetry.py` 是 10-27 的上游版——**说明它是 10-27 那次升 0.1.53 时丢的**，
昨晚的升级只是"接着丢"了另一批。这也解释了为什么机主会觉得"以前丢过、这次又丢"。

## 4 根因（两条，都要改）

1. **升级方式本身**：从 `src0271` 复制出 `src028`，再把 148 个上游文件**整文件覆盖**上去。
   只要我们的改动落在"上游也会改的文件"里，就会被静默覆盖，**没有任何提示**。
   昨晚我甚至做过"全树 SHA 比对"，但比的是 **`src028` vs 上游 0.2.8** ——这个比法有个致命盲点：
   被覆盖的文件看起来"就等于上游"，**被判成正常**。正确比法是 `src028` vs **`src0271`**（旧树）。
2. **没有补丁清单，也没有门禁**：补丁只存在于 `build024/patches/*.py` 和 `patches/*.patched` 里，
   没人知道"哪些文件不能覆盖"，构建成功后也不会检查"标记还在不在"。
   W793 丢失之所以没被发现，是因为**它丢得很安静**：编译照样成功（只是 rocBLAS 整段没了），
   运行时也照样出 token（只是慢一点）。

## 5 处置与验证

| 动作 | 内容 |
|---|---|
| 恢复 W793+W776 | 幂等脚本 `albus/w830/restore_cmake.py` 写回 `src028/CMakeLists.txt`（锚点断言、留 `.bak-w830`） |
| 重建引擎 | `build-028r`（窄窗口 `WINDOW_MAX_T=auto`，选项从 0.1.54 的 cache 反推）→ **344/344，EXIT=0**，`rocblas_state_` 警告归零 |
| 部署 | `/data/bin/strata-0.1.54n2`（38,262,328 B，md5 与产物一致；旧 `n` 保留可回滚） |
| 恢复 TEL-PCIE | 3-way 合并：只把我们的 5 处加到**当前**上游文件上（`+51/−3`），保留上游新的 `_loop` 健壮性；`py_compile` 通过 |
| 重建镜像 | `strata-gfx906:0.2.8p1`（旧 `0.2.8` 保留），镜像内 `BW_REFRESH_S` ×2 |
| 切生产 | exe → `n2`、镜像 → `0.2.8p1`，202 s 就绪，`/health` ok；配置备份 `.bak-w830-cutover` |
| 验证 | `/metrics` 出现 `gpu_pcie_rx_mb: 60.65`；decode **46.27 tok/s**（修复前 46.25/46.28，无回归）；TTFT 常数项以 §6 的 **1190 → 915 ms**（ABBA 各两轮）为准 —— 本节原写的 1206→843 是**单次复核读数**，不作结论（AUDIT12 更正） |

## 6 rocBLAS 的收益（同镜像、只差 exe 的 A/B）

见 `data/w830_ab.log`：`tn`（n）与 `tn2`（n2）各两轮、每轮 3 次热身 + 3 长度 ×2 次，
判据是 `TTFT = 常数 + 边际 × token` 的**常数项**（rocBLAS 只影响小 GEMM，也就是常数项那一块）。

同镜像（`0.2.8p1`）、同配置，**只差 exe**，ABBA 各两轮，每轮 3 次热身 + 3 长度 ×2 次：

| 臂 | exe | 常数项 (ms) | 边际 (ms/tok) | 两轮常数 |
|---|---|---|---|---|
| tn | `strata-0.1.54n`（无 W793/W776） | **1190** | 1.327（753 tok/s） | 1201 / 1178 |
| tn2 | `strata-0.1.54n2`（已恢复） | **915** | 1.316（760 tok/s） | 857 / 973 |

- **常数项 −275 ms（−23%）**，两轮方向一致；**边际不变**（1.327 → 1.316，噪声内）。
- 折算到实际提示：500 tok 1.85 → **1.57 s**；1151 tok 2.72 → **2.43 s**（−11%）；4345 tok 6.93 → **6.63 s**（−4%）。
- decode 未受影响：`0.2.8p1 + n2` 上 3×512 得 **46.27 tok/s**（修复前 46.25/46.28）。
- 机理上说得通：rocBLAS 的 f16 GEMM 表影响的是短 T 的 dense 投影，也就是"固定开销"那一块，不动边际。

⇒ **W793 不是一个"洁癖项"，它值约 0.28 s 的首 token 延迟。** 这也说明被覆盖式升级丢掉的东西里，
可能有我们从未察觉的性能项——所以门禁比这一次数值更重要。

## 7 防复发（已落地）

1. **补丁清单**：`deploy/patches/LOCAL_PATCHES.tsv` —— 每行一个补丁：文件、标记、检查位置、用途。
2. **门禁脚本**：`albus/w830/verify_patches.sh` —— 升级/重编/换镜像后必跑，**现行 13 项检查**（写此文时 8 项，W831 后扩到 13）
   （树、`build.ninja`、镜像内文件、部署二进制与产物的 md5）。**任一缺失即 `GATE FAIL`，不许部署**。
   当前状态：8/8 `GATE PASS`。
3. **流程**：
   - 升级前先跑门禁，记录基线；
   - **清单里的文件一律不许整文件覆盖**，要 3-way 合并（被丢的 19 个"旧文件"正是覆盖带来的正常升级，
     说明覆盖本身没错，错在没区分"我们改过的"）；
   - 升级后先比 **新树 vs 旧树**（不是 vs 上游），列出所有差异再分类；
   - 构建后检查两条金丝雀：`rocblas_state_ ... not used` 警告不得出现；`build.ninja` 里
     `-DSTRATA_USE_HIP=1` 必须只挂在 `dflash2.cpp` 上。

## 8 顺带的结论：今晚的"该落生产"

昨晚至今天所有轮次的判定里，**该改配置的都已经在生产里**（`MMQ_KQ=1`、`PROMPT_F16=1`、`--spec 4 --spec-min-p 0.70`、
`--pcie-frac 0.20`、`adapt 4/96`、`PREFILL_CPU_SHARE=auto+3072` 等 33 args / 14 env 全部在位，逐一核对见 §9）；
被判"否/不动"的都没有进生产（`SH_STREAM`、`adapt=1/80/0.97`、`batch 2`、`Q3_K_XL`、`CPU_SHARE=0`）。
**唯一"该在而没在"的就是本文这三样补丁**，现已恢复。

## 9 配置面复核（ADOPTED 逐条对生产）

登记表 52 条 ADOPTED → 抽出 36 个配置 token → **33 个在生产配置里**；3 个"缺席"经核为误报或本就该不设：
`STRATA_ROCBLAS_AVAILABLE`（构建期变量，不是 env）、`--adapt-`（正则截断的假 token）、
`STRATA_SH_STREAM`（四臂判定不开）。其余 17 条 ADOPTED 是构建/镜像/选型类，按 §1 逐项验证。
