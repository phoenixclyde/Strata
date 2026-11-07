# W1033 报告 · AUDIT28：整改 64 份审计输出，方案收成一张导航表

**一、生产容器（10 字段）**

| # | 字段 | 值（全部容器内/现场取值，2026-11-07 02:0x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | **`2d765942e041`**（full `2d765942e041f31f7cf3999a7fbabe8073a0ca0fd21b355228392c1624150a04`）· `strata-gfx906:0.2.11-101` |
| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B · `--version` 0.1.57 |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 3a | args 明细（19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` = `{"status":"ok","max_context":262144,…}` · `restarts=0` · `StartedAt=2026-11-06T16:48:17Z` |
| 5 | 资源隔离 | `ulimit -l` = **unlimited** · `VmLck 0 kB` / `VmPin 0 kB`（PLE 走 mmap，故意不锁） |
| 6 | 显存布局 | `expert cache auto: 22.88 GiB free, 700 MiB reserved (+218 MiB draft head) -> 6779 slots`；prompt 路径 **borrows 1554 槽（3.49 GiB）**；VRAM used 33,606,098,944 B / total 34,342,961,152 B（**VRAM free 0.69 GiB**）|
| 7 | 回滚件 | `-001`(在产) · `-002/003` · `-004`(0.9.0) · `-005`(H1) · `-006`(H2) · `-008`(ladder-5) · `-010`(K10) · `-011`(K13)；`ci/rollback.sh --exe strata-0.1.57-001 --apply` |
| 8 | 本轮改动 | 生产装机 **0 次**、引擎 **无净变更**；`disk=build=running` 三方 md5 均为 `5e63174dbd7cc04e5fa1b5fc455b2a73` |
| 9 | ROCm | 容器内 `.info/version` **10.1.0** · HIP **7.16.26323-0000000**(`hipconfig`) · clang **24.0.0git** · `ROCM_BUILD=7.14.0-gfx906+20260802001858`（AMD 官方组件矩阵已复核） |
| 10 | llama.cpp | **b11062** · `3cf03257f219afbe7334045ff7c6a06ac68c627d` · 整树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** — `gfx906/mi50` @ 6501c28f · tag `mi50-0.2.11-r33-14` · **领先 78 / 落后 0** / merges 0 · **脏 0 行**；本轮只改本机文档与门脚本，不推生产分支。

**三、本次落生产** — 引擎：**无净变更**；**重启 0 次、停机 0 分钟、回滚 0 次**；镜像/容器/config 全部未动。唯一远端读取是 `docker inspect` / `md5sum` / `rocm-smi` / `/health`，无任何写操作。

**四、进度** — 346 条 / 已结 264 / **76.3%**；队列 `R51` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`（`R101` OPEN 随 `P392`，`R99`/`R100`/`R102` 均已 DONE_NEG）。

---

## 正文

**1. 最贵的一条：审计件自己的「外网复核」是错的（P0）。** `deploy/AUDIT26_W898_W1005.md:33` 把「#31188 PR 内没有性能栏、+17.2% 无法核实、只能写作者称」写成结论，据此把方案的数字降级、把 `DGX Spark +17.2%` 塞进 `tools/plan_retired.py:31` 的退役表。上 GitHub API 逐字核：PR `31188` 正文**有** `### Performance` 对照表（`llama-bench -p 16384 -b 2048 -ub 2048 -r 5`）——DGX Spark Qwen3-30B-A3B Q4_K_M **2911.4→3410.8 t/s = +17.2%**、RTX 5090 **12611.7→13330.3 = +5.7%**，`created_at=2026-10-26`、`merged_at=updated_at=2026-10-28`（不是事后补写）。⇒ 结论改成「**数字属实，但 CUDA + MoE 融合路径（要 gate/up 行交错），gfx906 不适用**」；`P391`/`R102` 的否决不变，**理由换掉**。已全链改：`AUDIT26` 源头横幅、`AUDIT_INDEX` 行、`W832` 3 处、`PROGRESS` 4 行（`P302`/`R96`/`P280`/`R102`）、`plan_retired.py` 理由、`albus/w1032/reply.md` 更正横幅，并加门拦「撤回结论以现行事实出现」。

