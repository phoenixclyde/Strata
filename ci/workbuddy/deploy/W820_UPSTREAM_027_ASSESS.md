# W820：要不要升到上游最新版（2026-10-28）

> 结论先行：**上游最新对我们没有"必须升"的理由，建议不迁移生产，改为并排构建 0.1.52 做一次 3 臂 A/B。**
> 但顺手发现一个真实偏差：**运行中的容器没有 `--ulimit memlock=-1`**（我们自己的脚本里有），
> 这是 P141 那条通道一直"锁不住表"的前置原因。这一条零成本，可以现在就修。

---

## 1 上游现在到哪了

| 对象 | 最新 | 说明 |
|---|---|---|
| app / Control | **v0.2.7.1**（tag） | 0.2.7 发布 2026-10-27 14:54 UTC；0.2.7.1 只有 ARM/Spark 与 Mac 两部分 |
| **x86 Qwen 引擎** | **0.1.52** | 资产 `strata-engine-0.1.52-linux-x86_64-*`；0.2.7.1 明确写「x86 用户没有新引擎、没有速度变化、不需要更新」 |
| main 分支 | **0.1.53** | 0.2.7.1 之后 20 条提交全是 Metal / Mac / DGX Spark（aarch64）/ feed 解析，**没有一条 x86 Qwen** |
| 我们的基线 | **0.1.49.2** = tag **v0.2.4.2** | 见 §2 的逐文件证明 |

**没有 gfx906 的预编译包**：v0.2.4 / 0.2.5 / 0.2.6 / 0.2.7 的 HIP 资产只有
`hip-halo`(gfx1151) / `hip-rx6000`(gfx1030) / `hip-rx7900`(gfx1100) / `hip-rx9070`(gfx1201) 四种。
gfx906 在 `docs/OLDER_GPUS.md` 里是这一行：

> `Instinct MI50 / MI60, Radeon VII | gfx906 (wave64) | built by hand: -DSTRATA_HIP_GFX906=ON`

⇒ **任何一次升级都是我们自己从源码构建**，不是下载包。这是永久成本，也意味着升级应该"攒着等"，不必追每个小版本。

---

## 2 我们到底跑的是哪份源码（不是猜，是逐文件比对）

方法：在容器里对 `/src/src`、`/src/include`、`/src/cmake`、`/src/CMakeLists.txt` 共 **492 个文件**逐个算
git blob sha1（`sha1("blob <len>\0" + content)`），与上游 `git/trees/v0.2.4.2?recursive=1` 的 blob sha 对照。

```
local files 492   same_as_0.2.4.2  489   different  3   not_in_upstream 0
```

**只有 3 个文件被改过**，而且都是我们自己留了注释的：

| 文件 | 改动 | 状态 |
|---|---|---|
| `CMakeLists.txt` | ① W793：gfx906 分支里补 `find_package(rocblas)`，让 `STRATA_ROCBLAS_AVAILABLE` 真正定义（否则 rocBLAS 解表编成空）；② W776：把 `STRATA_USE_HIP=1` 只作用于 `dflash2.cpp`；③ `STRATA_ENABLE_HIP OR STRATA_HIP_GFX906` 才链接 rocBLAS 表 | **仍在用** |
| `src/kernels/cuda/qsa_decode_attn.cu` | W794：query swizzle 从只认 `kv_mode==1` 放宽到 `(kv_mode==1 ‖ kv_mode==3)`，并补 `attn_chunk_kernel<3,…>` 两个实例 ⇒ **k8v4 上才能吃 swizzle** | **仍在用**（生产是 k8v4） |
| `src/kernels/cuda/fused_gr.cu` | W788 R5-A：`STRATA_GR_TILEV=1280` 小 tile 开关（默认不设 = 与 0.2.4 逐字节同路径） | **可弃**（register 已判 TILEV 否） |

> 这条把以前记忆里"镜像 = 0.2.4.2 + rocBLAS + max-ilp + swizzle"压缩成了可执行的清单：**实际是两处半**。
> 升级要重打的补丁面 = 2 个文件（`CMakeLists.txt`、`qsa_decode_attn.cu`），第 3 个可以直接丢。

---

## 3 0.2.4.2 → 0.2.7 的引擎面有多大，其中多少落在 gfx906 上

用 git tree 比 blob sha（不是看发布说明）：

