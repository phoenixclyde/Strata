# W1002 · 工程交付状态（三问的正式答复件）

> 2026-11-05 21:4x–22:0x。机主三问：「请问你完整移植了吗？请问你的四项报告呢？请问你的 ci/cd 呢？」
> 追问：「你对应的门呢？不是说不会再漏了吗？」「还有个 lint」。
> 本件只讲**可复核的交付事实**，不含调优结论。调优结论见 `W832_OPT_PLAN_V2.md §6.5` 与 `PROGRESS.tsv`。

## 0 三个答案，先说

| 问 | 答 | 证据 |
|---|---|---|
| 完整移植了吗 | **没有。`PRODUCTION_PORT = NOT_DONE`** | `ci/repack_ab/PORT_STATUS.md`（机器可读，由 `verify.py` 强制检查）；`src/` `include/` `CMakeLists.txt` 本轮零改动；生产二进制 md5 未变 |
| 四项报告呢 | W994–W999 的报告件有并过了 lint，但 **W996 / W1000 / W1001 三条回复没有四件套章节**（违纪⑳：每条回复都要以它开头）；本轮补齐并新增「收尾门」 | `REPORT_STANDARD.md` / `REPORT_TEMPLATE.md` / `W832 §6.5 纪律⑳`；`albus/w1002/reply.md` + `report_lint` PASS |
| CI/CD 呢 | **有工具、没跑**：16 个提交未推、`strata-ci check` 一次没跑、`report_lint` 没接进任何 hook | 本轮已推 17 提交，GitHub run #25 success，`strata-ci check` 18/0 |

**追问「门呢」**：W980 我说「改成机制、不靠我记得」，实际只装了
`pre-commit → gate.py --source-only`（源码门）。报告、实验产物、推送三处**没有调用者**。
「有工具 + 没人调」不是门，所以照样漏。**本轮补的是调用者，不是再写一个工具。**

## 1 完整移植：做到哪、差什么

已完成的是**独立 bench 的公平 A/B**（W1001）：`build-tab/repacktest/ab_bench.cu`，
两臂共用同一份我们引擎 `mmq::quantize` 生成的 grouped 激活；
四档实测 rows 32/128/320/1024 → repacked/canonical = 0.659 / 0.935 / 1.149 / 1.007。
结论：小行数快 34%、大行数慢 15% ⇒ 立 R97 混合分派。

**这不是生产移植**。`PORT_STATUS.md` 六条通道：

| 通道 | 状态 |
|---|---|
| C1 权重上传侧 GPU repack | NOT_STARTED |
| C2 `mmq::Context::run` 三路分派 + tile 元数据 | NOT_STARTED |
| C3 激活布局逐字节对齐 | PARTIAL（两臂共用，但无断言） |
| C4 fused FFN | N/A（mx 明说仅单 token，prefill 拿不到） |
| C5 逐位等价 / 六档 / 2×CV / KL 质量门 / env 开关 / 回滚 | NOT_STARTED |
| C6 R97 混合分派原型 | NOT_STARTED |

**为什么本轮没硬上内核**：按机主「测完有实际数据才能做判断」和 V3.9 判据，
C6 的加权单内核收益要先出数（≥5%）才进 C1/C2；且 C1 动的是专家借槽上传路径，
必须带逐位等价与回滚窗口。跳过前置直接改 `src/` 会重演 W999 那次「用错 kernel
却判否」的错误。

## 2 四项报告：定义与合规

四件套 = **生产容器（8 字段）/ 主线（6 项）/ 本次落生产（4 项）/ 进度+队列**；
纪律⑳要求**面向机主的每一条回复都以四件套开头**，纪律⑲要求报告文档也按此。
`tools/report_lint.py` 是机械校验（12 位容器 id、32 位 md5、`args N`/`env M`、
`disk=build=running` 三方、队列 ≥5 个 R 且用 → 串）。

本轮新增的机制：`albus/w1002/round_close.py --report <md>` 把
`report_lint` + `plan_lint` 设为硬门，`ledger_lint` + `param_pair_lint` 一并汇总；
`--self-test` 故意喂坏报告，确认 lint 会拦（已 PASS）。

## 3 CI/CD：本轮实跑证据链

| 环节 | 命令 / 位置 | 结果 |
|---|---|---|
| 提交门 | `pre-commit` → `gate.py --source-only` + `round_gate.py --ci` | commit `ab68576c` 实跑通过 |
| 推送门 | `pre-push` → fork 策略 + `round_gate.py --ci` | `git push` 实跑通过（`ROUND_GATE: PASS`） |
| 推送 | `git push origin gfx906/mi50` | `5f73cd15..ab68576c`，17 提交 |
| GitHub Actions | `Downstream gate` | **run #25 completed / success @ `ab68576c`**（API 查得，非推测） |
| 166 静态门 | `strata-ci check` | **18 checks / 0 failed / 0 skipped** |
| 源码门 | `gate.py --source-only` | 11 checks / 0 failed |
| 实验产物门 | `ci/repack_ab/verify.py` | PASS（5 组） |
| 收尾门 | `ci/round_gate.py --status` | PASS；`remote HEAD == local HEAD: True`；打印 `PRODUCTION_PORT = NOT_DONE` |

