# W1039 — port-all 按 b12180 重编：pa3 可复现、pa4 抓到死代码、pa5 把 DP4A 从 +6.8% 救到 −11%——**但数值门判否，不装机**
> 一句话：**同一个开关，改一行调度，从"慢 7%"变成"快 11%"**——然后数值门说这 1.8% 是拿 6.45 个百分点的 top-1 换的，**不换**。
> 生产全程未换件，config 逐字节还原（`5e9b81e2…`），在产仍是 `b12180`；pa5 留在分支上、开关默认关。

---

**一、生产容器（10 字段，2026-11-07 10:06 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` |
| 2 | 运行中引擎 | `strata-0.1.57-b12180` · md5 `d24f8293b575fbcee6c097239d9599cb` · 43,207,464 B |
| 3 | config | md5 `5e9b81e2f66ca48999766d2ae0201fb6` · `exe=/data/bin/strata-0.1.57-b12180` · args 37 / env 9 |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T02:03:48Z`（= 10:03:48，第三窗口还原后的启动） |
| 5 | 资源隔离 | `VmLck 0 kB` · `ulimit -l` unlimited · `memlock=-1:-1` |
| 6 | 显存 | used 33,495,392,256 / total 34,342,961,152 ⇒ **VRAM free 847,568,896 B（0.79 GiB）**；expert cache 7463 槽 / 21.79 GiB；the prompt path borrows 2606 槽（7.62 GiB） |
| 7 | 回滚件 | `/data/bin` **52 件** · `b12180`（在产）→ `k10p`（`e0a6987f…`）→ `-001`（`5e63174d…`） · 本轮新增候选 `pa3`/`pa4`/`pa5` · `ci/rollback.sh` |
| 8 | 本轮改动 | 引擎**无净变更**：disk = build = running 三方一致（`b12180` / `d24f8293…`）；config 改过 8 次又逐字节还原；**重启 8 次、停机 354 s**；装机 0；回滚 0 |
| 3a args 明细 | 37 项，本轮 `--kv` 未动：`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10`（19 个 `--flag`） |
| 3b env 明细 | 9 项；三个实验臂里临时加过 `STRATA_GFX906_ATTN_DP4A` / `ATTN_DPP` / `ATTN_LDS_PAD` / `ROUTE_DPP`，已全部撤除：`HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z） + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`，落后上游 0 / 领先 80，脏 0 行）。实验分支 `gfx906/port-all` @ `62d10e25`，本轮 4 个提交（`806a4b2f` overlay 探测 / `3b935ddf` OPT 接线 / `8b5e547f` b12110 API 差 / `62d10e25` warp-per-group），工作树改动 0 行（9 个未跟踪的 `.bak_*` 备份不在提交内）。

**三、本次落生产** — 三个窗口，每臂换引擎前停容器、改 config、起容器、等 health，结束还原 `b12180` 并核对 `exe` 与 md5：

| 窗口 | 时段 | 重启 | 停机 |
|---|---|---|---|
| ① pa3 零效果 | 09:02–09:16 | 3 次 | 129 s |
| ② pa4 负收益 | 09:18–09:32 | 3 次 | 135 s |
| ③ pa5 救法 | 09:55–10:04 | 2 次 | 90 s |
| ④ 数值门试跑 | 10:13–10:14 | 1 次 | 52 s |
| ⑤ 数值门正式 | 10:18–10:29 | 1 次 | 683 s |

**前三窗口合计 重启 6 次 / 停机 264 s（129+135）**；救法窗口 重启 2 次 / 停机 90 s；数值门两次 重启 1+1 次 / 停机 52 s + **683 s**
⇒ 本回合合计 **重启 10 次 / 停机 1089 s / 回滚 0 次 / 装机 0 次**。最长单次停机 **683 s**（数值门三臂独占 GPU）。

