#!/usr/bin/env python3
"""W1036 第二段收工：A0 实测结论 + 事故记录，写进报告/账本/方案/记忆。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REP = os.path.join(ROOT, "albus", "w1036", "reply.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")


def row(rid, block, item, kind, status, note, ref, kw):
    return "\t".join([block, rid, item, "W1036", kind, "1", "1", status, note, ref, "KW:" + kw])


SEC = """
**9. A0 实测：没有可分辨的收益（四个指标全在 2×CV 带内）。**
窗口 06:10:54–06:14:38，一换件两重启，两臂各冷启一次、同盐值同内容、逐请求交错取数：

| 指标 | ctl（`-001`，dp4a=软件循环） | a0（port-all，标志全关） | Δ | 2×CV | 判 |
|---|---|---|---|---|---|
| prefill 3.4K | 1569.3 µs/tok（CV 0.4%，n=3） | 1609.8（CV 3.4%，n=3） | **+2.6%** | 6.8% | 带内 |
| prefill 10.8K | 1267.6 µs/tok（CV 0.2%，n=2） | 1268.8（CV 0.0%，n=2） | **+0.1%** | 0.4% | 带内（几乎恒等） |
| decode tok/s | 62.50（CV 13.6%） | 60.46（CV 13.6%） | −3.3% | 27.2% | 带内 |
| decode ms/window | 41.30（CV 17.2%） | 41.28（CV 17.2%） | **−0.0%** | 34.4% | 带内 |

3.4K 那臂的 `+2.6%` 全部来自**第一条请求**（5674 ms，冷启后的首条），后两条 5378/5383 对 ctl 的 5341/5331 只差 +0.8%；10.8K 这一档 CV 只有 0.2%/0.0%，**差 0.1%**，是最硬的一条：**这条代码路径的成本没有变**。

**机制（源码核实，不是猜）**：`iq_kernels.cu:103` 的 dp4a 落在 `vec_dot_q2_0_q8_1` / `vec_dot_iq2_xxs_q8_1` / trellis（`tq_lut_i8`）——**是 Q2/Q3/IQ 类型**，不是我们 MoE 用的 Q4_K。decode 侧 `native_mmvq.cu` 那 45 处 dp4a 确实被换成了单指令，但 **decode 只有 0.6% 算力利用率**（10 专家 × 48 层 × 3 矩阵 ≈ 236 MMAC/ token，60 tok/s ⇒ 14 GMAC/s，而 FP16 峰值 26.5 TFLOPS），本来就是延迟/带宽受限 —— 把 28 条指令换成 1 条，**在这两个相位上都看不见**。

**举一反三（这条比结论更值钱）**：A0 的零结果**同步否掉了 B3 的前提**。B3（HC down-GEMM 用 q8_1 激活 + dp4a）与 MMVQ 同族——都是 decode 窗内的整数点积——既然 MMVQ 的 45 处 dp4a 换成单指令都测不出差异，B3 的上限也就是 0。所以 B3 不再需要窗口，直接按"前提不成立"处理。

**A0 去留**：留着。它**逐位不变**、指令更少、且是 B1/B2 能成立的前置（否则那些站点会更慢）。但**不许把它记成收益**。

**10. 事故：v1 窗口把生产打宕了约 2.5 分钟（我自己造成的）。**
06:03:46 装候选时，我把 config 的 `exe` 写成了**宿主路径** `/home/albus/strata166/data/bin/strata-0.1.57-pa0`；容器里只有 `/data/bin/...`，引擎 exec 失败 ⇒ `docker` 进入 `restarting` 循环（`RestartCount` 到 11）。06:06:0x 我手工 `sudo cp` 还原 config 并重启容器，06:07:22 恢复 `running`。**停机约 2.5 分钟**。

三个缺陷，全部是我自己的：

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | `exe` 用宿主路径 | 配置里只写**容器路径**（`/data/bin/<名字>`），宿主路径只用于 `cp` |
| 2 | `trap` 里 `restore()` 不校验就被后续流程覆盖 | restore 后**必查 md5**，不符就 `sudo` 重试，仍不符则中止（不再继续"测量"） |
| 3 | `trap` 收到 TERM 后 return 而不退出 ⇒ 脚本在被杀之后继续跑，把生产二进制当候选测了 | 加 `trap 'restore; exit 130' INT TERM`，与 `trap restore EXIT` 分开 |

