# W828 · 升到上游最新（v0.2.8 / 引擎 0.1.54）并把 AMD 侧改动全部落到 gfx906

## AUDIT12 更正摘要（2026-10-31）

> 本文件已过 AUDIT12（W826–W831 对抗审计）。三处 P0/P1 已就地更正，明细见 `AUDIT12_W826_W831.md`：
>
> 1. **§6.1 的 read 三档不可比** —— `strata-0.1.54n` 缺 W793/rocBLAS（`rocblas` 字符串 0 个 vs 0.1.53 的 3 个），
>    而 rocBLAS 正打在 prefill 的 f16 GEMM 上。**"升级 0 回归 0 收益"只对 decode 成立。**
> 2. **层数 = 48（原写 60）** —— `native_experts.txt` 的 layer 0..47、`48×512=24576`。受影响：§6.14 的每窗口字节/带宽、
>    §6.15 的并集 94 GB、§6.16 的搬运 72 GB/15 GB/s（更正后 52 GB/11 GB/s，反而与 W829 的 12 GB/s 实测对上）。
> 3. **§6.8 的 exact 表是 19 项（原写 15）**，且 `GDN_HEAD/GDN_PP` 我们本就开着，"一项都没开"不成立。
>
> 另：§6.15/§6.16 的 TTFT 曲线是在 **0.1.54n（无 rocBLAS）** 上量的，生产已是 `n2`，常数项 **1197→915 ms**；
> "对外口径"的 500 tok≈1.9 s / 3K≈5.2 s / 8K≈11.7 s 应各减约 0.28 s（且 8K 由 7.2K 实测验算约 12.5 s，原 11.7 s 是外推）。



> 2026-10-31 01:0x · 起点：生产 `strata-0.1.53` · `--pack ud-q4_k_xl` · env 14 / args 33 · 配置指纹 `23da2da1`
> 目的：不是"要不要升"，而是**升完之后我们的平台上哪些 AMD 改动真的能跑起来、哪些结构上用不上**。

---

## 0 结论（先看这四条）

1. **上游最新就是 v0.2.8 / 引擎 0.1.54**（tag `v0.2.8` 2026-10-29T22:40Z；`main` HEAD `870aedd9` 2026-10-29T17:07Z，在 tag 之内）。没有 0.2.9。
2. **0.2.8 的 AMD 专属大改只有一件：verify/batch 窗口 8 → 16 行（HIP）**。我逐 hunk 看过它涉及的全部 GPU kernel，
   窄构建（`STRATA_VERIFY_MAX_T=8`）下**每一个 kernel 都只实例化原来的那套，bits 与 0.1.53 相同**。
3. **但 16 行窗口到不了我们的单请求路径**：`src/program/generate.cpp` 新增了一条硬检查
   `if (o.spec > kVerifyNarrowT) → "a speculative window holds 2..8 tokens"`。**solo/spec 窗口永远 ≤ 8 行**，
   16 行只给 `--batch` 的并发槽位用。⇒ 想吃到它，只有开 `--batch`（多并发）这一条路。
4. **我们的构建落在"auto=8"那一支**：`STRATA_HIP_GFX906=ON` 会把 `STRATA_ENABLE_CUDA` 置 ON、`STRATA_ENABLE_HIP` 留 OFF，
   而 CMake 的 `auto` 判定是 `if(STRATA_ENABLE_HIP) 16 else 8`。⇒ **必须显式 `-DSTRATA_WINDOW_MAX_T=16` 才拿得到 HIP 引擎本该有的 16 行**
   （上游默认没算上 gfx906 compat 这条支线）。这一点是可提上游的缺陷。

---

## 1 上游到底改了什么（引擎面 42 文件 / 148 文件全量）

| 改动 | 我们命中？ | 依据（源码逐字） |
|---|---|---|
| **16 行窗口**（HIP） | **只有 `--batch`** | `generate.cpp`：`if (o.spec > kVerifyNarrowT) { "--spec %d: a speculative window holds 2..%d tokens"; return 1; }` |
| `s2_expert_grouped` 两趟（`GMAX=8`） | 宽窗口才走 | `kGroupPasses=(kVerifyMaxT+7)/8`；`if constexpr (kWide) if (second) ...<GMAX>` |
| `expert_source` `kMaxWindowEntries` 128→256 | 宽窗口才走 | `kWindowMaxT <= 8 ? 128 : 256` |
| `resident_plan` 128→256 线程 | 宽窗口才走 | `kResidentPlanMax = kVerifyMaxT > kVerifyNarrowT ? 256 : 128` |
| `native_mmvq` 9..16 列实例 | 宽窗口才编 | `MAX_NCOLS = STRATA_VERIFY_MAX_T > 8 ? 16 : 8`；9..16 的 case 在 `#if` 里 |
| `native_bf16` / `native_moe` / `shared_expert` 上限 | 宽窗口才放宽 | `n_tok > kVerifyMaxT`（窄构建 = 8，与旧版同值） |
| `fused_gr_read_multi` 切片 | 宽窗口才走 | `if (n_tok <= kFusedGrMaxT) return ..._slice(...)` —— ≤8 走原实现 |
| **#4474** 自动缓存预留 256 MiB | **命中**（我们用 `--expert-cache auto`） | `auto_cache.hpp`：`kLateAllocMib = 256`，槽位按 `reserve + 256 MiB` 算 |
| **#4051** 新引擎等旧引擎还内存 | **命中**（我们重启频繁） | `expert_source.cpp`：`wait_for_ram(need, 20 s, 0.25 s, 2 s, ...)` |
| **#4518** PLE 表锁挡住对话缓存时归还锁 | **不命中**（`ulimit -l` 8 MB，`mlock` 拿不到） | `ple_residency.hpp`：`ple_lock_blocks_cache()` |
| **#4420** park 的 `--batch` slot 不再丢共享前缀 | **不命中**（无 `--batch`） | `conversation_cache.hpp`：`supersedes_richer()` |
| `STRATA_ROUTE_PRIOR` 默认改回 0 | 无变化（HIP 本来就是 0） | `sm120_series.hpp`：`route_prior_default()` 恒 `0.0f` |
| **工具调用容错**（98.3% vs 92.9%，1462 轮） | **命中，且是纯 Python** | `serve/frontend.py +242/−35`、`serve/server.py +77/−13`：`tool_call_recovery=True` 默认、`_Lenient` JSON 读、`param_end` 修 #4427/#4078 |
| DeepSeek / Metal / Arc / 四卡 profile | 不命中 | 平台无关或别的后端 |

---

## 2 为什么窄构建"逐位不变"—— 三个层面各自确认

1. **编译期**：`window_limits.hpp` 用 `STRATA_VERIFY_MAX_T`（CMake cache `STRATA_WINDOW_MAX_T`）一个数派生所有上限；
   `static_assert(kWindowMaxT == 8 || kWindowMaxT == 16)`。窄构建下 `kWindowMaxT=8=kVerifyNarrowT`，所有"宽"分支被 `#if`/`if constexpr` 编掉。
2. **kernel 实例**：`verify_kernels.cu` 把 `case 7: case 8:` 单列成 `kVerifyNarrowT, false` 实例，`default` 才是 16；
   即 8 行窗口拿到的就是 0.2.7 那个 instantiation。
3. **launch 路径**：`moe_grouped_s2_window(..., max_group=n)` 在窄构建里直接调 `moe_grouped_s2`（`max_group` 被 `(void)` 掉）。

⇒ 所以本轮 **窄构建的速度/精度数据只能用来证明"升级没有回归"，不能指望正收益**。

---

## 3 我们的构建落在哪一支（源码级）

`CMakeLists.txt:86-92`：

```cmake
option(STRATA_HIP_GFX906 "Build the CUDA targets for AMD gfx906 through HIP (wave64 compat layer)" OFF)
if(STRATA_HIP_GFX906)
  if(STRATA_ENABLE_HIP) message(FATAL_ERROR ...) endif()
  set(STRATA_ENABLE_CUDA ON CACHE BOOL "" FORCE)
endif()
```

注释逐字："with it on, STRATA_ENABLE_CUDA is on and STRATA_ENABLE_HIP stays off, **so every "CUDA" branch of the tree is the one taken**"。

而窗口的 auto 判定（`CMakeLists.txt:107-119`）：

```cmake
if(STRATA_ENABLE_HIP OR STRATA_ENABLE_CUDA)
  if(STRATA_WINDOW_MAX_T STREQUAL "auto")
    if(STRATA_ENABLE_HIP) set(_strata_window_max_t 16) else() set(_strata_window_max_t 8) endif()
```

