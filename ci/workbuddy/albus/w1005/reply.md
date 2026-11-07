**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native …unsloth-UD-Q4_K_XL-00001-of-00004.gguf --expert-profile /src/data/expert-profile.bin --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --expert-profile-save /data/profiles/q4kxl-learned.bin --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` = unlimited；`VmLck`: 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free（启动时值，本轮未重启） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致；本轮只**读**生产（18 次冷 prompt 探针） |

**二、主线** gfx906/mi50 @ 13254cfb · tag `mi50-0.2.10-r32-15-g13254cfb` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 1 提交 `13254cfb`（5 文件 +379：`ci/prefill_phases/` 四件 + `round_gate.py` 接门），已推。
**四、进度 + 队列** 227 条 / 已结 148 / 65.2%；主线 187 / 141；死块池 0/28。队列：R95（重定义为**外围/host 侧**）→ R94 质量门 → R91 → R89 → R46 → R49 → R50。

---

## 一、R95 的四个数字，三条是错的

R95 立了五轮，判据里一直写「gate/up **1.91×**、down **1.87×**、dequant **3.9×**、wait copy **14×**（占 68%）」。这四个数来自**一条** 2056 token 的日志行和**一条** 15757 的，而那份日志跨了十几次重启、83 个长度簇。本轮用同一个二进制、同一份 config、互不为前缀的冷 prompt、每档 n=3 重测：

| 项 | 旧（W990） | 现在 2K | 8K | 16K | 判 |
|---|---|---|---|---|---|
| gemm gate/up | 1.91× | **1.57×**（0.392 vs 0.249 ms/tok） | 1.17× | — | 数字改写 |
| gemm down | 1.87× | **1.52×**（0.245 vs 0.161） | 1.09× | — | 数字改写 |
| `dequant` | 3.9×（266 ms） | **161 ms（5.0%）** | 525 ms | 491 ms | **不是每 token** |
| `wait copy` | 14×（170 ms） | **37 ms（1.2%）** | 75 ms | 114 ms | 已被 issuer 修掉 |

两处是**口径错**，不是数错：

- `dequant` 根本不是反量化，是 `mmq::gather_native_group`（把每个专家 blob 散射进 MMQ group buffer，`prefill.cpp:5543/5588/7005`）。它的绝对值随专家并集饱和（161→525→491），**按 token 归一化就凭空造出「3.9× 的每 token 惩罚」**。
- `wait copy` 170→37 是因为拷贝已经移到第二条 stream + issuer 线程；旧数停在修好之前的那份日志里。

2K 相对 16K 的真实惩罚 = **0.290 ms/tok × 2084 = 605 ms，占 2K prefill 的 19%**；其中 gate/up 296、down 174（**合计 470 ms = 78%，即 prefill 的 14.7%**），`dequant` 99、`host grouping` 91、`router` 33，attention 反向省 190。

## 二、三个候选全部出局，而且都不必写代码

| 候选 | 结论 | 证据（本地方可复核） |
|---|---|---|
| A 让 J<64 可用 | 出局 | `W992`：Q4_K 的 J 在四张架构表里都从 64 起 |
| B 小专家走 GEMV/MMVQ 分流 | **出局** | 上游 `MUL_MAT_ID` 在 **GCN** 上对 Q4_K/Q5_K/Q6_K 的阈值是 **4 行**（`mmvq.cu:190` + `ggml-cuda.cu:2206`）；我们 ncols p50=331 / p90=742（W991）⇒ 可分流的小组近乎不存在 |
| C 去掉 group gather | **天花板 5.0%，两条通路都被挡住** | `STRATA_MMQ_DIRECT` 需 `-DSTRATA_MMQ_TAB=ON`，gfx906 结构性编不出（`W994`），且上游自测「多数专家从 RAM 流式」时只有 1.5%；`STRATA_PREFILL_ROUTED_STREAM` 是 1K 档 **−7.6%**（`R66`） |

## 三、举一反三：差点做错的一件事

残余的 1.57× 很容易被归给「tile 几何」，然后照上游 **MoE stream-k（PR #22174，双 3090 +17%）** 移植一轮。本地证据否掉了这条路：

- `ci/repack_ab/WIDTH_SWEEP.tsv`（同一 kernel、三臂、20 个测点）显示每行成本 **192→1024 行完全平坦，0.0033 ms/row**，只有 ≤96 行才劣化；
- 2K 的每组专家平均 **411 列**，正落在平坦区。

⇒ **1.57× 不在 MMQ 核内**，在每专家/每组的外围（host 建表与派发、组循环）。stream-k 赚的是核内 wave 量化，我们这里没有可赚的。下一手因此从「移植内核」改成「量 host/launch 侧」，`STRATA_TRACE` 是现成探针。

另外三件：

- **相位表的每个数必须能追到「同二进制 + 冷 prompt + 每档 n≥3」**；跨 build 的日志只配用来提假设。
- **per-chunk 量必须同时报绝对值与所在档**，否则「per token」会把它变成随长度缩放的假惩罚——`dequant` 就是这么被误读五轮的。
- **上游阈值可以直接判死一个移植想法**：B 没写一行代码就出局了。

## 四、门（不是口头声称）

- 新增 `ci/prefill_phases/`：`w1005_probe.py`（探针）、`phases.py`（判据）、`PREFILL_PHASES.tsv`（18 行实测）、`README.md`（旧表错在哪）。
- `phases.py --check` 两条判据：每行 26 个相位之和 = 该行 GPU timeline（±3%，打印取整到 ms）；**方案引用的 10 个数值必须等于表里的值**——改数据不改方案即 FAIL。
- 负向自测 **4/4 按预期 FAIL**：篡改 2K 簇 `dequant`（156 vs 161）、破坏一行之和（−3.6%）、删除 16K 簇（无簇可定位）、抬高 `gpu_ms`（−6.1%）。
- 已接进 `ci/round_gate.py --ci`（本轮 `ROUND_GATE: PASS`，输出含 `PHASES: PASS`）；workflow `paths` 已含 `ci/**`，本提交会触发 run。
- 方案与账本：`W832 §6.2 新30` 按实测重写、`§6.5` 追加 W1005 回写块（含三条候选处置与四条举一反三）；`PROGRESS.tsv` +5 行（P294–P298）。
- `plan_lint` A–F PASS（71 个 R 号、账本缺 0）；`ledger` 29 项、`param_pair` 15 处**均未增加**；四件权威件双侧逐字节 `W832 2eea907b…` / `PROGRESS e3104250…` / `PARAM_REGISTER 0f1efc3e…` / `ID_MAP 81891d72…`。
