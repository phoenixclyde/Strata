# AUDIT30 — 整改类：所有审计输出 + 方案本体（AUDIT28 的续集，对象=审计件自身）

> VERDICT: AUDIT30 P0=0 P1=1 P2=4 P3=0

机主令（2026-11-08 14:13）：「整改所有审计输出，并优化调优方案。」

时间 2026-11-08 14:15–15:0x。**生产零改动**：未重启、未换引擎、未改 config；全部为本机文件与工具、
GitHub API 在线核对。本件是 AUDIT22/AUDIT28 一系的「整改类」审计：对象不是业务轮次，而是
**审计输出自身**（24 件编号件 + 42 件 COMPANIONS + 2 本台账 + 方案本体）与**看管它们的门**。

COVERED: AUDIT6 AUDIT7 AUDIT8 AUDIT9 AUDIT10 AUDIT11 AUDIT12 AUDIT13 AUDIT14 AUDIT15 AUDIT16 AUDIT17 AUDIT18 AUDIT19 AUDIT20 AUDIT21 AUDIT22 AUDIT23 AUDIT24 AUDIT25 AUDIT26 AUDIT27 AUDIT28 AUDIT29

## 0 总判

**P0 = 0，P1 = 1，P2 = 4；5 条全部整改完毕（无一条登记挂着）。**

| id | 级别 | 位置 | 缺陷 | 处置 |
|---|---|---|---|---|
| A30-1 | **P1** | `tools/audit_outputs.py` + `deploy/` 顶层 | **点名门只扫 `*.md`**：AUDIT24 的 3 份 TSV 分片（`AUDIT24_GP4_W938_W951.tsv` / `AUDIT24_W905_W917.tsv` / `AUDIT24_W928_W937_GP3.tsv`）从「每个审计输出必须被点名」的门下逃逸；同时 **deploy/ 顶层躺着 304 份 `.bak` 编辑副本**（AUDIT 件 30 + PROGRESS 99 + 方案 53 + W750/713/776 计划 64 + SESSION_STATE 7 + 配方 5 + …），对所有门隐形——AUDIT29 A29-7 只清了 `albus/` 的 32 份报告副本，deploy/ 这一层没人看过 | ① 门扩展：`audit_ish()` 收 `.tsv`（台账两件显式豁免）；新增 **check 5**：deploy/ 顶层禁止任何 `.bak`（必须进 `deploy/_bak/`），自测同步扩展；② **304 份全部移入 `deploy/_bak/`**（历史保留，不再与活件同级）；③ COMPANIONS 补点名 3 份 TSV。现 `strays=0 / companions=42 / PASS` |
| A30-2 | **P1** | `W832_OPT_PLAN_V2.md` | **35 行表格 cell 数与表头不符**（AUDIT29 A29-6 只登记未修）：三类伤——**粘连行 3 处**（R32‖R33、R35‖R36、R42‖R20 被 `||` 挤成一行）、**短行 ~15 处**（尾部格子丢失，如 R31/R34/R38/R47/R48/R57/R55/R40/R41/R20、R101/R102、新1/新2、R5/R6、R15、R26、R49 等）、**内容裸竖线 3 处**（`max\|Δlogit\|`×2、`\|Δ\| ≥ 2×CV`）+ 多余尾格 3 处 | **全部修复，`tables clean`（35→0）**：粘连行按行拆开；短行用 `—` 补齐尾格（如实标注「未记录」，不编造内容）；裸竖线改 `‖·‖` 或 `\|` 转义；目录表 W1041 行补回丢失的「轮次」列。基线降为 0（`TABLE_SHAPE_BASELINE.tsv`），今后**任何**新破坏立即 FAIL |
| A30-3 | P2 | `AUDIT27_W1006_W1031.md:23` | A27-6 行内 `TESTING\|ADOPTED` 裸竖线把表格劈成 7 格（表头 6）——审计件自己犯了它在治的病 | 改 `／`；AUDIT27 基线 1→0 |
| A30-4 | P2 | 审计件的外证引用面 | 审计件引用的上游编号需要复核（「该上网查一定要上网查」）：#29953、#30168、#30553、#30837、#31188、#31247 | GitHub API 逐一核对：**6/6 全部 merged 且标题与审计件记载一致**（#30553 cap MMQ Stream-K / #30837 enforce DP4A MMQ tile height / #31188 fuse MoE gate/up+GLU / #31247 Q8_1 correction sum / #30168 src1 precision / #29953 MMQ OOB reads）。AUDIT26 对 #31188 的撤回（AUDIT28）与现状自洽 |
| A30-5 | P2 | `AUDIT29_W1032_W1052.md §6` | A29-6 边界写着「35 行留给下次编辑修」——本件把它做完了，边界若不闭合会变成「没人知道修没修」 | §6 第 1 条加 **【AUDIT30 已完成】** 闭合标注 |