**四、进度** — **398 条 / 已结 312 / 78.4%**（本轮 +11：`P445`–`P455`）。队列：`R104`（`--kv-grow`）→ `R103` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`。

---

## 一、pa3：怎么编的，凭什么可信（`P445`）

配方三件事：① `/out` 从 `build-port2` **整目录拷贝**（继承全部 cmake flags，不手抄）；② `/llama.cpp` = `tmp/w1037/llama-master`（就是 b12180 用的那棵树，`mmq.cuh` = `627c4c62`）；③ 重跑 `cmake -S /src -B /out -DSTRATA_MMQ_TQ_OVERLAY=ON`。

两条坑：**overlay 生成器在 port-all 里还是旧探测**（按 `get_nthreads` 推断 write-back 的第 5 个模板实参），对 b12180 必挂 ⇒ 搬 pr/k10 的修；**光换树不够**，还要补 b12110 的 API 差（`mul_mat_q_case` 加 `GGML_PREC_Q8` **26 处**、`ggml_cuda_mmq_get_config` 加精度参 5 处、`new_pool_for_device` 加 ctx 形参 1 处）。

**可复现**：把 build 目录再拷一份、`ninja -t clean` 全量重编，得到**同一个 md5 `b2ba6304ddc848100ba72140e49ef9a9` / 43,306,640 B`** ⇒ 既排除旧树残留目标文件，也证明可重建。

## T2 窗口①：又一次"改到死代码"（`P446`）

三臂 ctl / pa3+`ATTN_DP4A` / pa3+`DPP`+`LDS_PAD`+`ROUTE_DPP`，每臂 2.5K×2 + 8K×2 + 16K×2。`qsa attn` 8K **2238 → 2235 / 2232 ms**、16K **4731 → 4718 / 4750 ms**，整条 prefill 偏差 ≤0.15%（2×CV 0.19%）——逐毫秒不动。

根因（源码 + 启动横幅互证）：日志 `:146006` 写着 *"the rounding-level recipe is on … **GFX906_ATTN_QUERY_SWIZZLE** …"* ⇒ `use_query_swizzle` 为真；而 W1037 接的那段条件（`qsa_decode_attn.cu:1143-1152`）是 `opt != 0 && !lane_cell && !use_query_swizzle` ⇒ 永不成立。生产跑 `attn_chunk_kernel<3,false,true,true>`，OPT 版是 `<M,false,false,false,OPT>`，**不是同一条实例化**。

**同族第三次**（`P425` 派发包在别的宏、`P441` 接错函数、`P446` 被配方里的开关挡住）⇒ 判据：判断开关在不在热路径，除看调用链，还得看**生产配方本身打开了哪些实例化**。

## T3 窗口②：开关真跑了，结论是负的（`P447`）

pa4 把派发放进 `if (use_query_swizzle)` 内，用 `attn_chunk_kernel<M,false,true,true,O>`（`qsa_decode_attn.cu:1172`）。

| 臂 | 8K `qsa attn` | 16K `qsa attn` | 8K 整条 | 16K 整条 |
|---|---|---|---|---|
| ctl | 2234 ms | 4727 ms | 1253.0 µs/tok | 1278.9 µs/tok |
| **+DP4A** | **2387（+6.84%）** | **5074（+7.35%）** | **+1.07%**（2×CV 0.10%） | **+1.44%**（2×CV 0.51%） |
| +DPP | 2217（−0.76%） | 4705（−0.47%） | +0.10%（2×CV 0.86%） | +0.14%（2×CV 0.13%） |

## T4 深挖：为什么"照理会快"却慢了（`P449` / `P450`）

常数 `CHUNK=64`、`THREADS=256`、`G=12`、`HD=256`、`NSC=4`、`top_k=2048` ⇒ **每 query 64 个块**。

- 量化段（`qsa_decode_attn.cu:234-247`）：`if (t < G*NSC)` 只有 **48/256 线程**，每线程串行 64 次 amax + 64 次 div/cvt ≈ **448 条**，其余 208 线程等 `__syncthreads`，且**每 query 重复 64 次**；
- 分数段确实省：每 cell 每 lane 基线 ≈130 条（12×8 FMA + 反量化 + reduce12），dp4a ≈85 条 —— 但每 8 个 MAC 只省 3 条（2 `v_dot4` + cvt + 2 mul 收尾 vs 8 `fma`），4× 密度被吃回 1.6×。