还有一条不是缺陷但要知道：**刚重启的引擎，第一条请求不写 `strata prefill timing` 行**（v1 因此报"no prefill timing line"），现在每臂先发一条预热请求并允许 3 次重试；另外**同一提示会被 prompt cache 整段命中**（我第一次手工复现时把缓存喂热了，导致下一轮 3 次重试全部无 prefill），所以窗口内用一次性盐值（`a0_salt`）保证两臂同文本、跨窗口不撞缓存。
"""


def main():
    rep = io.open(REP, encoding="utf-8").read()
    if "**9. A0 实测" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply +§9/§10")
    else:
        print("reply already has §9")

    prog = io.open(PROG, encoding="utf-8").read().rstrip("\n").split("\n")
    ids = {l.split("\t")[1] for l in prog if l.count("\t") > 5}
    add = []
    if "P421" not in ids:
        add.append(row("P421", "B10环境与版本",
                       "A0 实测无收益：dp4a 换 v_dot4_i32_i8 后，10.8K prefill 差 0.1%（CV 0.2%/0.0%）、"
                       "3.4K +0.8%（剔冷启动首条）、decode ms/窗 −0.0%，四个指标全在 2×CV 带内；"
                       "由此同步否掉 B3 的前提（decode 整数点积不是 ALU-bound）",
                       "count", "DONE_NEG",
                       "机制：iq_kernels 的 dp4a 落在 Q2/Q3/IQ trellis 类型（:103），不是我们的 Q4_K；"
                       "decode 算力利用率 0.6%（236 MMAC/token @ 60 tok/s）⇒ 28→1 条指令看不见。"
                       "A0 保留（逐位不变且是 B1/B2 前置），但**不记收益**",
                       "P419",
                       "v_dot4_i32_i8|不带|Q2/Q3/IQ"))
    if "P422" not in ids:
        add.append(row("P422", "B8工程",
                       "事故：A/B 窗口把 config 的 exe 写成宿主路径，容器 exec 失败进入 restarting，"
                       "生产停机约 2.5 min（06:03:46–06:06:0x），已手工还原",
                       "count", "DONE",
                       "三个缺陷：① exe 必须写容器路径 /data/bin/<名>；② restore 不校验 md5 且被后续流程覆盖；"
                       "③ trap 收 TERM 后 return 导致脚本继续跑、把生产二进制当候选测。"
                       "已修：md5 校验 + sudo 重试 + 中止；TERM 分支 exit 130；每臂预热 + 3 次重试 + 一次性盐值",
                       "P421",
                       "restarting|容器路径|预热"))
    if add:
        io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(prog + add) + "\n")
        print("ledger +%d" % len(add))
    else:
        print("ledger has P421/P422")

    plan = io.open(PLAN, encoding="utf-8").read()
    if "**补充 11（A0 实测：零结果，并同步否掉 B3）**" not in plan:
        blk = ("\n**补充 11（A0 实测：零结果，并同步否掉 B3）**：dp4a 换 `v_dot4_i32_i8` 后，10.8K prefill 差 "
               "**0.1%**（CV 0.2%/0.0%）、3.4K +0.8%（剔冷启动首条）、decode ms/窗 −0.0%，四指标全在 2×CV 带内。"
               "机制：`iq_kernels.cu:103` 的 dp4a 只服务 Q2/Q3/IQ trellis 类型（我们是 Q4_K），"
               "而 decode 算力利用率 0.6% ⇒ 28→1 条指令在两个相位都看不见。"
               "**推论：B3（HC q8_1+dp4a）与 MMVQ 同族，前提同步不成立，不再占窗口**。A0 保留（逐位不变、"
               "是 B1/B2 的前置），但不记收益。\n")
        i = plan.rfind("### 回写 · W1036")
        j = plan.find("\n### 回写 ·", i + 10)
        if j < 0:
            j = len(plan)
        plan = plan[:j] + blk + plan[j:]
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
        print("plan +补充 11")
    else:
        print("plan has 补充 11")

    mem = io.open(MEM, encoding="utf-8").read() if os.path.isfile(MEM) else ""
    if "A0 实测" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("- A0 实测 **零结果**（10.8K prefill 差 0.1%，CV 0.2%/0.0%）⇒ decode 整数点积不是 "
                     "ALU-bound，**B3 前提同步作废**。A0 保留但不算收益。\n"
                     "- 事故：A/B 窗口把 config 的 `exe` 写成宿主路径 ⇒ 容器 restarting，生产停 2.5 min。"
                     "规矩：**配置里只写容器路径**；restore 必须 md5 校验；TERM 分支要 exit；"
                     "每臂先预热、窗口内用一次性盐值防 prompt cache。\n")
        print("memory appended")


if __name__ == "__main__":
    main()
