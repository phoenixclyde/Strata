#!/usr/bin/env python3
"""W1036 第四段：gfx906 专用 MMQ 代码盘点 + 已备好的 Q4_K 载入暂存补丁（未验证编译）。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REP = os.path.join(ROOT, "albus", "w1036", "reply.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")

SEC = """
**13. 有没有「专门的 gfx906 MMQ 优化代码」可移植？有，但只有三份，且两份不适用。**
把 survey 里所有 fork 的 matmul 目录翻了一遍，gfx906 专用 MMQ 代码只集中在 `iacopPBK` 的三份文件：

| 文件 | 是什么 | 对我们适用吗 |
|---|---|---|
| `matmul/mmq.cuh` | `GFX906_LOAD_TILES_Q8_0_ASYNC` / `GFX906_STORE_TILES_Q8_0_LDS_*`：把 tile 载入拆成「先全部读进寄存器、再全部写 LDS」；另有 `gfx906_load_q4_0_quants_vectorized`（2×int4 代替 8 次标量） | **手法适用，代码不适用**：宏只服务 **Q8_0** 权重与 **Q4_0** 激活；我们是 Q4_K |
| `matmul/mmq-prefetch.cuh` | Y/X tile 的 L2 预取（`global_load_dword` 后丢弃值） | 低优先：y 是小操作数，本来就在 L2；且是"读了就扔"的写法，收益不确定 |
| `matmul/mmf.cuh` | 自写 FP16 GEMM（M 9–2048） | **不适用**：那是 f16 权重的中批 GEMM，我们走量化 MMQ |

**真正值得移植的是那个手法**，而且它对着我们实测的缺口：`mmq-load-tiles.cuh:711`（`ggml_cuda_mmq_load_tiles_q4_K` 的 dp4a 分支）现在是**每次迭代一次依赖载入 + 一次 LDS 写**——

```cpp
for (int i0 = 0; i0 < I; i0 += nrows*nwarps) {
    const block_q4_K * bxi = x + kbx0 + i*stride;
    const int qs0 = get_int_b4(bxi->qs, txi);   // 唯一的载入，马上被用
    x_qs[i*(MMQ_TILE_NE_K + 1) + txi] = qs0;    // 立刻写 LDS
}
```

一个线程同时只有 **1** 个载入在飞。把它改成「先把 N 个迭代的 32 位读全发出去，再统一写 LDS」，同时在飞的就是 **N** 个——**逐位不变**（同样的值、同样的写序、同样的 LDS 布局），只有内存级并行度变了。这正是 iacop 那个宏在做的事，只是搬到 Q4_K 上。

**已交付的东西（状态要说清）**：`albus/w1036/mmq_stage_patch.py`（幂等补丁，带 `--revert`，用 `-DSTRATA_GFX906_MMQ_STAGE` 控制，默认不开）已写好，并且**已应用到 ggml 的副本**（`tmp/w1036/ggml-test`）并自检通过（3 处 `qs_cache`）。**但没有完成编译验证**：单独编 `mmq.cu` 只产出 871 B 的空目标（这个 TU 的设备端实例化依赖 CMake 那套宏），所以验证必须走**真实构建**——那不需要停服，用独立 build 目录再编一次即可（约 3 分钟），跑完再决定要不要开测量窗口。

