"""W1035 第 33 段：口径校准 —— ncols 是「单专家最大行数」，M 饥饿假说撤回。

同时保留：填充 8–12% 仍成立（④ 仍出局）；top-k 未知（不能再反推）。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035ad"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 口径校准：ncols = 单专家最大行数】**：源码 `prefill.cpp:5319` 是 `gu.max_rows = maxr`，"
          "而 `Context::run` 把 `p.max_rows` 直接喂给 `pick_J`（`moe_mmq.cu:504`）⇒ "
          "**日志里的 `ncols` 是「组内单专家最大行数」，不是组内总行数**（`MMQ_GROUP=16` 专家/launch、"
          "`kGatherGroupMax=16`）。"
          "**推论全部改写**：① 中位 **296 行/专家**是**健康**的 ⇒ **我上一轮「每专家 ~18 行、M 饥饿」的推断错，撤回**；"
          "② 由 `ncols` 反推的 **top-k=4 也作废**（那是把单专家行数当总行数算的），top-k 未知；"
          "③ **填充 8–12% 仍成立**（按 `ncols` 单专家行数与 J 折算恰好是同口径），**④ 仍出局**。"
          "⇒ **754 ms 相对 roofline 的 8–76× 缺口，现在没有任何候选能解释**；"
          "**下一手必须先拿到 top-k 与每 token 实际路由数**（从 pack 元数据或 `--router` 侧读，不再反推）。")

SEC = """
**33. 口径校准：`ncols` 是「单专家最大行数」，我上一轮的 M 饥饿推断撤回。**
上一轮我用 `ncols` 中位 296 反推「每专家 ~18 行」，得出"tile 打不满、利用率 28%"。**源码把这个推断推翻了**：

```
prefill.cpp:5319     gu.max_rows = maxr;          // 组内单专家的最大行数
moe_mmq.cu:504       const int J_best = pick_J((int) t, p.max_rows, mmq_fb);
```

`p.max_rows` 直接喂给 `pick_J`，而日志里的 `ncols` 打印的正是它 ⇒ **`ncols` = 单专家最大行数**，
不是"组内总行数"。（分组常数：`MMQ_GROUP = 16` 专家/launch、`kGatherGroupMax = 16`。）

**三处改写**
1. **中位 296 行/专家是健康的** ⇒ **「每专家 ~18 行 + M 饥饿」这条推断错，撤回**。
2. **由 `ncols` 反推的 `top-k = 4` 同时作废**——那是把"单专家行数"当成"组内总行数"再除 48 层算出来的。**top-k 现在未知**。
3. **填充 8–12% 的结论仍然成立**：用"单专家行数 vs J"折算本来就是同口径，所以 **④ 仍出局**。

**于是状态回到诚实的空位**：`gemm gate/up` 2.5K 时 **754 ms**，相对计算下限 ~10 ms、带宽下限 ~90 ms 差 **8–76×**，
而**目前没有任何候选能解释这个缺口**（①③④⑤ 全出局，② 未测且先验低）。

**下一手（先拿数、不猜）**：从 **pack 元数据 / router 侧**取「top-k」与「每 token 实际路由数」，
再据此重算 roofline 的分子。**在拿到 top-k 之前，我不再提"利用率多少"这类数**。

**这一轮的教训（第五次同类）**：**每次我把日志字段当成"我以为的语义"，就会错一次**。
`ncols`、`PLE`、`launch 96` 全是这个病。**规则：用任何日志字段前，先回到源码确认它打印的是哪个变量。**
"""

PLAN_ADD = """
**补充 20（同日，口径校准）**：源码核实 `gu.max_rows = maxr` 且 `pick_J(p.max_rows)` ⇒ **`ncols` = 单专家最大行数**（`MMQ_GROUP=16` 专家/launch）⇒ **「每专家 ~18 行 / M 饥饿」撤回**、**top-k=4 的反推作废（top-k 未知）**；**填充 8–12% 与 ④ 出局仍成立**。`gemm gate/up` 754 ms 相对 roofline 8–76× 缺口**现无候选解释**。下一手：从 pack 元数据/router 取 top-k 与每 token 路由数，再重算 roofline。**规则：用任何日志字段前先回源码确认它打印的是哪个变量**（ncols / PLE / launch 96 已连错三次）。
"""

MEMSEC = """
- 06:1x **口径校准：ncols = 单专家最大行数**（`gu.max_rows=maxr` → `pick_J(p.max_rows)`，MMQ_GROUP=16）⇒ **「每专家 18 行 / M 饥饿」撤回**、**top-k=4 反推作废**；**填充 8–12% 与 ④ 出局仍成立**。gate/up 754 ms 对 roofline 8–76× 缺口**无候选解释**。下一手：从 pack/router 取 top-k 再算。**规则：用日志字段前先回源码确认语义（ncols/PLE/launch96 已连错三次）。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "口径校准：ncols = 单专家最大行数" in t:
        return "P418 已记校准"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加口径校准"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "33. 口径校准" in t:
        return "§33 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§33 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 20（同日，口径校准）" in t:
        return "方案补充 20 已存在"
    anchor = "**补充 19（同日，roofline + 填充出局）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 20 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "口径校准：ncols = 单专家最大行数" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