**2. 64 份审计输出第一次全部被点名。** 机械盘点 `deploy/AUDIT28_OUTPUT_REMEDIATION.md:1`：**23 件编号审计**（AUDIT6–AUDIT28）+ **39 件冻结派生产物**（`AUDIT17_CLOSURE.md` 与 `W*_AUDIT / W*VERDICT / W*REVIEW`）+ 2 本台账 + 1 份索引。其中 8 件（AUDIT15/18/19/20/21/22/25/26）原无统一总判、其余格式各异，索引 P 列**只能手抄**（AUDIT24 曾差 1 条、AUDIT25 曾整行 `—`）。本轮给每件补一条 `> VERDICT: AUDIT<n> P0=.. P1=.. P2=.. P3=..` 机读行，`tools/audit_outputs.py:1` 逐件比对索引；`AUDIT_INDEX` 新增 `COMPANIONS:` 清单，修掉 `tools/audit_index.py` 里 `want[n]` 对同号文件只留最后一个、把 `AUDIT17_CLOSURE.md` 静默覆盖的盲区。冻结件**逐字保留**（W1007 曾机械改 10 份历史件再回滚），只登记不重写。合计现为 **40 / 148 / 124 / 7（23 件）**。

**3. 方案从「2,300 行里找现行值」收成一张导航表。** 实测 `W832_OPT_PLAN_V2.md` 有 20 行自持「队列」、10 处带日期的「重排 / 执行顺序 / 队列第 1 序」、26 个回写块无目录，还有 1 处仍写「当前按 §6.5 顶部排序」。新增 `§0.2 本件怎么读`（7 行：现值、队列、条目、回写、退役数字、未结项、指针各去哪）、`§6.5.0 回写块目录`（26 块全覆盖、取块首句作摘要）、§6.5 抬头历史快照横幅，并把 4 处非引用块的陈旧声明改标。`tools/plan_single_source.py:1` 硬门：唯一队列恰好 1 行且在 §0.1、目录必须覆盖全部回写块、历史排期声明必须带标记、活文档禁写 `W832:<行号>`、分母必须等于 `PROGRESS.tsv`。15 个行号指针里 6 个在活文档，全换成小节名；`AUDIT_LEDGER.tsv` 的 `loc` 列与记忆件按冻结纪律保留，只在索引台账写明「2026-10-31 快照」。

**4. 外网补核 5 组，不猜。** #22174（`cuda: disable MMQ stream-k by default for MoE`）正文 2597.04→2848.26 = **+9.67%**、单卡 ≤0.073% 成立，但 PR **closed 未合并**，别写成「上游已默认关」；#22298 是 `fastdiv` 降开销 + **仅当 tiling 效率损失 ≤10%** 才跳过 stream-k fixup，不是无条件「取代」；AMD 官方 ROCm 10.1.0 兼容矩阵（2026-10-05 发布）逐项吻合 AUDIT23 的 CK 1.2.0 / rocBLAS 5.5.0 / hipBLASLt 1.4.1 / HIP 7.14 / LLVM 23，且官方矩阵最老只到 gfx908、**不含 gfx906**；AMD 官方 MI50 规格 **1 TB/s**、60 CU、FP32 **13.3 TFLOPS** 与 AUDIT19 的 1024 GB/s 分母一致，顺带发现 W1014 记的 13.4 是抄写误差。「约 17% 的 2×4090 报道」与 `sdot4 21.7 TOPS` 本轮**未核到一手出处**，明确标「未复核」，不删也不当判据。

**5. 一次事故，已恢复并留痕。** 本轮一次 `io.open(p,"w").write(re.sub(...))` 在同一表达式里先截断文件、后因闭包作用域报错，把 `deploy/AUDIT24_W900_W951.md` 写成 **0 字节**。已由开工前的 `*.bak_a28_20261107_015655` 逐字恢复，重放 VERDICT 行与指针替换两处改动，`AUDIT_OUTPUTS` / `ROUND_CLOSE` 全绿后才继续。这正是铁律「写文件禁同式内 read+open」的反例，已写进 `AUDIT28 §4` 与 `P404`。

**6. 门与收尾。** 新增 `tools/audit_outputs.py`、`tools/plan_single_source.py`（各负向自测 4/4），接进 `albus/w1002/round_close.py:23` 的 HARD；`AUDIT_LEDGER_A24.tsv` 补 8 行 A28 标记 ⇒ `audit_closure` 64 行全 RESOLVED。生产零改动，权威件（含动态派生的 AUDIT28）逐字节同步 166。

**7. 未结与边界。** `P392` 的 prefill-only LOGPOS 数值门仍需停生产 10–15 min，**未经你点头不执行**；R51/K10「免费」只在 prefill 2K/8K 形状成立；`P309`/`P335`/`R101` 保留 OPEN 并各带解除条件。冻结件里的旧口径与旧行号是**有意保留的历史证据**，现行口径一律走 `W832 §0.2`。
