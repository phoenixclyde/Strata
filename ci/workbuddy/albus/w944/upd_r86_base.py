# -*- coding: utf-8 -*-
"""W944b: append the canonical baseline numbers to R86."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
ADD = (" 【W944 基线 2026-11-04 15:0x｜A 级】kq_bench 同形状对照（16 专家 x 320 token = 5,120 rows，生产同一份 libstrata_mmq.a）："
       "**Q5_1 down [2560,640] 1.53 ms = 5.47 TMAC/s（峰 25%）**、Q8_0 down 1.78 ms = 4.70（22%）、"
       "Q4_K gate/up 2.26-2.57 ms = 6.5-7.4（30-35%）⇒ **Q5_1 供给率最低**，与 mx 宣称的 +84% 同向"
       "（milpster 的 Q5_K 1.30 cyc/byte vs Q6_K 0.74 也是同一类结论：5-bit 系解包/缩放最重）。"
       "expert_bytes：Q5_1 1,228,800 / Q8_0 1,740,800 / Q4_K[1280,2560] 1,843,200 ⇒ repack 后 stride 变，moe_mmq_tab 的步进必须同步改。"
       "口径：三条都在生产运行中测（共享 GPU，Q4_K CV 偏大），只用于量级与对照，正式 A/B 要停服独占重测。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R86":
            f8[8] += ADD; changed.append("R86"); ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed)