```
files 4892 -> 5149    changed 400（apps 98 / src 67 / docs 35 / include 35 / tests 33 / tools 32 / serve 20 …）
new     257（src 33 / tests 31 / include 18 / serve 62 / apps 79 …）
gone    0
引擎面（src+include+CMake）= changed 105 + new 51
```

然后交叉"文件里含 `STRATA_HIP_GFX906`"（代码搜索 73 个文件）与"被改过"：

**带 gfx906 分支且被改动的代码文件 = 13 个**
`include/strata/core/verify.hpp`、`include/strata/prefill/moe_fused.hpp`、
`src/core/{conversation_snapshot,conversation_state,expert_cache,expert_source,mtp,verify}.cpp`、
`src/kernels/cuda/{fused_gr,native_mmvq,qsa_prompt_attn,verify_kernels}.cu`、`src/prefill/moe_fused_iq.cu`。

抽检两个：

- `qsa_prompt_attn.cu`（我们的提示注意力走 FP32 QSA 内核）——改动只有一处：`STRATA_PROMPT_ATTN_IMMA`
  从"opt-in"变成"sm_80+ 默认开"。**gfx906 没有 INT8 MMA，分支没动**。
- `expert_cache.cpp` —— `STRATA_EC_NO_VMM` 的排除条件里本来就含 `STRATA_HIP_GFX906`，未变。

**两个"不会静默改默认值"的证据（这决定了升级的风险等级）：**

1. `src/core/arch_defaults.cpp`（0.2.7）：仍然只有 **gfx1151** 和 **gfx12(RDNA4)** 两张表，
   判 `gfx_arch_is_gfx1151` / `gfx_arch_is_gfx12` 直接 return ⇒ **gfx906 拿到空表，一个开关都不会被翻**（与 W800 结论一致）。
2. `docs/AMD_HIP.md`（0.2.7）明写：`STRATA_FILE_CACHE_OLD_RULE` —— **gfx906 保持旧的文件级缓存规则**，
   `=0` 才拿新规则。⇒ 文件缓存行为默认与我们今天一致。

---

## 4 真正与我们有关的变化（只有四项）

| # | 变化 | 对我们的意义 | 量化 |
|---|---|---|---|
| 1 | **`STRATA_PLE_AUTO_RAM`**（0.2.7 新增，默认开） | 启动时按 RAM 把 26.8 GiB n-gram 表**常驻并锁定**；`--ple-io` 不给时也会自己判定 | 上游给的 `--ple-io ram`：1K **+16.5%**、4K **+30.6%**、8K **+16.8%**（72 GB 卡）。我们自己量到 **-12% ± 4%**（W810/W812/W814，drop_caches 前置）。方向一致、量级同源 |
| 2 | PLE reader 不再永久等待（#3602），`STRATA_PLE_CHECK=1` 可重读可疑行 | 健壮性。我们现在一旦某次读失败，后续请求就挂住 | 无速度含义 |
| 3 | 会话缓存不再串用别人的 K/V（#1503） | 正确性。多会话/多槽位时是真实缺陷 | 无速度含义 |
| 4 | 深度上下文 top-k 换宽内核（>135K cells，提示 ≥90K） | 我们 ctx 262144，但目前只在 1.5-5K 上跑；一旦上长文档才有意义 | R9700 500K 提示 716→962 tok/s |

另外三条"便宜但不一定用得上"：`STRATA_PREFILL_WARM=0`（竞技场载入期不再预热 BF16/FP16 乘积）、
`STRATA_KVA=1`（近似读最后 12 层，14K +11% / 30K +18%，**会掉细节**）、`STRATA_FILE_CACHE_OLD_RULE=0`（试新规则）。

## 5 与我们无关的（下次不用再翻）

12 GB NVIDIA 卡的 route prior（`STRATA_ROUTE_PRIOR`，13 GiB 以上不适用）、两卡 layer-major prefill（`STRATA_PREFILL_LAYER_MAJOR`，单卡保持旧路径）、
两卡批量流水（`STRATA_BATCH_GROUPS_NV_SERIAL`）、`--split-serve`、sm_89/sm_80 的表、gfx12 的四个 decode 开关、
RDNA4 的 PLE/hipBLASLt、Strix Halo 的 HC_Q8 矩阵单元、DeepSeek 的 RAM store / Engram / 视觉塔 / 大上下文。