⇒ **我们（HIP_GFX906）被算成 CUDA，auto=8**。
上游注释给 CUDA 定 8 的理由是 `CUDA_MODULE_LOADING=EAGER`（宽 kernel 一启动就吃 VRAM），
但**这条理由在 HIP 上不成立**（"a HIP code object loads on first use, so the extra kernels cost nothing until a wide window forms"）——
我们的 `.cu` 正是用 HIP 编的（`CMAKE_HIP_ARCHITECTURES=gfx906`、`/opt/rocm/llvm/bin/clang++`、`hip_compat` 头）。

⇒ **`-DSTRATA_WINDOW_MAX_T=16` 是正确的、不是超范围使用**；不显式给，就等于让 gfx906 白丢 HIP 引擎的能力。

---

## 4 源码级移植：第一个真实缺口（不是设计，是缺宏）

首次全量构建在 `src/core/dflash2.cpp:205-207` 失败：

```
error: use of undeclared identifier 'cudaDeviceGetStreamPriorityRange'; did you mean 'hipDeviceGetStreamPriorityRange'?
error: use of undeclared identifier 'cudaStreamCreateWithPriority';       did you mean 'hipStreamCreateWithPriority'?
```

根因链条：

- `dflash2.cpp` 是 **HOST translation unit（.cpp）**，它直接调 CUDA 运行时 API；
- 上游 wave32 HIP 后端（`STRATA_ENABLE_HIP`）用 hipify，`cuda*` 名字由工具改名 —— 所以上游自己不会踩；
- 我们的 **gfx906 compat 层** `include/strata/platform/hip_compat/strata_hip.h` 是**手写宏表**，
  它映射了 `cudaStreamCreateWithFlags` 却漏了 `cudaStreamCreateWithPriority` 与 `cudaDeviceGetStreamPriorityRange`；
- 这两个宏只存在于 `include/strata/dsv41/hip_extra.h`，而那个头只被 CMake 用 `-include` 喂给 dsv41 的测试目标。

**为什么 0.1.53 没暴露**：`build-0271` 里 `dflash2.cpp.o` 的时间戳比 `src0271` 的源码新（源码 10-27 解包，build 10-29 建），
ninja 判为 up-to-date **没有重编**。⇒ 0.1.53 的二进制里那段 dflash2 代码不是这份源码编出来的。这是**旧账**，本轮新构建才把它摊开。

**修法（已应用，2 行）**：`strata_hip.h` 在 `cudaStreamCreateWithFlags` 后补

```c
#define cudaStreamCreateWithPriority hipStreamCreateWithPriority
#define cudaDeviceGetStreamPriorityRange hipDeviceGetStreamPriorityRange
```

语义与 CUDA 一一对应（HIP 的两个 API 就是 CUDA 的同名物），无行为改变。单文件编译验证通过（51 warnings，0 error）。

---

## 5 我们的 AMD 补丁在 0.1.54 上是否还在

`src/kernels/cuda/qsa_decode_attn.cu` 是**我们改过、且上游 0.2.8 没改**的唯一热路径文件（74 个"与上游不同"的文件里唯一进产物的一个）：

- `md5 402e58da…` 在 `src0271` 与 `src028` 相同 ⇒ 升级没覆盖它；
- 与上游 v0.2.8 的 diff 只有 **37 行**，全部是我们 W794 的补丁：
  `use_query_swizzle` 扩到 `kv_mode == 3`（k8v4），以及 `attn_chunk_kernel<3, ...>` 两个实例。
- ⇒ **`STRATA_GFX906_ATTN_QUERY_SWIZZLE` 与 `ATTN_REDUCE12` 在 k8v4 上的收益，0.1.54 继续有效。**

其余 73 个差异文件是 `.bat/.ps1`、`metal/*`、`src/dsv41/*`（`STRATA_BUILD_DSV41=OFF` 不编）、`packaging/*`、`tests/*`、`docs/*` —— 都不进产物。

**上游全树校验**（`git trees/v0.2.8?recursive=1` 的 blob SHA 逐个比）：
本地 8012 文件（含 third_party 2837）、与上游逐字节相同 **5101**、不同 **74**、上游有我们没有 **54**（都是 apps/tests/docs）。

---

## 6 实测

### 6.1 窄构建 A/B（0.1.53 vs 0.1.54n，同 33 args / 14 env）

| 项 | 0.1.53 | 0.1.54n | 差 |
|---|---|---|---|
| decode 中位（5×128 tok，T=0） | **45.90 tok/s**（41.6 / 46.6 / 45.1 / 45.9 / 47.5） | **45.70 tok/s**（40.2 / 46.9 / 44.4 / 45.7 / 48.6；中位 45.70、均值 45.16） | **−0.44%**（噪声内） |
| read 1315 tok | 3.56 s | 3.34 s | −6.2% |
| read 2542 tok | 4.89 s | 5.07 s | +3.7% |
| read 4548 tok | 6.87 s | 7.54 s | +9.8% |
| **专家缓存槽位** | **7551 / 22.04 GiB** | **7463 / 21.79 GiB** | **−88（−1.17%）** |

**判读**：
- decode 差在噪声内（跨容器同配置实测漂 12-16%，A/A 都测到过）；read 三档方向不一致（−6.2/+3.7/+9.8），不是系统偏移。
- 唯一**确定**的差异是槽位：`#4474` 的 `kLateAllocMib=256` 从缓存里扣掉了 **正好 256 MiB**（22.04 → 21.79），
  与源码 `auto_cache_slots(free, reserve, blob, min_slots, 256)` 完全对得上；槽位 −1.17%。
- 结论（**AUDIT12 已收窄**）：**decode 0 回归、0 收益**；但 **read 三档不可比** ——
  两臂代码不同源：`strata-0.1.54n` 里 `rocblas` 字符串 **0 个**（0.1.53 为 3 个，`build-028.log` 有 2 条
  `rocblas_state_ ... not used`），而 rocBLAS 正打在 prefill 的 f16 GEMM 上（W830 §6 同镜像 A/B：常数项 1190→915 ms）。
  所以 read 的 −6.2/+3.7/+9.8% 混了"缺 W793"这一项，不能拿来判引擎版本。
- 注意：两臂的 `warm0` 差 60 倍（198 s vs 3.45 s）—— 第一臂在编译刚结束后跑，页缓存被冲掉，首个请求要把 71.7 GiB 专家重新读一遍。
  **这是环境噪声，不是引擎差异**；后续任何"首请求"读数都要看这一条。

### 6.2 生产切换（已完成）

- 二进制：`/data/bin/strata-0.1.54n`（`strata 0.1.54`，38,233,480 B），旧 `strata-0.1.53` 原样保留
- Python 层：镜像 `strata-gfx906:0.2.8`（`FROM 0.2.4p4` + `COPY serve strata_control strata_cli tools`）
- 配置：`exe` 改一行，备份 `data/strata-huihui-ud-iq4_xs.json.bak-w828`，新 md5 `6e569fe6…`
- 启动 236 s 就绪，`/health` ok，`/v1/models` 名字不变
- 冒烟：普通对话 2.7 s 正常；**工具调用成功**（`finish=tool_calls`，`get_weather{"city":"北京","days":[1,2]}`），
  serve 日志 `writing a tool call: get_weather: 113 of max 160 tokens, 39.6 tok/s`
- 回滚：`exe` 改回 `/data/bin/strata-0.1.53` + 镜像换回 `0.2.4p4`，配置备份在 `*.bak-w828`

### 6.3 calibrate（官方工具，引擎 0.1.54n，副本配置 `/data/w828_calib.json`）

跑完 `EXIT=0`，用时约 55 分钟（每次引擎重启要 255 s 载入 71.73 GiB）。

**它自己选的：**

```json
"settings": { "--pcie-frac": "0.20", "--spec-min-p": "0.50",
              "--adapt-every": "1", "--adapt-swaps": "80", "--adapt-decay": "0.97" },
"env": { "STRATA_SH_STREAM": "1" }
```

| 项 | 它测到的 | 我们复测 | 裁定 |
|---|---|---|---|
| `--pcie-frac` | 0: 44.4 · **0.2: 44.5** · 0.35: 39.8 · 0.55: 36.1 · 0.75: 32.7 · 1.0: 26.9（3 轮中位，单实例内） | — | **现值 0.20 已是全局最优**；0 与 0.2 在噪声内，0.35 起掉 11% |
| `--spec-min-p` | 0.3: 43.7 · **0.5: 45.4** · 0.7: 45.2（3 轮中位） | — | 0.5 只比 0.7 高 **0.4%** ⇒ 不动（低于 3% 门槛，也低于我们的 5%） |
| `--pool-workers` | 20: 43.6 · 13: 43.6 · 10: 42.9 · 5: 40.9（默认更好） | — | **不设**（默认最优） |
| `--adapt-*` 1/80/0.97 | 默认 44.8 → **49.4（+10.3%）**（单次，跨容器） | **见 §6.5：两轮长生成 ABBA，判据 `ms/window`，两对都是它更慢（+4.1% / +2.1%）** | **不采纳** |
| `STRATA_SH_STREAM=1` | 0: 40.4 → **1: 43.5（+7.7%）** | 未复测 | **待办**（上游也说明该值逐机不定，必须 ABBA） |

