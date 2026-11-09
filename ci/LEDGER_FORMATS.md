# CI 证据账本格式与阈值（单一来源定义 · W1079/B1 前置 8）

> 活件路径：本机 `deploy/` + 166 `/home/albus/strata166/deploy/`（`mirror_check.py` 仓派生逐字节同步）。
> 可执行语义以治理仓 `tools/source_provenance.py` / `tools/ci_runs_lint.py` / `tools/deploy_gate.py` 为准；本件是人读定义（Compliance as Code 的声明面）。

## CI_RUNS.tsv —— D7 CI 证据覆盖账
| 列 | 含义 |
|---|---|
| key | 构建 sha（40 hex）或制品名（strata-*） |
| ref | 证据位置（ci/retro/* 等）或 `(exempt)` |
| run | GitHub Actions run id；`-` = 无 run |
| status | `success` / `exempt`（EXPECTED_FAIL 登记豁免）/ `failure` |
| note | 备注 |

**D7 判据**：装机 exe 的构建 sha 必须命中 `success` 或登记 `exempt` 的覆盖行，否则 REFUSE（fail-closed；SKIP≠PASS）。

## REBUILD_RECIPE.tsv —— 重建配方
exe → 构建输入三件套 sha 反查（复合 pin：基底 + mmq patch 两级记录）。

## SOURCE_PROVENANCE.tsv —— 来源三件账（声明 / 镜像 / 实建）
检查 A–D：三方 pin 一致；**check D**（构建树 vs 实建 md5）现为 `EXPECTED_FAIL EXP-0001`（解除条件 = P604 重建装机对齐，见 `deploy/EXPECTED_FAIL.tsv`）。