**证据强度说明**：这些"与我无关"不是读标题得出的——每一条都对应 `arch_defaults.cpp` 的架构判断，
或发布说明里写明的卡型/后端条件。

---

## 6 为什么"最多只有百分之几"，而我们的瓶颈不在这

我们自己的相位表（W798/W803/W804）：**decode 占一轮 64-83%**，decode 里 72% 是 GPU-reach wait；
prefill 里 ple 12.9-16.7%、attn 16%、hc 18%、gemm gate/up 16%、gdn 14%、gemm down 9%。

0.2.7 的 Qwen 提速项（route prior / layer-major / 批量流水 / sm_89 表 / gfx12 开关）**没有一项落在 gfx906**，
所以：

- decode：预期 **0%**（0.2.5 那条 "fewer GPU launches per layer, decode +13%" 在正文里属于 **DeepSeek** 一节）；
- prefill：最好情况吃到 PLE 常驻的 **-12%**，折到端到端 = **-2% ~ -4%**；
- 端到端合计：**0 ~ 4%**，且**前提是本机真能把表锁住**。

## 7 那个前提在本机现在不成立 —— 两个硬条件

`include/strata/core/ple_residency.hpp`（0.2.7）的准入逻辑写得很直白：

```cpp
inline bool ple_resident_admit(available, table_bytes, experts_ram_bytes, headroom_bytes) {
    if (!available || table_bytes == 0 || experts_ram_bytes == 0) return false;
    return conversation_memory_admit(available, table_bytes + experts_ram_bytes, headroom_bytes);
}
```

本机账：表 **26.8 GiB** + 专家竞技场 **55.43 GiB** + headroom（8 GiB）≈ **96 GB**，要一次性判给。
但宿主上跑着 **ComfyUI（PID 1544598，RSS 52.1 GB，已持续 1 天 3 小时）**，实测 `MemAvailable = 9.3 GB`。
⇒ **只要 ComfyUI 在，0.2.7 的自动常驻一定拒绝**（拒绝后回落到 direct，即今天的 0.2.6 行为，不会更差，但也没有收益）。

第二个条件更硬：`ple_residency.hpp` 的注释说的是"an unbuffered read into that arena needs the pages locked"，
即**表要锁定**。而本机：

```
docker inspect strata166-407 --format '{{json .HostConfig.Ulimits}}'  ->  []
容器内 ulimit -l  ->  8192 KB
```

**我们自己写的 `_b022_run.sh` / `_b023_run*.sh` 里都有 `--ulimit memlock=-1`，上游 gfx906 配方也要求它，
但正在跑的容器（`strata-gfx906:0.2.4p4`，创建于 2026-10-25 08:53）没有。**
这就是日志里一直只有 `loaded (not locked)` 的原因，也解释了为什么 W810 的 C 臂里表会被竞技场那 55.43 GiB 的缓冲流冲掉。

⇒ **两件零成本、与升不升级无关的事：**
1. 重建容器时补 `--ulimit memlock=-1`（其余 `--ipc host`、`--device=/dev/kfd`、`--device=/dev/dri`、`--group-add video` 已齐）。
2. 想拿 PLE 常驻，要么停 ComfyUI，要么认下"启动快/提示快只能选一个"。

### 7.1 memlock 的实测（已做）

| 容器 | `rlimit(MEMLOCK)` | `mlock` 512 MiB |
|---|---|---|
| 现在的生产容器 | `(8388608, 8388608)` | **rc = -1, errno = 12（ENOMEM）** |
| 同镜像 + `--ulimit memlock=-1` | `(-1, -1)` | **rc = 0** |

配合源码 `ngram.cpp` 的 POSIX 分支（`madvise(WILLNEED)` → 16 线程逐页 touch → `mlock`），
以及失败时那句 `PLE table mlock failed (…; raise ulimit -l): its pages stay faulted in but may be reclaimed`：
**今天这张 26.8 GiB 的表永远是"touch 过但可被回收"的状态**，W810 C 臂里它被竞技场冲掉不是偶然。

### 7.2 事故记录：第一次引擎级重测让服务空了 6 分钟（2026-10-29 00:00-00:06）

时间线（全部本机时间）：