**方法学结论（重要，比参数更值钱）**：
`calibrate` 对**能在单实例内用 `strata_tune` 扫**的参数（`--pcie-frac`、`--spec-min-p`）跑 3 轮交替，这两项的结果我们完全信；
但对**每个值都要重启引擎**的参数（`--pool-workers`、`--adapt-*`、`STRATA_SH_STREAM`）**只测一次**——
跨容器 decode 漂 12-16%（W825 §3.3 已量过），于是 adapt 的"+10.3%"在我们 ABBA 下缩到 +1.6% 且方向不稳。
⇒ **calibrate 的"单实例内扫描"结果可直接用；"需重启"的结果必须我们自己 ABBA 复测。**

**另一条副产物**：`--pcie-frac` 的曲线解释了我们为什么一直是 20 — 20% 的 miss 走 PCIe 正好落在这张卡的拐点上，
再往上（0.35）CPU 少算了专家但 PCIe 也堵了，净掉 11%。

### 6.4 宽构建（`-DSTRATA_WINDOW_MAX_T=16`）与 `--batch 16`

**编译**：`build-028w` 全量通过（164/164，0 error），`strata 0.1.54`，**45,596,776 B**（比窄版大 **7.36 MB**，正是 9..16 的额外 kernel 实例），
`-DSTRATA_VERIFY_MAX_T=16`、含 `moe_grouped_s2_wide` 符号 ⇒ **gfx906 能编出 16 行窗口的全部 kernel**。

**运行（`--batch 16`）**：**装不下**，而且是结构性的：

```
strata generate: WARNING: --batch 16: slot 8's session does not fit on CUDA0 (2.95 GiB each, 1.22 GiB free); 8 slots
strata generate: --batch: 8 slot sessions on CUDA0 (2.95 GiB each); 1.22 GiB free
strata generate: --batch 8: the slot sessions take 23.60 GiB of VRAM on CUDA0 that the expert cache would otherwise hold
strata generate: native head upload: out of memory (156 MiB of 32752 MiB VRAM free on this GPU)
```

- **每个 slot 的会话要 2.95 GiB**（262144 上下文的 KV + buffer），不是我们原先按 k8v4 × 256K 估的 214 MiB；
- 16 slots 需要 47 GiB，引擎自己降到 8 slots（23.60 GiB），专家缓存被挤到没有 → head upload OOM，启动失败；
- ⇒ **16 行窗口在本机永远用不上**：solo 硬限 8 行（P182）+ batch 要 ≥9 slots 才进 9..16 行 + 9 slots 需 26.6 GiB VRAM（超过这张卡）。

**顺带的推论**：连 `--batch 2` 都要付 5.9 GiB（2 × 2.95），专家缓存 21.79 → ~15.9 GiB（槽位 −28%），
所以"并发摊薄权重读取"这条路在我们 **262144 上下文 + 32 GB** 的配置下空间很小
（上游那 +31~39% 是短上下文/小模型）。**`--batch` 从"待测"降级为"已知代价过高"**。

宽版二进制保留在 `/data/bin/strata-0.1.54w`（不参与生产），用于将来换小上下文或更大卡时验证。

### 6.5 `--adapt-*` 专项复测（两轮，改用相位表）

calibrate 报的 +10.3% 我第一轮用 128-token 生成复测，得到 +1.6% 且方向不一致。**这次重做，原因有三个，都是方法问题**：

1. **生成太短**。上游 `calibrate.py` 自己写了：`128-token answers end before it shows (on a Xeon E5-2673 v3 with DDR3, every 1 / 160 / 0.97 measured +0.7% with 128 tokens and +7.9% with 512-token answers)`。
   我的第一次复测正是 128 token ⇒ **机制还没走完就结束了**。这次改 **512 token × 3 条**（语料本身是"写 400 词"的工程题）。
2. **指标选错**。tok/s 是墙钟，同批漂 12-16%（P175）；正解是 `STRATA_DECODE_TIMING=1` 打出的 **`ms/window`**（GPU 事件计时，同臂 3 样本只差 ±3%）。
3. **没验证机制是否真的动作**。`--adapt-swaps 80` 是不是真的换了 80 个？日志行尾的 `swaps/window` 直接回答。

两臂：`ta` = 生产配置（`--adapt-every` 默认 4 / `--adapt-swaps` 96 / `--adapt-decay` 0.7）；`tb` = `1 / 80 / 0.97`。两臂都加 `STRATA_DECODE_TIMING=1`，顺序 **ta → tb → tb → ta**。

| 臂 | 3 条 512-token 的 `ms/window` | 中位 | tok/s 中位 | swaps/window |
|---|---|---|---|---|
| ta #1 | 39.80 / 40.96 / 38.41 | **39.80** | 44.17 | 13.4 / 8.7 / 10.1 |
| tb #1 | 41.22 / 43.08 / 41.42 | **41.42** | 42.10 | 13.8 / 13.7 / 14.6 |
| tb #2 | 38.31 / 40.15 / 39.61 | **39.61** | 45.77 | 3.0 / 13.1 / 15.9 |
| ta #2 | 38.78 / 42.51 / 37.26 | **38.78** | 45.37 | 13.5 / 8.0 / 10.3 |

**配对判读（`ms/window`，抗噪尺子）**：
- 对 1：41.42 / 39.80 = **tb 慢 4.1%**
- 对 2：39.61 / 38.78 = **tb 慢 2.1%**
- 两对**同向** ⇒ `--adapt-*` 1/80/0.97 比默认**略慢**，不是 calibrate 报的 +10%。

**机制层的解释（为什么参数没用）**：
- `swaps/window` 两臂都在 3-16 之间抖，**没有系统差异**（默认 8.0-13.5，adapt 3.0-15.9）。
- 这印证：我们的专家缓存命中率已经 **95.1-97.4%**，每轮能换的"缺失但仍常被路由"的候选只有约 14 个，
  `--adapt-swaps 80` 远大于候选池 ⇒ 参数是空转；`--adapt-every 1` 只是把同样多的交换摊到更多轮。
- 上游那个 +7.9% 是 DDR3（~24 GB/s）上的：那时"多换一点进 VRAM"能省掉很贵的 CPU 计算。
  我们是 **4 条 DDR4-2133 四通道（~68 GB/s）**（`dmidecode`：DIMM_A1/B1/C1/D1 各一条 32 GB），
  CPU 算 miss 的专家没那么贵，换进 VRAM 省下的还不够付 PCIe 搬运。

**结论：`--adapt-*` 不采纳，生产维持默认（4 / 96 / 0.7）。**

**这一轮顺带定死两条测量规矩**（比参数本身重要）：
- 对"跟随对话"的机制类参数，**生成长度要到 512 token**，且判据用 `ms/window` 不用 tok/s；
- 每个机制类参数都要先看**机制计数器**（`swaps/window`、命中率）确认它真的动了，再看速度。
  第一次复测就是"只看到 +1.6% 就下结论"，没注意 128 token 根本没让它走完。

### 6.6 `STRATA_SH_STREAM` 专项复测（四臂，512 token + `ms/window`）

calibrate 报 `=1` 比 off 快 7.7%（单项、跨容器），这是最后一个没结的参数。测前先把**上游三份互相矛盾的实测**摆出来（GitHub API 取的原文）：

| 来源 | 硬件 | 结论 |
|---|---|---|
| #816 | RX 6800 16 GB（gfx1030，**Windows**） | fork **on 慢 12-22%**（42.5 → 56.4 tok/s with `=0`） |
| #1272 | 2× RX 6900 XT（gfx1030，**Linux**） | fork **on 快 7-10%**（37.8 → 40.4 单卡，58.6 → 64.5 双卡） |
| 评论（R9700） | AI PRO R9700 32 GB（gfx1201，`--resident-experts`） | fork **on 慢 45%**（43.4 → 63.0 with `=0`） |
| 4× R9700 | — | off 快 13-45% |

上游在 `docs/AMD_HIP.md` 给了机理：**fork 要"藏"点东西**——窗口里有 CPU 专家时，shared expert 在 doorbell 发布后才 fork，
正好跑在 GPU 干等 CPU 池的那段时间里（它举的例子：4859 槽位、`GPU-reach wait 20.7 of 39.1 ms`）；
**每个被路由的专家都在 GPU 上时没有等待可填，fork 就只剩每层两次 cross-stream 事件依赖**。

**先量我们的机理条件**（`STRATA_DECODE_TIMING=1` 的 per layer-window 段）：

```
per layer-window: CPU experts 0.58 (0.70 entries), VRAM hits 21.41, PCIe 0.01; 10.4 swaps/window
```

