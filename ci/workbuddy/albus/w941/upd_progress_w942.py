# -*- coding: utf-8 -*-
"""W942: close R61 (DONE, A-level PMC) and R60 (DONE_NEG on the VALUBusy gate); append evidence to R84.
Line-wise edit: every other line stays byte-identical."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

R61_EV = (" 【W942 结题 2026-11-04 14:2x｜A 级】工具门：rocprofv3 **当启动器**可用（W941 证），"
          "独立可执行 build-r28/kq_bench（16 专家 x 1024 token = **16,384 rows**，Q4_K gate/up [1280,2560]，"
          "链生产同一份 libstrata_mmq.a）自然退出 ⇒ csv 落盘。"
          "**实测 VALUBusy = 67.1%**（kernel mul_mat_q<(ggml_type)12, 64, false>，J=64，4 次 launch 28.2 ms，7.05 ms/次）；"
          "quantize_mmq_q8_1 72.7%（占 1.4%）。事件计时 7.56/7.79/7.74 TMAC/s = 微基准峰 21.52 的 **36%**。"
          "**VALU 67% 忙 + 供给率 36% ⇒ VALU 时间花在辅助指令**（与 W924 的 dp4a 占 53.3% 吻合），不是取数排队。")

R60_EV = (" 【W942 判死 2026-11-04 14:2x｜A 级】R61 实测 **VALUBusy 67.1% >= 40% 门** ⇒ stream-k 解决的"
          "『in-flight bytes 不足』不是瓶颈，改 K 切分不减少 VALU 指令数 ⇒ **不做**。"
          "W923 的 50-65% 算术预判方向对、数值低估（真实内核指令配比比微基准更差）。")

R84_ADD = (" 【W942 依据升级 2026-11-04 14:2x】R61 实测 VALUBusy **67.1%**（A）+ W924 dp4a 段占 **53.3%**（B）⇒ "
           "dot8 把该段减半 ⇒ 总指令 −26.7% ⇒ kernel 上限 **−17.9%** × gate/up 占 prefill 20.4% = **端到端 −3.65%**，"
           "略高于 2xCV 门 3.2%，且分子分母都是实测。**否证条件**：若 R74 过门后 ISA 里 v_dot4 未减半 / v_dot8 未出现 ⇒ 路径没走到；"
           "若 kernel 时间不降 ⇒ VALU 不是唯一瓶颈，按 W904 先例判否，不再追加变体。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" not in ln:
        out.append(ln)
        continue
    f8 = ln.split("\t")
    if len(f8) >= 9 and f8[1] == "R61" and f8[7] != "DONE":
        f8[7] = "DONE"; f8[8] = f8[8] + R61_EV; changed.append("R61->DONE"); ln = "\t".join(f8)
    elif len(f8) >= 9 and f8[1] == "R60" and f8[7] != "DONE_NEG":
        f8[7] = "DONE_NEG"; f8[8] = f8[8] + R60_EV; changed.append("R60->DONE_NEG"); ln = "\t".join(f8)
    elif len(f8) >= 9 and f8[1] == "R84":
        f8[8] = f8[8] + R84_ADD; changed.append("R84+ev"); ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))

print("changed:", changed)
