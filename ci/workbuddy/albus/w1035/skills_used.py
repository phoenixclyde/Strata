"""W1035 第 14 段：技能「用过没有」——真跑一遍，抓到三处文档缺陷。

一次落盘、单次执行。所有长件先备份。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035f"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


SEC = """
**14. 「创建了以后用过吗」——没有，现在是补上的第一遍；一跑就抓到三处我自己写的错。**
上一条我说「4 个技能已落地」，但**只加载过一个**，没执行过里面任何一条命令。机主一问，就有了这一轮：按每个技能**自己写的步骤**跑，跑不通就改技能。

| 技能 | 怎么"用"的 | 结果 |
|---|---|---|
| `workbuddy-round-gate-hooks` | 执行它 §4 的六分支负向（`skill_test_hook.py`） | **第一遍 3/4 FAIL**：它的负向步骤是错的；改完 **6/6 PASS** |
| `strata-deploy-evidence-gate` | 按 §0 审计在产版本 | 技能漏了 `--live` ⇒ **误报 D1/D2 REFUSE**；补上后 `D1 PASS 5e63174d…` / `D2 PASS 40 个制品`，1.9 s 出结论 |
| `engine-io-attribution` | 在 166 上把 S1–S6 逐条执行（`skill_test_io.py`） | **全通**，且 S6 公式被实测打假（见下） |
| `strata-quant-quality-gate` | **不能跑**（要停生产 10–14 min） | 已加「验证状态」表，明写「三臂整跑 = 未执行，是设计稿不是实录」 |

**三处缺陷（都是"设计时看起来对"的典型）**
① **钩子技能的负向步骤根本不可能通过**：它教「标记任意文件、再把它移走」。实际标记只决定**要不要跑门**，门验的永远是 `albus/<轮次>/reply.md`（轮次取自 `HANDOFF` 的 `SNAPSHOT`）。改法是**破坏那个文件本身**（缩成 50 字 / 移走），并把这条写成「实跑发现的坑」。
② **装机门的审计命令漏 `--live`**：本机没有 `/home/albus/strata166/data/bin`，不给 `--live` 时 D1/D2 因"查不到"而 REFUSE——**看起来像"这版不合格"，其实是没去问 166**。两次对照已写进技能。
③ **IO 技能的 S6 会把启动装载算成"持续读盘"**：`累计 read_bytes ÷ uptime` = 90.1 GB / 14537 s = **6.20 MB/s**，而按请求算是 **1.33 MB/s**。差的那 78 GB 是容器启动时的模型装载。**这是"持续读盘"报告最常见的假数**，技能里已写两条正确算法。

**这一遍的实测读数（`engine-io-attribution` 逐条复现，全在本机生产上取）**

| 步 | 读数 |
|---|---|
| S1 空闲 10 s | 仅 `sda` 84 KB/s（机械盘噪声），`nvme` 0 ⇒ 请求驱动 |
| S2 冷请求 917 tok | `read_bytes` **14.91 MB** / `rchar` **0.02 MB** ⇒ mmap 缺页；墙钟 **2.11 s** |
| S3 smaps Rss 差 | **+14.2 MiB**，全部落在 `…-00002-of-00004.gguf`，其余映射 +0.0 |
| S4 驻留率 | 6946.6 MiB / 46.44 GiB = **14.6%** |
| S5 同提示 30 s 后再打 | `read_bytes` **0.00 MB**、墙钟 **0.25 s** ⇒ **页不过期** |
| S6 对账 | 330 请求 · 累计 90.1 GB / 14537 s = 6.20 MB/s（**含启动装载，不能当持续读盘**） |

⇒ 与上一轮用另一套脚本得到的结论**逐项一致**（14.9 vs 16.25 MB、14.6% vs 13.9%、0.00 MB 热请求），说明技能里的步骤不是循环论证，是可独立复现的第二条路径。

