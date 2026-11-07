"""W1035 第 19 段：把「按词能不能搜到」做成硬门 claim_homes.py。

一次落盘、单次执行。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035l"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


SEC = """
**19. 「先跑」= 把按词检索做成硬门（`tools/claim_homes.py`），不是再手工查一遍。**
前面两次都是人工核查（`P408` 补号、`P265` → `P416`），**人工核查会腐坏**——下一轮没人再查一次，同样的坑原样出现。所以这次做成机器门：

**设计（不新增文件，只给账本加第 11 列）**：每条账本行写 `KW:词1|词2|…`，由作者声明「下一轮该按哪些词搜到这条」；门只查一件事——**声明的每个词必须真的出现在这一行自己的文本里**（标题 + 备注 + 第 10 列）。词不在行里 ⇒ 说明这行没按那个说法写下来 ⇒ 下一个人按那个词搜不到 ⇒ 当场红。

**四条防作弊判据**
| # | 判据 | 防的是什么 |
|---|---|---|
| A | 本轮每行必须有 `KW:` 且 ≥2 个词 | 随手糊一个词交差 |
| B | 词长 ≥3；全账本命中 >25 行的词直接拒 | 拿 `166` / `配置` 这类"满账本都是"的词当检索键 |
| C | 声明词必须在本行文本内 | 声明与内容脱节（`P265` 那种：数字在、按词搜不到） |
| D | 本轮在账本里没有任何行 ⇒ FAIL | "没写就没事"的空转 |

**负向自测（4/4 PASS）**：无 KW 列 / 词不在行内 / 词太泛 / 正常 → 分别红、红、红、绿。

**活体负向（用真账本）**：把 `P408` 的 `KW:mmap 缺页|shard-2|页不会过期` 改成含 `不存在的词xyz`，
门立刻报 `P408: 声明了 '不存在的词xyz'，但本行文本里没有这个词`。

**过程中抓到我自己一个实现 bug（第 N 次"写完必须测"）**：`body` 一开始写成 `f[8:]`，
**把第 11 列 `KW` 自己也算进了"行内文本"**——于是每个声明词必然"在行里"，门等于永远 PASS。
负向用例「词不在行内」当场把它照出来（`want_fail=True got=False`），改成 `f[8:10]` 才真。
**如果没写负向用例，这个门会以"全绿"的姿态骗过所有人。**

**已落地**：`tools/claim_homes.py` 接进 `round_close.py` 的 **HARD**（第 12 道）；本轮 9 条账本行全部补上 `KW:`：

| 号 | KW |
|---|---|
| `P407` | 静态重估 / tile / q8_bytes |
| `P408` | mmap 缺页 / shard-2 / 页不会过期 |
| `P410` | fail-open / ensure_ascii / 四件套 |
| `P411` | dispatch / round_gate / Actions 未禁用 |
| `P412` | 分支保护 / Stop 钩子 |
| `P413` | deploy_gate / PR-only / 判据输出 |
| `P414` | 3.5/8 / 九个阀门 / gh_gate |
| `P415` | 独立技能 / quick_validate / 热加载 |
| `P416` | decode 不稳 / corr 0.49 / 命中率 |

**注意它管不到什么**（别过度声明）：它只保证「声明与内容一致」，**不保证你声明了该声明的词**——
换句话说，它可以防"写的和搜的对不上"，防不住"你压根没想到该按什么词找"。后者只能靠人（或下一轮真去搜一次）。
"""

PLAN_ADD = """
**补充 6（同日，「先跑」）**：`tools/claim_homes.py` 接进 `round_close` HARD（第 12 道）。账本加第 11 列 `KW:词1|词2`，门查「声明的每个词必须出现在本行文本里」+ 四条防作弊（≥2 词 / 词长≥3 / 全账本命中>25 行拒 / 本轮无行即 FAIL）。负向自测 4/4；活体负向：给 `P408` 塞 `不存在的词xyz` 立刻红。**实现 bug 一次**：`body` 取 `f[8:]` 把 KW 列自身算进行内文本 ⇒ 门永远 PASS，被负向用例照出，改 `f[8:10]`。**边界：能防"声明与内容脱节"，防不住"没想到该按什么词找"。**
"""

MEMSEC = """
- 05:0x **「先跑」→ `tools/claim_homes.py` 进 HARD（第 12 道）**：账本加第 11 列 `KW:词1|词2`，门查「每个声明词必须出现在本行文本」，四条防作弊（≥2 词/词长≥3/全账本命中>25 行拒/本轮无行即 FAIL）。自测 4/4；活体负向（P408 塞 `不存在的词xyz`）立红。**抓到自己一个 bug**：`body=f[8:]` 把 KW 列自身算进行内文本 ⇒ 永远 PASS，改 `f[8:10]`。**边界：防不住"没想到该按什么词找"。**
"""


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "19. 「先跑」= 把按词检索做成硬门" in t:
        return "§19 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§19 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 6（同日，「先跑」）" in t:
        return "方案补充 6 已存在"
    anchor = "**纪律：结论要能被三条独立路径找到——按号 / 按词 / 按方案节。**"
    if anchor not in t:
        return "锚点未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(anchor, anchor + "\n" + PLAN_ADD, 1))
    return "方案补充 6 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "claim_homes" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
