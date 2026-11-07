# W1037 报告 · R103 开窗前的地基：A5 是死代码，两支判否，开窗清单就位

**一、生产容器（10 字段）**

| # | 字段 | 值（2026-11-07 06:4x–07:2x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041`（full `2d765942e041f31f7cf3999a7fbabe8073a0ca0fd21b355228392c1624150a04`）· `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` |
| 2 | 运行中引擎 | **`strata-0.1.57-b12180`** · md5 `d24f8293b575fbcee6c097239d9599cb` · 43,207,464 B（llama.cpp b12180 == master `bcb01528` + `mmq@4c1004c`）；回滚 `k10p` = `e0a6987f732a401f780f5dad5812812f` |
| 3 | config | md5 **`5e9b81e2f66ca48999766d2ae0201fb6`** · `exe=/data/bin/strata-0.1.57-b12180` · args 37 / env 9 |
| 3a | args（19 flag） | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1`（本轮 5 个 gfx906 开关**一个都没进生产 env**） |
| 4 | 健康 | `/health` = `{"status":"ok","max_context":262144,"loaded":true}` · `running` · restarts=0（RestartCount 只计策略重启）· StartedAt `2026-11-07T00:06:33Z`（= 本机 08:06:33，**b12180 装机后的启动**） |
| 5 | 资源隔离 | 引擎 `VmLck 0 kB` · `ulimit -l` unlimited · `memlock=-1:-1` |
| 6 | 显存布局 | expert cache **7463 slots / 21.79 GiB**；prompt 路径 **borrows 2606 槽（7.62 GiB）**；VRAM used 33,602,011,136 B / total 34,342,961,152 B ⇒ **VRAM free 740,950,016 B（0.69 GiB）**（b12180 装机后取） |
| 7 | 回滚件 | `/data/bin` 46 个文件（40 个引擎二进制 + 工具）· `-001` 在产 · `ci/rollback.sh --exe strata-0.1.57-001 --apply` · config 侧 `cp *.bak`；本轮候选 `pa1` **只在 `build-port2`，未进 `/data/bin`** |
| 8 | 本轮改动 | **本轮换了一次在产件**：`-001` → `k10p`（llama.cpp b12110 + mmq@4c1004c），disk = build = running 三方一致（`e0a6987f…`），config md5 `53ac61e0…` → `e23bbce5…`（只改 `exe`）；本轮**装机 2 次（pa1 已还原 / k10p 在产）/ 重启 4 次 / 停机 178 s / 回滚 0 次**。源码改动全部在分支 `gfx906/port-all`（`8b44f3d1`）与 worktree `pr/k10` |
| 9 | ROCm（容器内） | `.info/version` = **10.1.0**；HIP **7.16.26323-0000000**（`hipconfig`）；clang 24.0.0git；rocprofv3 1.3.5 |
| 10 | llama.cpp | pin **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`；另存 `ref/llama_b12169` 作最新对照 |

**二、主线** — `gfx906/mi50` @ e181bda5（`git describe` = `mi50-0.2.11-r33-14-2-ge181bda5`，落后上游 0 / 领先 80，脏 0 行）。
新分支 `gfx906/port-all` 从它拉出、领先 **2** 个提交（`79516b21` 全量移植 + `8b44f3d1` A5 派发修复），未合主线；分支名不在 CI 白名单，push 不触发 Actions。

**三、本次落生产** — **本轮累计：重启 5 次 / 停机 220 s / 装机 3 次 / 回滚 0 次**。07:23–07:27 A/B 窗口 3 次重启（136 s）；07:49 K10 装机 1 次（42 s）；08:06 升 b12180 装机 1 次（42 s，`running = /data/bin/strata-0.1.57-b12180`）。
b12180 冒烟（2.5K n=6 / 8K n=4）：**8K −0.28%（2×CV 0.47%）**、2.5K +0.04%、decode 不比 k10p 差 ⇒ 保留，`k10p` 退居回滚。
**没做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口。

**四、进度** — **383 条 / 已结 300 / 78.3%**（W1037 校正；本轮 +17：`P425`–`P441`）。
队列：**`R103`（置顶，等开窗）** → `R95`（暂不结案）→ `R94` → `R91` → `R89` → `R46` → `R49` → `R50`。