⇒ 命中率 **21.41/(21.41+0.58+0.01) = 97.3%**，**每层窗口只有 0.58 个专家走 CPU**。也就是说：
我们的 `GPU-reach wait`（27-31 ms / 窗口，占 72%）**不是在等 CPU 池**，而是 VRAM 侧自己的读取；
fork 想填的那个洞在我们这里根本不存在。

四臂实测（`ta` = 未设，`tc` = `STRATA_SH_STREAM=1`，两臂都开 `STRATA_DECODE_TIMING`，各 3 条 512-token）：

| 臂 | `ms/window` | 中位 |
|---|---|---|
| ta #1 | 39.80 / 40.96 / 38.41 | **39.80** |
| tc #1 | 40.15 / 38.19 / 37.65 | **38.19** |
| tc #2 | 39.21 / 39.87 / 37.34 | **39.21** |
| ta #2 | 38.23 / 40.55 / 37.63 | **38.23** |

- 对 1：tc 比 ta 快 4.0%
- 对 2：tc 比 ta **慢 2.6%**
- **方向相反** ⇒ 噪声；均值差 0.7%。

**判定：不采纳，生产维持 HIP 默认（off）。**

**顺带又一次证明 tok/s 不能当判据**：同一臂（ta）在不同时间是 44.17 与 47.46 tok/s（+7.5%），
而 `ms/window` 在四次同配置臂里是 39.80 / 38.78 / 39.06 / 38.23（±2%）。

**这一条把参数层结清了**：`--pcie-frac`（0.20 最优）、`--spec-min-p`（0.5 只高 0.4%）、`--pool-workers`（默认最优）、
`--adapt-*`（慢 2-4%）、`STRATA_SH_STREAM`（±2% 噪声）—— **五项全部不需要改**，我们的配置已经在这台机器的最优点上。

### 6.7 calibrate 重跑一次：它自己可重复吗？

同一台机器、同一个引擎（`strata-0.1.54n`）、同一份配置，跑了两次（3425 s / 3273 s）。**两次给出的建议完全不同**：

| 项 | run1 | run2 |
|---|---|---|
| `--pcie-frac` | 0.20 | **0.00** |
| `--spec-min-p` | 0.50 | **0.70** |
| `--adapt-*` | 1 / 80 / 0.97 | **1 / 160 / 0.97** |
| `STRATA_SH_STREAM` | 1 | **（未设）** |

逐项拆开，**能信的和不能信的一刀切得很干净**：

| 项 | 测量方式 | run1 | run2 | 可重复？ |
|---|---|---|---|---|
| `pcie_sweep` 曲线 | 单实例内 `strata_tune`，3 轮交替 | 0:44.45 · 0.2:44.54 · 0.35:39.83 · 0.36:37.97 · 0.55:36.11 · 1.0:26.88 | 0:44.13 · 0.2:43.55 · 0.35:40.73 · 0.36:38.88 · 0.55:35.63 · 1.0:27.77 | **是**（排序完全一致，数值差 ≤3.3%） |
| `min_p_sweep` | 同上 | 0.3:43.65 · 0.5:**45.44** · 0.7:45.21 | 0.3:42.64 · 0.5:45.20 · 0.7:**45.42** | **最优点互换**（差 0.5%，等价） |
| `workers` | 每值重启 | 20:43.59 · 13:43.57 · 10:42.93 · 5:40.90 | 20:43.46 · 13:43.37 · 10:42.93 · 5:40.16 | **是**（几乎逐位相同） |
| `adapt` | 每值重启，**单次** | default 44.82 · **1/80: 49.43 (＋10.3%)** · 1/160: 43.74 | default 46.70 · 1/80: 45.46 · **1/160: 50.96 (＋9.1%)** | **否，且结论相反**。同一候选两次差 5-7 tok/s；**哪一臂恰好落进"快"的容器状态就赢** |
| `sh_stream` | 每值重启，**单次** | 0:40.43 · **1: 43.45 (＋7.5%)** | **0: 41.37** · 1: 40.94 (−1.0%) | **否，结论相反** |
| `confirm`（默认 vs 标定值） | 单实例内 3 轮交替 | 0.36/0.5 = **39.09** vs 0.2/0.5 = **44.46** | 0.36/0.5 = **38.62** vs 0.0/0.7 = **45.48** | **是，且幅度很大** |

**三条结论**：

1. **calibrate 的"单实例内扫描"可以直接信**（pcie 曲线、workers、confirm 三次都稳到 ≤3.3%）；
   **"每个值重启引擎"的项完全不能信**——噪声 ±10%，足以让任意候选看起来赢 7-10%，两次跑会给出相反答案。
2. **`--spec-min-p` 的"最优点"本身在噪声里**：0.5 与 0.7 只差 0.5%，两次各选一个。**这一项不该有"最优值"这个概念**，
   只能得出"0.3 明显差（−4%），0.5-0.7 等价"。
3. **一个可重复、且比参数本身更值钱的发现：引擎按带宽自己算的 `--pcie-frac 0.36`，比最优（0 或 0.2）慢 13.7% / 17.8%**
   （两次 `confirm` 都是 3 轮交替，方向与幅度一致）。我们的 `native pack` 路径走 `pcie_frac_for_gbps(实测带宽, base)`，
   在 PCIe 3.0 x16 + 44 线程四通道 DDR4 上它**高估了"该走 PCIe"的比例**——CPU 算专家没有它假设的那么贵。
   ⇒ 显式写 `--pcie-frac 0.20` 是必要的（否则默认 0.36 慢 13.7%），这一点值得提上游。

**行动：一个参数都不改。** `0.00` 与 `0.20` 在两次 sweep 里互有胜负（差 1.3%），
生产保持 0.20（已在生产验证过、且对 PCIe 带宽波动更鲁棒）；`spec-min-p 0.70`、`adapt` 默认、`SH_STREAM` off 全部维持。

### 6.8 AMD 开关全空间审计：上游给集显开的 19 项 exact 优化，我们只手动开了 2 项（AUDIT12 更正）

前面几节都是"0.2.7.1→0.2.8 改了什么"。这一节换问法：**上游所有 AMD 优化里，我们还有哪些没开？**

**上游仍是最新**（`v0.2.8`，`src` 最新提交 `b119f40f` 2026-10-29T14:39Z 在 tag 内，`main` HEAD `870aedd9`）。

`docs/AMD_HIP.md`（0.2.8 版）提到 **69 个 `STRATA_*`**，其中 29 个我们没设。逐个归类后**没有一个是 gfx906 上白捡的速度项**：

| 类别 | 数量 | 例子 |
|---|---|---|
| gfx11/gfx12 硬件专属（要 WMMA/MFMA） | 8 | `HIP_WMMA`、`PF_GEMM`、`SCORES_THREAD`、`SELECT_WMMA`、`GDN_CHUNKED`、`PF_FUSED`、`HIP_QUEUE_PRIME`、`HC_PERSIST`（wave32） |
| iGPU prompt set（Radeon 780M） | 5 | `PA_FAST`、`HC_UPMIX`、`IGPU_PROMPT_SET` 等 |
| 默认即最优 / 启动期 | 4 | `HIP_ROUTER_OLD`（换成慢的）、`PREFILL_WARM`（arena 加载时的预热，**它在帮我们**）、`TOPK_OLD`（90K-135K 带才相关）、`FILE_CACHE_OLD_RULE` |
| 已开 | 1 | `PLE_AUTO_RAM`（日志里 "chosen by the residency policy" 就是它） |
| 比现有路径慢 | 1 | `RDNA2_SGEMM`——文档明写 "Slower than the FP16 route"，而我们 `PROMPT_F16=1` 已走 FP16 |
| 已否（上一轮） | 1 | `SH_STREAM` |

**真正的死角在另一张表**：`src/core/arch_defaults.cpp` 里 gfx1151 的 **19 项**（`arch_defaults.cpp:58-90` 逐条数得；原文写 15 项，AUDIT12 更正） "Exact (bitwise) on Aurora" 优化
（`Q8_PACKED`、`Q6_PACKED`、`MMVF_ROWS`、`ATTN_LANECELL`、`EXPERT_V2`、`LFUSE`、`GDN_SPLIT`、`QFUSE`、`PLE_BATCH`、
`HC_UPMIX`、`HCD_EXACT`、`CVEC_FUSE`、`GDN_CONVL2`、`GDN_NOY`、`TOPK_REG_MIN_BLOCKS`）。
它们在代码里**没有架构门**（只是 `getenv` 读取），上游只在 Strix Halo（gfx1151，RDNA3.5 集显，wave32）验过，
**从未在任何独显上测量**。这是"所有 AMD 优化都扩展到我们平台"这句话真正指的东西。

**本轮实测 5 项**（两臂一组，`ms/window` 判据，各 6 条 512-token 测量，与同批 `ta` 基线比）：

