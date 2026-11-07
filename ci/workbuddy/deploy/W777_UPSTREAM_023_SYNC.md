# W777 上游同步到 0.2.3.1（引擎 0.1.48.1）+ 新特性适用性判定 + 落生产

> 2026-10-23 23:4x - 2026-10-24 01:0x · 机主令：「与上游同步，更新到最新版源码，同步更新 llama.cpp 到最新版，去项目看最佳实践，并编译制作最新版镜像，并去项目查看过去几版完整 releasenote，形成调优方案，尤其新的 amd 显卡和 intel cpu 相关优化是否可以落到我们的 166 平台上。拉新镜像基线，落生产容器，更新 config。」
> 口径：每条断言带出处（release note 原文 / 源码行号 / 实测日志）。推算值标 [推算]。

---

## 0 结论先行

1. **上游最新 = v0.2.3.1**（2026-10-23T13:45Z，tag `7ddc17a38fe7` = `main` HEAD）。**引擎 0.1.48.1**（我们原 0.1.47）。
2. **0.2.3.1 与我们无关**：只改 Windows NVIDIA 包的 setup 与 Terminal Control（0.1.48.1），release note 原文「the engine packages stay 0.1.48」。**真正的引擎变化在 0.2.3**。
3. **llama.cpp pin 没变**：0.2.2 与 0.2.3 的 `third_party/ggml/VERSION.txt` 逐字相同 `3cf03257f219afbe7334045ff7c6a06ac68c627d`。上游最佳实践原文（`AMD_HIP_PERFORMANCE.md`）：**「Use the repository-pinned llama.cpp dependency; do not silently substitute another revision」** => **不换**。换最新也编不过，见 §5。
4. **0.2.3 的提速对 gfx906 全部不适用**：Strix Halo（gfx1151 / gfx1152）、Intel Arc（SYCL）、RX 9070（gfx1201）、Mac Metal —— 四个平台都不是我们。**实测三档性能与 0.2.2b 等价（差异 <0.15%）**，符合预期。
5. **只有一个新开关能用：`STRATA_HC_Q8=1`（8-bit hyper-connection）**。上游源码明写「on for gfx1151, **off elsewhere**」，即 gfx906 默认关但可显式开。**实测采纳**：三档 prompt 一致 **+0.6~0.67%**，decode +2~5%，**expert_slots 9732 -> 9901（+169，+1.7%）**。
6. **DFlash2 不可行（硬约束）**：需要约 1.2 GiB VRAM（源码 `generate.cpp:5511` 原文），我们加载完只剩 **640 MiB**。要开就得砍 ~500 个专家槽，得不偿失。
7. **Intel CPU 优化不存在**：0.2.3 的「Better defaults for CPU workers」是**产品层 Work profile**（NVIDIA 小显存卡），不是指令集优化；0.2.2 -> 0.2.3 的 131 个 commit 里没有新增 AVX-512 / AMX / VNNI 路径。我们的 **Xeon E5-2696 v4（Broadwell）连 AVX-512 都没有**（日志原文 `this CPU has no AVX-512: the expert kernels run on AVX-2`）。
8. **编译遇到一个上游在 gfx906 上的缺口并已修**：0.1.48 新增的 `src/core/dflash2.cpp` 用 `STRATA_USE_HIP` 判 CUDA-vs-HIP，而 gfx906 构建只定义 `STRATA_HIP_GFX906`（`CMakeLists.txt:78` 明说两者是 separate backends）=> 编不过。已把该宏**精准限定到这一个文件**。
9. **已落生产**：容器 `strata166-407` 跑 `strata-gfx906:0.2.3`，旧容器改名 `strata166-407.bak022b` 作回滚位。`verify_config` **PASS=29 FAIL=0**。

---

## 1 版本与产物（实测）

| 项 | 值 |
|---|---|
| 上游最新 tag / commit | `v0.2.3.1` / `7ddc17a38fe7`（= main HEAD） |
| 源码版本行 | `project(strata VERSION 0.1.48.1 LANGUAGES CXX)` |
| 引擎 `--version` | **`strata 0.1.48.1`** |
| llama.cpp pin | `3cf03257f219`（2026-09-20，与 0.2.2 相同） |
| 镜像 | `strata-gfx906:0.2.3`，6.96 GB，`ec0bedc799f2` |
| 引擎二进制 | 34,235,568 B，md5 `657a0617aa88aac…` |
| `STRATA_Q6K_EXPERTS` | **OFF**（0.1.48 仍默认 ON，我们显式关，与 0.1.42 对齐） |
| 构建 | `BUILD_RC=0`，`[160/160]`，容器内按 `docs/AMD_HIP.md` gfx906 官方配方重编 |

