"""W1035 第 21 段：补 P417（claim_homes 门本身没记账）+ 分母同步 + 清单。

反讽记录：这条门正是为「按词搜不到」而建，结果它自己按 `claim_homes` 搜账本 = 0 命中。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"
SNAP = "albus/w1034/HANDOFF.md"


def backup(p):
    b = p + ".bak_w1035p"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


ROW = ("B8工程\tP417\t账本加第 11 列 `KW:` + 新门 `claim_homes.py`：一条结论必须能被「按词」搜到\tW1035\t"
       "count\t1\t1\tDONE\t"
       "**W1035 立**：「结论要能被三条独立路径找到——按号 / 按词 / 按方案节」的前两条机械化。"
       "账本 schema 从 10 列扩到 11 列：第 11 列 `KW:词1|词2`，由作者声明「下一轮该按哪些词搜到这条」；"
       "新门 `tools/claim_homes.py` 只查一件事——**声明的每个词必须真的出现在这一行自己的文本里**"
       "（标题 + 备注 + 第 10 列，**不含 KW 列自身**）。四条防作弊：① 本轮每行必须有 KW 且 >=2 词；"
       "② 词长 >=3；③ 全账本命中 >25 行的词直接拒（`166`/`配置` 这类不是检索键）；④ 本轮账本无行即 FAIL。"
       "**负向**：自测 4/4（无 KW / 词不在行内 / 词太泛 / 正常）；活体负向——给 `P408` 塞 `不存在的词xyz` 立刻红。"
       "**抓到自己一个实现 bug**：`body = f[8:]` 把 KW 列自身也算进「行内文本」⇒ 门永远 PASS，"
       "被负向用例照出（want_fail=True got=False），改 `f[8:10]` 才真——**没写负向用例的话，这道门会以全绿姿态骗过所有人**。"
       "已接进 `round_close.py` HARD（第 12 道）；`progress.py` 同步接受 10/11 列、`COLS` 加 `kw`；"
       "账本头部加列说明注释。**边界**：它只保证「声明与内容一致」，防不住「压根没想到该按什么词找」——"
       "而这条边界当天就被自己踩到一次（`claim_homes` 本身在账本 0 命中，才补的 P417）。\t"
       "KW:claim_homes|检索键|KW:")


SEC = """
**21. 清单与一次现世报：`claim_homes` 门自己没记账，补 `P417`。**
机主要清单，机器扫了一遍「本轮新增的号」。扫的同时按词反查，抓到反讽的一条：

```
grep claim_homes  deploy/PROGRESS.tsv  ->  0 命中
grep 检索键        deploy/PROGRESS.tsv  ->  0 命中
```

**我为「按词搜不到」建的那道门，它自己按词搜不到。** 这是同一个毛病的第三次（`P408` 漏号 → `P265` 寄居 → 现在这个），
而且这次踩中的正是我在 §19 里写下的那条边界：*"它防不住「压根没想到该按什么词找」"*。今天证明那句话不是免责声明，是预言。

已补 **`P417`（B8工程）**：账本扩到 11 列 schema + `claim_homes.py` 的判据、四条防作弊、负向结果、那个 `f[8:]` 的实现 bug、
以及接入 HARD 的位置，全部写进备注；KW 声明为 `claim_homes|检索键|KW:`，三词都能在行内找到（门自证通过）。

**本轮新增编号清单（10 个，全部 DONE）**

| 号 | 块 | 一句话 |
|---|---|---|
| `P407` | B8工程 | `P392` 静态重估：`#29953` 只改缓冲区大小，tile 选择逐行等价；MoE 预填自带 128 块余量 |
| `P408` | B10环境与版本 | 磁盘读 = gguf shard-2 的 mmap 缺页；页不过期；13.9% 常驻 |
| `P410` | B8工程 | 自审：两次漏交四件套；根因是所有门都是「拉」式 |
| `P411` | B8工程 | CI/CD 实测：Actions 未禁用（dispatch 204 / #48 success）；本机缺 `ci/round_gate.py` |
| `P412` | B8工程 | 分支保护已设 + `Stop` 钩子 v3 跑真门 |
| `P413` | B8工程 | 「能否落生产」改为判据输出（`deploy_gate` D1–D6）；主线不改 PR-only |
| `P414` | B8工程 | 九个阀门逐条实测；`deploy_gate` 接进 `deploy.sh 3.5/8` |
| `P415` | B8工程 | 4 个独立技能落地（钩子 / 装机门 / IO 归因 / 数值门），含不建三个的理由 |
| `P416` | B10环境与版本 | decode 不稳归因：命中率 `corr 0.49`；冷请求 A/B 20 vs 10 **Δ −0.1%（带 23.9%）** |
| `P417` | B8工程 | 账本第 11 列 `KW:` + `claim_homes` 门（本轮） |

**只改备注、未新开号**：`P265`（加「编号见 P416」）、`P392`（挂 C 门备跑状态）。
"""

PLAN_ADD = """
**补充 8（同日，清单与现世报）**：`claim_homes` 与 `检索键` 在账本 **0 命中** ⇒ 补 **`P417`**（账本 11 列 schema + 门判据 + 四条防作弊 + `body=f[8:]` 实现 bug + 接 HARD 位置）。**这道门正是为「按词搜不到」而建，它自己按词搜不到**——§19 写的边界（"防不住没想到该按什么词找"）当天被自己踩中，证明那不是免责声明。
"""

MEMSEC = """
- 04:2x **现世报：`claim_homes` 门自己 0 命中**（`grep claim_homes` 账本 = 0）⇒ 补 **`P417`**。同一毛病第三次（P408 漏号 → P265 寄居 → 这次）。本轮新增 10 号：P407/P408/P410/P411/P412/P413/P414/P415/P416/P417，全 DONE；另改备注 P265（见 P416）、P392（C 备跑状态）。
"""


def add_row():
    t = io.open(PROG, encoding="utf-8").read()
    if "\tP417\t" in t:
        return "P417 已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    idx = None
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P416"]:
            idx = i
    if idx is None:
        return "P416 未找到"
    lines.insert(idx + 1, ROW)
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return "P417 已插到 P416 之后"


def fix_denominator():
    import subprocess, sys
    r = subprocess.run([sys.executable, "tools/progress.py"], capture_output=True, text=True)
    head = r.stdout.splitlines()[0]
    import re
    m = re.search(r"条 (\d+) ／ 已结 (\d+)（([\d.]+)%）", head)
    if not m:
        return "progress 输出无法解析: " + head
    n, d, pct = m.group(1), m.group(2), m.group(3)
    t = io.open(PLAN, encoding="utf-8").read()
    new = "**%s 条 / 已结 %s / %s%%**（W1035 校正；" % (n, d, pct)
    cur = re.search(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1035 校正；", t)
    if not cur:
        return "§0.1 分母行未匹配"
    if cur.group(0) == new:
        return "分母已是 %s/%s" % (n, d)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(cur.group(0), new, 1))
    return "分母 -> %s/%s" % (n, d)


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "21. 清单与一次现世报" in t:
        return "§21 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§21 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 8（同日，清单与现世报）" in t:
        return "方案补充 8 已存在"
    anchor = "**② 驻留率回溯做不了**（restart 不清页缓存；要 drop_caches，风险高，未做）。"
    if anchor not in t:
        return "锚点未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(anchor, anchor + "\n" + PLAN_ADD, 1))
    return "方案补充 8 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "claim_homes` 门自己 0 命中" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_row, fix_denominator, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
