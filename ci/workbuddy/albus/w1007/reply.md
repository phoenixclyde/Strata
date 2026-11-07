**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args 37；env 9 |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl --native … --expert-cache auto --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144 --kv k8v4 --prefill auto:16384 --prompt-cache-every 8192 --conversation-cache-mib 4096 --vision --mtp-window 8192 --vram-reserve-mib 832 --ple-io mmap --pool-workers 10` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_GFX906_TUNED` `STRATA_PREFILL_CPU_SHARE` `_MAX` `STRATA_PREFILL_TIMING` `STRATA_ROCBLAS_TUNING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt 2026-11-05T11:58:52Z |
| 5 | 资源隔离 | `ulimit -l` unlimited；`VmLck` 0 kB |
| 6 | 显存布局 | expert cache 7463 slots / 21.79 GiB、borrows 2606（7.62 GiB）、882 MiB of VRAM free（启动时值） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407` |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` |

**二、主线** gfx906/mi50 @ 13254cfb · tag `mi50-0.2.10-r32-15-g13254cfb` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。**三、本次落生产** 改动 0；重启 0 次；停机 0；代码面 0 提交（只动 `deploy/` 与 `tools/`）。**四、进度** 237 条 / 已结 157 / **66.2%**；队列 R95 → R94 → R91 → R89 → R46 → R49 → R50 → R98。

---

## 一、审计输出整改：三个真缺陷

| # | 缺陷 | 证据 | 处置 |
|---|---|---|---|
| 1 | **索引的手写计数与审计件打架** | `AUDIT_INDEX` 的 AUDIT24 行写 **P1 15**，审计件总判写 **16**；合计 34/125/107 也没跟上 AUDIT25/26 | 计数改由表推导（`audit_index.py --fix-total`）⇒ **36/129/110/7（21 件）**，并加判据「合计 ≠ 逐行和即 FAIL」 |
| 2 | **残值号无人认领**：`R15 的残值`（wait copy 预取深度）在索引里挂了很久，**账本里没有这个号** | `plan_lint` 只查「有号→有账」、`ledger_lint` 只查行内字段 ⇒ 两边都看不见 | 立 **R98**（§6.2 新32，判据是「先量后动」）+ 全库写法统一为「X 的残值」+ `tools/pointer_lint.py` |
| 3 | 索引的合计一直是手抄 | 一处 `--fix-total` 就改出 36/129/110/7，与逐行求和的差正好是 AUDIT24 那一处 15→16 和两个新审计 | 合计只能由脚本生成，门再比对一次 |

## 二、方案优化：从「三个副本」到「一个来源」

方案 1204 行里，同一个数字有三处副本、两张执行序（其中一张头行写着「不要按它排期」）。现在：

- **§0.1 现行事实（唯一来源）**：生产八字段、2K 相位（3191 ms / gu 816 / down 510 / dequant 161 / wait copy 37）、2K 相对 16K 的 1.23×、专家类型、进度分母、**唯一队列**、六件权威件、退役数字去处。别的章节写数字只许两种形式——**指向 §0.1，或写明「某轮实测」并给证据件**。
- **单队列**：删掉 V3.9 执行序表（12 行），只留一句指针。这是「两份执行序」这个问题的根治，不是再标一次 SUPERSEDED。
- **附录 A 退役数字表**：8 项旧值，每项写清「谁判的、换成什么」，`plan_retired.py` 强制「旧值只许出现在这里或删除线里」。

## 三、外网：一条新发现，两条上一轮的更正

- **新发现 `tandem.cpp`**（独立于 ggml-org 的 llama.cpp 补丁集）：做的事与我们同构——GPU 专家缓存 + 宿主专家 + **缺失专家由 CPU 并行承担**；报告在 **Qwen3.8-Flash-Next** 上 3.3×（IQ3_S+MTP，单 4090）、64K 上下文 prefill 1.4–1.8×。**不立项**：收益集中在 64K（专家并集已饱和），我们 2K 的缺口在 host/launch 侧；且数字来自单卡单模型。判据写进方案：R95 收尾后 2K 仍 >10% 缺口，先读它的 expert-split 内核。
- 上一轮更正的 **#22174（+9.67%，方向是关掉 stream-k）** 与 **#31188（PR 内无性能栏）** 已进附录 A，不会再被当成现行事实引用。

## 四、门（全部有负向自测）

| 门 | 判据 | 负向 |
|---|---|---|
| `audit_index.py` | 每个审计件有行 / 每行有件 / **合计 = 逐行和** | 2/2 |
| `pointer_lint.py` | 残值号必须有人认领；`§6.2 新<N>`、`§6.5 · W<N>` 必须存在 | 2/2 |
| `plan_retired.py` | 退役数字出现在「事实表行」即 FAIL | 5/5 |
| `mirror_check.py` | 六件权威件逐字节 | 6/6 |

五道硬门全接在 `round_close.py`，本轮：`report_lint PASS` / `plan_lint PASS` / `AUDIT_INDEX PASS` / `PLAN_RETIRED PASS` / `POINTER PASS` / `MIRROR PASS`。

## 五、边界（没做的，以及为什么）

- **冻结的历史件不动**：`W713_PLAN`、`W750_MASTER_PLAN`、`W775*`、`W863_*` 保留旧写法——它们是带日期的证据件，`pointer_lint` 的作用域因此限定在活文档。我一度机械改写了 10 份历史件，已逐字回滚。
- **行数 1204 → 1253**：+49 是 §0.1、附录 A 与 W1007 回写块，删掉的是重复的执行序表。**副本数**从 3 降到 1，这比行数重要。
- 生产、账本口径之外的东西一律没碰；分母 232 → 237 是 R98 与 P304–P307 五个新行，不是把旧项判结。
