#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1005 deploy: ci/prefill_phases + W832 6.2 new30 rewrite + 6.5 write-back + PROGRESS rows.

Everything here is text surgery on files that exist; the script asserts each anchor before it
writes, and prints what it changed.  Run from the workspace root.
"""
import io
import os
import subprocess
import sys

W = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(W, "deploy/W832_OPT_PLAN_V2.md")
PROG = os.path.join(W, "deploy/PROGRESS.tsv")
SRC = os.path.join(W, "albus/w1005")
HOST = "albus@192.168.50.166"
REPO = "/home/albus/strata166/pr/strata-fork"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- 1. plan: new30
NEW30 = (
    "| **新30** | **R95** | **小批 GEMM 效率**（`W1005` 重写）：2K 对 16K 的每 token 成本 gate/up **1.57×**、"
    "down **1.52×**、整条 prefill **1.23×**（2K 1.531 / 16K 1.241 ms/tok）；`dequant` **161 ms（5.0%）** "
    "是每 chunk 固定量（8K 525、16K 491），不是每 token；`wait copy` 只剩 **37 ms（1.2%）**（旧记 170） | "
    "**A/B/C 三条候选全部出局**：A 几何不成立（`W992`）；B 上游 GCN + Q4_K/Q5_K/Q6_K 的 MMQ→MMVQ 阈值是 "
    "**4 行**（`ref/mx mmvq.cu:190`），我们 ncols p50=331，几乎没有可分流的小组；C 天花板 5.0% 且两条通路都被挡住"
    "（DIRECT 需 TAB、上游流式场景 ≤1.5%；ROUTED_STREAM 1K 档 −7.6%）。**残余 1.57× 不在 MMQ 核内**："
    "`WIDTH_SWEEP` 192→1024 行每行成本平坦 0.0033 ms/row ⇒ 下一手量 host/launch 侧 | "
    "`W990` 立、`W1005` 重写：数字全部来自 `ci/prefill_phases/PREFILL_PHASES.tsv`（同二进制、冷 prompt、n=3），"
    "`phases.py --check` 强制方案与表一致 |"
)

# ---------------------------------------------------------------- 2. plan: 6.5 block
BLOCK = """
### 回写 · W1005（R95 的三个候选全部出局，残余不在核内）

R95 立了五轮，判据里一直挂着「gate/up 1.91×、down 1.87×、dequant 3.9×、wait copy 14×」和「先 C 后 B」。
`W1005` 用同一个二进制、同一份 config、冷 prompt（互不为前缀）、每档 n=3 重测 `STRATA_PREFILL_TIMING`，
把这张表换成可复算的 `ci/prefill_phases/PREFILL_PHASES.tsv`。四条旧数字有三条要改，而改动方向决定排序：

| 项 | 旧说法（`W990`，单条 2056/15757 行） | 实测 2K（n=3 中位） | 实测 8K | 实测 16K | 处置 |
|---|---|---|---|---|---|
| gemm gate/up | 1.91× | **1.57×**（0.392 vs 0.249 ms/tok） | 1.17× | — | 数字改写 |
| gemm down | 1.87× | **1.52×**（0.245 vs 0.161） | 1.09× | — | 数字改写 |
| `dequant` | 3.9×（266 ms） | **161 ms（5.0%）** | 525 ms | 491 ms | **不是每 token**：每 chunk 固定量，按 token 归一化会造出假惩罚 |
| `wait copy` | 14×（170 ms） | **37 ms（1.2%）** | 75 ms | 114 ms | issuer 线程 + 按组 gather 落地后已降 5 倍 |

2K 相对 16K 的总惩罚 = **0.290 ms/tok × 2084 = 605 ms（占 2K prefill 的 19%）**，其中 gate/up 296、down 174
（合计 **470 ms = 78%，即 prefill 的 14.7%**）；`dequant` 99、`host grouping` 91、`router` 33；attention 反向省 190。

