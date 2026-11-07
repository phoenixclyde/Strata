# -*- coding: utf-8 -*-
import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
s = io.open(PLAN, encoding="utf-8").read()

a = "| 进度分母 | **300 条 / 已结 216 / 72.0%** |"
b = "| 进度分母 | **303 条 / 已结 219 / 72.3%** |"
assert a in s, "denominator"
s = s.replace(a, b, 1)

a2 = "`mi50-0.2.11-r33-10` @ `faaeb1c6`"
b2 = "`mi50-0.2.11-r33-11` @ `bc56628a`"
assert a2 in s, "tag"
s = s.replace(a2, b2, 1)
a3 = "behind 0 / ahead 73 / merges 0）"
b3 = "behind 0 / ahead 74 / merges 0）"
assert a3 in s, "ahead"
s = s.replace(a3, b3, 1)

BLOCK = """

---

## §6.5 回写 · W1029（2026-11-06 21:19–21:45）CI 的红是硬编码路径；门交回 GitHub

### 一、`#42–#44` 连红 9–11 秒，原因一行日志

`GET /actions/jobs/<id>/logs`（要绕开带 `Authorization` 的 302 才拿得到正文）尾部逐字：

```
ROUND_GATE: FAIL (1)
  - selftest_pin.py: [BAD] baseline: both declarations agree   rc=2
```

`rc=2` 是 **python 打不开文件**，不是 pin 判错。根因在 `ci/selftest_pin.py` 顶部：

```python
RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"   # 我的工作仓绝对路径
```

runner 上没有这个路径 ⇒ 每个用例都以 `rc=2` 结束 ⇒ 唯一必须通过的那一例（baseline）必然 `[BAD]`。
**一个路径 bug 穿着 pin bug 的外衣，把 44 次 run 之后的每一次推送都判红。**

修法：`RC` 由 `__file__` 推导；文件不存在时 `SystemExit` 明确报错，不再被计成 `[BAD]`。
判据（不是叙述）：**depth-1 clone**（没有工作仓路径、没有 tag，正是 runner 的样子）跑
`ci/round_gate.py --ci` → `ROUND_GATE: PASS`、`SELFTEST: 4/4`。

### 二、工作流顺带补两条

| 改动 | 为什么 |
|---|---|
| `actions/checkout@v7` 加 `fetch-depth: 0` + `fetch-tags: true` | depth-1 检出**没有 tag**，凡是读 tag 的检查都会因「与本次改动无关」的原因失败 |
| `ci/gh_gate.py`（新） | 部署第 0 步改为**要求 GitHub 上这次 sha 有一条 completed = success 的 `downstream-gate` run**；exit 6 = 没 run/还在跑，7 = 失败（打 URL），8 = API 不通 |

`ci/deploy.sh` 第 0 步现在先问 GitHub；W1028 的本地回执降级为「提示一句」，不再是判据。
这正是「必须走 GitHub」在代码里的样子：**门在变更落地的地方执行**。

### 三、仓库级开关是关的，而且 API 会说谎

| 探针 | 结果 |
|---|---|
| `GET /repos/phoenixclyde/Strata/actions/permissions` | `{"enabled": true, "allowed_actions": "all"}` |
| `PUT` 同接口 | **204** |
| `PUT /actions/workflows/403412814/enable` | **204** |
| `POST …/downstream-gate.yml/dispatches` | **422 `Actions has been disabled for this repository`** |
| 同账号**非 fork** 仓 `phoenixclyde/vllm-gfx906-routeb` 同一调用 | 422 **`Workflow does not have 'workflow_dispatch' trigger`** ⇒ 那边 Actions 是活的 |
| 推送 `faaeb1c6` / `bc56628a` 后 30 s | `GET /actions/runs` 无新 run；`gh_gate.py` 返回 6 |
| 邮箱 | 收件箱/垃圾箱**没有**任何 GitHub 的「Actions 已禁用」通知（只有 7 封 Run failed） |

结论三条：① 不是账号级（同账号另仓正常）；② 不是 workflow 级（state 一直是 `active`）；
③ 是**这个仓库自己的 Actions 开关**，REST API 翻不动，只有 Web UI 能开。

**需要你点一下（两处任一）**：仓库 → **Settings → Actions → General → Allow all actions**；
或 **Actions 标签页顶部的 `I understand my workflows, go ahead and enable them`**。
点完立刻可验：`python3 ci/gh_gate.py --wait 300` 会等到第一条 run 并给出 `PASS` 或失败 URL。

在此之前：`gh_gate.py` 一律 exit 6，`deploy.sh` 一律拒装。这是**故意的**——能被「云端不方便」绕过的门
不算门。

### 四、R99 与生产

R99 不变（S1 的 `tile_spec` 仍 hang 在 75-token，三个候选未验证）；生产零改动、零重启，
`strata-0.1.57-001` / config `53ac61e0…` / 容器 `2d765942e041` 全未变。

### 五、纪律

门的三段式现在是：**GitHub run（判据）→ 本地 round_gate（推送前自检）→ 166 接收端回执（第二双眼睛）**。
顺序不能反：后面的都不能替前面的作证。
"""
s = s.rstrip("\n") + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated")