| 臂 | 开关 | `ms/window` 6 条 | 中位 | 相对基线 |
|---|---|---|---|---|
| **ta**（基线） | — | 37.46 / 38.98 / 36.85 / 39.47 / 40.88 / 36.62 | **38.22** | — |
| **td** | `ATTN_LANECELL` + `MMVF_ROWS` + `LFUSE` | 38.50 / 37.61 / 37.08 / 38.76 / 37.98 / 36.27 | **37.80** | **+1.1%** |
| **te** | `EXPERT_V2` + `GDN_SPLIT` | 38.72 / 39.49 / 37.65 / 40.11 / 38.74 / 36.91 | **38.74** | **−1.4%** |

配对方向：td `+0.4% / −3.8%`、te `−3.4% / +1.8%` —— **都不稳定**，合并后都在 ±1.5% 内。
**`td` 唯一的正面信号是方差减半**（6 条跨度 1.42 ms vs 基线 4.26 ms，`LFUSE` 少 launch 可能真的压了抖动），
但中位没动，不够进门槛。

**为什么全部无效——一个统一的解释**（这比逐个否掉有用得多）：

我们的 `decode timing` 把窗口时间切成 `verify 34.0 (GPU-reach wait 28.0 + per-layer host 4.1) + draft`，
即 **GPU-reach wait 占 77%**：GPU 有 3/4 的时间在等专家数据（VRAM 读 + 少量 PCIe），不是在算、也不是在等 launch。
上面这 5 个开关全都属于"**省算力 / 省 launch / 提高小 kernel 效率**"，被 77% 的等待直接淹没。
**它们的设计场景是 16 GB 集显**（数据都在统一内存里、等待很短、算力才是瓶颈）——前提与我们相反。

**结论：这 5 项全部不采纳。** 剩余 10 项（`Q8_PACKED`/`Q6_PACKED`/`QFUSE`/`PLE_BATCH`/`GDN_CONVL2`/`GDN_NOY`/
`CVEC_FUSE`/`PF_PAD`/`TOPK_REG_MIN_BLOCKS`/`HC_UPMIX`）按同一逻辑优先度很低：
它们同样属于"省算力/省 launch"类别，而 `Q8_PACKED`/`Q6_PACKED` 改的是权重内存布局（与我们的 `HC_Q8=1` 交互风险高），
真要试应先解决**那 77% 的等待**，而不是在剩下的 23% 里抠 1%。

### 6.9 `--batch 2` 的等待账：账算完了，**不可摊薄**

§6.8 把 77% 的等待定为主项后，唯一有理论依据的方向是"用并发把等待摊到两个 token 上"。
上一轮我否掉 `--batch 2` 只算了 VRAM 账（每 slot 2.95 GiB），**没算等待账**。这次补上。

**代价（实测）**：`filling the GPU's expert cache (7463 → 5447 experts, 21.79 → 15.88 GiB)`，槽位 **−27%**，与预测一致。

**单流（一个请求，验证是否回归）**：44.37 tok/s 中位（基线同批 45-47）⇒ **−3~5%**。

**双流（两个请求同时发，各 512 token，3 轮）**：

| 轮 | 流 0 | 流 1 | 合计 |
|---|---|---|---|
| 1 | 25.75 tok/s（19.9 s） | 25.15（20.4 s） | **50.9** |
| 2 | 25.41（20.0 s） | 23.77（21.3 s） | **49.2** |
| 3 | 24.67（20.8 s） | 23.00（22.3 s） | **47.7** |
| 中位 | — | — | **49.18** |

**判读**：双流合计 49.2 tok/s，**只比单流的 45-47 高 5-8%，远不是 2 倍**；
每流从单流的 22 ms/token 掉到 **40 ms/token（+82%）**。
对"两个人都要 512 token"的场景，`--batch 2` 总耗时 20.5 s 对串行 22.8 s，**只快 10%**，而每个人的体感从 45 掉到 25 tok/s。

**为什么摊不动——机理**：并发能共享的只有**每窗口读一次的东西**（dense 权重、shared expert、head）。
我们的 77% 等待在**专家读取**上：K=10 路由、512 个专家，两个请求每层的专家集合交集期望只有 `10×10/512 ≈ 0.2` 个，
而每层 VRAM 命中 21.4 个 ⇒ **跨请求共享率约 1%**。专家读取几乎完全无法共享。
上游那个 "+31~39%" 是在 dense 主导的小模型 / 短上下文上测的。

**结论：`--batch 2` 不采纳。** 这条把 §6.8 的推论闭环了：
**77% 的等待既不能靠省算力绕开，也不能靠并发摊薄**——在这台机器（262144 上下文 + UD-Q4_K_XL + 32 GB）上，
它已经接近这三个约束下的性能边界。真要再往上，只有改变约束本身（更低位宽 / 更小上下文 / 更大显存）。

### 6.10 数值债总量：**KL 0.0293**（底噪 0，账本上第一次有这个数）

记了十几轮的"8 个会改 bits 的开关叠在一起值多少 KL"，这次量了其中 **5 个**
（AUDIT12：账本 8 项里 `MMQ_KQ` 保留、`GDN_HEAD`/`GDN_PP` 根本没进表，实测只翻了 KV / RT_SKIP / PROMPT_F16 / SELECT_SIMT / HC_Q8）。方法沿用 W824 §10 的口径（`STRATA_LOGPOS` +
`STRATA_LOGPOS_TOPK=64` → `kl_prop` 配对 KL），并按 W826 的硬前提**把 `STRATA_PREFILL_CPU_SHARE` 固定为 0**
（否则底噪 0.025 与效应同量级，只能得"判不了"—— W824 第一次就是这么废掉的）。

**三臂**（同一引擎、同一 8 个 prompt 顺序、`share=0`）：

| 臂 | KV | RT_SKIP | PROMPT_F16 | SELECT_SIMT | HC_Q8 |
|---|---|---|---|---|---|
| **E0**（生产全量） | k8v4 | 7 | 1 | 1 | 1 |
| **E0b**（同 E0，底噪） | k8v4 | 7 | 1 | 1 | 1 |
| **Eall**（最小近似） | **fp16** | **0** | **0** | **0** | **0** |

**底噪 = 0（逐字节）**：`E0r.tsv` 与 `E0br.tsv` **md5 完全相同**（`f224eccc…`，各 48 行）。

**结果（45 个共同 scored 位置）**：

| 配对 | n | KL mean | KL median | argmax 一致 | top-10 重叠 | mean\|Δlp_tgt\| |
|---|---|---|---|---|---|---|
| E0 ‖ E0b（底噪） | 45 | **0.0000** | 0.0000 | 100.0% | 1.00 | 0.00000 |
| **E0 ‖ Eall（总账）** | 45 | **0.0293** | 0.0001 | **97.8%** | **0.85** | **0.13327** |
| E0b ‖ Eall（复核） | 45 | 0.0293 | 0.0001 | 97.8% | 0.85 | 0.13327 |

**判读**：
- 总量 **KL 0.0293**，落在 W825 定的 0.02–0.05 区间（<0.02 全结清、>0.05 必须二分）。**不需要立刻二分**，
  但要记账：这是**我们的额外近似**的边际代价（不含 4-bit 量化本身的损失）。
- **median 0.0001 而 mean 0.0293** ⇒ **一半以上的位置几乎不动**，代价集中在少数位置；
  argmax 只有 **2.2%** 的位置换了，top-10 平均少 1.5 个候选。
- 对照上游给的单 `RT_SKIP` 量级 0.003–0.006：我们这 **5 项**叠加是它的 **5–10 倍**，量级自洽。
- 口径提醒：`E0` 本身已是 UD-Q4_K_XL（4-bit 权重），所以 0.0293 是"在 4-bit 之上再加的近似"，
  不是"相对 fp16 模型的偏差"。

**这一项结清。** 若以后要压这个数，最省的办法是先二分（`RT_SKIP=7` 与 `k8v4` 各占多少），
但那要再花两个窗口，而 0.0293 已经在可接受档内。








### 6.11 投机窗口策略（`--spec` 上限 × `--spec-min-p` 门槛）：全轴关闭，且在**平地**上

§6.8 只测了"开关类"优化，从没动过**窗口策略**。而按 §6.8 自己的逻辑，窗口宽度是唯一能"把一个窗口的固定成本摊到更多 token 上"的乘数——
所以必须量。**8 条臂、6 个新配置、两组 ABBA**（每组 3 条 512-token 贪心，判据 `tokens/window ÷ ms/window`，不是 tok/s）。

> **AUDIT12 注（判据口径）**：声明的是 `tokens/window ÷ ms/window`，但下表 `tok/s` 列与"相对基线"列其实是 **wall tok/s**。
> 两列相差 1.2–3.7%，与要判的效应同量级。按**声明判据**复算：`ta` 1.79/39.44=**45.38**、`th` 1.79/37.50=**47.73（+5.2%）**、`tk` 1.63/35.24=**46.25（+1.9%）**。
> 所以"平地 / 生产在正中"这个结论**只在 wall 口径下成立**；换判据列，`th` 反而领先。要用哪一列，必须先把两列的差说清。