---

## 正文

**1. 交接自证先给结论。**
`python tools/handoff_check.py` → `HANDOFF: PASS (prompt=2319ch snapshot=W1037 denom=369/286 gates=12 live=off report=Y)`；
`python tools/progress.py` → 12 块 / 369 条 / 已结 286（77.5%），主线口径 341 条已结 286（83.9%）；生产 `/health` ok、restarts=0、在产引擎 md5 与 handoff 一致。
**生产健康，本轮不动它。**

**2. 开窗前先做了一件零成本的事：点开关。结果 pa0 里的 A5 是死代码。**
`strings <bin> | grep -c <VAR>`，五个开关在 `-001` 里 **0 个**（生产本来就没这个特性，符合预期），在 `pa0` 里 **4 个**：

| 开关 | `pa0` | 含义 |
|---|---|---|
| `STRATA_GFX906_ROUTE_DPP` | 1 | A1 router 归约 |
| `STRATA_GFX906_ATTN_DPP` | 1 | A3 softmax DPP |
| `STRATA_GFX906_ATTN_DP4A` | 1 | B1+B2 分数 dp4a |
| `STRATA_GFX906_ATTN_LDS_PAD` | 1 | A2 LDS 列 pad |
| `STRATA_GFX906_Q8_GATHER8` | **0** | A5 8-wide gather |

根因：`kv_q8.cu:221` 的**派发**仍包在 `#if defined(STRATA_EXPERIMENTAL_SM60)` 里；W1036 只把 8-wide 内核定义（`kv_q8.cu:110`）与 `pre75_q8_gather()`（`kv_q8.cu:158`）
放进了 `STRATA_HIP_GFX906` 分支 ⇒ 这个函数**没有任何调用者**，链接时被整个丢掉，连字符串都不在 `.rodata` 里。
**如果直接开窗，A5 会被写成「测了，零收益」——那是假的，实际是「没跑」。** 已修（派发处补 `|| defined(STRATA_HIP_GFX906)`，默认仍由 env 关着，
所以 pa1 的默认行为不变），重建 **pa1 = md5 `36bc1be7` / 43,043,424 B**，五开关 **5/5 在册**；`build-port2/strata` 与候选件同 md5（D1 身份），
`STRATA_HIP_GFX906=1` 在 `build.ninja` 里出现 259 次（不是空开关）。
**这条要固化成门**：凡是「一分支一编译、逐项开关」的 A/B，开窗前必须点开关。成本 0，能挡住整臂白跑。

**3. 两支判否，理由都在数字里，不在印象里。**

**(a)「Q4_K 只到 J=64 ⇒ MoE 白算」——判否。** 生产日志里 **12,268 行** `pick_J`，按 `ceil(ncols/J)*J/ncols` 统计：

| type | n | ncols 中位数 | padding 中位数 | 均值 |
|---|---|---|---|---|
| 7 = Q5_1 | 5,499 | 296 | 7.9% | 12.4% |
| 8 = Q8_0 | 667 | 302 | 7.2% | 11.0% |
| 12 = Q4_K | 5,961 | 296 | 7.9% | 12.4% |
| 13 = Q5_K | 141 | 294 | 7.6% | 14.4% |

尾部全在 `ncols=1` 这种退化样本（8×），而 gate/up 这类 ncols≈3000–4000 的调用 **≤1.8%**（3144 → 3200 列）。
另外把 pin（`3cf0325` = b11062）与最新 `b12169` 的 `mmq-config-gcn.cuh` **逐字节 diff：空**（Q4_K 段在 `mmq-config-gcn.cuh:120-130`，J 的选择在 `mmq.cuh:371-381` 的 `ggml_cuda_mmq_get_J_max`：`min(ne11,512)` 向下每 8 找一档；而 `mmq.cu:249` 只对 RDNA3/4 才把 `ncols_opt` 换成每专家均值，gfx906 走 `ne11`）——
「Q4_K 给 J≤64、Q8_0 给到 128」是**上游全局现状**，不是我们落后；J 加倍只减块数与权重重读（按 tile 算 −26% 流量），**不改 FLOPs**。
⇒ 不做表扩展，不开窗。