```
23:59:14  docker stop comfyui-cu130          ← 为腾 52 GB 给表
23:59:5x  docker stop strata166-407 + drop_caches
00:00:2x  起一次性容器 strata166-w820a（memlock=-1 + 生产配置）
00:00:2x  该容器 30 秒后 Exited(1)            ← 引擎没起来
00:00:25  ComfyUI 自行回来（StartedAt 16:00:25Z，RestartCount=0，无 systemd 单元）
00:06:23  发现 8090 一直为空
00:06:32  docker start strata166-407 → 176 s 后就绪（冷启），HEALTHY
```

**未查明**：容器 `exit(1)` 的原因——我在被打断前没把 `docker logs` 落盘，`docker rm` 后日志丢失。
候选两个（ComfyUI 回来抢 52 GB 后竞技场分配失败 / memlock 放开后某处锁定失败退出），**无证据，不结论**。

**已改的规则**：①"停生产 / drop_caches"这类操作不在使用时段做，等时间窗；
②一次性容器**先 `docker logs` 落盘再 rm**；③长实验用 `setsid nohup` 落地，不占长连接。

---

## 8 风险与成本（升级如果真做）

| 项 | 量 |
|---|---|
| 构建 | 源码树重下（无 .git，5149 个文件）、重打 2 处补丁、`cmake -B build -G Ninja -DSTRATA_HIP_GFX906=ON …`；cmake 最低 3.24、C++20、`hip_compat` 层**未变**、llama.cpp pin 未变 |
| 回归面 | 13 个带 gfx906 分支的改动文件；**维护者没有 gfx906 卡**（文档原话：checked to compile for gfx906 and nothing more），出问题没人兜 |
| 基线 | 142 行登记、约 30 轮 A/B 的结论全部基于 0.1.49.2；换二进制等于基线清零，必须重跑关键判据（`ple` 相位、decode tok/s、槽位 9873、启动两档、36 题、KL） |
| 观测兼容 | **相位表未变**：`kPfNames` 21 项两版逐字相同，`strata prefill timing: … ple N (x%)` 格式未变 ⇒ 我们的 `mt_read/analyze` 脚本不用改（已核对） |

## 9 判定

**不迁移生产。** 理由按权重：
1. 收益不落在瓶颈上（decode 占 64-83%，0.2.7 对 gfx906 的 decode 收益为 0）；
2. 唯一有量的收益（PLE 常驻）在本机被 ComfyUI 的 52 GB 与缺失的 memlock 挡住，**今天升也拿不到**；
3. 成本是"全部基线重跑 + 无维护者兜底的回归面"，而 gfx906 永远要自建 ⇒ 应该**攒到有 gfx906 相关改动时一次升**。

**替代动作（建议按序，状态截至 2026-10-29 01:20）：**
1. **[部分完成]** 先修 memlock（零成本，见 §7），并在 0.1.49.2 上重测 `--ple-io ram`：**若锁得住，-12% 可能变稳甚至变大**，这是不需要升级就能拿的钱。
   - 已完成：flag 级验证（8 MB 限额 → `mlock` 512 MiB `ENOMEM`；加 `--ulimit memlock=-1` → `rc=0`）。
   - 未完成：引擎级重测。第一次尝试造成 6 分钟不可用（见 §7 的事故记录），此后**改为等时间窗**。
2. **[完成，形态有变]** 并排构建 0.1.52。原计划写"镜像 `strata-gfx906:0.2.7`，**与生产并存**"——**这半句是错的**：
   32 GB 显存只够一个引擎（33.72 GB / 32 GB 卡），任何 A/B 都必须停生产，不可能并存。
   实际做法：**不建镜像，产出裸二进制** `src027_out/strata-0.1.52`，用配置里的 `exe` 字段指向它
   （`serve/server.py` 天然支持 `exe` 绝对路径）——更轻、可随时删、不污染镜像库。补丁两处照旧，`GR_TILEV` 丢弃。
3. **[待跑]** 3 臂交错（0.1.49.2 / 0.1.52 / 0.1.49.2），同一语料、n≥2、判据：`ple` 相位、`attn` 相位、decode 中位、`expert_slots`、启动秒数、36 题；**端到端 ≥5% 才采纳**（<5% 属本机噪声，W809 已立这条规则）。**需独占 GPU ⇒ 需停生产的时间窗。**
4. **[未到]** 若采纳，再按 §3 的 13 个文件逐个看 gfx906 分支，补 `STRATA_FILE_CACHE_OLD_RULE=0`、`STRATA_PREFILL_WARM` 的 A/B。

## 9.1 已完成的准备（2026-10-29 00:29）

