# W1032 报告 · AUDIT27：26 个未审轮次、1 个 P0，以及「门自己瞎了」的三种形态

**一、生产容器（10 字段）**

| # | 字段 | 值（全部容器内/现场取值，2026-11-07 01:0x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | **`2d765942e041`**（full `2d765942e041f31f7cf3999a7fbabe8073a0ca0fd21b355228392c1624150a04`）· `strata-gfx906:0.2.11-101` |
| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B · `--version` 0.1.57 |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 3a | args 明细（19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` = `{"status":"ok","max_context":262144,…}` · `restarts=0` · `StartedAt=2026-11-06T16:48:17Z` |
| 5 | 资源隔离 | `ulimit -l` = **unlimited** · `VmLck 0 kB` / `VmPin 0 kB`（PLE 走 mmap，故意不锁） |
| 6 | 显存布局 | `expert cache auto: 22.88 GiB free, 700 MiB reserved (+218 MiB draft head) -> 6779 slots`；prompt 路径 **borrows 1554 槽（3.49 GiB）**；VRAM used 33,601,904,640 B / total 34,342,961,152 B（**VRAM free 0.69 GiB**）|
| 7 | 回滚件 | `-001`(在产) · `-002/003` · `-004`(0.9.0) · `-005`(H1) · `-006`(H2) · `-008`(ladder-5) · `-009`(K10) · `-010`(K10 复测) · `-011`(K13)；`ci/rollback.sh --exe strata-0.1.57-001 --apply` |
| 8 | 本轮改动 | 生产装机 **0 次**、引擎 **无净变更**；`disk=build=running` 三方 md5 均为 `5e63174dbd7cc04e5fa1b5fc455b2a73` |
| 9 | ROCm | 容器内 `.info/version` **10.1.0** · HIP **7.16.26323-0000000**(`hipconfig`) · clang **24.0.0git** · `ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| 10 | llama.cpp | **b11062** · `3cf03257f219afbe7334045ff7c6a06ac68c627d` · 整树 hash `6feee58927d5f1efd38e72bbc1db061d`（GitHub git/ref API 复核） |

**二、主线** — `gfx906/mi50` @ 6501c28f · tag `mi50-0.2.11-r33-14` · **领先 78 / 落后 0** / merges 0 · **脏 0 行**；上游基线与镜像 `/src` 同源。实验台账分支 `gfx906/lcpp-picks` 本轮推到 **`209d3ca2`**。

**三、本次落生产** — 引擎：**无净变更**；**重启 0 次、停机 0 分钟、回滚 0 次**；镜像/容器/config 全部未动（审计全程只读）。唯一远端写入是 `gfx906/lcpp-picks` 分支上的两份流程文档提交，不碰生产树。

**四、进度** — 342 条 / 已结 260 / **76.0%**；队列 `R51` → `R95` → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`（`R101` OPEN 随 `P392`，`R99`/`R100`/`R102` 均已 DONE_NEG）。

---

## 正文

**1. 范围不是「从上一次审计往后推」推出来的。** `albus/audit27/scope.py:1` 从三处取并集——记忆件的 `##` 轮次标题、`deploy/*.md` 文件名、`PROGRESS.tsv` 的 `source` 列——再与 `AUDIT_INDEX.md` 逐行解析出的覆盖区间求差。这里修掉一个老陷阱：`albus/w831/audit12_scope.py:14` 用 `W(\d{3})`，会把 `W1006` 读成 `W100`，对四位轮号整体失效。结果：全库 291 个编号，AUDIT26 上界是 W1005 ⇒ **W1006–W1031 共 26 轮从未被任何审计覆盖**；另补审 era 之前的 W706/W707，复核 W854/W855/W884/W885 无此轮、W863 由 AUDIT18 单轮覆盖。审计件 `deploy/AUDIT27_W1006_W1031.md:1` 带 `COVERED:` 清单与 26 行逐轮表。

**2. 总判 1 P0 / 8 P1 / 5 P2，14 条全部整改或显式登记。** 最贵的一条：`gfx906/lcpp-picks` 分支的 `ci/lcpp_picks/README.md` §3 仍在命令下一个执行者用「48-token 贪心指纹逐字节相同」验收补丁——而 `P388` 实测同一引擎同一提示连跑两次 `en2k` 234 vs 242、`zh2k` 82 vs 79，这个门本就不成立；§6 还写着「ladder-5 回答退化 ⇒ #29953 REJECTED」，与 `P389`/`P390` 及 `PICKS.tsv` 的 ADOPTABLE 直接冲突。`252ec8ff` 只改了 `PICKS.tsv`，没改 README 和 `apply.sh`。已按「撤回必须回写源头」补齐三处并推分支 `209d3ca2`：换 prefill-only LOGPOS / `quant_quality` 相对门、`apply.sh` 状态枚举补 ADOPTABLE、§7 资产表补 K10/K13 两臂。