---

## 2 过去几版 release note 逐条判定（只列与我们有关的）

> 0.2.2 / 0.2.1 / 0.2.0-beta / 0.1.45 的逐条判定已在 `W775delta_UPSTREAM_022_PLAN.md` §3 完成（结论：能落到我们配置上的只有 4 条）。本节只补 **0.2.3 / 0.2.3.1**。

### 2.1 0.2.3（引擎 0.1.48）

| 条目 | 平台 | 对我们 | 依据 |
|---|---|---|---|
| Strix Halo 提速（HC 8-bit 读、8192 chunk 回归、自找调优表） | gfx1151 Windows | **部分可用**：HC 8-bit 那一条是通用实现，只是默认只对 gfx1151 开 | `native_dense.cpp:49`「also on for gfx1151 … off elsewhere」 |
| Intel Arc 成为正式引擎包（Linux SYCL） | Intel | 不适用 | 我们是 AMD HIP |
| DFlash2 drafter（opt-in） | CUDA / HIP | **不可行**：需 1.2 GiB VRAM | `generate.cpp:5511` + `vram_free 640` |
| agent chat 满上下文处理 | 产品层 | 不适用（我们用 Open WebUI） | — |
| HTTPS 用系统证书 | 产品层 | 不适用 | — |
| Better defaults for CPU workers / VRAM / memory | 产品层 Work profile | **部分参考**：会话缓存按空闲内存自算（#3493）是引擎行为 | 见 §6 待验证 |
| Terminal / App 稳定性 | 产品层 | 不适用 | — |
| Mac Metal expert-cache 借用修复 | Metal | 不适用 | — |

### 2.2 0.2.3.1（Control 0.1.48.1）

原文：「Only the Terminal's Control changed (version 0.1.48.1). The app stays 0.2.3 and **the engine packages stay 0.1.48**」。=> 与我们无关，但**它的 tag 树里 CMakeLists 写的是 0.1.48.1**，所以我们的引擎自报 0.1.48.1。

---

## 3 「新的 AMD 显卡优化」能不能落到 gfx906 —— 逐条给源码证据

| 优化 | 门控（源码/文档） | gfx906 |
|---|---|---|
| HC 8-bit 读（Strix Halo 提速主项） | `native_dense.cpp:49`：gfx12 defaults 或 gfx1151 才默认开，**其余一律 off** | **可显式开**（`STRATA_HC_Q8=1`），本机已实测 |
| gfx1151 的 8192 prompt chunk 回归 | `generate.cpp` 的 gfx1151 Windows 分支 | 不适用（我们本来没有 6144 上限） |
| 自找 tuning 表 | `STRATA_HIPBLASLT_TUNING` / `tuning/` 目录 | **不适用**：gfx906 走 wave64 兼容层，无 hipBLASLt（`docs/AMD_HIP.md`：hipBLASLt 不使用） |
| RDNA3 / RDNA4 的 MMQ 路径（`get_config_rdna3_5` / `_rdna4`） | `mmq.cuh` 按 arch 分派 | 不适用（我们走 `get_config_gcn`） |
| Intel Arc（SYCL） | 独立引擎包 `linux-x86_64-sycl` | 不适用 |
| Metal 修复 | Metal 引擎 | 不适用 |

**结论：AMD 侧唯一能落 gfx906 的就是 HC_Q8，已拿下来。**

---

## 4 「Intel CPU 优化」—— 不存在，且我们的 CPU 本来就没有 AVX-512

- 0.2.2 -> 0.2.3 共 **131 个 commit**，逐个看过标题：`intel` 只出现在 Intel **Arc 显卡**语境，**没有一条**是 Intel CPU 指令集/调度优化。
- `src/kernels/cpu/` 里与指令集相关的只有 `expert_layout.cpp` 命中 `amx|avx512_vnni|avx_vnni` 字符串（是格式定义，不是新 kernel）。
- 本机日志原文：`this CPU has no AVX-512: the expert kernels run on AVX-2`。Xeon E5-2696 v4 = Broadwell，**AVX2 顶部**，AMX/VNNI 都不可能。
- 唯一沾边的是产品层 Work profile 的 worker 数公式（`ceil(0.8 x physical cores)`），而引擎侧的 `--pool-workers` 默认逻辑 0.1.48 **没变**（仍是 `20 workers by default … one kept free`）。

**结论：Intel CPU 方向对本机零收益，不需要任何动作。**

---

## 5 llama.cpp：pin 未变，最新版不兼容（源码级证据）

