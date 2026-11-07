"""W1035 第 28 段：三处更正（含撤回我对候选③ 的判决）+ 找到真正的零停机数据源。

1) 相位行与 pick_J 都写在宿主机 /data/*.log，不在 docker logs ⇒ 窗口 A 数据一直在；
2) PLE 2382 ms 是累计值，单次 ~35 ms（0.9%），差点报成 58%；
3) launch 数实测 ~1491 @2K（不是 96）⇒ 「6.9 ms/launch ⇒ ③ 否」的判决撤回，③ 重新开放。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035y"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 三处更正（含撤回一条判决）】**：① **数据源找错了**——相位行 `strata prefill timing: …` "
          "与 `pick_J: …` **都写在宿主机 `/data/strata-huihui-ud-iq4_xs.log`（15 MB，pick_J 共 12,268 行）**，"
          "不在 `docker logs`；所以我先前「引擎 stderr 不进日志」只对 docker logs 成立，**窗口 A 的数据一直存在**。"
          "② **`PLE 2382 ms` 是累计值**（逐次 +30~45 ms），单次约 **35 ms ≈ 0.9%**，不是 58%——差点把累计当单次报出去。"
          "③ **launch 数实测 ≈1491 @2K**（按 `pick_J` 分段计数），不是我用组数估的 96 ⇒ "
          "**「665 ms ÷ 96 = 6.9 ms/launch ⇒ 候选③ 否」这条判决建立在错的 launch 数上，撤回**；"
          "按实测：2K wall 3682 ms ÷ 1491 = **2.47 ms/launch**，`~0K` 档 756 launches、`~4K` 档 1786。"
          "**J 分布**：J=64 占 **73%**（8981/12268），type 12（Q4_K）5961、type 7 5499、type 8 667；"
          "ncols 1–13824 ⇒ 与 gfx906 配置表「Q4_K/Q5_1 最大 J=64」一致。"
          "**下一手不再要窗口**：`pick_J` + 相位行都在文件里，可按请求对齐做零停机分析。")

SEC = """
**28. 三处更正，其中一条是撤回我自己的判决——`R95` 的候选③ 重新开放。**
这轮我没做新实验，只做了一件更值钱的事：**核对数据源**。结果是三处错。

**① 数据源找错了。** 相位行和 `pick_J` **都不在 `docker logs`**，而在宿主机
`/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log`（15 MB，`pick_J` 共 **12,268 行**）。
我上一轮说"引擎 stderr 不进日志"——那句话只对 `docker logs` 成立。
⇒ **窗口 A 的数据一直存在**，我白停了一次机，本该先 `ls` 一眼那个目录。

**② `PLE 2382 ms` 是累计值。** 那条 `host: … PLE 2382 ms` 逐次递增（+30/+37/+43/+34/+34），
**单次约 35 ms ≈ wall 的 0.9%**。我第一眼按"2382/4104 = 58%"解读，**差点又报一个错数**。
判据很简单：**累计计数器的值是单调不减的**，看到单调就先怀疑累计。

**③ 我关于候选③ 的判决要撤回。** 当时算的是「665 ms ÷ 96 次 launch = 6.9 ms/launch ⇒ 高三个数量级 ⇒ 否」。
96 是我按"层 × 组"估的。**实测按 `pick_J` 分段计数**：

| 长度档 | wall | launches | ms/launch |
|---|---|---|---|
| ~0K（n=4） | 1108 ms | 756.5 | 1.46 |
| ~2K（n=5） | 3682 ms | **1491.2** | **2.47** |
| ~4K（n=1） | 6013 ms | 1786.0 | 3.37 |

**1491 次，不是 96 次。** 于是"6.9 ms/launch 荒谬"这个推论不成立——**候选③（调度/建表）重新开放**，
而且 launches 随长度上升（756 → 1491 → 1786），说明它**不是纯固定项**，与"固定项"的关系需要重算。

**J 分布（顺带拿到）**：`J=64` 占 **73%**（8981/12268）；type 12（Q4_K）5961、type 7 5499、type 8 667；
`ncols` 1–13824。与 gfx906 配置表「Q4_K/Q5_1 最大 J=64」一致——这条是**生产运行期**的独立佐证，
正好补上 `P407` 只有静态表的缺口。

**下一步（不需要窗口）**：`pick_J` 与相位行同在一个文件里，可按请求对齐，
**零停机**做「J / launches / 各相位 ms」的逐请求相关。这比我原本要申请的"相位探针窗口"便宜得多。

**这一轮的教训**：连续三轮我都在"数据在哪 / 计数器是累计还是单次 / 我估的数对不对"上栽跟头，
而不是在物理上。**动手前先 `ls` 数据源、先看计数器的单调性、先用实测替换估算**——三条都要进门。
"""

PLAN_ADD = """
**补充 15（同日，三处更正 + ③ 重开）**：① 相位行与 `pick_J` 在宿主机 `/data/strata-huihui-ud-iq4_xs.log`（15 MB / pick_J 12,268 行），**不在 docker logs** ⇒ 窗口 A 数据一直在；② `PLE 2382 ms` 为**累计值**，单次 ~35 ms（0.9%），勿当 58%；③ **launch 实测 ~1491 @2K**（非估算的 96）⇒ **「6.9 ms/launch ⇒ ③ 否」撤回，候选③ 重开**；实测 2K `wall 3682 / 1491 = 2.47 ms/launch`，且 launches 随长度 756→1491→1786。**J=64 占 73%**（type 12/7 为主），与配置表一致（运行期佐证 `P407`）。下一手零停机：`pick_J` + 相位行按请求对齐。**纪律候选：动手前先 ls 数据源 / 先判计数器是否累计 / 先用实测替换估算。**
"""

MEMSEC = """
- 05:1x **三处更正（含撤回判决）**：① 相位行与 `pick_J` 在宿主机 `/data/strata-huihui-ud-iq4_xs.log`（15 MB，pick_J 12,268 行），**不在 docker logs** ⇒ 窗口 A 白停、数据一直在；② `PLE 2382 ms` 是**累计**（单次 ~35 ms = 0.9%），差点报成 58%；③ **launch 实测 ~1491 @2K**（我估 96）⇒ **「6.9 ms/launch ⇒ ③ 否」撤回，候选③ 重开**；2K `3682/1491 = 2.47 ms/launch`，launches 随长度 756→1491→1786。**J=64 占 73%**（type12/7），运行期佐证 P407。下一手零停机：pick_J + 相位行按请求对齐。**纪律：先 ls 数据源 / 先判累计 / 先实测替换估算。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "三处更正（含撤回一条判决）" in t:
        return "P418 已记更正"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加更正"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "28. 三处更正" in t:
        return "§28 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§28 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 15（同日，三处更正 + ③ 重开）" in t:
        return "方案补充 15 已存在"
    anchor = "**补充 14（同日，复现失败与撤回）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 15 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "三处更正（含撤回判决）" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