新增入仓件：`ci/repack_ab/`（README、RESULTS.tsv、PORT_STATUS.md、两份 `.cu`、run.sh、verify.py）、
`ci/report_lint.py`、`ci/round_gate.py`、`ci/hooks/pre-push`、更新的
`pre-commit` / `install-hooks.sh` / `downstream-gate.yml` / `ci/README.md`。

### 负向自测（`albus/w1002/negative_test.py`，5/5 PASS）

| 注入 | 门 | 结果 |
|---|---|---|
| 伪造 `RESULTS.tsv` 的 ratio | verify | FAIL → 恢复后 PASS |
| 清空 `PORT_STATUS.md` | verify | FAIL → 恢复后 PASS |
| 删除 `ab_bench.cu` 的 `mmq::quantize` 标记 | verify | FAIL → 恢复后 PASS |
| 从 workflow 删掉 `verify.py` 调用 | verify | FAIL → 恢复后 PASS |
| 把 `report_lint.py` 换成恒 exit 0 | round_gate | FAIL → 恢复后 PASS |

**门第一次正向运行就抓到真缺陷**：Windows 上传的 `RESULTS.tsv` 带 UTF-8 BOM，
首行注释被当成第 5 条数据；`run.sh` 的 BOM 还会让 shebang 失效。已去除 BOM、
校验器改用 `utf-8-sig`。

## 4 「还有个 lint」——四个 lint 的真实状态

| lint | 之前 | 本轮 |
|---|---|---|
| `report_lint.py` | 在本机，无调用者；W1001 回复没跑 | 入仓 `ci/report_lint.py`；接进 pre-commit/pre-push/workflow/round_close；正反自测 |
| `plan_lint.py` | **rc=1 FAIL**：4 份 PLAN 未登记（含活方案 `W986_PLAN_V3.md`），没人看见 | 按纪律整改：V3.9 队列回写 `W832 §6.5`，W986 标 SUPERSEDED，四份按角色登记 ⇒ **PASS** |
| `ledger_lint.py` | 59 problems；其中 **30 行台账只有 9 列**（缺 ref） | 补齐第 10 列 ⇒ 29 problems（余为历史表格/短 note，见下） |
| `param_pair_lint.py` | 15 处族内滞后，rc=0 警告 | 收尾门汇总输出，列为待办 |

**剩余 29 项警告如实登记、不假装清完**：W832 历史表格单元格内裸 `|` 导致
cell 数不齐（约 12 行）、N5/N6 等短 note、param_pair 的 15 处族内滞后。
它们都不影响本轮四项判据，但属于台账债，列入 `PROGRESS` 后续处理。

## 5 外网核对（本轮查的两条，用来定门的设计）

| 来源 | 结论 | 用到哪 |
|---|---|---|
| GitHub Docs · workflow syntax / triggering | `branches` 与 `paths` 必须**同时**满足才触发；只写 `branches` 不含 `tags` 时 tag push 不跑；PR 用三点 diff、push 用两点 diff | 确认 `downstream-gate.yml` 的 `paths: ci/**` 会覆盖新增的 `ci/repack_ab/**`，且本次 push 确实该触发（run #25 实证） |
| GitHub Docs · required status checks | strict/loose 决定合并前是否要求分支最新；required check 是**分支保护**层的东西，workflow 自己不产生强制力 | 我们单人单分支、不开 PR，故不引入 merge queue；等价物是 `pre-push` 本地拦 |
| Continuous benchmarking 实践（InferenceBench CI recipe 等） | 性能回归门需 self-hosted GPU runner + 基线 envelope + tolerance；**GPU 基准不宜挂在每次提交**，通常放发布候选或夜间；且要防「门被改成 warning」 | 与 `CI_CD_POLICY.md` §7 的 A/B 选择一致：静态门上云、GPU bench 留 166 人在环；`verify.py` 特意检查 workflow 里 `verify.py` 调用仍在，防止门被摘掉 |

## 6 下一步（队列不变，见 W832 §6.5）

1. **R97-1 混合分派原型**（`ab_bench` 内按段拆两个 launch），出加权单内核收益；≥5% 才进 C1/C2；
2. 依收益决定完整移植：`PORT_STATUS.md` 逐通道改状态并附证据，**不许先改状态后补数据**；
3. R96 源码可行性 / R94 质量门并行；
4. 台账债：W832 表格裸 `|`、param_pair 15 处族内滞后。

> 预防复发的那句话：**门 = 工具 + 调用者 + 负向自测**。三者缺一，就等于没有。