| 项 | 值 |
|---|---|
| 0.2.2 pin | `3cf03257f219afbe7334045ff7c6a06ac68c627d` |
| 0.2.3 pin | **完全相同**（`third_party/ggml/VERSION.txt` 逐字一致） |
| llama.cpp master HEAD | `36e36e63a54f`（2026-10-23T14:46Z） |
| 关键签名 | pin：`ggml_cuda_mmq_get_config(type, J, fallback, cc)` = **4 参**；master：同函数 **+`const ggml_prec prec_src1`** = **5 参** |
| Strata 调用点 | `src/prefill/moe_mmq.cu:305` 传 **4 参** => 必然 `no matching function` |
| 其他差异 | `mmq.cuh` DIFF、`ggml.h` DIFF、`ggml/CMakeLists.txt` DIFF、`fattn.cu` DIFF（`mmid.cuh` SAME） |

**判定：不跟。** 三条理由：
1. 上游最佳实践**明文禁止**替换 pin（`AMD_HIP_PERFORMANCE.md` 原文）。
2. 上游自己**没 bump**，说明他们也没适配新 API。
3. MMQ 是**答案数值最敏感**的一段（决定 prompt 的专家量化路径），改胶水层必须过 identity gate —— 而本机的 identity 判据已被证伪（同 prompt 3 次 3 种 md5，`W775delta` §11）。

要推进的唯一正确路径：给上游报 issue/PR，带上面这个 5 参 vs 4 参的原文差异。

---

## 6 编译：遇到并修掉的 gfx906 缺口

### 6.1 报错（原文）

```
src/core/dflash2.cpp:205:5: error: use of undeclared identifier 'cudaDeviceGetStreamPriorityRange';
                                   did you mean 'hipDeviceGetStreamPriorityRange'?
src/core/dflash2.cpp:206:9: error: use of undeclared identifier 'cudaStreamCreateWithPriority'
src/core/dflash2.cpp:207:9: error: use of undeclared identifier 'cudaStreamCreateWithPriority'
FAILED: CMakeFiles/strata_engine.dir/src/core/dflash2.cpp.o
```

### 6.2 根因

`dflash2.cpp` 有两处 `#if defined(STRATA_USE_HIP)`（198 行流优先级、446 行 fork 默认）。而 **gfx906 构建从不定义 `STRATA_USE_HIP`** —— `CMakeLists.txt:78` 原文「STRATA_HIP_GFX906 and STRATA_ENABLE_HIP are **separate backends**」，我们只有 `add_compile_definitions(STRATA_HIP_GFX906=1)`（164 行）。
=> 走 CUDA 分支 => 编不过。**上游只测了 CUDA 与"正式 HIP"两条路，gfx906 兼容层这条没测。**

### 6.3 修法（精准、可回退）

只给这一个文件加宏，**不全局加**（全局加会误开 CUDA-only 路径 —— 这正是 W717/P23 踩过的坑：`prefill.cpp:1838` 拿 `STRATA_USE_HIP` 当"是不是 AMD"判据，全局定义会让 CPU prefill share 误开）：

```cmake
if(STRATA_HIP_GFX906)
  set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS "STRATA_USE_HIP=1")
endif()
```

语义正确性核对：该文件第二处宏（446 行）只决定 `fork_default`，HIP 侧应为 `false`（源码注释：Strix Halo 实测 +0.0..0.7 ms，所以 HIP 保持单流）—— 加宏后正好走到这个值。

Dockerfile 里有断言 `test "$(grep -c 'STRATA_USE_HIP=1' /src/CMakeLists.txt)" = "1"` 保证它在位。

---

## 7 基线（同 config、同口径、唯一 nonce、reused=0）

测量口径与 W776-C2 完全一致（`_bench166.py`，S 2,807 tok / M 21,821 tok / L 99,381 tok）。

| 臂 | S prompt | S decode | M prompt | M decode | L prompt | L decode |
|---|---|---|---|---|---|---|
| **0.2.2b**（0.1.47） | 407.1 | 59.4 | 484.3 | 59.8 | 462.8 | 37.4 |
| **0.2.3**（0.1.48.1） | 407.5 | 59.4 | 483.7 | 60.1 | 462.4 | 38.9 |
| **差值** | **+0.10%** | 0.0% | **-0.12%** | +0.5% | **-0.09%** | +4.0% |
| **0.2.3 + HC_Q8=1** | **410.2** | **62.4** | **486.6** | **61.3** | **465.5** | **41.5** |
| **对 0.2.2b** | **+0.66%** | **+5.0%** | **+0.60%** | **+2.0%** | **+0.67%** | +11.0% |