先看基线为什么值得怀疑：生产 `--spec 4` 下 **平均只用到 2.18 行**（`avg T 2.18`），而**按深度实测接受率是
80.2% / 76.9% / 57.9%**（深度 0/1/2，样本 187/91/38）。也就是说窗口开得比用到的宽，门槛先把窗口截断了。

| 臂 | spec 上限 | min-p | 额外 | T | tokens/窗口 | ms/窗口 | **tok/s** | 相对基线 |
|---|---|---|---|---|---|---|---|---|
| **ta**（生产） | 4 | 0.70 | — | 2.18 | 1.79 | 39.44 | **47.05** | — |
| ta2（复测） | 4 | 0.70 | — | 2.21 | 1.79 | 38.69 | 46.27 | −1.7% |
| ta3（复测） | 4 | 0.70 | — | 2.06 | 1.71 | 37.86 | 45.71 | −2.8% |
| **tf** | **8** | 0.70 | — | 2.32 | 1.84 | 39.39 | **44.97** | −4.4% |
| **tg** | 8 | **0.50** | — | **3.35** | 2.03 | **50.80** | **39.96** | **−15.1%** |
| **th** | 8 | 0.50 | **`STRATA_SPEC_COST=1`** | 2.28 | 1.79 | 37.50 | 46.03 | −2.2% |
| **tk** | 8 | **0.85** | — | **1.79** | 1.63 | 35.24 | **47.01** | −0.1% |
| **tl** | 8 | **0.90** | — | 1.64 | 1.51 | 33.76 | 45.66 | −3.0% |

**四条判读**：

1. **上限不是约束，门槛才是**。`--spec 4 → 8`（tf）后 T 只从 2.18 变 2.32，tok/s 落在基线自身漂移内
   （基线三条 `47.05 / 46.27 / 45.71`，跨度 **1.34 tok/s = 2.9%**）。所以"把上限抬到 8"这件事本身是空操作。
2. **放松门槛是明确亏损**（tg −15.1%）。机理可测：门槛 0.50 让 T 涨 54%（2.18→3.35），
   tokens/窗口 只涨 **13%**（1.79→2.03），而 ms/窗口 涨 **29%**（39.4→50.8）。
   原因在**专家并集**：`VRAM hits`（每层-窗口读到的专家数）从 **19.9 → 31.4**（+58%），
   并且新增行的接受率只有 **62%**（深度 1–4：62% / 62.5% / 52.6% / 62.5%）。**加的行大多被拒，但要付全额读取**。
3. **收紧门槛没有收益**（tk/tl）。门槛 0.85 把 T 压到 1.79、ms/窗口 省 4.2 ms，但 tokens/窗口 也掉 0.16，
   两者相抵，tok/s 仍 47.01。门槛 0.90 掉到 45.66。
4. **引擎自己的成本感知规则给出了同一个点**（th）：`STRATA_SPEC_COST=1` 按实测每行成本算 tokens/ms，
   它把 T 收到 **2.28**、tok/s 46.03 —— 与我们门槛 0.70 得到的 2.18 几乎重合。
   **这是独立验证：生产配置已经站在最优点上。**

**结论：窗口策略是一段**平地**（T ∈ [1.6, 2.4] 内 tok/s 全在 45.7–47.1），生产在正中；T>3 才是悬崖。不改。**

### 6.12 更正 §6.8 的解释：那 77% 不是"在等专家"

§6.8 用 `GPU-reach wait 28.0 / 38.2 ms = 77%` 推出"GPU 四分之三时间在等专家数据"，并用它解释
为什么 5 个开关都只有 ±1.5%。**这个读法错了**，本轮拿到了逐 kernel 的分解（引擎自己打的
`strata decode GPU stages (ms/window)`，`verify.cpp:2487-2488` 的标签表）：

| 组成 | ms/窗口（GDN+QSA 合计） | 占比 |
|---|---|---|
| **专家 VRAM 读取**（`VRAM hits`） | **10.51** | **23.4%** |
| **两条 dense MLP 支路**（`hc0/hc1` 的 norm+down+up） | **7.46** | **16.6%** |
| GDN 层主体（q8 gemv 2.44 + z 1.55 + out-proj 1.62 + rec 0.67 + ab 0.52 + conv 0.21） | 7.01 | 15.6% |
| 等待（waitA/waitB/PCIe grp/waitCPU/copy+combine/gap） | 6.50 | 14.5% |
| QSA 层主体（q+q-idx 1.67 + attention 1.78 + scores+topk 0.89 + out-proj 0.60 + kv 0.83） | 5.88（子项和 **5.77**，余 0.11 未归类 —— AUDIT12 P2-5） | 13.1% |
| 路由（`router+plan+bell`） | 3.84 | 8.5% |
| shared expert + 量化 | 2.04 | 4.5% |
| head | 1.73 | 3.8% |
| **合计** | **44.98** | 100% |

**关键更正**：`GPU-reach wait` 是**宿主机在等 GPU 到达某个里程碑**（host 侧空转），不是 GPU 在等数据。
一个窗口的 GPU 时间被摊在 **15+ 个 kernel** 上，**最大单项只占 23.4%**。

这一条同时解释了 §6.8 的全部结果：**表里 >5% 的五项（专家读取 23.4% / 超连接 16.6% / GDN 15.6% / 等待 14.5% / QSA 13.1%）没有一项能靠单个开关整块拿掉**（每项本身又摊在多个 kernel 上），所以每一项"省算力/省 launch"的开关都只值 ±1.5%。
不是说优化被"等待淹没"，而是**分母本身就分散**。以后判断这类开关，先看这张分解表里它对应多大规模的 kernel，
不要先假设有个巨大的主项。

### 6.13 关掉自适应层（`--adapt-swaps 0`）：−4~−6%，机理清楚

4 臂（ta / tm / tm / ta，各 3 条 512-token 贪心）：

| 臂 | swaps/窗口 | CPU 专家/层-窗口 | VRAM 命中/层-窗口 | T | tok/win | ms/win | tok/s |
|---|---|---|---|---|---|---|---|
| **ta（生产）** | 7.0 | 0.61 | 20.3 | 2.17 | 1.78 | 38.46 | **46.28** |
| tm | **0** | **2.93** | **14.3** | 2.06 | 1.76 | 39.53 | 44.52（−3.8%） |
| tm2 | **0** | **2.93** | **14.3** | 2.07 | 1.72 | 39.32 | 43.49（−6.0%） |
| ta2 | 4.0 | 0.63 | 20.5 | 2.16 | 1.78 | 37.55 | 45.48（−1.7%） |

**机理（这条比结论有用）**：关掉自适应后，路由到的专家被搬出 VRAM（20.3 → 14.3/层），
**每层多 2.3 个专家落到 CPU 去算**（0.61 → 2.93，+380%），省下的那点 swap 开销远不够付 host 时间。

**顺带纠正一个前提**：稳态下 `adapt wait` 只有 **0.11 ms/窗口**（首请求 1.5 ms 是冷启动），
所以"关掉它能省 1.4–2.4 ms"根本不成立 —— 上一轮相位表里的 1.4–2.4 是**含冷启动的臂均值**，我读错了。
⇒ **默认 `--adapt-every 4 --adapt-swaps 96` 是对的，不改。**

### 6.14 降位宽（UD-Q3_K_XL）的账：+6% 换 2.3 倍 KL，**建议不动**

先把家底量清（`data/packs/ud-q4_k_xl/native_experts.txt` + `conversions.json`，类型 id 按 `ggml.h:389-429` 核实）：

- 专家载荷 **77.0 GB**，占 111.3 GB 模型的 **69%**；单专家 **3.07 MB**（layer 0：gate/up=Q4_K id 12、down=Q5_1 id 7）
  到 **3.93 MB**（layer 2：Q5_K id 13、Q8_0 id 8）。
- 每窗口专家读取量 ≈ 21.4/层 × **48 层** × ~3.1 MB ≈ **3.2 GB**；对应 `VRAM hits` 的 10.51 ms ⇒ **约 300 GB/s（MI50 峰值的 ~30%）**
  （AUDIT12 更正：模型是 **48 层**，`native_experts.txt` 的 layer 0..47 + `48×512=24576` 与 W829 §0 的 24576 实例一致；原写 60 层/3.9 GB/375–400 GB/s）
  （MI50 HBM2 峰值约 1 TB/s 的 37–40%，对单/双行 GEMV 属正常）。

若换 **UD-Q3_K_XL**（Unsloth 官方体积 111.3 → **90.0 GB**，−19%，且差距几乎全在专家上 ⇒ 专家约 −27%）：