**(b)「预填内核还有 5.4× 空间」——下修到 ≤1.69×（更正 `P423` 的表述，不动它的事实）。**
`vecdotq.cuh:542-556` 的 Q4_K×Q8_1 MMQ 内环是 `dp4a((v[j] >> (4*i)) & 0x0F0F0F0F, u[...], acc)`——
**每 4 个 MAC 至少 3 条 lane 指令**（移位 / 与 / dot4），外加 v、u 的取数。算术很干脆：

- dp4a 峰值 26.5 TMAC/s（60 CU × 64 lane × 1.72 GHz × 4 MAC/指令）；按「1 条 dot4 = 4 MAC」的峰值口径，
  3 条指令能给出的上限 = 26.5 / 3 = **8.8 TMAC/s**；
- 2.5K gate/up 实测 3.93 TMAC / 754 ms = **5.21 TMAC/s** ⇒ 等价 **≈5.1 条指令 / 4 MAC**；
- 剩余空间 **8.8 / 5.21 = 1.69×**，不是 26.5 / 5.21 = 5.1×。

要吃这 1.69× 只能减少「每 4 MAC 的指令数」，唯一路径是让**激活也变 4-bit** 去走 `v_dot8_i32_i4`（8 MAC/指令、原生 nibble 不用解包），
而 `P38` 已判否（改精度 + 改格式）。⇒ **Q4_K MoE GEMM 没有内核级空间**，预填剩下的杠杆只在 R95 的固定项与 D2 的调度侧。

**4. 但 `P427` 不否掉 B1/B2——用的是同一把尺子。**
attn 分数内环现在是 **2.0 条指令 / MAC**：每个 cell 每个 head 是 256 次 `(float)c*sc` 反量化 + 256 次 FMA，一个 MAC 摊一条半指令，
离 0.75 的下限还有 **2.7×**；换 dp4a 后 ≈0.27 条/MAC（256/4 = 64 条 dot4 + 每组 scale 乘 + q 量化摊薄）。
**GEMM 侧已经贴顶，attn 侧没有**——这就是窗口只测 attn 的原因，也是 `P427` 与 `P421`（A0 零结果）不矛盾的边界：
A0 修的是 decode MMVQ 那条本来就不是 ALU-bound 的路。

**5. 为窗口定判据的相位账（同一批请求、n=2 同形状、`本机实测`，取自引擎日志）。**

| 形状 | GPU timeline | `qsa attn` | `gemm gate/up` | `gemm down` | `dequant` |
|---|---|---|---|---|---|
| 3403 tok | 5358 ms | **575（10.7%）** | 1126（21.0%） | 691（12.9%） | 570（10.6%） |
| 10773 tok | 13543 ms | **2231（16.5%）** | 2651（19.6%） | 1677（12.4%） | 539（4.0%） |

attn 份额随长度从 **10.7% → 16.5%**（3.16× token 换来 3.88× attn 时间），所以 B1/B2 的收益上限**随长度上升**，
判据取 8K/10.8K，不取 2K。按分数相位占 attn 的 ~48%（`PORT_PLAN §5` 的每 cell 账）估算：
3.4K 现实带 **2–4%**、10.8K **4–6%**。

**6. 上游再核查（本轮两处，都留了可复查出处）。**
① 本地两棵树：`ref/llama_3cf0325`（pin b11062）与 `ref/llama_b12169` 的 `mmq-config-gcn.cuh` **diff 为空**；Q4_K 表已有 `I=128` 行但 `J` 只到 64。
② 外网同卡实测（skyne98 `gfx906-dot4-dot8`，60 CU @1725 MHz）：`sdot4` 依赖链 21.7–22.3 TOPS、ILP4 43.0–44.4 TOPS（= 10.9–22.2 TMAC/s，理论 26.5），
`sdot8` 恰为 2×；同一站另一篇 `fp32-vs-qdq-dot` 的结论是「热循环里做 QDQ 比纯 fp32 慢 3×（2.00 vs 5.95 TOPS），只有**摊薄转换**才有收益」。
⇒ 与 `P427` 同向：**dot4 速率不是瓶颈，指令条数和摊薄方式才是**；也解释了为什么 B2 必须把 q 的量化放在「每步一次」而不是每个 cell 一次。