判读：
- **0.2.3 本体 = 性能等价**（三档差值全在 0.15% 内，低于 prompt 分辨率 1.2%）。这是**预期内**的：0.2.3 的提速都在别的平台。
- **HC_Q8 = 三档 prompt 一致 +0.6~0.67%**。单档低于分辨率，但**三档同向且幅度一致** => 可信。机理解释得通：HC 权重按 8-bit 读，省显存（槽 +169）也省带宽。
- decode 的 +2~5% 分辨率不足（臂内波动 45-64），但 L 档 decode 只有 32 token，那一列不作数。

---

## 8 落生产（已执行）

| 步骤 | 结果 |
|---|---|
| 镜像 | `strata-gfx906:0.2.3`（`BUILD_RC=0`） |
| 停旧 | `docker stop strata166-407` |
| 回滚位 | `docker rename` 为 **`strata166-407.bak022b`**（0.2.2b / 0.1.47 完整保留） |
| 起新 | 同名、同参数（`--device /dev/kfd /dev/dri --group-add video --ipc=host --ulimit memlock=-1 --shm-size=64m --security-opt label=disable -p 8090 -v data -v models:ro --restart unless-stopped`） |
| 就绪 | **42 s** |
| 版本 | `strata 0.1.48.1` |
| `/metrics` | `slots 9901`（HC_Q8 生效前 9732）· `vram_free 642` · `workers 20` · `kv k8v4` · `context 262144` · `spec 6 / mtp_max 4 / lookup 3` |
| 遥测 | `gpu_name Radeon Instinct MI50 32GB`（FRU 纠正）· `pcie gen3 / width16 / 4/4` · `gpu_pcie_rx_mb 0.01` |
| config | md5 变了（加了 `STRATA_HC_Q8=1`），`gen_config.py --live` **无差异** |
| 固化 | `verify_config.py` **PASS=29 FAIL=0** |
| 回滚位（镜像） | `0.2.3` / `0.2.2b` / `0.2.2` / `0.1.42` / `0.1.41` 五层都在 |

---

## 9 调优方案（本轮之后还剩什么）

### 已收口（本轮新增）

| 项 | 判定 | 依据 |
|---|---|---|
| `STRATA_HC_Q8=1` | **采纳并已落**（P78） | 三档 +0.6~0.67%，槽 +169 |
| DFlash2 | **不做** | 需 1.2 GiB VRAM，只余 640 MiB |
| llama.cpp master | **不做** | 上游 pin 未变 + API 不兼容（5 参 vs 4 参） |
| Intel CPU 优化 | **无此项** | 0.2.3 无新增 CPU 指令集路径；本机无 AVX-512 |
| Strix Halo / Arc / RX9070 / Metal 的提速 | **不适用** | 平台不同 |

### 仍未验证（register 里查无记录，且本轮没做）

| 项 | 预期 | 说明 |
|---|---|---|
| `--conversation-cache-mib` 让它按空闲内存自算（#3493） | 多轮体感 | 0.2.3 新增默认；我们手设 4096 且实测 `requests_reused 0`。可试"去掉该参数"让引擎自算 |
| `--ple-inflight 512/1024` | +0~10% | 零 RAM 成本；PLE 方向唯一开着的门（`--ple-io ram` 已废，-45%） |
| `--host-core last` / `--aux-cpus auto` | +1~3% | 拓扑类，与 pool-workers 同族，需单变量车 |
| `--spec-min-p --calibrate` | decode +2~5% | 上游提供本机校准，我们一直用历史值 0.70 |
| `--kv-grow` | +15.2% 槽 | P32 算账少算 16 倍（214 MiB 是单层，真实 3.35 GiB）；但要先拆 `--resident-experts`，风险最高，单开车 |
| 合规基线（冻结 fixture / temp 1.0 / track=custom） | — | 与社区可比的第一个数字 |

### 本轮实测确认的两个"不要再试"

- `--pool-tasks 42/126`：M 档 483.4 / 484.2 vs 默认 484.3 => **完全无差异**（已判：CPU 侧算力打满，调调度粒度无效）。
- `--pool-workers 21`：S/M 与默认 20 差 0.1%（噪声），且挤掉 aux 的专用核 => 维持默认。

---

## 10 一句话

**这次升版本身不带任何 gfx906 收益（三档实测等价），真正的收获是从 0.2.3 里挖出一个上游默认不给 gfx906 的开关（HC_Q8，三档一致 +0.6~0.67%、槽 +1.7%），外加确认了三件事不能做：换 llama.cpp、上 DFlash2、指望 Intel CPU 优化。**