| 项 | 现值 | 换成 Q3 | 说明 |
|---|---|---|---|
| 专家读取 | 10.51 ms/窗口 | ~7.7 ms | 按字节线性推 |
| decode | 46 tok/s | **~49 tok/s（+6%）** | 窗口 45 → ~42 ms |
| **top-1 一致率**（对 BF16） | **92.3%** | **88.3%** | Unsloth 官方 KLD 表 |
| **平均 KLD**（对 BF16） | **0.047** | **0.107** | 同上，**2.3 倍** |
| 总量（叠加我们 0.0293 的工程近似） | ~0.076 | ~0.136 | **+79%** |
| 支持风险 | — | **高** | 现役专家类型只有 12/13/7/8；**Q3_K(11)、Q2_K(10) 在 Qwen 专家路径没有显式分派**（`kQ3_K` 只出现在 dense 的 `native_mmvq` 调优表与 DeepSeek 引擎） |

**结论：换手率不划算。** +6% 速度的价格是质量档整体降一级，且要先解决类型支持。
真要更快，优先**不动质量**的两条：更大显存（命中率→100%、等待消失）、或把上下文降到 16-32K 换 `--batch`/16 行窗口。

**顺带把"换档"这条轴横着比完**（Unsloth 同一张 KLD 表，表内可比、绝对值不可跨源）：

| 档 | 体积 | top-1 | KLD | 相对现档 |
|---|---|---|---|---|
| **UD-Q4_K_XL（现档）** | **111.3 GB** | **92.3%** | **0.047** | — |
| UD-Q5_K_XL | 158.3 GB | 93.7% | 0.030 | 体积 +42%，质量只 +1.4pt ⇒ 装不下，换不回 |
| UD-IQ4_XS（我们上一档） | 93.7 GB | 89.6% | 0.084 | 省 16% 字节但 KLD 翻 1.8 倍 ⇒ 回不去 |
| UD-Q3_K_XL | 90.0 GB | 88.3% | 0.107 | 省 19% 字节、KLD 翻 2.3 倍 ⇒ 不划算 |

⇒ **现档正好是"质量/字节"这条曲线上的拐点**：往下每省 15–19% 字节要付 1.8–2.3 倍 KL，往上 +42% 体积只换 1.4pt。
这台机器上 111.3 GB 已经在可装的上沿，所以**这条轴也到界了**。

### 6.15 TTFT 第一次量清：1.20 s 固定 + 1.316 ms/token，且 prefill 的数学路径值 64%

以前只有两个零散点（W803：1.03 / 1.56 s）。这次**不停服**在生产上量曲线：发**不同文本**的 prompt
（避免 prompt 缓存命中），`max_tokens=1`，墙钟即 TTFT，每个长度 3 条、重复性 ±1%。

| 提示 tokens | 1151 | 2213 | 4365 | 拟合 3000 | 拟合 8000 |
|---|---|---|---|---|---|
| TTFT | 2.87 s | 4.00 s | 6.86 s | 5.15 s | 11.7 s |

线性拟合：**TTFT = 1197 ms + 1.316 ms/token**（边际 **760 tok/s**）。
**缓存命中对照**：同一个 7123-token prompt 再发一次只要 **0.296 s**（≈**24k** tok/s；原文写 27k，AUDIT12 复算 7123/0.296=24.1k）
⇒ 多轮对话只付新增 token 的价，**那 1.2 s 是"新 prompt"一次性的**。

再把 prefill 的数学路径做 A/B（`STRATA_PREFILL_MMQ=0` = 全 FP16；其余 33 args / 14 env 与生产完全一致，
prompt 种子相同）：

| 路径 | 固定项 | 边际 | 1151 tok | 4365 tok |
|---|---|---|---|---|
| **现役（MMQ，`mmq_plan()` 默认开）** | **1.20 s** | **760 tok/s** | 2.87 s | 6.86 s |
| 全 FP16 | 3.06 s | 463 tok/s | 6.22 s | 12.42 s |

**两条结论**：

1. **MMQ 值 +64% prefill 吞吐**，并把固定项砍掉 1.86 s。⇒ §6.8「单项只有 ±1.5%」的结论**只适用于 decode**；
   在 prefill 上，数学路径的选择是**数量级**的。**`STRATA_PREFILL_MMQ` 永远不要设 0**（踩一脚慢 **1.64 倍**；原文写 1.8 倍，AUDIT12 复算 760/463）。
2. **固定项的来源被判定了**：数学路径一换，固定项从 1.20 s 涨到 3.06 s ⇒ 它不是 HTTP/模板开销，
   而是**第一个 chunk 的 staging + 计算**。所以它不能靠"减框架开销"拿掉，只能靠更快的内核。
3. **AUDIT12 更正：上表 FP16 那一行自相矛盾** —— `3.06 s + 1151/463 = 5.55 s`，表里却写 6.22 s；
   若以 6.22 s 与 12.42 s 反解，则是 `4.00 s + 518 tok/s`。两组数**不能同时引用**。
   结论（FP16 明显更慢）不受影响，但引用这条时只能引"固定项"或"边际"其中之一。
4. **这条结论有对照臂，但原稿漏记**：同一 harness（停生产、起容器、3 条热身、33 args/14 env）跑默认 env 得
   **1206 ms + 1.317 ms/tok**，与活生产的 `1197 + 1.316` 吻合 ⇒ **基线不是冷启动伪影**。
   这一臂是本节结论成立的关键，缺了它，读者无法排除"热引擎 vs 冷容器"的替代解释。

顺带否掉一个候选：**`--prefill-pipe` 是层切分专用**（`generate.cpp:712` 注释、calibrate 也这么写），
单卡无意义 —— 省了一次白跑。

**落地口径**（**AUDIT12 已按 n2 重算**：常数 915 ms + 1.316 ms/tok）：新对话 500 tok ≈ **1.6 s**；3K ≈ **4.9 s**；8K ≈ **12.2 s**
（>4.3K 后边际会变大，纯线性外推给 11.7 s、偏低；原文 1.9/5.2/11.7 是 0.1.54n 的口径，已过期 0.28 s）；
同一对话追加 ≈ **0.3 s + 1.3 ms × 新增 token**。

**那 1.2 s 是什么（未定，但排除了两条）**：

- 启动日志写死 `strata serve: prompt chunk auto: 8192 tokens, a 384-slot ring`，当时测的 prompt（≤4.4K）**都在一个 chunk 内**
  （§6.16 另外测了 7.2K 与 14.3K，后者已跨 chunk，另论 —— AUDIT12 P2-10）
  ⇒ 固定项**不是**多 chunk 的重复 staging，分块这条路排除。
- 若它是"把 chunk 的专家并集从主机搬到 VRAM"：并集 ≈ 512 专家 × **48 层** × 3.07 MB ≈ **75 GB**（AUDIT12 更正：原按 60 层写 94 GB），
  走 PCIe 3.0 x16（12.6 GB/s）要 7.5 s，走 DDR4 四通道（≈68 GB/s）要 1.4 s —— **只有后者量级接近实测 1.2 s**。
- **但这条解释站不住**：A/B 只换了数学路径（MMQ ↔ FP16），**要搬的字节没变**，而固定项从 1.20 s 涨到 **3.06 s（2.55×）**
  ⇒ 固定项里至少有一大部分是**首 tile 的计算/setup**，不是纯搬运。
- 两种解释各自都有一处对不上（搬运解释不了 2.55×；计算解释不了"1200 token 也算出 1.2 s 的常数"）。

⇒ **结论：这 1.2 s 的构成在 0.1.54 上无法判定**，因为当时只查到 decode 的相位表（`STRATA_DECODE_TIMING`）。

> **W834 更正（2026-10-31）**：上面这句是错的 —— **prefill 侧有计数器**。
> `src/prefill/prefill.cpp:2731` 起定义了 `STRATA_PREFILL_TIMING=1`，打 **21 个相位**：
> embed+steps / hc read / gdn / qsa proj / qsa indexer / qsa select / qsa attn / router+shared /
> **host grouping** / gather / **wait copy** / dequant / gemm gate/up / gemm down / combine / ple /
> kv stage / gdn conv+gates / gdn recurrence / gdn out proj / hc write，
> 并额外记 host 侧 `sync` / `chunk` / `setup` 三项。
> ⇒ 这 1.2 s **不需要改源码就能分解**，当时只是 grep 的范围漏了 `src/prefill/`。

能确定的只有：**它随数学路径变化 ⇒ 与算力有关；它不随长度变化 ⇒ 是 chunk 级常数。**

（**这条已在 §6.16 解开**：`CPU_SHARE=0` 一臂证明"固定项"在两条路径上是**两件不同的事** ——
`auto` 的 1.20 s 是 CPU 起跑延迟，`=0` 的 4.74 s 是 PCIe 搬运约 52 GB（AUDIT12：原文 72 GB 按 60 层算）。
不过 §6.16 的补测推翻了我原来按拟合外推的"长文档更快"：**4.3K 以上两者收敛，任何长度 `=0` 都不赢**。）

