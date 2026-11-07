"""W1035 第 20 段：P416 未结① 结案 —— --pool-workers 20 vs 10 的冷请求 decode A/B。

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
    b = p + ".bak_w1035o"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


RESULT = (" **【W1035 冷请求 A/B 结案（P416 未结①）】**：两臂各**冷启一次**（`docker restart`，"
          "health 40.0 s / 45.0 s），同一批 6 条随机提示（seed 固定、两臂内容相同），取引擎自己的 "
          "`expert cache … hit` 行：**w10 77.1 tok/s（CV 12.0%，min 58.9 / max 84.2，hit 均值 90.8%）**、"
          "**w20 77.1 tok/s（CV 11.4%，min 59.9 / max 84.3，hit 90.9%）** ⇒ **Δ = −0.1%，2×CV 带 = 23.9%**，"
          "**带内不可分辨**。更关键的是**臂内**：两臂的**第 0 条都只有 59–60 tok/s（hit 66.4%）**，"
          "随后 71.5→82→84 爬到 hit 98% ⇒ **决定 decode 的是「专家在不在 VRAM / 刚启是否预热」，不是线程数**；"
          "20 workers 对冷请求也无增益。**边界（不夸大）**：n=6/臂、顺序执行非交错、单次冷启，"
          "CV 12% 使该测试只能分辨 >24% 的差异；要抓 5% 级别的差异必须交错重复多轮。"
          "config 已按字节还原（`53ac61e0c663a6a46b7a5aa2e610bf43`），停机约 **3 min**。")


SEC = """
**20. `P416` 未结①结案：`--pool-workers` 20 vs 10 在**冷请求**上也拉不开（Δ −0.1%，带 23.9%）。**
机主催「先跑这几个任务」，指的是 `P416` 里挂着的两个未结。① 现在做完了：

**设计**（为什么要三个周期而不是一次）
两臂都必须从**同样的冷状态**出发——10 臂若用跑了 10 小时的热缓存、20 臂用冷缓存，比的就不是参数而是冷热。
所以：`w10 冷启 → 6 条随机提示` → `w20 冷启 → 同一批 6 条提示` → **还原 config 再重启**。

| 臂 | decode 均值 | CV | min / max | hit 均值 | 首条 |
|---|---|---|---|---|---|
| `w10`（20→10 的现役） | **77.1 tok/s** | 12.0% | 58.9 / 84.2 | 90.8% | 58.9（hit 66%） |
| `w20`（默认值） | **77.1 tok/s** | 11.4% | 59.9 / 84.3 | 90.9% | 59.9（hit 66.4%） |

**Δ = −0.1%，2×CV 带 = 23.9% ⇒ 带内，不可分辨。**

**真正的信息在臂内**：两臂的**第 0 条都只有 59–60 tok/s（hit 66%）**，随后 71.5 → 80.5 → 82 → 84.3 爬到 hit 98%。
⇒ **decode 慢的机制是「专家不在 VRAM + 刚启动没预热」，不是「线程少」**；加回 20 workers 对冷请求也没有任何帮助。
这条与 `P416` 主结论（命中率 corr 0.49）方向一致，且是**在冷请求上**补的，补掉了 `P265` 那个「bench 全是热请求」的缺口。

**必须写清的边界（不夸大）**
- n=6/臂、顺序执行**非交错**、单次冷启；CV 12% ⇒ 这个测试**只能分辨 >24% 的差异**，抓不住 5% 级别。
- 只有第 0 条是真"冷"，之后同臂内的 hit 单调上升（专家画像在学）⇒ 后 5 条实际是"半热"。两臂同样偏，配对仍成立。
- 因此结论的正确说法是：**「在冷启后的前 6 条请求上，20 vs 10 无可分辨差异」**，不是「线程数永远无关」。

**② 驻留率回溯未做，且现在做不了**：`docker restart` 不清页缓存，重启后首条仍读到热页，无法回答「14.6% 是否低于切 mmap 之前」。要答它只能做一次 **drop_caches + 冷读**，那是更高风险的动作（会影响 ComfyUI/其他容器），我没做、也不建议顺手做。
"""

PLAN_ADD = """
**补充 7（同日，P416 未结① 结案）**：`--pool-workers` 20 vs 10 **冷请求** A/B（两臂各冷启一次、同批 6 条随机提示）：`w10` **77.1 tok/s**（CV 12.0%、hit 90.8%）vs `w20` **77.1 tok/s**（CV 11.4%、hit 90.9%）⇒ **Δ −0.1%，2×CV 带 23.9%，带内**。臂内：两臂第 0 条都 59–60 tok/s（hit 66%），爬到 84（hit 98%）⇒ **决定 decode 的是命中率/预热，不是线程数**。边界：n=6/臂、非交错、单次冷启 ⇒ 只能分辨 >24%。config 按字节还原（`53ac61e0…`），停机约 3 min。**② 驻留率回溯做不了**（restart 不清页缓存；要 drop_caches，风险高，未做）。
"""

MEMSEC = """
- 04:20 **P416 未结① 结案（真跑，停机 3 min）**：`--pool-workers` 20 vs 10 **冷请求** A/B，两臂各冷启 + 同批 6 条随机提示：w10 **77.1 tok/s**（CV 12.0%、hit 90.8%）vs w20 **77.1**（CV 11.4%、hit 90.9%）⇒ **Δ −0.1%，带 23.9%，带内**。臂内两臂都是 **59–60 tok/s（hit 66%）→ 84（hit 98%）** ⇒ decode 由**命中率/预热**决定，不是线程数。**边界：n=6/臂、非交错、只能分辨 >24%。** config 已字节还原 `53ac61e0…`。**② 驻留率回溯做不了**（restart 不清页缓存）。
"""


def add_p416():
    t = io.open(PROG, encoding="utf-8").read()
    if "冷请求 A/B 结案" in t:
        return "P416 结果已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P416"]:
            while len(f) < 11:
                f.append("")
            f[9] = (f[9].rstrip() + RESULT).strip()
            f[10] = "KW:decode 不稳|corr 0.49|命中率"
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P416 已追加冷请求 A/B 结果"
    return "P416 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "20. `P416` 未结①结案" in t:
        return "§20 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§20 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 7（同日，P416 未结① 结案）" in t:
        return "方案补充 7 已存在"
    anchor = "**边界：能防\"声明与内容脱节\"，防不住\"没想到该按什么词找\"。**"
    if anchor not in t:
        return "锚点未找到"
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(anchor, anchor + "\n" + PLAN_ADD, 1))
    return "方案补充 7 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "P416 未结① 结案" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_p416, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
