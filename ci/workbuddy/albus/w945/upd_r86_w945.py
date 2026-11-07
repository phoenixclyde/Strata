# -*- coding: utf-8 -*-
"""W945: R86 evidence — source-level layout, PMC (MemUnitStalled 0.36%), ISA (29x 32-bit loads, 0x 128-bit)."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
ADD = (" 【W945 源码级 2026-11-04 15:3x】拿到 mx 的 8 个源文件（190 KB，~/strata166/ref/mx/）逐行对照："
       "①布局 = nibble 平面（16B/块，行 stride 去别名）+ 第五位平面（4B）+ half2{d,m} 平面（4B），合计 24B/块 = canonical，显存零增长；"
       "②`rp_traits<Q5_1>` 注释逐字点名 **the 640-column expert downs of Qwen3.8** —— 这个 trait 就是为我们的 down 做的；"
       "③`repack_q51_host` 只有 3 个 memcpy、**一个 bit 都不改** ⇒ 与 FEATURES 的 byte-identical 一致，不需要 KL 门；"
       "④移植面 = host repack(40 行) + `ggml_cuda_mmq_load_tiles_q5_1` 三平面取数(40 行) + expert_stride(3 行，数值不变 1,228,800)。"
       "**本机实测（A 级，停服独占）**：PMC `mul_mat_q<7,64,false>` VALUBusy **58.0%**、**MemUnitStalled 0.36%**（Q4_K 是 0.11%）"
       " ⇒ **MMQ 不是访存受限**，repack 只能靠少发 load 指令；ISA 该 kernel 1,301 条里 **global_load_dword 29 条、dwordx2/x4 各 0 条**"
       "（`bxi->qs` 落在 24i+8，编译器不敢发 128-bit）⇒ 对齐假设在指令层成立，repack 后应约 8 条 dwordx4（带 .cs）。"
       "**但 +84% 是 dense 27B 大 M 的读数，我们每专家仅 ~320 token，权重摊薄差一个量级** ⇒ 端到端预期下调为 **0 ~ -6.3% 未知**，"
       "唯一判法是 kq_bench 两臂 A/B：delta>=40% 动生产、<20% 判否、20-40% 记边际。")

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