**7. 开窗清单（等点头，脚本已就位、已过语法检查）。**

| 臂 | 二进制 | 开关 | 目的 | 请求 |
|---|---|---|---|---|
| `ctl` | `strata-0.1.57-001` | 无（**不重启**，在当前生产上测） | 当次基线 | 5 预填 + 3 decode |
| `b` | `pa1` `36bc1be7` | `ATTN_DP4A=1` | B1+B2 | 同上 |
| `c` | `pa1` | `+ATTN_DPP +ATTN_LDS_PAD +ROUTE_DPP` | A1/A2/A3（bitwise，只判不劣化） | 同上 |

预填 = 2.5K×3 + 8K×2；**三次重启**（装机 / 加开关 / 还原）⇒ 预计 **5–8 min 不可用**。
安全设计逐条对着 W1036 的事故（`P422`）：`exe` 只写**容器路径**、config 备份 + md5 校验还原（失败重试 sudo，仍不符即中止）、
TERM 立即 `exit 130`、单引擎断言、每臂预热 + 每次取数 3 次重试 + 一次性盐值（防 prompt-cache 污染）、任一臂失败即整体中止。
配置改写已在**副本**上验过：只多一个 env 键，`args` / `model_name` / `port` 不变，还原后与原文**语义相等**。

**8. 举一反三：本轮沉淀的三条可复用判据。**
① **开关可见性**（`strings` 点开关）——「逐项开关」的实验设计有一个隐藏失效模式：开关在源码里、但派发被别的宏挡住，于是整臂静默变成 no-op。
② **padding 要按分布算，不按最坏样本算**——12,268 行日志里中位数 7.9%，只看 `ncols=1` 会得出「padding 8×」的错觉，只看 3144 会得出「padding 可忽略」的错觉。
③ **指令预算 = 上限 ÷ 每 MAC 指令数**——「利用率 18.5%」这句话本身没有信息量，必须先算清楚这条内环每 MAC 至少要发几条指令，否则会把结构性的 3 条指令当成 5.4× 的机会。

**9. 仍欠（不掩盖）。**
D2（`rocprofv3` 每 CU `SQ_INSTS` 方差、最忙/平均比）与 D3（rocBLAS 表 fallback 覆盖）都要独占窗口；B3 前提已被 `P421` 否掉；
C1（V 侧 fp16 累加）与 A4（逐文件 max-ilp）仍 defer；`P392` 的数值门、`P309`/`P335` 仍 OPEN，解除条件不变。

**10. 手法四条：把「能拿」变成指令计数（机主追问后的补账，`P428`–`P431`）。**
四条逐条落进 `PORT_PLAN §4.F`，每条带「判据 / 样本 / 停机 / 成本」：

| # | 手法（宿主） | 我们的落点 | 结果 |
|---|---|---|---|
| F1 | 载入暂存（iacop，Q8_0 载入软件流水） | Q4_K dp4a 分支 `mmq-load-tiles.cuh:711` | **编译通过、ISA 判否**：`s_waitcnt` 6192 → **6165（−0.44%）**，`global_load` 3788 / `ds_write` 289 / `v_dot4` 5184 **逐项相同** ⇒ 期望 <1%，不开窗 |
| F2 | DPP 归约（iacop `gfx906-common.cuh`） | A1 router + A3 softmax（pa1 里） | bitwise，随窗口一起测 |
| F3 | half-warp 32 线程派发（iacop `mmvq.cu`） | decode MMVQ / MoE 小矩阵 | **判不适用**：gfx906 只有 wave64，32 lane 空转半个 wave；decode 已在地板、收益不作成功判据 |
| F4 | 预量化直喂（exabit norm 直吐 Q8_1 / iacop `mmq-prequantized`） | 与 `STRATA_QFUSE` 同题 | **前置已否**：B3 前提被 `P421` 否掉；`wait copy` 在 2.5K 只占 1.2%，分母不够 |

