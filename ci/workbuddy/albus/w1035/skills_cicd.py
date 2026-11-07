"""W1035 第 15 段：补第 5 个技能 strata-ci-cd（CI/CD 拓扑与触发实测）。

一次落盘、单次执行；长件先备份。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035g"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


SEC = """
**15. 补齐第 5 个技能 `strata-ci-cd`（机主问「CI/CD 你不落独立技能吗」）。**
上一批 4 个技能里，`strata-release` 管「怎么编/怎么装」、`strata-deploy-evidence-gate` 管「凭什么允许装」，**没有一个管「什么时候会自动跑、跑在哪、怎么证明它真会跑」**——而这恰好是我这几轮反复重查的东西（触发条件、分支保护边界、pre-push 位置），每次都要重新翻 API 和记录。所以补这一个。

内容不是复述流程图，而是四类可复核事实：
① **13 个节点分布在 GitHub / 166 / 本机**，标出三个真正的阻断点（pre-push `round_gate` · `deploy.sh 0/8` `gh_gate` · `3.5/8` `deploy_gate`）；
② **六条触发条件**（T1 dispatch / T2 白名单+命中 paths / T3 不命中 / T4 非白名单 / T5 tag / T6 PR）**正例与反例都测过**——只测正例等于没测；
③ **三层门的真实覆盖面**：Actions 只静态（workflow 自述 *deliberately not a build*）· 分支保护只挡合并（直推返回 `Bypassed rule violations`）· pre-push 是唯一"到点必跑"；⇒ **门该设在装机前，不是 merge 前**；
④ **分支方针**：生产单分支且名字不带版本号、实验走 `ci/**`、上游只读（`core.hooksPath` 未设 → 默认 `.git/hooks/`，`pre-push` 头两行硬拒推上游）、只 rebase 不 merge。

**逐个核过，不靠记忆**：`ci/` 下 `round_gate.py`(7327 B) · `install-hooks.sh`(354 B) · `bench.py`(5540 B) · `rollback.sh`(2631 B) · `gh_gate.py`(5573 B) · `gate.py`(15374 B) · `gate_receipt.py`(3556 B) **全部实存**（上一版 `head -20` 截断导致 `rollback.sh` 看着像不存在，这次逐个 `-f` 断言）；本机 `ci/` 只有 `bundle_budget` 与 `prefill_phases`——**本机跑不了对等门**，这条也写进坑位。
`quick_validate` 通过；同时把 `strata-deploy-evidence-gate` 的分工表补上 `strata-ci-cd` 一行，避免两个技能各说一半。

**为什么它是技能而不是一段文档**：它的价值在**反例**——「为什么不触发」比「什么会触发」更容易记错，而错一次就会得出"CI 是摆设"或"我推了它就该跑"的相反结论。
"""

PLAN_ADD = """
**补充 2（同日，第 5 个技能）**：`strata-ci-cd` —— 13 节点拓扑（GitHub 只静态 / 编译装机 A/B 全在 166 / 三个阻断点）、**六条触发条件正反例实测**（含"不该触发"的三条）、三层门真实覆盖面（Actions 仅静态、分支保护只挡合并不挡直推、pre-push 唯一硬拦 ⇒ **门设在装机前**）、分支方针（生产单分支不带版本号 / 实验走 `ci/**` / 上游只读 / 只 rebase）。`ci/` 下 7 个脚本逐个 `-f` 断言实存；本机 `ci/` 只有 bundle_budget 与 prefill_phases ⇒ **本地对等门跑不了**。
"""

P415_NOTE = ("  **第 5 个技能（机主追问 CI/CD）**：`strata-ci-cd`——13 节点拓扑 + 六条触发条件正反例 + "
             "三层门覆盖面（Actions 仅静态 / 分支保护只挡合并 / pre-push 唯一硬拦）+ 分支方针；"
             "`ci/` 下 round_gate/install-hooks/bench/rollback/gh_gate/gate/gate_receipt 逐个 `-f` 断言实存；"
             "本机 ci/ 只有 bundle_budget+prefill_phases ⇒ 本地对等门不可跑。")

MEMSEC = """
- 04:2x **第 5 个技能 `strata-ci-cd`**：13 节点（GitHub 只静态 / 编译装机 A/B 全在 166 / 三个阻断点 pre-push·gh_gate·deploy_gate）+ 六条触发条件**正反例都测**（T1 dispatch 204→#48 / T2 白名单+paths→#49 / T3 不命中不跑 / T4 非白名单不跑 / T5 tag 不跑 / T6 PR→3 run）+ 三层门覆盖面（分支保护**只挡合并不挡直推**⇒ 门设在装机前）+ 分支方针（生产单分支·名字不带版本号·实验 ci/**·上游只读·只 rebase）。`ci/` 7 个脚本逐个 `-f` 断言实存（rollback.sh 2631 B 存在，曾被 `head -20` 截断误判）。**本机 ci/ 只有 bundle_budget+prefill_phases，本地对等门跑不了。**
"""


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "15. 补齐第 5 个技能" in t:
        return "§15 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§15 已写"


def add_ledger_note():
    t = io.open(PROG, encoding="utf-8").read()
    if "第 5 个技能（机主追问 CI/CD）" in t:
        return "P415 备注已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P415"]:
            lines[i] = l + P415_NOTE
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P415 备注已追加"
    return "P415 未找到"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 2（同日，第 5 个技能）" in t:
        return "方案补充 2 已存在"
    anchor = "校验器只查结构，查不出步骤错**——技能也必须写一条跑一条。"
    if anchor not in t:
        return "锚点未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(anchor, anchor + "\n" + PLAN_ADD, 1))
    return "方案补充 2 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "第 5 个技能 `strata-ci-cd`" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_section, add_ledger_note, add_plan, add_mem):
        print(fn.__name__, "->", fn())