**治理问题（比补丁更要紧）**：`/home/albus/strata166/llama.cpp`（166 MB）**不是 git 仓库**，而它是生产构建的输入。任何对它的改动都不可追溯、不可回滚到"改动前"。所以这个补丁在落地前必须先解决版本化：`git init` + 先提交一份原始快照，之后每个补丁一个提交。否则就是我刚刚在 A/B 窗口上犯过的同一类错——**改了不可追溯的生产资产**。
"""


def row(rid, block, item, kind, status, note, ref, kw):
    return "\t".join([block, rid, item, "W1036", kind, "1", "1", status, note, ref, "KW:" + kw])


def main():
    rep = io.open(REP, encoding="utf-8").read()
    if "**13. 有没有「专门的 gfx906 MMQ 优化代码」可移植" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply +§13")
    else:
        print("reply has §13")

    prog = io.open(PROG, encoding="utf-8").read().rstrip("\n").split("\n")
    ids = {l.split("\t")[1] for l in prog if l.count("\t") > 5}
    add = []
    if "P424" not in ids:
        add.append(row("P424", "B8工程",
                       "gfx906 专用 MMQ 代码只有 iacop 的三份（Q8_0 载入暂存 / Q4_0 向量载入 / f16 GEMM），"
                       "两份不适用；可移植的是「寄存器暂存再写 LDS」手法，已给 Q4_K 写好幂等补丁，"
                       "未通过编译验证；llama.cpp 非 git 仓库是治理缺口",
                       "count", "OPEN",
                       "落点 `mmq-load-tiles.cuh:711`（现为 1 载入→1 LDS 写，线程只有 1 个载入在飞）。补丁 "
                       "`albus/w1036/mmq_stage_patch.py`（-DSTRATA_GFX906_MMQ_STAGE 控制，默认关）已应用到 "
                       "ggml 副本；单独编 mmq.cu 只出 871 B 空目标 ⇒ 验证必须走真实构建（不需停服）。"
                       "`/home/albus/strata166/llama.cpp` 不是 git 仓库，落地前必须先版本化",
                       "P423", "寄存器暂存|mmq-load-tiles|非 git 仓库"))
    if add:
        io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(prog + add) + "\n")
        print("ledger +%d" % len(add))
    else:
        print("ledger has P424")

    plan = io.open(PLAN, encoding="utf-8").read()
    if "**补充 13（gfx906 专用 MMQ 移植面）**" not in plan:
        blk = ("\n**补充 13（gfx906 专用 MMQ 移植面）**：gfx906 专用 MMQ 代码只存在 iacop 的三份文件里——"
               "`mmq.cuh`（Q8_0 载入暂存 + Q4_0 向量载入）、`mmq-prefetch.cuh`（Y/X tile L2 预取）、"
               "`mmf.cuh`（f16 GEMM）。其中 Q8_0/Q4_0 的宏对我们（Q4_K + q8_1 激活）不适用，f16 GEMM 也不适用；"
               "**可移植的是「先把 N 个载入发出去、再统一写 LDS」这个手法**。落点 "
               "`mmq-load-tiles.cuh:711`：现状是一次依赖载入 + 一次 LDS 写，线程只有 1 个载入在飞。"
               "补丁 `albus/w1036/mmq_stage_patch.py` 已就绪（`-DSTRATA_GFX906_MMQ_STAGE`，默认关）并应用到副本，"
               "**编译验证待真实构建**。`llama.cpp` 不是 git 仓库 ⇒ 落地前必须先版本化。\n")
        i = plan.rfind("### 回写 · W1036")
        j = plan.find("\n### 回写 ·", i + 10)
        if j < 0:
            j = len(plan)
        plan = plan[:j] + blk + plan[j:]
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
        print("plan +补充 13")
    else:
        print("plan has 补充 13")

    mem = io.open(MEM, encoding="utf-8").read() if os.path.isfile(MEM) else ""
    if "MMQ 移植面" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("- gfx906 专用 MMQ 代码只有 iacop 三份（Q8_0 暂存 / Q4_0 向量 / f16 GEMM），两份不适用；"
                     "可移植的是「寄存器暂存再写 LDS」手法（`mmq-load-tiles.cuh:711` 现在是 1 载入→1 LDS 写）。"
                     "补丁 `albus/w1036/mmq_stage_patch.py` 已就绪、未编译验证。\n"
                     "- **`/home/albus/strata166/llama.cpp` 不是 git 仓库**（166 MB，生产构建输入）⇒ 改它之前必须先版本化。\n")
        print("memory appended")


if __name__ == "__main__":
    main()