F1 的机制值得记住：`threads_per_row = MMQ_ITER_K/(4*QR4_K) = 16`、`nrows = 64/16 = 4`、`nwarps = 256/64 = 4`
⇒ `STEP = nrows*nwarps = 16`、`I = 128` ⇒ 环路**只有 8 轮**，`#pragma unroll` 之后编译器本就把 8 次载入排到一起，
手工暂存没有可重叠的余量。**「这套写法在别人那儿有用」和「在我们这条固化配置上有用」是两个命题**，能分开它们的只有计数。

**11. 两处补账：最新版核对到位、0.9.0 的尾巴收口（`P429` / `P430`）。**
① 上一轮拿 `ref/llama_b12169` 当「最新」是**错的对照物**。本轮直接取 master
`bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z，距今约 8 小时），
其 `mmq-config-gcn.cuh`（HTTP 200 / 26,167 B / 256 行）与 pin 的同名文件 **`diff` 为空**，Q4_K 的 J 上限仍是 64
⇒ `P426` 的判否在**真 master** 上成立；顺带说明这 6.5 周上游没动过 gfx906 的 MMQ 表。
② `R100`（0.9.0 整树 / b12110）此前只留下「K10 免费」这一句，**没有处置**。本轮写成处置：
K10 = 534.83 / 716.72 vs 在产 532.76 / 714.89 ⇒ **+0.39% / +0.26%**（2×CV 内）；唯一实质修复 `#29953` 是越界读，
而我们的热路径自带 128 块余量（`P407`）⇒ 对我们是 no-op。**判不采用**；若要「跟上游对齐优先于收益」，一次重编 + 一个窗口即可。

**12. 「跟上游对齐优先于收益」——落实的第一步撞出三处丢失（`P432` / `P433`）。**
① **我们的 llama 树就是上游 pin**：`diff -rq ref/llama_3cf0325 llama.cpp` **输出为空**（166 MB / 1632 文件逐字节相同）
⇒ 没有隐藏补丁集，「对齐」纯粹是换 pin，这比我原先担心的干净。
② **K10 这次从上游重建，不靠那棵丢掉的树**：`ref/llama_b12110` 全树 + `ggml/src/ggml-cuda/mmq*`
（`mmq.cu` / `mmq.cuh` / `mmq-load-tiles.cuh` / `mmq-vec-dot.cuh` + 10 个 `mmq-config-*.cuh`）取自
`4c1004c49221b07c3b8108977e3d1991fc9f45cc`（2026-10-19T07:41:14Z，PR #30553），叠合后 `mmq.cuh` md5 `b74eadc5…` → `627c4c62…`。
③ **换 pin 的真实代价是 API**：上游把 `mul_mat_q_case` 从 `template<ggml_type>` 改成 `template<ggml_type, ggml_prec>`
（`mmq.cuh:1536` / `DECL_MMQ_CASE` 变成 `<type, GGML_PREC_Q8>`），我们树里 **25 处**调用要补第二个实参
（`mmq_kq_lib.cu` 4 / `mmq_nvfp4_w4a8.cu` 1 / `moe_mmq.cu` 20），已在 worktree `pr/k10` 改完。
④ **一个会被误读成 API 错的构建坑**：`build.ninja` 用的是 `/out/ggml-tq-overlay/` 里的**拷贝**头文件（configure 期生成）。
我之前为了跳过 cmake 把 `RERUN_CMAKE` 改成了 phony，于是换 `/llama.cpp` 之后编的仍是旧副本；
第一次的「`strata_w4a4_mul_mat_q_case` 没有匹配函数」其实是这个。⇒ **换 llama 树必须重新 configure。**

