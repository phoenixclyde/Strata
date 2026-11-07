"""W1035 第 34 段：从 GGUF 头取真常数 → roofline 重算，MoE GEMM 只有峰值的 1.6%。

关键更正：expert_used_count=10（不是我反推的 4）；ffn=640（gu 打包 1280 行 = gate+up 各 640）；
我先前把 MACs 多算了一倍。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035ae"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 GGUF 真常数 + roofline 重算】**：解 GGUF 头（67 个 KV）得：**`expert_used_count = 10`**"
          "（我先前反推的 4 作废）、**`expert_feed_forward_length = 640`**（`gu` 打包 1280 行 = gate+up 各 640，"
          "我先前按 2×1280×2560 算 MACs，**多算了一倍**）、`expert_count=512`、`block_count=48`、"
          "`embedding_length=2560`、`attention.indexer.top_k=2048`（QSA 稀疏注意力的 key 上限）、`general.sampling.top_k=20`（采样，不是路由）。"
          "**重算 2.5K 的 gate/up**：2500 token × **10** 专家 × 1280×2560 MAC = **82 G MAC = 164 GFLOP**；"
          "MI50 FP16 峰值 13.3 TFLOPS ⇒ 下限 **12.3 ms**；实测 **754 ms** ⇒ **只有峰值的 1.6%**。"
          "带宽侧：512 专家 × 1.84 MB × 48 层 = **45 GB** ⇒ @1 TB/s **45 ms**，实测 754 ⇒ **17× 于带宽下限**。"
          "每专家行数（若均匀）= 2500×10/512 ≈ **49 行**，与 `ncols` 中位 296（组内单专家最大）自洽（路由偏斜）。"
          "⇒ **缺口不是「行太少」，是「核的效率」**：1.6% 峰值 + 17× 带宽，指向 Q4_K 在核内反量化与 tile 组织，"
          "**这正是 `R95` 该攻的地方**，且与 `P297`「残余不在 MMQ 核内」**冲突**——`P297` 需要重审。")

SEC = """
**34. 从 GGUF 头拿到真常数：`top-k = 10`、`ffn = 640`；MoE GEMM 只有峰值的 1.6%。**
不再反推，直接解 GGUF 头（67 个 KV，`struct` 解析）：

| 键 | 值 | 说明 |
|---|---|---|
| `qwen4exp.expert_used_count` | **10** | **真实 top-k**；我先前反推的 4 作废 |
| `qwen4exp.expert_feed_forward_length` | **640** | `gu` 打包成 1280 行 = gate(640)+up(640) |
| `qwen4exp.expert_count` | 512 | — |
| `qwen4exp.block_count` | 48 | — |
| `qwen4exp.embedding_length` | 2560 | — |
| `qwen4exp.attention.indexer.top_k` | **2048** | QSA 稀疏注意力的 key 上限 |
| `general.sampling.top_k` | 20 | 采样用，**不是**路由 |

**roofline 重算（2.5K 的 gate/up）**
- MACs = 2500 × **10** × 1280×2560 = **82 G MAC = 164 GFLOP**（我先前按 2×1280×2560 算，**多算一倍**）；
- 计算下限：164 GFLOP ÷ 13.3 TFLOPS = **12.3 ms**；实测 **754 ms** ⇒ **峰值的 1.6%**；
- 带宽下限：512 专家 × 1.84 MB × 48 层 = **45 GB** ÷ 1 TB/s = **45 ms**；实测 ⇒ **17× 于带宽**。

**两个推论**
1. **每专家行数若均匀 = 2500×10/512 ≈ 49 行**，与 `ncols` 中位 296（组内单专家**最大**）自洽（路由偏斜，少数专家吃很多行）。
   ⇒ **缺口不是"行太少"**，`M 饥饿` 这条彻底不成立（上一轮已撤，这轮有正数支持）。
2. **缺口的形状是「核效率」**：1.6% 峰值、17× 带宽，指向 **Q4_K 在核内反量化 + tile 组织**，而不是数据搬运、不是调度、不是 padding。

**这条与 `P297` 冲突，必须指出**：`P297` 记的是「残余不在 MMQ 核内（`WIDTH_SWEEP` 每行成本平坦）」。
现在 2.5K 的 gate/up 只有峰值 1.6%、带宽 1/17，**要么 `P297` 的口径只适用于它测的形状，要么它测的量不含反量化开销**。
**`P297` 需要重审**——这是本轮唯一一处推翻既有结论的地方，我不擅自改它，只登记冲突。
"""

PLAN_ADD = """
**补充 21（同日，GGUF 真常数与 roofline 重算）**：GGUF 头 ⇒ **`expert_used_count=10`**（反推的 4 作废）、**`ffn=640`**（gu=1280 行 = gate+up 各 640，先前 MACs 多算一倍）、`expert_count=512`、`blocks=48`、`emb=2560`、`indexer.top_k=2048`。重算 2.5K gate/up：**164 GFLOP ⇒ 下限 12.3 ms，实测 754 ms = 峰值 1.6%**；带宽 45 GB ⇒ 45 ms，**17× 于带宽**。每专家行数 ≈49（均匀），`ncols` 中位 296 与之自洽 ⇒ **M 饥饿彻底不成立**。**缺口形状 = 核效率（Q4_K 反量化 + tile 组织）**。**与 `P297`（残余不在 MMQ 核内）冲突，登记待重审**。
"""

MEMSEC = """
- 06:2x **GGUF 真常数**：`expert_used_count=10`、`ffn=640`（gu 1280 行=gate+up 各 640，先前 MACs 多算一倍）、512 专家/48 层/emb 2560、`indexer.top_k=2048`。重算 2.5K gate/up：**164 GFLOP ⇒ 12.3 ms 下限，实测 754 ms = 峰值 1.6%**；带宽 45 GB ⇒ 45 ms（17×）。每专家 ≈49 行 ⇒ **M 饥饿彻底不成立**；**缺口=核效率（Q4_K 反量化/tile 组织）**。**与 P297「残余不在 MMQ 核内」冲突，登记待重审**。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "GGUF 真常数 + roofline 重算" in t:
        return "P418 已记 GGUF"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加 GGUF 常数"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "34. 从 GGUF 头拿到真常数" in t:
        return "§34 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§34 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 21（同日，GGUF 真常数与 roofline 重算）" in t:
        return "方案补充 21 已存在"
    anchor = "**补充 20（同日，口径校准）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 21 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "GGUF 真常数" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