**对照项目**：iacop `fattn-q8.cuh` 的 `quantize_Q_to_shared` **全线程参与**、一块摊 `nbatch_K`(128–256) 个 key、KV 原生 Q8_0 不需反量化。
**外证**（skyne98，同代 MI50 实测）：热循环 QDQ 的 int8-dot4 **2.00 TOPS vs fp32 5.95（0.34×）**；摊薄复用后 dot4 21.7 vs 13.0（1.67×）。同站 dot 吞吐 sdot4 21.7–22.3 TOPS ⇒ **硬件没打折**。

## T5 窗口③：warp-per-group 把 DP4A 救回来（`P451` / `P452`）

只改一处：48 个组 ÷ 8 warp（每 warp 6 组）、**每 lane 2 个值**、5 级 `__shfl_xor` 求 amax、各转自己那 2 个值 —— 形状抄 llama.cpp `quantize_q8_1`。

| 形状 | ctl `qsa attn` | pa5+DP4A | Δ | ctl 整条 | pa5+DP4A | Δ | 2×CV |
|---|---|---|---|---|---|---|---|
| 2.5K | 575 ms | **510** | **−11.22%** | 1584.4 µs/tok | 1573.9 | −0.66% | 5.07%（不显著） |
| 8K | 2234 ms | **1982** | **−11.29%** | 1253.6 | **1231.2** | **−1.78%** | 0.50% |
| 16K | 4714 ms | **4212** | **−10.65%** | 1278.7 | **1258.1** | **−1.61%** | 0.11% |

decode 59.00 → 61.45 tok/s（CV 8–10%，不可分）。

**位相同**：`amax = max(|x|)` 与顺序无关，`d = amax/127`、`round(x/d)` 逐元素同一表达式 ⇒ 码字逐字节不变，−11% 全部来自调度（旧 48/256 线程、448 条/线程；新 256/256 线程、≈84 条）。

## T6 顺带修掉一个静默正确性洞（`P448`）

`STRATA_ATTN_OPT_DISPATCH`（`qsa_decode_attn.cu:1077`）只有 `case 1/2/4`，`default: break;` 之后直接 `return` ⇒ 同时开两个开关（如 `DPP|LDS_PAD` = 5）会**一个内核都不发就返回**，调用方照常 merge，输出是残留数据、**不报错**。已扩到 `case 1..7`。窗口①恰好被 swizzle 挡住，否则那臂会测出"零成本"的假象。

## T7 数值门：判否（`P453`）

工具 `tools/quant_quality.py`（`run` / `compare`），5 段 × 999 位 = **4995 个配对点**，三臂：

| 臂 | 内容 | top-1 | KL | KL p99 | PPL（run / ref） |
|---|---|---|---|---|---|
| A vs Ab | pa5 + `ATTN_DP4A=0`，同 argv 两容器（**自一致地板**） | **100.00%** | **0.00000** | 0.0000 | 4.048 / 4.048 |
| A vs B | pa5 + `ATTN_DP4A=1`（开关） | **93.55%** | **0.04130** | 0.6109 | 4.057 / 4.048 |

- **地板是 0**（100% / 0.00000）⇒ 环境完全确定，0.0413 不是噪声，是开关本身；
- 两条判据**都破线**：KL 0.0413 是阈值 0.0139 的 **3.0 倍**，top-1 93.55% 差 99% 线 **6.45 个点**；
- 归因干净（技能 §6）：A 与 B **同 exe、只差一个 env** ⇒ 这一门归因到 `ATTN_DP4A` 一个开关，不是整栈。

**⇒ 判决：pa5 不装机。** 它用 1.78% 的 prefill 换掉 6.45 个百分点的 top-1 与 3 倍的 KL——按项目标尺这是负优化，
`P451` 从 OPEN 改 **DONE_NEG**，`deploy_gate` D4 保持红。代码留在 `gfx906/port-all`、开关默认关。

**偏差（必须写，否则会被当生产值）**：工具 FIXED 强制 `--expert-cache 1500` / `--pcie-frac 0` / `--adapt-every 100000` /
`STRATA_PREFILL_CPU_SHARE=0` / `STRATA_ROUTE_TAIL_SKIP=0`；**`--kv` 从工具默认 fp16 改为 `k8v4`** ——
否则 `kv_mode=0`、dp4a 派发条件（`kv_mode==3||kv_mode==1`，`qsa_decode_attn.cu:1146`）永不成立，这一门会测出「零差异」的假通过。
它测的是 **GPU MMQ 内核的 prefill 数值**，不含主机侧 CPU share。

