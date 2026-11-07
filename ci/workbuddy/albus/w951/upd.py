# -*- coding: utf-8 -*-
"""W951: R84 gets the root-cause fix; R91 carries the full porting plan (P1-P6)."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

R84_ADD = (" 【W951 根因已定位并修复 2026-11-04 16:2x｜A 级，全部实跑】"
           "①最小复现 probe1（1 块/K=256/单线程）：ratio 恰好 100 ⇒ host 参考多乘一次激活 scale，kernel 公式本身对；"
           "②在 M=64 版加 **host 模拟**（同一循环同一公式、不用 GPU）：HOST-SIM ratio **0.9976**、HOST-SIM-DOT8 ratio **1.0365** ⇒ 公式与数据全对；"
           "③与 kernel 的唯一差别 = **缺 warp 归约**（32 lane 各写同一个 y 位置、互相覆盖，只剩 1/32 的 K）；"
           "④补 `__shfl_down_sync` 后重跑：**dp4a rel_l2 0.00319 / dot8 0.06481**（修复前 0.99481/0.99590）。"
           "**新结论**：int4 激活的精度代价是 int8 的 **20 倍**（0.0032→0.0648），这是 W4A4 的真实代价；"
           "原型吞吐 dp4a 0.47 / dot8 0.35 TMAC/s **无效**（瓶颈是 8 warp 重复读整行权重 = 8x 流量，不是 dot 指令）。")

R91 = ("**W951 立（2026-11-04 16:2x，机主「我要完整的 dot8 移植方案，你列一个 R」）**。与 R84 分工：**R84 = 内核原型与验证（已完成 P0）**，"
       "**R91 = 接进生产 MMQ 的六阶段**。完整方案见 `W951 §4`。"
       "**P1 量化器**：float→int4（每 32 值 scale + **Σa** 写进 block 头），与 `quantize_mmq_q8_1` 并列，env `STRATA_MMQ_W4A4=1`；判据：与 CPU 参考逐元素一致。"
       "**P2 tile 布局**：`x_qs` int8→int4（**LDS 减半**），改 `mmq-load-tiles.cuh` 激活侧与 `mmq.cuh` 尺寸常量；判据：`prefill_mmq_tab_test` 在新基准下仍逐位。"
       "**P3 vec_dot**：新增 `vec_dot_q4_K_q4_impl_mmq`（`sdot8(q^0x8…,a)+8Σa`，min 项乘 Σa）；判据：ISA 断言 Q4_K 实例内 `v_dot4` **减半** 且 `v_dot8` **>0**。"
       "**P4 精度门**：`W913` logits 口径 KL ≤0.005、argmax ≥99%（分辨率 0.0032）；**rel_l2 0.0648 预示可能过不了 ⇒ 这一步决定生死**。"
       "**P5 A/B**：prefill 六长度档（6.4K/16K/32K/64K/130K）+ decode，`0 reused`，`|Δ|≥2×CV`；端到端上限仅 **2.05%**（W943），压在 3.2% 门之下。"
       "**P6 回滚**：`STRATA_MMQ_W4A4=0` 一行回退 + 镜像 `.new`+`mv`；演练一次。"
       "**诚实预判**：P4 大概率是终点（int4 激活精度 + 2.05% 上限）；但按机主要求按序实测，P4 不过即停，不做 P5。"
       "**顺序不许跳**：P1（零停服单测）→ P3 的 ISA 断言（最早看到 v_dot8 出现）→ P4 精度门 → 才谈 P2/P5。")

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R84":
            f8[8] += R84_ADD; changed.append("R84"); ln = "\t".join(f8)
    out.append(ln)

while out and out[-1] == "":
    out.pop()
out.append("\t".join(["B5本机缺口", "R91",
                      "dot8 生产接入（P1 量化器 / P2 int4 tile / P3 vec_dot / P4 KL 门 / P5 A/B / P6 回滚）：把 W4A4 + v_dot8 接进 Q4_K 的 MMQ",
                      "W951 §4", "count", "1", "0", "OPEN", R91, "W951;W947;W943"]))
out.append("")

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed, "+ R91")
