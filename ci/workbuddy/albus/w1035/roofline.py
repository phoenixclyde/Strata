"""W1035 第 32 段：roofline 夹逼 + 填充浪费实测 8–12%（④ 定量出局）+ M 饥饿得到支持。

假设全部写出来，不藏。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035ac"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 roofline 与填充实测】**：`pick_J` 的 `ncols`（每次调用的行数）实测："
          "中位 **296**、均值 491、p90 1245、max 13824（12,268 条）；按 J 折算**填充浪费中位 8%、均值 12%** ⇒ "
          "**候选④（tile 填充地板）定量出局**——它最多解释 12%，而 2.5K 的 gate/up 是 754 ms。"
          "roofline（假设写全）：2.5K × top-k 4 × 2 矩阵 × 1280×2560 ⇒ **131 GFLOP**；MI50 FP16 峰值 13.3 TFLOPS ⇒ **下限 ~10 ms**；"
          "若 512 专家/层全读，权重 48×512×3.69 MB = **90 GB** @1 TB/s ⇒ **~90 ms**。"
          "**实测 754 ms ⇒ 比计算下限高 76×、比带宽下限高 8×** ⇒ 既不在算力顶也不在带宽顶。"
          "**M 饥饿得到旁证**：定长每 token 成本随长度下降（2.5K **302 µs/tok** → 4–16K 斜率 **200**），"
          "正是「每专家行数太少、tile 打不满」的特征。**待测（零停机）**：从路由统计拿「每专家平均行数」，"
          "若 ~18 行而 J=64，则单专家利用率 28%，与 8–76× 的缺口方向一致。")

SEC = """
**32. roofline 夹逼 + 填充实测：④ 定量出局，M 饥饿成为主要解释。**
2.5K 的 `gemm gate/up = 754 ms` 到底离谱到什么程度？两端都算：

**假设（写全，便于被推翻）**
- 2.5K token、top-k = 4（由 `ncols` 反推：1491 launches × 296 行 ÷ 48 层 ≈ 9176 行/层 ÷ 2500 ≈ 3.7，接近 4）；
- gate/up 各 1280×2560，Q4_K ≈ 4.5 bit/权 ⇒ 每专家 3.69 MB（两矩阵）；
- MI50 FP16 峰值 ~13.3 TFLOPS；VRAM 带宽 ~1 TB/s。

**两端**
| 界 | 算法 | 值 |
|---|---|---|
| 计算下限 | 2500×4×2×1280×2560 = 131 GFLOP ÷ 13.3 TFLOPS | **~10 ms** |
| 带宽下限 | 48 层 × 512 专家 × 3.69 MB = 90 GB ÷ 1 TB/s | **~90 ms** |
| **实测** | — | **754 ms** |

⇒ **比计算下限高 76×、比带宽下限高 8×**。既不在算力顶，也不在带宽顶。

**候选④ 定量出局**：`pick_J` 的 `ncols` 实测中位 **296**、均值 491、p90 1245；按 J=64 折算
**填充浪费中位 8%、均值 12%**。**12% 解释不了 8–76×**，④ 到此彻底出局（此前只是"未获支持"，现在是"定量不可能"）。

**M 饥饿（每专家行数太少）成了主要解释，而且有旁证**：定长每 token 成本**随长度下降**——
2.5K 实测 **302 µs/tok**（754/2.5K），4–16K 段的斜率是 **200 µs/tok**。同样的核，行数多了反而每 token 更便宜，
这正是"每专家行数太少、tile 打不满"的特征（若每专家 ~18 行而 J=64，单专家利用率只有 28%）。

**下一步（零停机）**：从路由统计拿「每专家平均行数」，把 18 这个数从推断变成实测；
若成立，`R95` 的解法方向就明确了——**不是找更快的核，而是让每个专家一次吃到更多行**
（更长 chunk、跨请求合批、或按专家分组重排 token），这与 `P297`「残余不在 MMQ 核内」自洽。
"""

PLAN_ADD = """
**补充 19（同日，roofline + 填充出局）**：`ncols` 中位 296/均值 491 ⇒ **填充浪费 8–12%** ⇒ **④ 定量出局**（最多解释 12%）。roofline：131 GFLOP ⇒ 计算下限 ~10 ms；90 GB 权重 ⇒ 带宽下限 ~90 ms；**实测 754 ms = 76×/8×**。**M 饥饿为主解释**，旁证：每 token 成本 2.5K 302 → 4–16K 200 µs/tok（行多反而更便宜）。下一步零停机：从路由统计取「每专家平均行数」（推断 ~18，J=64 时利用率 28%）。
"""

MEMSEC = """
- 06:0x **roofline + 填充出局**：ncols 中位 296 ⇒ 填充浪费 **8–12%** ⇒ ④ 定量出局；roofline 计算下限 ~10 ms、带宽下限 ~90 ms，**实测 754 ms（76×/8×）**；**M 饥饿成主解释**（每 token 成本 2.5K 302 → 4–16K 200 µs/tok）。下一步：路由统计取每专家行数（推断 ~18，J=64 利用率 28%）。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "roofline 与填充实测" in t:
        return "P418 已记 roofline"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加 roofline"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "32. roofline 夹逼" in t:
        return "§32 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§32 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 19（同日，roofline + 填充出局）" in t:
        return "方案补充 19 已存在"
    anchor = "**补充 18（同日，定长绝对值排序）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 19 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "roofline + 填充出局" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
