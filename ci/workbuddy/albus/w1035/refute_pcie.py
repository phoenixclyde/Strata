"""W1035 第 25 段：候选① 被实测否掉（PCIe 仅 0.1–1.2%）；④ 的实验做坏了，撤回。

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
    b = p + ".bak_w1035v"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 零停机判别：候选① 被否】**：引擎每次请求已在日志里自报"
          "`expert cache Z% hit (+W% of the routed experts over PCIe)`。同长度 ≈2K、内容全新、"
          "两批各 6 条（不重启不改配置）：**批1** wall 均值 **3.56 s**、hit 84.3%、**pcie 0.7%**；"
          "**批2** wall **3.44 s**、hit 95.6%、**pcie 0.1%**。⇒ **走 PCIe 的专家只占 0.1–1.2%**，"
          "按 3.07 MB/专家折算只有 ~10 个专家、**~30 MB ≈ 1.5 ms**，**不可能构成 665 ms 的固定项** ⇒ "
          "**候选①（权重搬运）否掉**；「借 3.49 GiB 槽位」是**复用 VRAM 槽位、不是每次拷贝**。"
          "**候选④（tile/填充地板）成为唯一未否的候选**：每个(专家,tile)只跑一次、小 T 时 tile 欠填，"
          "成本 ∝ 专家数×tile 数 而与 token 数无关——与 `P297`（每行成本平坦）一致。"
          "**④ 的实验本轮做坏了（撤回）**：想用「同长度不同路由分散度」判别，结果两条长度差 6%"
          "（2896 vs 3076 tok）、各 n=1，且 `repeat` 反而慢 16%，与④预测相反 ⇒ **该对照作废，不作证据**。"
          "**下一手**：④ 要 n>=5、长度差 <=1%、交错执行（零停机可做）。")

SEC = """
**25. 零停机把候选① 否掉了——`--pcie-frac` 那条窗口不用开了。**
原本准备为候选① 开 `--pcie-frac 0.0` 的窗口。**先读源码，省了这次停机**：`pcie_frac` 的注释写在
`core/verify.cpp:2415` 与 `program/generate.cpp:889`——它是「**decode 时 miss 的专家里走 PCIe 直读的比例**」
（native pack 默认 0.55 DMA），**不控制 prefill**。拿它做 prefill 窗口只会白停。

**改从日志里直接读**。引擎每条请求都自报：
```
done: 4 tokens in 7 s (44.3 tok/s) … expert cache 74.7% hit (+1.0% of the routed experts over PCIe)
```
于是零停机做「同长度 ≈2K、内容全新、两批各 6 条」：

| 批 | wall 均值 | hit 均值 | **pcie 均值** |
|---|---|---|---|
| 1（相对冷） | 3.56 s | 84.3% | **0.7%** |
| 2（相对温） | 3.44 s | 95.6% | **0.1%** |

**⇒ 候选① 否掉。** 走 PCIe 的专家只占 **0.1–1.2%**；按 3.07 MB/专家折算约 **10 个专家 ≈ 30 MB ≈ 1.5 ms**，
与 665 ms 差 **两个数量级**。所谓「借 1554 槽 / 3.49 GiB」是**复用 VRAM 槽位**，不是每次 prefill 拷贝。
我上一条把它列为"领先假说"并算出"有效 5.6 GB/s"——**那个算式的前提是错的**，一并撤回。

**候选③ 早已被结构否掉**（`Context::run` 每次一个 kernel，6.9 ms/launch 高三个数量级）。
所以现在**只剩候选④：tile / 填充地板**——每个 (专家, tile) 只跑一次、小 T 时 tile 欠填，
成本 ∝ **专家数 × tile 数**、与 token 数无关；这与 `P297`「每行成本平坦」自洽。

**④ 的实验我这一轮做坏了，撤回**：想用「同长度、不同路由分散度」判别，结果两条长度差了 **6%**
（2896 vs 3076 tok）、各 **n=1**，且 `repeat` 反而**慢 16%**——与④的预测相反。
长度没对齐 + 单样本，说明不了任何事。**记录为"实验做坏"，不作为证据。**

**下一手（零停机，不需要窗口）**：④ 要 **n≥5、长度差 ≤1%、交错执行**；若 ④ 成立，
`b` 应随「专家数 × tile 数」变，而与 token 数无关——同长度下改变路由分散度即可拉开专家数。
"""

PLAN_ADD = """
**补充 12（同日，候选① 否）**：`--pcie-frac` 经源码核实是**decode-miss 专用**（`verify.cpp:2415` / `generate.cpp:889`），不控 prefill ⇒ 窗口取消。改读引擎自报的 `+W% of the routed experts over PCIe`：同长度 ≈2K、两批各 6 条（零停机）⇒ **pcie 0.1–1.2%**，折 ~10 专家 ~30 MB ≈1.5 ms ⇒ **候选①（权重搬运）否**；「借 3.49 GiB」是复用 VRAM 槽位。**候选④（tile/填充地板）为唯一未否候选**，下一手 n≥5、长度差≤1%、交错。**④ 本轮实验做坏并撤回**（长度差 6%、n=1、方向相反）。
"""

MEMSEC = """
- 04:4x **候选① 被零停机否掉**：`--pcie-frac` 经源码核实只管 **decode-miss**（`verify.cpp:2415`），prefill 窗口取消。读引擎自报 `+W% routed experts over PCIe`：2K、两批各 6 条 ⇒ **pcie 0.1–1.2%**（~10 专家 ~30 MB ≈1.5 ms）⇒ 搬运假说否；「借 3.49 GiB」是复用槽位。**候选④（tile 填充地板）为唯一未否**（与 P297 每行成本平坦一致）。**④ 实验做坏撤回**：长度差 6%、n=1、repeat 反慢 16%。下一手 n≥5、长度差≤1%、交错。本轮往生产发了 ~20 条请求（不停机）。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "候选① 被否" in t:
        return "P418 已记候选① 否"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加候选① 否"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "25. 零停机把候选① 否掉了" in t:
        return "§25 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§25 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 12（同日，候选① 否）" in t:
        return "方案补充 12 已存在"
    anchor = "**补充 11（同日，窗口 A 与结构判决）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 12 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "候选① 被零停机否掉" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