## 1 为什么这批门洞重要（不是洁癖）

- **304 份备份副本与活件同级**，意味着任何按文件名/最新 mtime 取「审计结论」的脚本或人都可能拿到
  一份过时的审计——与 W1006（索引停在 AUDIT24）同型的病，只是这次藏在文件系统层。
- **门只扫 `*.md`** 意味着「每个审计输出必须被点名」这句承诺对非 md 产物从来没兑现过。
- **35 行劈开的表格**意味着 AUDIT24 纪律 22（治这个病的规矩）在它的主治对象上从未生效过——
  与 AUDIT29 A29-5（ledger_lint 瞎了）是同一种失败模式：**规矩在，电没接**。

## 2 修复明细（可复核）

| 件 | 动作 | 验证 |
|---|---|---|
| `tools/audit_outputs.py` | `audit_ish()` 收 `.tsv`；新增 check 5（顶层 `.bak` 必须 0）；docstring 更新 | `strays=0 / companions=42` PASS；对 304 份备份的检测已在本次运行中实证（修前 FAIL 1） |
| `deploy/_bak/` | 新建，收纳 304 份（30 份 AUDIT 件备份 + 274 份台账/方案/计划备份） | `ls deploy/*.bak*` = 0 |
| `deploy/AUDIT_INDEX.md` | COMPANIONS +3 份 AUDIT24 TSV 分片 | `audit_outputs` companions=42 PASS |
| `deploy/AUDIT27_W1006_W1031.md` | A27-6 行裸竖线改 `／` | 表格 0 破坏 |
| `deploy/W832_OPT_PLAN_V2.md` | 3 处粘连行拆分 + ~15 行补格 + 3 处裸竖线 + 3 处多余尾格 + W1041 行补轮次列 | `ledger_lint tables: clean` |
| `deploy/TABLE_SHAPE_BASELINE.tsv` | 重写：W832=0、AUDIT27=0，注明修复历程 | 门改为止痛点：新破坏立即 FAIL |
| `deploy/AUDIT29_W1032_W1052.md` | §6.1 加闭合标注 | 「留待下次」不再悬空 |

## 3 逐件体检（24 件编号审计 + 42 件配套，全部过机）

- **机读 VERDICT 行**：24/24，一行不少、一行不多，P 列与索引逐件相等（`audit_outputs` check 1）。
- **COMPANIONS**：42/42 文件存在（`audit_outputs` check 2，现含 3 份 TSV 分片）。
- **台账**：`AUDIT_LEDGER.tsv` / `AUDIT_LEDGER_A24.tsv` id 唯一、状态合法（check 3）。
- **撤回声明**：BAD_CLAIMS 全库扫描 0 处现行违规（check 4）——AUDIT26 #31188 误判的撤回链完整。
- **合计与边界**：由 `audit_index.py` 从表派生（非手打），`--fix-total` 已跑。

## 4 边界（不冒充完成）

1. `_bak/` 里 304 份是**冻结的历史证据**，只收纳、不清理——是否删除由机主定。
2. 短行补的 `—` 格表示「该格内容在历史编辑中丢失、未考证」，不是编造；如需真值须回到对应轮次产物。
3. AUDIT30 自身未被他件审计（`audit_scope` 显示 debt=1，即 W1054 本轮），按阈值 8 正常。
4. AUDIT29 §6.2 的「历史报告跨分支引用不追改」维持不变（改历史=伪造证据）。
