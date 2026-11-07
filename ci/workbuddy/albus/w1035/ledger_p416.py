"""W1035 第 16 段：给 decode 不稳那条开号（P416）+ 交叉引用 + 落账。

背景：§9 的四项里只有「磁盘读归因」有号（P408），decode 不稳当时被塞进 P265 第 10 列，
没有独立编号 ⇒ 不可被检索/引用，等于会丢。本脚本补号并重算数字。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035h"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


ROW = ("B10环境与版本\tP416\tdecode 不稳的归因：主因是专家缓存命中率（corr 0.49），不是线程数；"
       "`P265` 的 decode 臂有证据缺口\tW1035\tcount\t1\t1\tDONE\t"
       "**W1035 立（本条原先只作为 `P265` 第 10 列的备注存在，无独立编号 ⇒ 不可检索，现补号）**："
       "从 `docker logs` 取全部 `expert cache … hit` 行，筛 `tokens>=64` 的请求 **n=106**（两次独立统计一致）："
       "命中 **<90%** 的 **28** 个均值 **51.3 tok/s**，命中 **>=90%** 的 **78** 个均值 **65.0**，"
       "**corr(命中率, tok/s)=0.49**，全体均值 61.4、**CV 21.1%**（min 39.5 / max 82.2）；"
       "同一请求连跑 5 次 **37.7 / 58.4 / 59.0 / 67.2 / 61.4（CV 17.6%）**。"
       "⇒ **主因是「这个请求的专家在不在 VRAM」**（VRAM 装 7463 / 全包约 12288），不是线程数本身；"
       "但未命中部分正是 CPU 池去算，**线程数会放大每次未命中的代价**（方向与机主判断一致）。"
       "**门为什么没拦住**：`P265` 的 decode 臂 20w 36.23 vs 10w 36.53，**2×CV 带宽 13.4%**（看不见 <13% 的回归），"
       "且 bench 用同一条提示反复打、命中率趋近 100%，**未命中路径根本没被走到**。"
       "**两个未结（不猜）**：① `--pool-workers` 20 vs 10 的**冷请求** A/B 未做（需一次重启，等停机授权）；"
       "② shard-2 驻留率 14.6% 是否低于切 `--ple-io mmap` 之前，无法回溯（同一次重启可顺带回答）。"
       "方法可复现：`docker logs | grep 'expert cache' | sed -E …` → python 分桶（见 `albus/w1035/reply.md §9/§14`）。")


SEC = """
**16. 「编号多少」——四项里只有一项有号，已补 `P416`。**
机主拿 §9 问编号，逐项对账的结果很难看：

| §9 项 | 原编号 | 现状 |
|---|---|---|
| ③ 磁盘读归因（gguf mmap 缺页 / 页不过期 / 13.9% 常驻） | **P408** | 有号，DONE，⑦ 段带撤回记录 |
| ① decode 不稳（命中率分桶、corr 0.49） | **无号** | 当时塞在 `P265` 第 10 列当备注 |
| ② `P265` decode 臂的证据缺口（2×CV 13.4% + 全热请求） | **无号** | 同上 |
| ④ 两个未结（20 vs 10 冷请求 A/B、驻留率回溯） | **无号** | 同上 |

⇒ **补 `P416`（B10环境与版本）**，标题就是结论本身；`P265` 第 10 列加交叉引用「编号见 P416」。
**为什么必须开号而不是继续挂在 P265 下**：`P265` 的对象是「`--pool-workers 10` 这个参数决定」，
而这条的对象是「decode 波动的主因是什么」——**两件事，检索路径完全不同**。挂在参数行下，等于按"线程数"才能找到"命中率"。

**开号前重算了一遍，不引用旧快照**：`docker logs` 全量重解析，`tokens>=64` 的请求 **n=106**、命中 <90% 的 28 个均值 **51.3 tok/s**、>=90% 的 78 个均值 **65.0**、**corr 0.49**、CV **21.1%**（min 39.5 / max 82.2）——与先前逐项一致（本轮我发的两个 8-token 测试请求被 `>=64` 过滤掉，所以 n 未变）。

**这条和我这几轮反复犯的错是同一个**：`P408` 当初也是「有观测、没编号」，补号后才被当账认。判据很简单——**一条结论如果不能用一句 `P####` 指代，它下轮就会消失**。
"""

PLAN_ADD = """
**补充 3（同日，补号）**：`P416` —— decode 不稳的归因（命中率分桶 n=106：<90% 桶 28 个 @51.3 tok/s、≥90% 桶 78 个 @65.0、corr 0.49、CV 21.1%；主因是专家是否在 VRAM，线程数只是放大器）+ `P265` decode 臂证据缺口（2×CV 13.4%、bench 全热请求 ⇒ 未命中路径未走到）+ 两个未结（20 vs 10 冷请求 A/B 需重启；驻留率回溯）。**此前只作为 `P265` 第 10 列备注存在，无独立编号。**
"""


def add_ledger():
    t = io.open(PROG, encoding="utf-8").read()
    if "\tP416\t" in t:
        return "P416 已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    idx = None
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P416"]:
            return "P416 已存在"
        if l.split("\t")[1:2] == ["P408"]:
            idx = i
    if idx is None:
        return "P408 未找到，无法定位插入点"
    lines.insert(idx + 1, ROW)
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return "P416 已插到 P408 之后"


def cross_ref():
    t = io.open(PROG, encoding="utf-8").read()
    if "编号见 P416" in t:
        return "交叉引用已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P265"] and len(f) > 9:
            f[9] = f[9].rstrip() + " **编号见 P416**（本条只记参数决定，decode 归因单独成条）。"
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P265 第 10 列已加交叉引用"
    return "P265 第 10 列未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "16. 「编号多少」" in t:
        return "§16 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§16 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 3（同日，补号）" in t:
        return "方案补充 3 已存在"
    anchor = "**本地对等门跑不了**。"
    if anchor not in t:
        return "锚点未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(anchor, anchor + "\n" + PLAN_ADD, 1))
    return "方案补充 3 已加"


MEMSEC = """
- 04:3x **§9 四项只有一项有号 → 补 `P416`**：`P408` 管磁盘读；decode 不稳（n=106，命中<90% 桶 28 个 @51.3 tok/s vs ≥90% 桶 78 个 @65.0，corr 0.49，CV 21.1%）与 `P265` decode 臂缺口（2×CV 13.4%、bench 全热请求）此前只挂在 `P265` 第 10 列，**无独立编号 ⇒ 不可检索**。已开 `P416` 并在 P265 加交叉引用。**判据：结论若不能用一句 `P####` 指代，下轮就会消失。**
"""


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "补 `P416`" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_ledger, cross_ref, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