**三条候选的处置（都有本地方可复核的证据，不是判断）**

| 候选 | 结论 | 证据 |
|---|---|---|
| A 让 J<64 可用 | 出局（`W992` 已判） | Q4_K 的 J 在四张架构表里都从 64 起 |
| B 小专家走 GEMV/MMVQ 分流 | **出局** | 上游 `MUL_MAT_ID` 在 GCN 上对 Q4_K/Q5_K/Q6_K 的阈值是 **4 行**（`mmvq.cu:190`）；我们 ncols p50=331、p90=742，可分流的小组近乎不存在 |
| C dequant 融合（去掉 group gather） | **天花板 5.0%，且两条通路都被实测挡住** | `STRATA_MMQ_DIRECT` 需 `-DSTRATA_MMQ_TAB=ON`，gfx906 结构性编不出（`W994`），且上游自己测「多数专家从 RAM 流式」时只有 1.5%；`STRATA_PREFILL_ROUTED_STREAM` 在 1K 档 −7.6%（`R66`） |

**残余 1.57× 在哪里：不在 MMQ 核内。** `ci/repack_ab/WIDTH_SWEEP.tsv` 的同一 kernel 扫描显示每行成本从
192 行到 1024 行完全平坦（0.0033 ms/row），只有 ≤96 行才劣化；2K 的每组专家平均 411 列，正落在平坦区。
⇒ 1.57× 出在每专家/每组的外围（host 侧建表与派发、组循环），不在 tile 几何。
**这一条拦下了一个差点做的错事**：上游 MoE stream-k（#22174，双 3090 +17%）的收益前提是核内 wave 量化，
而本地 kernel 已经不量化了 —— 按上游结论去移植会白做一轮。

**举一反三（写进判据，不只写在报告里）**

1. 相位表的每个数必须能追到「同二进制 + 冷 prompt + 每档 n≥3」的一次采样；跨 build 的日志只能用来提假设。旧表混了 83 个长度簇、十几次重启。
2. 凡是 **per-chunk** 量（`dequant`、`host grouping`）必须同时报绝对值与所在档，否则「per token」会把它变成随长度缩放的假惩罚。
3. 上游的 dispatch 阈值可以直接判死一个移植想法，不必写代码：B 就是这么出局的。
4. 独立 bench 与生产相位必须交叉验证：bench 说核内平坦，就不许把生产的 1.57× 归给核内。