并排构建**已经做出来了**，全程没动生产：

| 项 | 结果 |
|---|---|
| 源码 | `Strata-0.2.7` 解到 `/home/albus/strata166/src027`，7973 个文件，`project(strata VERSION 0.1.52)` |
| 补丁 | `patch_027.py`：A/B/C 三处 CMake（W793 rocBLAS 接线、W793 链接条件、W776 dflash2 作用域）+ D 换 `qsa_decode_attn.cu`（W794）。0.2.7 的坑：`set(_strata_gpu_include_directories …)` **出现两次**，A 必须靠 `Strata: HIP (gfx906 compat) enabled` 那句定位 |
| llama.cpp | **pin 未变**：`third_party/ggml/VERSION.txt` 两版都是 `3cf03257…`（Sep 20）⇒ 直接复用现有 checkout，不用重下 |
| 构建 | 与生产**逐项相同**的 CMake 选项（Release / gfx906 / `STRATA_MMQ_KQUANTS=ON` / `Q6K_EXPERTS=OFF` / `GGML_DIR` 同路径），`notice -j 10`，**rc=0，2 分钟** |
| 产物 | `/home/albus/strata166/src027_out/strata-0.1.52`（38.2 MB；生产 0.1.49.2 是 35.0 MB），`--version` → `strata 0.1.52` |
| 编译期证据 | configure 日志里出现 `/opt/rocm/lib/cmake/rocblas/rocblas-config.cmake` ⇒ **W793 生效**；`strings` 有 `rocBLAS tuning enabled`、`STRATA_PLE_AUTO_RAM`、`PLE table mlock failed`、`STRATA_GFX906_ATTN_QUERY_SWIZZLE`；`gfx906` 代码对象 140 处 |
| **参数面兼容** | 两版 `--help` 各 **139 个 flag，无增无删**（`albus/w820/flags.json`）⇒ 我们那 33 个参数一个都不用改 |
| 待跑 | 3 臂交错 A/B（0.1.49.2 / 0.1.52 / 0.1.49.2）。配置已备：`/home/albus/strata166/data/w820_v52.json`（`exe=/opt/newbin/strata-0.1.52`），臂脚本 `w820_arm.sh`（支持额外挂载与 drop_caches 开关，**日志在 rm 之前落盘**） |

> A/B 必须独占 GPU（32 GB 装不下两个引擎），所以那是唯一需要停生产的环节——**等时间窗**，不在使用时段做。

## 10 数据出处

- 版本/资产/正文：GitHub API `releases?per_page=30`、`releases/tags/v0.2.{4,5,6,7}`、`tags`
- 文件面：`git/trees/v0.2.4.2?recursive=1` 与 `v0.2.7`（各 4892 / 5149 blob，未截断）
- 本地对照：容器内 `/src` 492 个文件 git blob sha1（`albus/w820/blobsha.py`）
- 文档（0.2.7 tag）：`docs/AMD_HIP.md`、`docs/OLDER_GPUS.md`、`docs/DETAILS.md`
- 源码（0.2.7 tag）：`include/strata/core/ple_residency.hpp`、`src/core/arch_defaults.cpp`、
  `src/kernels/cuda/qsa_prompt_attn.cu`、`src/prefill/prefill.cpp`（相位表）、`src/core/expert_cache.cpp`
- 本机实况：`docker inspect`（Ulimits/IpcMode/Image/Created）、`ulimit -l`、`/proc/meminfo`、`ps -eo pid,rss`
- 落地：`deploy/params/PARAM_REGISTER.tsv` 新增 **P146**（升级判定 DEFERRED）、**P147**（memlock 偏差 CANDIDATE）
- 脚本：`albus/w820/{gh,blobsha,reg_w820}.py`；发布正文 `albus/w820/rel/*.md`；上游对照文件 `albus/w820/up242|up027/`

## 11 A/B 第一轮：不可判定（漂移主导），但有一条可用结论

**时间** 2026-10-29 01:48-02:00，三臂 `A(0.1.49.2) → B(0.1.52) → A2(0.1.49.2)`，暖缓存、不清 cache，同一语料
（三臂 `sha16` 逐条相同：`f2c5c70c…` / `d8eac6b6…` / `881b5ee7…`）。跑完 `trap` 自动恢复生产，02:00:27 HEALTHY。

### 11.1 二进制的可区分性

