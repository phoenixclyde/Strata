# W948 · 报告固化（lint）+ llama.cpp 版本真相：**三家 gfx906 fork 都比我们旧，上游 master 才新**

> **【W953 更正 · 2026-11-04】本件（及其 AUDIT24 横幅）的版本判断作废，方向反了。**
> 正确锚点：我们的 `llama.cpp/CMakeLists.txt` 写着 **LLAMA_VERSION 0.4.1**，且
> `ggml/src/ggml-cuda/mmq.cuh` 与 upstream **`e6ab7c1a4` 逐字节相同（diff = 0，71,851 B）**
> ⇒ 我们就是 **0.4.1（2026-09-22）**。
> 同字段各 tag：`e6ab7c1a4` 0.4.1 · `b11553`(mx) **0.6.0** · exabit **0.7.0** · `b12099`/master **0.8.0**。
> ⇒ **「三家 fork 都比我们旧」是错的**：mx / exabit 都比我们新，只有 furnace 与我们同基座。
> `get_J_max` 是 **0.4.1 时代的上游符号、后被上游删除**（furnace 同基座但重写了 MMQ）——
> 所以「有它 = 更旧」，不是「我们的补丁」。`R90` 因此**从方向成立升级为硬事实：落后 4 个 minor**。

- 日期：2026-11-04 15:5x–16:1x
- 机主两条指令：①「第一项缺 arg env，最后一项缺队列……不能固化下来吗？」②「换，而且换紧跟上游的 gfx906 专门版本。」

---

## 1 固化：不是"我记得写"，是"机械校验不过就不许发"

新增三件，已落地：

| 文件 | 作用 |
|---|---|
| `tools/report_lint.py` | 读报告草稿，逐字段正则校验：12 位容器 id、**32 位 md5**、**`args N` / `env M`**、`expert cache`/`borrows`/`VRAM free`、`ulimit -l`/`VmLck`、回滚命令、**队列 ≥5 个 R 编号且用 → 串**。缺一条就 FAIL 并列名。 |
| `deploy/REPORT_TEMPLATE.md` | 八字段逐项写「必填内容」+「我犯过的反例」（例如第 3 项"只写 md5（被指出两次）"） |
| `albus/w948/snap2.sh` | 一次跑出 8 字段原始值，**args 33 条与 env 9 条带明细**，不再手抄 |

**流程固化**：`snap2.sh`（远端）→ `tools/progress.py`（进度）→ 抄 `W832 §6.5` 队列 → 填模板 → **`report_lint.py` PASS 才发**。

## 2 版本真相：数据推翻了"fork 更新"这个前提

用 `mirror 区 sha256`（CMake 的 `_strata_mmq_tab_known`）与 `get_J_max` 这两个硬标志比：

| 树 | mmq.cuh 大小 | mirror 区 SHA | 有 `get_J_max` | 与我们的 diff |
|---|---:|---|---:|---:|
| **我们的 pin（3cf03257）** | 71,851 B | **36e4dc71…**（已知） | **有** | — |
| furnace（e6ab7c1a4, 9-22） | 71,485 B | 36e4dc71…（同） | 无 | +0 / **−11** |
| exabit（master = merge-v0.7.0） | 74,285 B | 279e519a…（不同） | 无 | +210 / −223 |
| mx（b11553） | 74,323 B | 278a0532…（不同） | 无 | +210 / −221 |
| **llama.cpp 上游 master（b12099, 今天）** | **79,586 B** | — | **无** | **+/- 587 行** |

三条结论：

1. **furnace 是唯一能"零成本"换的**（mirror 区一致，只需把 11 行 `get_J_max` 的差异接受掉），但它的基线是 **9-22，比我们旧**；
2. **exabit / mx 的基线上游也没有 `get_J_max`** ⇒ 它们同样基于 9 月之前的树，**不是"更新"，是"更旧 + 自己的改动"**；
3. **真正新的是上游 master `b12099`（2026-11-04，今天）** —— 与我们差 **587 行**（单 mmq.cuh）。

⇒ 机主说的"太老"在**方向**上成立（我们落后 upstream master），但"换到某个 gfx906 fork"**会降级**。
正确目标不是换 fork，是 **换基线到 b12099 + 把 gfx906 专门改动作为补丁层叠上去**。

好消息（已核）：上游 master **已有 `mmq-config-gcn.cuh`**（#27841 的 GCN 配置，HTTP 200）⇒ 换过去不必重新搬它；
坏消息：`q8_repack/` 仍是 fork 独有（HTTP 404）⇒ repack（R86）要自己叠。

## 3 升级计划（分四步，每步可回滚）

| 步 | 动作 | 判据 | 风险 |
|---|---|---|---|
| **S1** | 下载 `b12099` 的 `ggml/src/ggml-cuda/` 全目录 → `~/strata166/ref/llama_b12099/` | 目录完整（文件数 ≥ 上游 listing） | 无（只读） |
| **S2** | 用 b12099 当 `STRATA_GGML_DIR` 编译，**先关 `STRATA_MMQ_TAB`** | 编出 `strata`，`build-r28` 不动（新 build 目录） | 中：`moe_mmq_tab.cuh` 的 static_assert 会失败 ⇒ 关 tab 规避 |
| **S3** | 重做 mirror：把 b12099 的 `mul_mat_q_process_tile → DECL_MMQ_CASE` 区同步进 `moe_mmq_tab.cuh`，更新 CMake known hash，跑 `prefill_mmq_tab_test` | 逐位相等 | 高：587 行 diff 里包含调度重构 |
| **S4** | 叠 gfx906 补丁层：repack（R86）、q8_1 cache（R87）、max-ilp（R49） | 各自 A/B | 中 |

**回滚**：`build-r28` 与 `~/strata166/llama.cpp` 都不动，新基线只在新目录；生产引擎不换，直到 S2/S3 出二进制且数字不劣。

## 4 本轮实际做到哪

- 固化三件：**完成**（lint / 模板 / snap2，已跑通，args 33 + env 9 全字段）；
- 版本比对：**完成**（五棵树，mirror SHA + get_J_max + 行级 diff）；
- S1（下载 b12099 全目录）：**未做**（本轮时间用于固化与比对），下一步第一件事。

## 5 一条要说清的自查

我上一轮说"我们 0.4.1、社区 v0.7.0、差 3 个 minor" —— **那个版本号对比是错的依据**：
`LLAMA_VERSION 0.4.1` 是我们树里那个快照的号，不能直接和 fork 的 release 名比先后；
真正的先后要看**代码标志**（`get_J_max`、mirror 区 SHA、行级 diff）。本轮就是用这三样重判的。