**这轮真正的教训不是"技能有 bug"，而是**：技能的校验器只查**结构**（frontmatter、字数、目录），查不出**步骤错了**——和 `report_lint` 查不出结论错是同一个病。所以技能也必须「写一条、跑一条」，跑不通就改，改完在技能里留下「第一版错在哪」。已把这句写进两个技能的开头。
"""

PLAN_ADD = """
**补充（同日实跑）**：4 个技能都按自己写的步骤跑过一遍，抓到三处文档缺陷并已修：
① 钩子技能的负向步骤错（标记 ≠ 门验的对象，门验 `albus/<轮次>/reply.md`；首测 3/4 → 修后 6/6）；
② 装机门审计命令漏 `--live`，会误报 D1/D2 REFUSE（补后 1.9 s 出 `D1 PASS / D2 PASS`，只剩 D3/D4 缺证据）；
③ IO 技能 S6 把启动装载算进"持续读盘"（6.20 vs 1.33 MB/s），已写两条正确算法。
`strata-quant-quality-gate` 的停机段**仍未执行**，技能内已加「验证状态」表明写。**校验器只查结构，查不出步骤错**——技能也必须写一条跑一条。
"""

P415_NOTE = ("  **同日实跑（机主问「用过吗」）**：4 个技能按各自步骤跑过——钩子技能首测 3/4 FAIL（负向步骤错："
             "标记只决定要不要跑门，门验 `albus/<轮次>/reply.md`），修后 6/6 PASS；装机门审计漏 `--live` 会误报 "
             "D1/D2 REFUSE，补后 `D1 PASS 5e63174d… / D2 PASS 40 制品` 1.9 s；IO 技能 S1–S6 全通并复现 "
             "14.91 MB / rchar 0.02 MB / Rss +14.2 MiB 全落 shard-2 / 驻留 14.6% / 热请求 0.00 MB 0.25 s，"
             "且实测 S6 公式含启动装载（6.20 vs 1.33 MB/s）；数值门仍未整跑，已加验证状态表。"
             "**校验器只查结构，查不出步骤错。**")

MEMSEC = """
- 04:1x **技能「用过吗」= 没用过，补跑一遍抓到 3 处文档缺陷**：① 钩子技能负向步骤错（标记≠门验对象，门验 `albus/<轮次>/reply.md`，由 HANDOFF SNAPSHOT 决定）→ 改后 6/6；② 装机门审计漏 `--live` ⇒ 误报 D1/D2 REFUSE；③ IO 技能 S6 `累计read_bytes/uptime` 含启动装载（6.20 vs 1.33 MB/s）。IO 五步法在 166 全通：冷请求 14.91 MB / rchar 0.02 MB / Rss +14.2 MiB 全落 shard-2 / 驻留 14.6% / 同提示 30 s 后 0.00 MB 0.25 s。**技能校验器只查结构，查不出步骤错，必须写一条跑一条。** 数值门仍未整跑（需停机）。
"""


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "14. 「创建了以后用过吗」" in t:
        return "§14 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§14 已写"


def add_ledger_note():
    t = io.open(PROG, encoding="utf-8").read()
    if "同日实跑（机主问「用过吗」）" in t:
        return "P415 备注已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    hit = 0
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P415"]:
            lines[i] = l + P415_NOTE
            hit = 1
            break
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return "P415 备注已加" if hit else "P415 未找到"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充（同日实跑）" in t:
        return "方案补充已存在"
    anchor = "**边界**：技能不阻断操作，门的形态仍是 `round_close` / `deploy_gate` / `Stop` 钩子。"
    if anchor not in t:
        return "锚点未找到，跳过"
    backup(PLAN)
    t = t.replace(anchor, anchor + "\n" + PLAN_ADD, 1)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t)
    return "方案 §八 已加实跑补充"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "技能「用过吗」" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_section, add_ledger_note, add_plan, add_mem):
        print(fn.__name__, "->", fn())