**三处真丢的，都补了门。** ① `-010`(K10) 的**源树没了**，而 `deploy_gate` 的 D2 只查回滚件、D6 只查报告，
没有一条门要求「这个二进制能再编一次」⇒ 新增 `deploy/REBUILD_RECIPE.tsv` + `tools/recipe_check.py`
（四列齐全才算候选，`LOST` 必须带编号；本轮 `--live` **PASS**：3 件可重建、1 件已登记）。
② `PORT_PLAN.md` 被机主定为「本方案的一个 R」，**166 上却没有这个文件** ⇒ `mirror_check.py` 6 件扩到 **7 件**
（新增 `EXTRA` 机制），`--sync` 后已同步。③ 手法①的 ISA 证据原本只在 166 的 `tmp/`（断电即丢）
⇒ 已抄成 `albus/w1037/STAGE_ISA_EVIDENCE.md`。

**13. 窗口已跑：三臂零效果，但原因是打错靶（`P434` / `P435`）。**

| 臂 | 2.5K gpu | 8K gpu | 2.5K `qsa attn` | 8K `qsa attn` | decode |
|---|---|---|---|---|---|
| ctl（`-001`，不重启） | 5372.7 ms | 13578.0 ms | 578.3 | 2237.5 | 57.6 tok/s |
| b（`ATTN_DP4A`） | 5480.7（+2.01%） | 13564.5（**−0.10%**） | 577.3 | 2241.0 | 59.7 |
| c（`+DPP +LDS_PAD +ROUTE_DPP`） | 5486.3（+2.11%） | 13575.0（**−0.02%**） | 576.7 | 2238.0 | 56.8 |

判据用当次 2×CV：2.5K 是 5.60%/6.40%（不显著，且首条是冷启动），8K 是 **0.20%/0.00%** ⇒ 8K 两臂差异在噪声地板上。
停机合计 **136 s**（三次重启 47/42/47），还原后 config md5 `53ac61e0…`、engines=1、`/health` ok。

**相位不动才是关键证据**：`qsa attn` 578.3 → 577.3、2237.5 → 2241.0，逐毫秒相同。改的代码若真在跑，
哪怕相位是访存受限也不会一丝不动。查 `prefill.cpp` 派发顺序：① `qsa_prompt_attn_batch_gated` → ② `qsa_prompt_attn_batch`
→ ③ `qsa_pattn_batch` → ④ 最后才循环调 `qsa_decode_attn_batch`（源码注释 "the decode kernel, 32 queries at a time"）。
**我们的开关只改第 ④ 条的 `attn_chunk_kernel`，而预填走 ①/②** ⇒ 改动不在热路径上。

⇒ `PORT_PLAN §4` 的「B2 真实落点 = `qsa_decode_attn.cu`，非 `qsa_pattn`」**作废**（当时只核了 `qsa_pattn` 在 HIP 下的编译条件，
没核 `prefill.cpp` 的派发顺序）。**真落点是 `qsa_prompt_attn.cu`**：2504 行、0 处 dp4a，分数与 V 累加是 fp32 `fmaf`
（`:353`/`:471-474`/`:725`/`:776`），分母 10.7%→16.5%。

**14. 四项报告第二次丢，这次是「数字过期」，已变成门（`P436`）。**
窗口跑完后，本报告开头的四件套仍写着「重启 0 次 / 0 分钟停机」，账本 `P434` 写的是三次重启、停机 136 s——
`report_lint` 只查字段在不在、`report_depth` 只查篇幅，**没有一道门比对报告里的数与账本里的数**。
新增 `tools/report_consistency.py` 接进 `round_close.py` HARD：按 SNAPSHOT 轮次取账本的最大重启次数/停机秒数，
要求「三、本次落生产」段出现同样的数。把旧文案放回去 → 当场 **FAIL 2 条**（负数自测）。硬门 13 → **14 道**。

**15. llama.cpp 那个搞定了：K10 从上游重建、编译通过、TQ overlay 保持 ON（`P437`）。**
分支 `gfx906/lcpp-k10` @ `fa8e6761`（父 = 主线 `e181bda5`，脏 0）；候选 `/data/bin/strata-0.1.57-k10p`
= `e0a6987f732a401f780f5dad5812812f` / 43,207,464 B（**未装机**）。四处 API delta：`mul_mat_q_case` 补 `GGML_PREC_Q8` **25 处**、
`ggml_cuda_mmq_get_config` **5 处**、`new_pool_for_device` 补 ctx **1 处**、
`cmake/strata_ggml_tq_overlay.cmake` 的 `", false"` 第 5 实参改为**直接探测 write-back 签名**（原来是从 get_nthreads 推断，b12110 已去掉）。
两个坑：换 `/llama.cpp` 必须重新 configure（否则编的是 `/out/ggml-tq-overlay` 里的旧拷贝）；TQ overlay 的版本探测不能靠推断。
上游三个 PR 已逐个核过：#29953（2026-10-08 OOB）、#30168（2026-10-09 prec 参数）、#30553（2026-10-19 = 4c1004c）。

