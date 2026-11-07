
---

## 10 每轮收尾门（W1002 新增，补的是「调用者」）

W980 承诺「改成机制、不靠我记得」，实际只装了 `pre-commit → gate.py --source-only`。
结果：16 个提交未推、报告 lint 在本机无人调、W999/W1001 的实验源码留在 `/tmp` 与
`build-tab/repacktest/`、活方案分裂到 `W986_PLAN_V3.md`（`plan_lint` 正在报 FAIL）。
**工具齐备但没有调用者，等于没有门。**

现在一条改动从写到发，会经过四道自动门：

```bash
# 提交（自动）
git commit                    # pre-commit: gate.py --source-only + round_gate.py --ci
# 推送（自动）
git push origin gfx906/mi50   # pre-push: fork 策略 + round_gate.py --ci
# 远端（自动）
#   GitHub Actions / Downstream gate: verify.py + round_gate.py --ci
# 166 收尾（每轮一次）
cd /home/albus/strata166/pr/strata-fork
/home/albus/strata166/ci/strata-ci check       # 18 项静态门
python3 ci/round_gate.py --status             # 已推? 树干净? 证据齐? 移植状态?
# 本机收尾（每轮一次）
python albus/w1002/round_close.py --report albus/w1002/reply.md   # 四个 lint
```

`round_gate.py --ci` 做三件事：跑 `ci/repack_ab/verify.py`（产物 / 结果一致性 /
fair-A/B 标记 / 移植状态 / CI 接线）、对 `report_lint` 做**正例必须 PASS + 反例必须 FAIL**
的自测、检查 `PORT_STATUS.md` 存在。`--status` 额外检查 hooks 已装、
工作树干净、`remote HEAD == local HEAD`。

**负向自测是硬要求**：`albus/w1002/negative_test.py` 注入 5 种破坏
（伪造 ratio / 清空移植状态 / 删 fair-AB 标记 / 摘掉 workflow 调用 / 让 lint 恒真），
每种都必须让门 FAIL、恢复后 PASS。W1002 实测 **5/5**。

### 本轮实跑记录（2026-11-05）

| 门 | 结果 |
|---|---|
| `commit ab68576c`（pre-commit 实跑） | PASS |
| `push 5f73cd15..ab68576c`（17 提交，pre-push 实跑） | PASS |
| GitHub `Downstream gate` **run #25** | `completed / success @ ab68576c`（API 查得） |
| `strata-ci check` | 18 checks / 0 failed / 0 skipped |
| `gate.py --source-only` | 11 checks / 0 failed |
| `verify.py` / `round_gate --ci` / `round_gate --status` | PASS / PASS / PASS |
| `round_close --self-test` | 坏报告被拒（PASS） |
| `plan_lint` | **FAIL → 整改后 PASS**（4 份 PLAN 未登记已处理） |
| `ledger_lint` | 59 → 29 problems（30 行 9 列台账已补第 10 列） |

门第一次正向运行就抓到真缺陷：Windows 上传的 `RESULTS.tsv` 带 UTF-8 BOM，
首行注释被计成第 5 条数据；`run.sh` 的 BOM 会让 shebang 失效。已去 BOM 并改
`utf-8-sig` 读取防复发。

> 边界不变：GPU 基准与部署仍留 166 **人在环**（单卡被生产占满，自动构建会抢 GPU）。
> 自动化的只有静态门与推送门；这不是没做 CD，是 `CI_CD_POLICY.md` §7 的显式选择。
