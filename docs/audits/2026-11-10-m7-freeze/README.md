# M7 冻结归档 · 2026-11-10（W1076）

> 【时效横幅 · M7/W1076】本目录所有件均为 `ci/w1047-coverage`（tip `7598100b1`，W1060b 冻结快照）的
> **逐字节搬运**，属冻结证据件：不改写、不更新、不与活件互相覆盖。现行值只认
> `deploy/PROGRESS.tsv`、`deploy/W832_OPT_PLAN_V2.md §0.1` 与 166 `/home/albus/strata166/deploy/` 活件。
> 大件（workbuddy 4552 路径镜像、大 TSV）在制品库 `/home/albus/strata166/archive/m7-20261110/`（不在 git）。

## 三组来源（M7 清单，MASTER_GOVERNANCE_PLAN §3 表）
| 组 | 来源 | 去处 | 内容 |
|---|---|---|---|
| provenance 5 件 | `ci/provenance/*` | 3 小件在 `provenance/`，2 大 TSV 在制品库 | 勘误范本/账本/447KB+3.6MB 清单 |
| workbuddy 冻结镜像 | `ci/workbuddy/` 4552 路径 | 制品库 tar.gz（含 180 个 C/CUDA 旧副本 + 68 个 /src/ 路径，历史口径 187 记差异） | L2 治理件 W1060b 全量 |
| 账本冻结快照 | `ci/workbuddy/deploy/{CI_RUNS,SOURCE_PROVENANCE,REBUILD_RECIPE}.tsv` | `ledgers/`（改名冻结，活件不覆盖） | 37/18/30 行 |
| 47 证据载体 | W1047–W1060 审计/调优报告、勘误横幅 | `evidence47/`（逐字保留；横幅在本 README 与各自原位登记） | 唯一载体=ci 分支 |

## 47 口径勘误（W1076 实测，两个「47」不是一回事）
- **47①** = `archive/*` 归档 tag：47 个（`git tag -l 'archive/*' | wc -l` 硬数），保已删分支、机制健康，欠注释规范（U14）。
- **47②** =「47 个 audit/CI 证据的唯一载体」（GOVERNANCE_PLAN §4.5）：**软引用，全库无逐项枚举**；同轮另一份盘点写的是「4551 个证据件」（= ci/workbuddy 整包），MASTER 写「20+ tag」——数字漂移实锤。
- **本次处置**：归档动作按 V3 §3-B 的**文件名清单**执行（与计数无关）；实抽 `deploy/AUDIT*` 32 件 + `albus/w1047..w1060` 报告 15 件（14 reply + wave64_audit；`draft_static.md` 草稿不计入）= **47 件**。数字巧合如实记录，**不**当作「恢复了 47 件唯一载体」的证明；若日后找到真枚举，再以取代链补入本目录。

## 取代链
- 本目录是 `ci/w1047-coverage` 分支（批 4 删除前会打 `archive/ci-w1047-coverage-final` tag）的**证据落地**；
- 活件演进不受本目录约束；本目录亦不覆盖任何活件（冻结写入纪律）。
- 校验：`M7_FREEZE_MANIFEST.tsv`（dest / git blob sha / size / sha256 / group / note）；重跑本归档脚本自动进入 verify-only 模式。