## T8 为什么"大幅提升"却过不了数值门：误差正好落在 0.19 nat 的判决边上（`P454`）

把两臂的 4995 个位置逐点对齐（`margin_analysis.py`）后，答案很硬：

| 量 | 值 |
|---|---|
| argmax 变了的位置 | **322 / 4995 = 6.45%** |
| 其中 A 的第一名在 B 里掉到**第 2 位** | **234（72.7%）** |
| 参考侧 top1−top2 间隔（nats） | p10 0.025 · **p50 0.191** · p90 1.055 · p99 3.96 |
| 间隔 < 0.1 nats 的改动 | 103（占改动 32%，占全体 2.06%） |
| 间隔 < 0.5 nats 的改动 | 242（占改动 75%） |
| |Δlogp(target)| | 中位 **0.018** · p90 0.402 · max 10.1 |

**这不是"答案错了 6.45%"，是"在 0.19 nat 的分岔口上换了边"**——四分之三是和亚军互换了名次。
而 int8 查询的量化步长恰好就是这个量级：

- q 的 int8 步长 = 组内 amax/127 ⇒ RMS 误差 ≈ 0.45% × amax ≈ **1.3% × σ_q**；
- 分数 = 256 维点积 ⇒ 相对误差 ≈ 1.3% ⇒ 对一个 O(1–10) 的分数就是 **0.01–0.13 nat**；
- 观察到的中位间隔 0.191 nat、中位 Δlogp 0.018 nat —— **同一个数量级**。

**⇒ 结论不是"实现写错了"，而是"8 bit 的步长正好压在模型做决定的间隔上"。**
项目标尺要 KL ≤0.0139，等于要求噪声再小 3 倍；单档 int8 做不到（步长与位宽是指数关系）。

## T9 能救的路子：把这一层从 int8 换成 fp16 点积（`P455`，未实施）

同一条分数段，换一种指令：

| 方案 | 每 8 个 MAC 的指令 | q 的相对误差 | 预计 attn | 预计 KL |
|---|---|---|---|---|
| 基线 fp32 fma | 8 `fma` | 0 | — | 0 |
| int8 `v_dot4`（已判否） | 2 dot4 + cvt + 2 mul = **5** | **1.3%** | −11% | **0.0413** |
| **fp16 `v_dot2_f32_f16`** | 4 dot2 + 1 mul = **5** | **0.03%** | 预计 **−8~−11%** | 预计 **<0.001** |

关键：`v_dot2_f32_f16` 是 **2 MAC/指令**，8 个 MAC 只要 4 条，而且**没有 int8 那套 cvt+2mul 的收尾**（k 侧 int8 转 f16 是精确的，scale 放到最后乘），
所以每头的指令数与 int8 路径相同（5 条），但 q 的精度从 1.3% 回到 0.03%——**快的一样快，误差小 40 倍**。
外证：同代卡上 `__builtin_amdgcn_fdot2 -> v_dot2_f32_f16`，摊薄复用后 21.9 TOPS vs fp32 13.0（skyne98 实测）。
工具链侧本轮已验证：`__builtin_amdgcn_fdot2(a, b, acc, false)` 在 `--offload-arch=gfx906` 下**编译通过**（`t_fdot2.cu`，CLANG=0，7,768 B 目标文件）。

**为什么还没有直接上**：它要新增一条 OPT 分支（共享 half 查询 tile + k 侧 i8→f16 打包 + 两个 score 分支各一份），
改错一处就是一次白烧的窗口。所以这一步按项目纪律走：**先编、再数值门、最后才测速度**；顺序不跳。

---

**产物**：`albus/w1039/reply.md`（本件）、`build_pa3.sh` / `build_pa3b.sh` / `build_pa4.sh` / `build_pa5.sh` / `repro_pa3.sh`、`port_all_api_fix.py` / `pa4_patch.py` / `pa5_patch.py`、`window.sh` / `window2.sh` / `window3.sh` + `ab_w1039.py`、`deep_dive.md`（预算推导全文）。
**原始数据**：166 上 `/home/albus/strata166/tmp/w1039/{arm_*,w2_*,w3_*}.json` 与 `window{,2,3}.log`。