**16. K10 装机完成（`P438`）。** 一次重启 42 s，`running = /data/bin/strata-0.1.57-k10p`（`e0a6987f…` / 43,207,464 B），
config `53ac61e0…` → `e23bbce5…`（只改 `exe`），`-001` 退居回滚件。冒烟两轮：**8K 1260.6 vs 对照 1256.6 us/tok = +0.32%**
（池化 2×CV 1.0%）、2.5K +0.47%（2×CV 2.5%）、decode 62.4 vs 57.6 tok/s（CV 14%/15%）⇒ 按机主口径**保留**。
**没做**：数值门（KL / top-1 的 LOGPOS 探针）仍需独占窗口——这条只覆盖性能面，别当成「已验证」。

**17. 还能升到最新吗？能编，收益要窗口判（`P439`）。**
master = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42），距 b12110 **70 个提交 / 300 个文件**。
按同一配方（master 全树 + `mmq*` 钉 `4c1004c`）**编译通过、零 API 改动**，候选 `/data/bin/strata-0.1.57-mstr`
= `d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B（未装机）。碰我们热路径的只有 4 条：`#31047`（已判否三次）、
`#31296`（NVFP4 融合，同族 `#29948` 曾 −5%）、`#31660`（MTP conv 快照）、`#30541`（量化 KV state copy）。
其余 ≈60 条是别的后端与模型支持。⇒ **能升，但 `R99` 就是在这条路上 −4.0/−4.6% 挂的，不能凭「编译过了」就装。**

**18. 升到 b12180 并装机（`P440`）。** b12180 的 sha 就是 `bcb01528`（= master HEAD），所以 07:57 编的 master 件就是它；
改名 `strata-0.1.57-b12180` 后装机，一次重启 42 s，config `e23bbce5…` → `5e9b81e2f66ca48999766d2ae0201fb6`（只改 `exe`）。两轮冒烟：
**8K 1257.1 vs k10p 1260.6 us/tok = −0.28%（池化 2×CV 0.47%）**、2.5K +0.04%、decode 62.1/66.3 vs 59.7/62.4 tok/s ⇒ 保留。
**没做**：数值门的 LOGPOS 探针仍需独占窗口。本轮累计重启 5 次、停机 220 s。

**19. 窗口零效果的真因：不是打错文件，是接错函数（`P441`，更正 §13/`P435`）。**
预填的调用链只有一条：`qsa_decode_attn_batch`（`:1073`，`kernel=-1`）→ `launch_chunks_batch` → `STRATA_ATTN_CHUNK_SEL(M,pre)`
（`:904-911`）= **`attn_chunk_kernel<M>`，没有 OPT 形参**；我们的 `STRATA_ATTN_OPT_BATCH/STEP` 只出现在 `:1170`
（`qsa_decode_attn_batch_rows`）和 `:1365`（`qsa_decode_attn_slots`）——变体路径，生产不进。
旁证：`qsa_prompt_attn_batch` 在 gfx906 按构造 `return false`（`qsa_prompt_attn.cu:2478-2480`）；`pattn_mode()` 默认 0（`qsa_pattn.cu:35`）。
⇒ §13 里「预填走 ①/②」是错的：② 直接拒绝、③ 没开，实际就是 ④，但 ④ 的派发里没有 OPT。
**已接线并编译通过**：`/data/bin/strata-0.1.57-pa2` = `234febafff8bcb502c2d462b3e5700c2` / 43,041,712 B（未装机）；
它的 llama 仍是 b11062，测之前要按 b12180 配方重编。