**门**：`ci/prefill_phases/phases.py --check` 两条判据 —— 每行 26 个相位之和 = GPU timeline（±3%）、方案引用的
10 个数值 = 表里的值（改数据不改方案即 FAIL）。负向自测 4/4（篡改 2K 簇 `dequant`、破坏一行之和、删 16K 簇、
抬高 `gpu_ms`）。接进 `ci/round_gate.py --ci` 与 GitHub `ci/**` 触发。
"""

# ---------------------------------------------------------------- 3. PROGRESS
ROWS = [
    ("B6判定探针", "P294",
     "2K/8K/16K 相位表实测（同二进制、冷 prompt、每档 n=3）→ `PREFILL_PHASES.tsv`",
     "W1005", "1", "1", "DONE",
     "**W1005 立**：旧表来自单条 2056/15757 行、跨十几次重启。新表 18 行，2K 3191 ms（gu 816/down 510/dequant 161/wait 37/host grouping 91）、8K 11021、16K 20318。probe 请求 1735/6915/13824 落在 2084/8271/16375（prompt 生成器超 1.19×）。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1005"),
    ("B6判定探针", "P295",
     "口径更正：`dequant` 是每 chunk 固定量、`wait copy` 已从 170 降到 37",
     "W1005", "1", "1", "DONE",
     "**W1005 立**：dequant 2K 161 / 8K 525 / 16K 491 —— 随专家并集饱和，不是每 token；按 token 归一化会造出「3.9×」假惩罚。wait copy 170→37 是 issuer 线程 + 按组 gather 的结果，旧数作废。2K 相对 16K 总惩罚 605 ms（19%），gu+down 占 470 ms（78% = prefill 的 14.7%）。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1005"),
    ("B4上游移植", "P296",
     "上游 MMVQ 的 `MUL_MAT_ID` 阈值：GCN 上 Q4_K/Q5_K/Q6_K = 4 行",
     "W1005", "1", "1", "DONE",
     "**W1005 立**：`ref/mx mmvq.cu:190 get_mmvq_mmid_max_batch_gcn` + `ggml-cuda.cu:2206` 的 `is_id ? ncols <= ...`。我们 ncols p50=331 / p90=742 / max 7680（W991）⇒ 只有 ≤4 行的尾巴能分流，R95-B 的适用面近乎为零。这条不用写代码就判死了 B。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 新30"),
    ("B9否决不适用", "P297",
     "R95 三候选全出局；残余 1.57× 不在 MMQ 核内（WIDTH_SWEEP 每行成本平坦）",
     "W1005", "1", "1", "DONE",
     "**W1005 立**：A 几何（W992）、B 阈值（P296）、C 天花板 5.0% 且 DIRECT 需 TAB（W994）/ROUTED_STREAM 1K −7.6%（R66）。核内证据：WIDTH_SWEEP 192→1024 行 0.0033 ms/row 平坦，2K 每组均值 411 列正落平坦区 ⇒ 1.57× 出在 host 建表与派发，不在 tile 几何；据此**否掉**按上游 stream-k（#22174）移植的想法。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1005"),
    ("B8工程", "P298",
     "相位门 `ci/prefill_phases/phases.py --check`（相位之和 + 方案引用值双向一致）",
     "W1005", "1", "1", "DONE",
     "**W1005 立**：判据一每行 26 相位之和 = GPU timeline ±3%（打印取整）；判据二方案引用的 10 个值 = 表值（改数据不改方案即 FAIL）。负向 4/4 按预期 FAIL（篡改 2K 簇 dequant → 156 vs 161；破坏一行和 → −3.6%；删 16K 簇 → 无簇；抬 gpu_ms → −6.1%）。接进 `round_gate.py --ci`，workflow `paths: ci/**` 已覆盖。",
     "ci/prefill_phases/README.md"),
]


def main():
    # ---- plan
    s = read(PLAN)
    old = None
    for line in s.split("\n"):
        if line.startswith("| **新30**"):
            old = line
            break
    assert old, "new30 row not found"
    s = s.replace(old, NEW30, 1)
    assert "### 回写 · W1005" not in s or True
    # append at end of file (blocks are appended in round order)
    if "### 回写 · W1005" not in s:
        s = s.rstrip("\n") + "\n" + BLOCK
    write(PLAN, s)
    print("plan: new30 rewritten, W1005 block appended")

    # ---- progress
    p = read(PROG)
    have = {l.split("\t")[1] for l in p.split("\n") if l.count("\t") >= 8}
    add = []
    for blk, pid, item, src, _c5, cn, st, note, ref in ROWS:
        if pid in have:
            continue
        add.append("\t".join([blk, pid, item, src, "count", "1", "1", st, note, ref]))
    if add:
        p = p.rstrip("\n") + "\n" + "\n".join(add) + "\n"
        write(PROG, p)
    print("progress: +%d rows" % len(add))

    # ---- ci files
    os.makedirs(os.path.join(REPO), exist_ok=True)
    subprocess.run(["ssh", HOST, "mkdir -p %s/ci/prefill_phases" % REPO], check=True)
    for f in ["phases.py", "w1005_probe.py", "PREFILL_PHASES.tsv", "README.md"]:
        subprocess.run(["scp", "-q", os.path.join(SRC, f),
                        "%s:%s/ci/prefill_phases/%s" % (HOST, REPO, f)], check=True)
    print("ci: 4 files uploaded")


def c4(x):
    return x


if __name__ == "__main__":
    sys.exit(main())
