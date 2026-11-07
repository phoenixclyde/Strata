#!/usr/bin/env python3
"""W1036 第三段：把「Q4_K 到底走不走 dp4a」核清，并更正上一段的机制口径。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REP = os.path.join(ROOT, "albus", "w1036", "reply.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")

SEC = """
**11. 更正：`Q4_K` 一直在走 dp4a，而且走的是「另一套」dp4a。**
上一段我写「`iq_kernels.cu:103` 的 dp4a 只服务 Q2/Q3/IQ，不是我们的 Q4_K」——**半对半错**。核清之后是两套 dp4a：

| 用在哪 | dp4a 来自哪 | gfx906 上 A0 之前 |
|---|---|---|
| **prefill MoE GEMM**（gate/up、down） | `moe_mmq.cu:533` → ggml `mul_mat_q_case` → `veccq.cuh` 66 处 `ggml_cuda_dp4a` → `common.cuh:750` **`__dp4a`** | **一直是硬件** |
| decode MMVQ / 我们自己的 iq/s2/dflash2 | 我们的 `hip_compat::dp4a`（`iq_kernels.cu:84` `#define ggml_cuda_dp4a(a,b,c) STRATA_DP4A(...)`） | **软件模拟（28 条）**，A0 才变 1 条 |

⇒ 所以 A0 的零结果是**自洽的**：它只动了第二套，而第二套的宿主相位（decode MMVQ）算力利用率 0.6%，本来就看不见。**prefill 一侧 A0 从头到尾没碰过**，它一直是硬件 dp4a。

**12. 「是不是可以走」：能走的指令已经走完了；缺的不是指令，是利用率。**
按 dp4a 的真实峰值算（64 CU × 64 lane × 1.725 GHz = 7.06 T 指令/s，每条 4 个 MAC ⇒ **28.2 TMAC/s**）：

```
prefill gate/up 2.5K：2500 tok × 10 专家 × 1280×2560 × 48 层 = 3.93 TMAC
实测 754 ms ⇒ 5.2 TMAC/s ⇒ dp4a 峰值的 18.5%
```

**还有 5.4× 的提升空间，但它不在「换哪条点积指令」上**——指令已经是 `v_dot4_i32_i8`，一条不多。剩下的 82% 只能来自占用率 / LDS / tile 组织 / CU 均衡。

一条看似可行、实测不可行的路也排掉了：**`v_dot8_i32_i4`**（gfx906 也有，一次 8 个 4-bit MAC）要求**两个操作数都是 4-bit**，而我们的激活是 q8_1（int8）；要用它就得把激活也压到 4-bit，那是**新的量化误差源**，不是"换个指令"。

⇒ 结论：`R95`/D2 的方向应当是 **用计数器证明 82% 花在哪**（survey 的 D2：每 CU `SQ_INSTS` 方差 + 最忙/平均比），而不是继续找"更快的点积"。这需要 `rocprofv3` 窗口。
"""


def row(rid, block, item, kind, status, note, ref, kw):
    return "\t".join([block, rid, item, "W1036", kind, "1", "1", status, note, ref, "KW:" + kw])


def main():
    rep = io.open(REP, encoding="utf-8").read()
    if "**11. 更正：`Q4_K` 一直在走 dp4a" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply +§11/§12")
    else:
        print("reply has §11")

    prog = io.open(PROG, encoding="utf-8").read().rstrip("\n").split("\n")
    ids = {l.split("\t")[1] for l in prog if l.count("\t") > 5}
    add = []
    if "P423" not in ids:
        add.append(row("P423", "B8工程",
                       "口径更正：Q4_K 一直在走 dp4a，但是**两套**——prefill MoE GEMM 走 ggml 的 __dp4a（一直硬件），"
                       "A0 只修了我们自己的 hip_compat 层（decode MMVQ 等）；prefill 利用率是 dp4a 峰值的 18.5%",
                       "count", "DONE_NEG",
                       "prefill gate/up 2.5K：3.93 TMAC / 754 ms = 5.2 TMAC/s，dp4a 峰值 28.2 TMAC/s ⇒ 18.5%，"
                       "5.4× 空间但不来自指令选择（已是 v_dot4_i32_i8）。`v_dot8_i32_i4` 不适用："
                       "激活是 q8_1(int8)，要压到 4-bit 才行 ⇒ 新误差源。方向改为 D2 计数器",
                       "P421", "两套 dp4a|18.5%|v_dot8 不适用"))
    if add:
        io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(prog + add) + "\n")
        print("ledger +%d" % len(add))
    else:
        print("ledger has P423")

    plan = io.open(PLAN, encoding="utf-8").read()
    if "**补充 12（Q4_K 的两套 dp4a；prefill 利用率 18.5%）**" not in plan:
        blk = ("\n**补充 12（Q4_K 的两套 dp4a；prefill 利用率 18.5%）**：`Q4_K` 一直在走 dp4a，但有两套实现——"
               "prefill MoE GEMM（`moe_mmq.cu:533` → ggml `mul_mat_q_case` → `common.cuh:750` `__dp4a`）**一直是硬件**；"
               "我们自己的 `hip_compat::dp4a`（decode MMVQ / iq / s2 / dflash2）在 gfx906 上一直是 28 条指令的模拟，"
               "A0 才修成 1 条。A0 的零结果因此自洽（它只动 decode，而 decode 算力利用率 0.6%）。"
               "prefill gate/up 2.5K = 3.93 TMAC / 754 ms = **5.2 TMAC/s = dp4a 峰值的 18.5%**：还有 5.4×，"
               "但**不在指令选择上**（已是 `v_dot4_i32_i8`）；`v_dot8_i32_i4` 不适用（激活是 int8）。"
               "⇒ 下一手是 D2：用 `rocprofv3` 的每 CU `SQ_INSTS` 方差证明 82% 花在哪。\n")
        i = plan.rfind("### 回写 · W1036")
        j = plan.find("\n### 回写 ·", i + 10)
        if j < 0:
            j = len(plan)
        plan = plan[:j] + blk + plan[j:]
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
        print("plan +补充 12")
    else:
        print("plan has 补充 12")

    mem = io.open(MEM, encoding="utf-8").read() if os.path.isfile(MEM) else ""
    if "两套 dp4a" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("- **两套 dp4a**：ggml 的 `__dp4a`（prefill MMQ 用，一直硬件）vs 我们 `hip_compat::dp4a`"
                     "（decode MMVQ 用，A0 前是 28 条模拟）。A0 只动后者 ⇒ 零结果自洽。\n"
                     "- prefill gate/up = **dp4a 峰值 18.5%**（3.93 TMAC / 754 ms vs 28.2 TMAC/s）；"
                     "`v_dot8_i32_i4` 不适用（激活 int8）。下一手 = D2 计数器，不是换指令。\n")
        print("memory appended")


if __name__ == "__main__":
    main()