**3. 三种「门自己瞎了」，都补成了硬门。** ①`tools/plan_lint.py:104` 的 `R\d{1,2}` 让三位数 R 号从 W1026 起隐形，`R101`/`R102` 在 `deploy/W832_OPT_PLAN_V2.md:529` 有条目却无账本行 ⇒ 双重免检；正则改 `\d{1,3}` 后方案 R 号 72→75、缺 0，并补登记两行。②`deploy/W832_OPT_PLAN_V2.md:24` 的「唯一事实块」分母停在 W1030 的 309/229，实际 342/260；队列在报告和方案里各写一套（一个丢 R89、一个把已结的 R100-S5 仍排最前）。③`albus/w1003/mirror_check.py:33` 把「最新审计件」写死成 AUDIT26，新审计一落地 166 就留旧件。新增 `tools/audit_scope.py:1`（A 审计债 >8 轮 FAIL / B 废止门以现行指令出现 FAIL / C 缺报告 FAIL / D 分母与队列 FAIL），负向自测 4/4，接进 `albus/w1002/round_close.py:23` 的 HARD。

**4. 六条「做完了还挂 OPEN」已结清。** `P380`（4% 归因与 zh 分区，H1/H2/K10/K13 已定位）、`P343`（全量重编卡 ggml，W1020 改挂 `llama_3cf0325` 后 154/154 LINK_OK，且 166 上四个 ref 里只有 pin 树含 `iqp.cpp`）、`P346`（第四指针，W1021 复核 `--version`=0.1.57）、`P359`（tile_spec，R99/S1 做完并判否）。`W832` §6.6 的 R99 四阶段方案抬头也补了关闭横幅与 W1026 落点——此前全文 `\bW1026\b` 命中 0。另两条在 `AUDIT_INDEX` 的未结表里：`R15 的残值` 已由 `R98` 判 DONE_NEG（W1014 三档 −0.53/−0.61/−0.55%）；`telemetry.py` 的 CI 修复经现场 md5 `94d6949d…` 与主线逐字节比对，确认已在 `strata-gfx906:0.2.11-101` 镜像里。索引里其余 9 条真 OPEN 已在 `deploy/AUDIT27_W1006_W1031.md §7` 逐条点名，不造新号。

**5. 外网逐条核过，不凭印象。** #29948 的 PR 正文限定 **NVIDIA Turing+**（DGX Spark Q4_K_M +7.1%、5090 +1.9~4.7%），所以 gfx906 上 `fusion.gate==nullptr`、−5% 是 codegen 代价；#31047 的 **1.23×** 只是 `MI60/MI50 · granitemoe Q4_0 · mb=64 · pp8192` 单一格；ORT #32182 的 4.54× 是 **closed 未合并**、只用 `mma.sync`(sm_80+) 且正文自述 FLA 在 T>1024 反超；tandem.cpp 的 3.3× 是 **GSM8K decode tok/s**，不是 prefill；`b11062`/`b12129`/`b12169`/`b12110` 四个 sha 与 v0.9.0(ggml 0.29.0) 全部对上；compare API 给出 `3cf03257..master` = **1115 commits**，与 W1031 一致。GitHub 官方文档还补了一条 W1029 没写的可能：若 UI 也开不了，可能是平台侧禁用状态，应联系 Support。#29478 的 MI50 增益主要来自同 PR 的 FATTN 屏障，而 `fattn` 不在我们 26 个 MMQ TU 的编译面 ⇒ 为 W1031「零效果」提供第二种解释。W1014 的 gfx906 dot 数据本轮未核到一手出处，标「未复核」，不删也不当判据。

**6. 收尾。** `deploy/AUDIT_INDEX.md` 补 AUDIT25 的 2/7/6（此前合计少算 15 条）与 AUDIT27 行，合计改为 **39/144/121/7（22 件）**；`tools/audit_index.py` 的边界与合计改为派生；`deploy/AUDIT_LEDGER_A24.tsv` 新增 13 行标记并刷新 md5 基线，`tools/audit_closure.py` = **56 行 / RESOLVED 56 / FAIL 0 / WARN 0**。`albus/w1020/reply.md:1` 是 26 轮里唯一缺的报告，补的是**明确标注非原始报告**的审计补录，不伪造当时十字段。

> **【AUDIT28 更正 2026-11-07】** 相邻的 `AUDIT26` 有一条外网复核结论是错的：它写「#31188 PR 内无性能栏、17.2% 无法核实」，而 PR 正文确有对照表（DGX Spark 2911.4→3410.8 = +17.2%）。该误判已连带改掉方案 3 处、账本 4 行、`plan_retired.py` 的理由与 `AUDIT26` 源头横幅，详见 `deploy/AUDIT28_OUTPUT_REMEDIATION.md`；AUDIT28 之后分母为 **346 / 264 / 76.3%**。

**7. 未结与边界。** `P392` 的 KL 门仍未完成（要停生产 10–15 min，**未经你点头不会停机**）；`R51` 的 K10「免费」只在 prefill 2K/8K 形状成立，不能外推；`P309`/`P335`/`R101` 保留 OPEN 并各写了解除条件。本轮全部动作只读生产，唯一远端写入是实验分支的文档提交。
