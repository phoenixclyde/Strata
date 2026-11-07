"""W1035 第 35 段：排除降频（1725 MHz / 200 W / 99%），效率 0.8% 是核级事实；下一手用现成 microbench。

含一处峰值口径更正：MI50 FP16 打包峰值 26.5 TFLOPS（非 13.3），效率进一步降到 0.8%。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035af"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 排除降频，效率降到 0.8%】**：2.5K 请求期间实测 GPU：`sclk` **1725 MHz（level 8 = 最高档）**、"
          "`mclk` 1000 MHz、功耗 **182–224 W**、`GPU use` **99–100%`** ⇒ **没有降频、没有限功耗、没有空闲**。"
          "**峰值口径更正**：MI50 的 FP16 **打包**峰值是 **26.5 TFLOPS**（13.3 是 FP32/非打包口径）"
          "⇒ 164 GFLOP ÷ 26.5 = **6.2 ms** 下限，实测 754 ms ⇒ **效率 0.8%**（先前按 13.3 算的 1.6% 也偏高）。"
          "⇒ **1% 量级的效率是核级事实**，不是时钟/功耗/带宽造成的。"
          "**下一手有现成工具**：源码里就有 `src/prefill/mmq_expert_bench.cpp`（专家 GEMM 微基准），"
          "直接跑它拿该核的**可达 TFLOPS**，就能判「0.8% 是核的天花板」还是「生产形状没喂饱它」。"
          "**这需要独占 GPU ⇒ 需要窗口**；我不擅自跑。")

SEC = """
**35. 排除基础设施：GPU 满频满功耗，效率 0.8% 是核的问题。**
1% 峰值这个数太反常，先查最容易被忽略的三件事——**降频、限功耗、GPU 空闲**。办法是边发请求边读传感器：

| 读数 | 值 |
|---|---|
| `sclk` | **1725 MHz**（level 8，最高档） |
| `mclk` | 1000 MHz（level 2） |
| 功耗 | **182 / 186 / 206 / 214 / 224 W**（空闲 17–18 W） |
| `GPU use` | **99–100%** |

⇒ **三项全排除**：没有降频、没有限功耗、没有空闲。

**顺带更正一个峰值口径**：MI50 的 FP16 **打包**峰值是 **26.5 TFLOPS**（我先前用的 13.3 是 FP32/非打包口径）。
于是 164 GFLOP ÷ 26.5 TFLOPS = **6.2 ms** 下限；实测 **754 ms** ⇒ **效率 0.8%**（先前算的 1.6% 也偏高一倍）。

**⇒ 结论收敛到一句**：**MoE GEMM 在满频满功耗下只跑到峰值的 0.8%**，这是**核级**事实，
不是时钟、不是功耗、不是带宽（带宽侧是 17×，但按算术强度 AI≈174 FLOP/B 远高于脊点 26.5 FLOP/B ⇒ 本该是**算力受限**）。

**下一手不用猜——源码里就有微基准**：`src/prefill/mmq_expert_bench.cpp`（专家 GEMM 专用 bench）。
跑它拿到该核的**可达 TFLOPS**，就能一刀切开两种可能：

| 微基准结果 | 含义 | 下一步 |
|---|---|---|
| 也只有 ~1% | 核的天花板就在这 | 换核/换算法（不是调参） |
| 明显更高（如 20–40%） | 生产形状没喂饱它 | 查分组/J/行数组织 |

**它要独占 GPU ⇒ 需要窗口**（约 3–5 分钟）。按铁律我先报窗口，等你点头；**不擅自跑**。
"""

PLAN_ADD = """
**补充 22（同日，排除降频）**：请求期间实测 `sclk` **1725 MHz（最高档）**、`mclk` 1000、功耗 **182–224 W**、`GPU use` **99–100%** ⇒ **无降频/无限功耗/无空闲**。**峰值口径更正：MI50 FP16 打包 26.5 TFLOPS**（13.3 是 FP32 口径）⇒ 下限 6.2 ms，实测 754 ms ⇒ **效率 0.8%**。⇒ **0.8% 是核级事实**。下一手：跑现成 `src/prefill/mmq_expert_bench.cpp` 拿可达 TFLOPS，判「核的天花板」还是「形状没喂饱」；**需独占 GPU，等窗口**。
"""

MEMSEC = """
- 06:3x **排除降频**：`sclk 1725 MHz`（最高档）、`mclk 1000`、功耗 **182–224 W**、`GPU use 99–100%` ⇒ 无降频/限功耗/空闲。**峰值口径更正：MI50 FP16 打包 26.5 TFLOPS**（13.3 是 FP32）⇒ 下限 6.2 ms，实测 754 ⇒ **效率 0.8%**，核级事实。下一手：`src/prefill/mmq_expert_bench.cpp` 微基准拿可达 TFLOPS（需窗口，等点头）。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "排除降频，效率降到 0.8%" in t:
        return "P418 已记降频排除"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加降频排除"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "35. 排除基础设施" in t:
        return "§35 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§35 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 22（同日，排除降频）" in t:
        return "方案补充 22 已存在"
    anchor = "**补充 21（同日，GGUF 真常数与 roofline 重算）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 22 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "排除降频" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