### 6.16 `STRATA_PREFILL_CPU_SHARE`：两条曲线，但**外推不成立** ⇒ 全线维持 `auto`

同一天、同 prompt 种子，只改一个 env。**先看实测（这是唯一算数的部分）**：

| 提示 tokens | 1151 | 2213 | 4345 | 7186 | 14324 |
|---|---|---|---|---|---|
| **现役 `auto` / MAX 3072** | **2.87 s** | **4.00 s** | **6.86 s** | **11.80 / 11.26 s** | **20.25 / 20.36 s** |
| `CPU_SHARE=0` | 5.42 s | 5.46 s | 6.87 s | 11.68 / 11.34 s | 20.26 / 20.34 s |

- **≤4.3K**：`=0` 明显更慢（500–2000 tok 时慢 1.5–2.5 s）。
- **≥4.3K**：两者**完全一样**（7.2K 差 0.5%，14.3K 差 0.1%）。
- ⇒ **`CPU_SHARE=0` 在任何长度上都不赢，生产维持 `auto`。**

**一处诚实的不对称**：chat 的三个点是在**已有流量、缓存温热**的引擎上测的；`=0` 那臂是**从冷启动**开始（首请求 5.80 s，第 2/3 条 5.42/5.44，冷启动衰减只有 0.4 s）。
所以短提示那 2.5 s 的差额**大部分来自 `share` 本身**，不是冷启动；但要完全干净，应在温热引擎上复测 `=0` 的短提示。这一点不影响结论（`=0` 在长端也没有收益）。

**我上一版在这里犯的错，必须记下来**：当时只有 1151/2213/4345 三个点，拟合出
`auto = 1.20 s + 1.316 ms/tok`、`=0 = 4.74 s + 0.493 ms/tok`，交点 4.3K，
于是**外推**出"8K 时 `=0` 只要 8.69 s（−26%）"。实测 7.2K 是 **11.68 s**，不是 8.69 s ——
**`=0` 的曲线在 4K 之后急剧上弯**（4.3K→7.2K 区间的边际是 1.69 ms/tok；**同口径**下 `auto` 在同一区间是 **1.64** —— 两者基本持平，不能说"还差"。
原文拿三点拟合斜率 1.32 去比实测区间斜率，口径不一致 —— AUDIT12 P1-8），
线性拟合只在取样区间内成立。

**规矩（新增）**：三段式线性拟合**不许外推到取样区间 2 倍以上**；特别是"边际速率"型结论，
必须先在一半与两倍处各补一个实测点再谈外推。

**仍然成立的两条**（它们都来自区间内实测）：

1. `=0` 的固定项确实是 **PCIe 搬运**：并集 **75 GB** − 缓存 21.8 GiB(=23.4 GB) ≈ **52 GB**，`52/4.74 ≈ 11 GB/s`
   （AUDIT12 更正：原用 60 层得 72 GB / 15 GB/s —— 15 GB/s 已超过 PCIe 3.0 x16 的实际带宽上限，与 W829 §0 的 "~12 GB/s 实测" 自相矛盾；48 层下 11 GB/s 反而对得上）
   ＝ PCIe 3.0 x16 实测带宽；`auto` 不搬，靠 CPU 从 RAM 补，所以固定项只有 1.20 s、边际被 CPU 拖到 760 tok/s。
   这解释了 §6.15 那个"固定项既不像搬运也不像计算"的矛盾：**两条路径的固定项是两件不同的事**。
2. `auto` 不会按长度自己切换（1.15K 与 4.3K 行为一致），所以"按用途切档"这个念头也**不必再考虑** —— 切了也没收益。

### 6.17 Web 控制台两处：monitor 页被上游封顶 1920，以及 WEB-UI 补丁的真实存留

起因：2560 宽窗口下 Monitor 页内容只占 **1920px**，两侧各空 ~320px，而 About/Chat 看起来「还是原来的」。

**（1）宽度：上游改的，我们一个字节没动**

- 三棵树的 `serve/web/app.css` md5 全等（`cf027c74…`）：`src0271`(0.1.53) = `src027` = `src028`(0.1.54)；容器 `/src/serve/web/app.css` 同 md5；
  HTTP 直取 `/web/app.css`（24171 B）也同 md5 ⇒ **不是我们的改动，也不是这次重建镜像引入的**。
- 按上游 tag 逐版追 `max-width`：

  | 上游版本 | 规则 |
  |---|---|
  | v0.2.2 ~ v0.2.6 | `.monitor, .about { max-width: 1240px }` |
  | **v0.2.7.1 / v0.2.8** | `.monitor, .about { max-width: min(100%, 1920px) }` |

- 另两条一直是上游设定，与我们无关：`.about { min(100%, 1100px) }`、`.chat { min(100%, 1100px) }`。
- **为什么这次才显形**：截图反算视口 = 2560。用三处尺寸互校（卡片 gap 14px→5.9px、`ctx-gauge` 150px、容器 1968px→829px），
  缩放因子 0.4219，即 1080×452 是 **2560×1073** 等比缩放 ⇒ 1920 的盖子第一次真正咬到，此前（1240 或窄窗口）不咬。
  ⇒ 结论：**上游改的，我跟着带进来了**，不是改错也不是漏改。

**（2）处置：一条 CSS 覆盖，作用域仅 monitor**

`serve/web/app.css` 末尾追加（幂等、带标记，`about`/`chat` 不动）：

```css
/* --- ALBUS-W831 (local patch; registry: deploy/patches/LOCAL_PATCHES.tsv) -------------
   Upstream v0.2.7.1 capped the dashboard at min(100%, 1920px). On a 2560-wide window that
   leaves ~320px dead on each side. Restore the pre-0.2.7.1 behaviour: fill the window.
   Scoped to .monitor only -- .about / .chat keep their upstream caps. */
.monitor { max-width: none; }
```

验证（本机无头 Chrome，`/#monitor` 前端支持 hash 直链）：**2560×1080 实图**下 8 张指标卡一行、Context/Recent requests/Conversation cache 全部通栏；
**1280×900** 下自动回落 4 卡一行，无横向滚动（全局 `box-sizing: border-box`，`width:100%` 不吃 padding）。

**（3）顺带查出的第二个问题：WEB-UI 补丁没在，而门禁给了假绿**

- 部署的 `app.js` 与上游 **v0.2.8 / v0.2.7.1 字节完全相同**（md5 `9fed14d1…`，92101 B）⇒ 我们的 WEB-UI 补丁**不在**里面。
- 把「我们的 patched(63395 B) − 它的 base orig(59958 B)」算出真实增量 **78 行**，逐行比对上游 v0.2.8：
  **74 行上游已原生具备**（`images` 页、`saveApiKey`、prefill 速率、采样默认值、火花线顶值 `Math.max(max||0,…,1)` 全都是官方功能），
  **只有 4 行是我们的**：PCIe 卡子行的 `· peak NN MB/s` 峰值后缀。
- **门禁为什么没报**：`WEB-UI` 那条用的标记是 `saveApiKey`，而上游自己就有这个词 ⇒ 假绿。已把标记换成真正只属于我们的 `pciePk`。
- 处置：按 `ALBUS-W831` 标记把 4 行精确补回（92101 → 92306 B），并保留上游新增的 `· idle GenN` 分支；实测
  `to GPU 0.0 MB/s · peak 162 MB/s`（发一条 24-token 请求后 `history/gpu_pcie_rx_mb` 出现 162.3 的采样）。
  空载时 `pciePk < 1` 不显示，避免 "peak 0.0" 噪声。

**（4）落地与一致性**

镜像 `strata-gfx906:0.2.8p2`（在 p1 基础上改 `serve/` 两层）。`app.css` / `app.js` 的 md5 **四处一致**：
`tree = image = container = 实际下发`（css `4c0a3b6b…`、js `6a968eaf…`）。
为避免二次停服（引擎加载 ~240 s），`app.js` 用 `docker cp` 热更新到运行容器，同时重建镜像；镜像内容与容器逐字节相同，
因此「重启」与「重建容器」都会得到同一份文件，不产生漂移。回滚件齐备：`0.2.8p1`/`0.2.8` 镜像、`app.css.bak-w831`、`app.js.bak-w831b`。

补丁门禁扩到 **13 项**（8 项 + 新增 5 项：W831 三条、WEB-UI 由 1 条扩为 3 条；原文写"新增 6"，AUDIT12 更正），当前 **13/13 PASS**。

---

## 7 数据出处

- compare API：`albus/w828/compare_0271_028.json`（70 提交 / 148 文件 / +5309 −476）
- 全树 SHA：`albus/w828/tree_028.json`（5229 blob）
- 上游文件：`albus/w828/up028/`（148 个）
- release 正文：`albus/w827/v0.2.8.md`
- 构建树：`166:/home/albus/strata166/src028`（= src0271 + 148 文件 + 2 行 compat 补丁）