| tokens | A（0.1.49.2） | B（0.1.52） | A2（0.1.49.2） | B 在 A/A2 区间内？ | 同二进制漂移带 |
|---:|---:|---:|---:|---|---:|
| 1453 | 3.46 s | 3.99 s | 4.13 s | **是** | 19.4% |
| 2498 | 4.92 s | 5.14 s | 5.19 s | **是** | 5.5% |
| 4568 | 8.46 s | 8.75 s | 8.74 s | **是**（差 0.01 s） | 3.3% |

⇒ **在 3-19% 的漂移带里，0.1.52 的提示时间无法与 0.1.49.2 区分**。这与我 §6 的预测一致（0.2.7 的 Qwen 提速项都在 NVIDIA/RDNA）。

### 11.2 漂移的来源：磁盘在本次会话里逐臂变慢（不是二进制）

| 臂 | 竞技场载入速率 | 启动 | decode 中位 |
|---|---:|---:|---:|
| A | **0.38 GiB/s** | 170 s | 48.9 tok/s |
| B | 0.39 GiB/s | 165 s | 26.5 tok/s |
| A2 | **0.32 GiB/s** | 196 s | 30.3 tok/s |

- **A2 与 A 是同一个二进制**，载入速率却慢 16%、decode 中位低 38% ⇒ 漂移全在环境侧。
- 三臂的引擎状态**几乎一致**，排除"B 臂行为异常"：decode 专家缓存命中率 93.8/93.8/93.9%，
  尾跳计数 10036/9861/9772（同量级）。
- decode 数字本身不可用：A 臂 p0→p2 是 42.5→51.5，A2 是 37.9→28.8，B 是 34.3→14.6 ——
  **同二进制内部就有 44% 的跨度**。原因：`mt_gen` 排在 3 次大 prefill 之后、每臂只有 3×128 token（2.5-4 s），
  测到的是"刚被 prefill 搅动过的缓存状态"，不是稳态。

### 11.3 下一轮必须改的三处

1. **decode 放最前面**（就绪后立刻测），3 次取中位，**不要排在 prefill 之后**；
2. **细粒度交错** `A B A B`（两轮）而不是 `A B A2`，让漂移对两臂对称；
3. **加 `STRATA_PREFILL_TIMING=1`** —— 这轮忘了加，所以没有相位表（`ple`/`attn`），而相位表才是本机唯一能判 2-3% 的标尺（W809）。
   代价：每臂 165-196 s 冷启（竞技场页不留在页缓存里），4 次启动 ≈ 12-14 分钟停服。

### 11.4 第一轮的净结论

- **没有发现 0.1.52 的收益**（提示侧与生产不可区分），也**没有发现代价**（启动 165 vs 170 s，同一噪带）。
- 因此"是否升级"这个问题目前仍是 **"不升"**，而且现在多了一条正面证据：升上去**也拿不到速度**。
- 剩下的唯一价值是 0.2.7 的**正确性/健壮性**修复（#3602 PLE reader 挂死、#1503 会话 KV 串用）—— 这两条不体现在速度上，要用故障注入或长跑验证。

---

## 12 AUDIT11 补注：这个"不升"的判定后来怎么样了（2026-10-30）

**W824 已经把引擎升到 0.1.53（tag v0.2.7.1）并落了生产**，理由正是本文 §11.4 的最后一条 ——
**#3602 / #1503 两条正确性修复，加上机主要最新版**，**不是性能**。

三条印证：

1. W824 的 A/B 复现了本文的判断：0.1.53 相对 0.1.49.2，prefill 三档**全为正**（+9.1 / +0.8 / +3.3%）、
   幅度小且未做 ABBA ⇒ **没有可见收益**（原文"升上去也拿不到速度"成立）。
2. W824 的全树校验：543/548 文件与上游一致，22 个差异全在 `src/dsv41/*`；二进制里 `dsv41` 字符串 **0**。
3. `src/kernels/cpu/portable.cpp:1` 逐字 `the CPU kernel symbols on a **non-x86** build` ⇒ 我们 x86 不编它。
   ⇒ 这次升级对 **x86 产物的实质变更 ≈ 版本号**。

⇒ 本文"不升"在当时**没有错**；被改的不是论据，而是**优先级**：正确性修复的权重大于"换不来速度"。
把这一条记在这里，是为了避免后来者把 W820/W823 的"不升"与 W824 的"升"读成决策反复。
