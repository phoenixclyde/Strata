# -*- coding: utf-8 -*-
"""登记 W784 的两条收口：
P84（REF）= routeK/llama.cpp 全线清点的收口行（关闭项与理由一行收纳）
P87（REF）= E0 分阶段归因基线（后续所有调优的上限依据）
"""
import io, time, shutil

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w784_" + time.strftime("%Y%m%d_%H%M%S"))

EV84 = ("【W784 2026-10-25 全覆盖清点收口】覆盖 routeK 202 个 gfx906 相关文件、45 个自有开关、13 份 DEVLOG(9,900 行)、"
        "llama.cpp pin 3cf03257 与 master 36e36e63 的 68 个差异文件。按 E0 实测上限（P87）逐项裁决："
        "① 关闭（附实测理由）：FA kernel 本体（稠密 vs 我方块稀疏、V int4 vs fp16、自有 pools vs paged）、"
        "GQA 打包（我方已按 G=12 更彻底）、KV 切分合并（已有 split+merge）、gather 融合/paged 直读/persist（结构不适用）、"
        "topk 单波内核（我方 router_top10_wave_kernel 31VGPR/priv0 已具备，它自己的 LDS 版 35.5us 与 width-64 版都更慢）、"
        "MoE 解码六项重排（V1 2.2x 慢/NPT=2 墙钟中性/V3/V4 DEAD-END/gemm2 NEUTRAL/K-split 2.4-4.2x 慢）、"
        "MoE 预填 BM 分档（我方预填 GPU 0%，前提不成立）、双缓冲预取（它实测 256VGPR+重溢出 5.8x 慢）、"
        "dense W4A16 自制 GEMV（87-97% 地板）、lm_head 杠杆（已在地板 3114 vs 3128us）、"
        "dot2/bf16（gfx906 无 bf16 dot，我方非 fp16）、"
        "routeK CPU MoE（dynamic_4bit_int_moe_cpu.cpp 逐字 only available on AArch64，x86 是桩）。"
        "② 保留：F1 fused_gr::gr_down_v3 溢出治理（256VGPR+956B，HC 12.8%）、F2 kv-grow(+1487 槽，专家流 32.2%)、"
        "F3 路由 fp64（7.0%）、F4 dense Q8 GEMV 按形状扫（11.2%）、F5 mmvq upstream 布局（从无计时）。"
        "③ 降级：Q8 量化 Q+dp4a / DPP 归约 / v_exp_f32（注意力一族合计仅 6.7%，实得 <=1%）。"
        "④ 纠错两条：Strata hip_compat 虽无 gfx906 dp4a 分支，但反汇编 native_mmvq 27,384 条、iq_kernels 43,110 条 v_dot4，"
        "编译器已吃成硬件指令；llama.cpp 两版 grep gfx906 逐行相同（仅行号位移），GCN tile 表未变 => 跟版无收益。")
NOTE84 = "收口：FA/MoE/topk/GEMV/llama.cpp 全线关闭，仅 F1-F5 保留（详见 W784）"

EV87 = ("【W784 E0 实测 2026-10-25】STRATA_DECODE_TIMING=1 + STRATA_VERIFY_PROFILE=1（generate.cpp:15208 那行）"
        "M 档 21,827 token、97 窗口稳态：74.76 ms/window = verify 56.36（GPU-reach wait 34.64 + per-layer host 18.83，其中 CPU 17.75）"
        " + commit/emit 0.05 + draft 7.04；GPU stages 合计 55.65 ms/window（verify 期间 GPU 占用 98.7%）。"
        "分布：专家流 17.94（VRAM hits 7.44 + waitB 6.49 + waitCPU 4.01）= 32.2%；HC 投影 7.15（hc0/hc1 down+up）= 12.8%；"
        "量化+dense GEMV 6.25 = 11.2%；router+plan+bell 3.87 = 7.0%；"
        "注意力一族 3.72（attention 2.11 + scores+topk 1.61）= 6.7%；其余 16.7 = 30.1%。"
        "用途：这是后续所有内核级改动的价值上限依据；任何声称能提升 decode 的改动，先对照此表算上限。"
        "注：打开计时后 decode_tps 由 63.0 降到 44.6（每请求一行 stderr），属测量开销，不是性能变化。")
NOTE87 = "E0 基线：专家流 32.2% / HC 12.8% / 量化+GEMV 11.2% / attention 6.7%"

rows = io.open(REG, encoding="utf-8-sig").read().splitlines()
rows = [ln for ln in rows if not ln.startswith(("P84\t", "P87\t"))]
new = [
    "\t".join(["P84", "REF", "routeK/llama.cpp gfx906 移植评估", "CLOSED", "-", "REFERENCE", "-", "-", "-", EV84, NOTE84]),
    "\t".join(["P87", "REF", "decode 分阶段归因基线", "E0", "-", "REFERENCE", "-", "-", "-", EV87, NOTE87]),
]
# P84 插在 P83 后；P87 放最后
out = []
for ln in rows:
    out.append(ln)
    if ln.startswith("P83\t"):
        out.append(new[0])
out.append(new[1])
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows:", len(out))