rows = [
    ("B8工程", "P367",
     "CI 连红 #42–#44 的真因：`selftest_pin.py` 里硬编码工作仓绝对路径 → rc=2 → baseline 必 [BAD]；修为 `__file__` 相对 + 缺失即 SystemExit",
     "W1029", "DONE",
     "**W1029 立**：从 `GET /actions/jobs/<id>/logs`（绕开带 Authorization 的 302）拿到逐字 `ROUND_GATE: FAIL (1) / selftest_pin.py: [BAD] baseline … rc=2`。"
     "`RC` 原为 `/home/albus/strata166/pr/strata-fork/ci/release_check.py`，runner 上不存在 ⇒ 每例都以 rc=2 结束。"
     "改为 `os.path.join(dirname(__file__),'release_check.py')`，并在 `run()` 里 `os.path.isfile` 断言。"
     "判据：**depth-1 clone**（无工作仓路径、无 tag）跑 `ci/round_gate.py --ci` → PASS、SELFTEST 4/4。",
     "ci/selftest_pin.py"),
    ("B8工程", "P368",
     "部署门改回 GitHub：`ci/gh_gate.py` 要求该 sha 有 completed=success 的 downstream-gate run；本地回执降级为提示",
     "W1029", "DONE",
     "**W1029 立**：`ci/deploy.sh` 第 0 步改为 `gh_gate.py --sha $(git rev-parse HEAD)`，exit 6=无 run/进行中、7=失败并打 URL、8=API/无 token；"
     "W1028 的 `gate_receipt.py` 保留但只打印提示。token 取 `GITHUB_TOKEN`→`deploy/tmp/_tok.txt`→`~/.config/strata/gh_token`。"
     "另修 `.github/workflows/downstream-gate.yml` 的 checkout：`fetch-depth: 0` + `fetch-tags: true`（depth-1 无 tag，读 tag 的检查会无关地红）。"
     "三段式：GitHub run（判据）→ 本地 round_gate（自检）→ 166 回执（第二双眼睛）。",
     "ci/gh_gate.py"),
    ("B8工程", "P369",
     "仓库级 Actions 开关关闭且 API 翻不动：permissions=enabled + PUT 204 + dispatch 422；同账号非 fork 仓正常 ⇒ 只能 Web UI 开",
     "W1029", "DONE_NEG",
     "**W1029 立**：`GET /actions/permissions` = `{enabled:true, allowed_actions:all}`；`PUT` 与 `PUT /actions/workflows/403412814/enable` 均 **204**；"
     "`POST …/dispatches` 仍 **422 Actions has been disabled for this repository**。同账号非 fork 仓 `phoenixclyde/vllm-gfx906-routeb` 同一调用返回 "
     "422 `Workflow does not have 'workflow_dispatch' trigger` ⇒ 那边 Actions 正常，排除账号级。workflow state 一直 `active`，排除 workflow 级。"
     "收件箱/垃圾箱无 GitHub 的禁用通知。**只能 UI 开**：Settings→Actions→General→Allow all，或 Actions 页顶部 Enable 按钮。"
     "在此之前 `gh_gate.py` exit 6、deploy 拒装（故意）。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1029"),
]

lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t"); ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in rows if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("progress +%d" % len(add))
