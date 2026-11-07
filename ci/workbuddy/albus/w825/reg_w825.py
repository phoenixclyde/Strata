# -*- coding: utf-8 -*-
"""W825：落账下一轮候选/排除项，并修正 4 条状态失真的旧项。"""
import csv, os

P = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "params", "PARAM_REGISTER.tsv")
P = os.path.abspath(P)
rows = list(csv.reader(open(P, encoding="utf-8"), delimiter="\t"))
hdr, body = rows[0], [r for r in rows[1:] if r and r[0].strip()]
ids = [r[0] for r in body]
print("before:", len(body), "rows; last ids", ids[-4:])

NEW = [
    # id, scope, name, value, family, status, requires, conflicts, synergizes, evidence, verdict
    ["P160", "engine", "tools/calibrate.py（官方硬件标定）", "python3 tools/calibrate.py <cfg.json>",
     "measurement", "PENDING",
     "独占 GPU（停生产）+ 副本配置（它会写回）", "—",
     "--pcie-frac / --spec-min-p / --pool-workers / --adapt-* / STRATA_SH_STREAM",
     "上游 0.2.7 自带 `tools/calibrate.py`（`calibrate.py:1-33`），一次标定六类硬件相关项；"
     "判据 `MIN_GAIN=0.03` 且要求「交错重测每轮都赢 + 中位超 3%」（`:49, :180`）；"
     "`--pcie-frac`/`--spec-min-p`/`--prefill-pipe` 通过 per-request `strata_tune` 在**单实例内**测多组，"
     "`--pool-workers`/`--adapt-*`/`SH_STREAM` 每个值需重启。**本机从未跑过**。",
     "**P0，最高优先**。理由：我们的 5 个硬件相关参数全部沿用「Ryzen 5 7600 + RTX 5070 + PCIe 5」测出的默认/手选值，"
     "而本机是 Xeon E5-2696 v4（22C/44T）+ DDR4-2133 + **PCIe 3.0 x16**，前提差两代。"
     "这是唯一一个「不新增功能、但把所有默认值落到真实基线」的动作。"],

    ["P161", "env", "STRATA_SH_STREAM", "未设（HIP 默认 off）",
     "decode", "CANDIDATE",
     "无（输出相同）", "—", "P160（calibrate 会测它）",
     "`calibrate.py:24-28` 逐字：`Off by default on HIP (#816: an RX 6800 on Windows and 4x R9700 decode 12-45% faster "
     "without it), but the same card family on another PC goes the other way (#1272: 2x RX 6900 XT on Linux, 6-11% faster "
     "with it), so it is measured here, per PC` 且 `The output is identical either way (same token ids)`。",
     "**未测**。这是账上**唯一一个「零质量风险 + 上游实测 12-45% 幅度」**的项，而我们恰好是从没测过的 AMD 机型。"
     "必须用 decode timing 的 `ms/window` + ABBA 交错判，不能看单次 tok/s。"],

    ["P162", "args", "--adapt-every / --adapt-swaps / --adapt-decay", "未设（默认层）",
     "decode", "CANDIDATE",
     "无", "—", "P160",
     "`calibrate.py:18-22` 逐字：`A PC whose CPU reads the missed experts slowly (DDR3, ~24 GB/s) gains from swapping "
     "more: 160 swaps every window measured +7.9% over the default tier on a Xeon E5-2673 v3 (DDR3) with an RTX 4060 Ti "
     "on PCIe 3.0 x8 (Q2_0; with the swaps taking effect a window later, #764)`。",
     "**未测**。上游给出先验的那台机（老 Xeon + DDR3 + PCIe 3.0 x8）与本机（Xeon E5-2696 v4 + DDR4-2133 + PCIe 3.0 x16）"
     "画像最接近，是本轮最值得试的一组。槽位覆盖率已从 40% 降到 30.7%，miss 更多 ⇒ 自适应层理论上更值。"],

    ["P163", "env", "STRATA_TSUM", "1",
     "prefill", "REJECTED",
     "V2K 路径（gu_type 12/13）或 S26 路径（gu_type 21）", "—", "—",
     "gfx906 可用（`s26_tsum.cuh:12-27` 的 fallback 是 `__shfl_xor_sync`，不依赖 gfx10+ 的 permlanex16/DPP）。"
     "但上游自家 harness 在 `iq_kernels.cu:6270-6272` 逐字写：`(+ down rows' items spread evenly over the lanes, one load "
     "group: bitwise, harness 1.09-1.12x vs 1.03-1.06x; **the same for gate / up was 0.6-0.8x**)`。",
     "**不采纳**（零成本排除，不占停机窗口）。它只对 down rows 有利，对 **gate/up 反而 0.6-0.8x**，"
     "而 gate/up 是本机最大相位（22.7%）。两条合起来必然亏。"],

    ["P164", "env", "STRATA_EXPERT_NIBBLE（4-bit gate/up 槽位）", "—",
     "decode", "N/A",
     "STRATA_EXPERT_NIBBLE_BUILT（= CUDA build + STRATA_EXPERIMENTAL_SM60）", "—", "—",
     "`iq_kernels.cu:4616` 逐字：`Built only with STRATA_EXPERT_NIBBLE_BUILT (a CUDA build with STRATA_EXPERIMENTAL_SM60); "
     "elsewhere a gu_nib layout`；`:6259-6263` 在无内核的构建里直接 "
     "`4-bit gate/up slots are not built into this engine` + `exit(1)`。",
     "**结构性不可用**（与 `STRATA_DENSE_MMQ`、`STRATA_EXPERT_V2K` 的 gfx12 分支同一类）。"
     "但它揭示的方向值得记：若能把专家 gate/up 压成 4-bit，blob 减半 ⇒ 槽位从 7551 翻到约 15000、覆盖率 30.7%→61%。"
     "上游只在 SM60 上做了，gfx906 要自己写内核。"],

    ["P165", "engine", "数值债账本（6 个改 bits 的开关，均未量 KL）", "见 evidence",
     "measurement", "REFERENCE",
     "STRATA_PREFILL_CPU_SHARE=0（否则底噪≈效应）", "—", "P158",
     "全部在场且源码逐字声明改数值：①`STRATA_ROUTE_TAIL_SKIP=7`（`expert_source.cpp:4887` "
     "`changes the output … its contribution is zero, without renormalisation`）"
     "②`STRATA_HIP_PROMPT_F16=1`（`gemm.cu:588` `changes the prompt path's numbers (an FP16 rounding)`）"
     "③`STRATA_MMQ_KQ=1`（`mmq_kq_abi.hpp:22` `other rounding than the FP16 path`）"
     "④`STRATA_SELECT_SIMT=1`（`qsa_select.cu:2256` `its sum order differs`）"
     "⑤`--kv k8v4`（`generate.cpp:908` `INT8 K (exact) + rotated Q4_0 V`）"
     "⑥`STRATA_HC_Q8=1`（`arch_defaults.hpp:8` 上游分类 `rounding-level, KL-gated`）。"
     "**六项叠加后从未量过总量**。",
     "**P1**。设计：不做 6 项×2 臂（12 次启动），而是先 2 臂量**总量**（E0 全量 vs Eall 最小近似），"
     "总量 KL<0.02 则全部结清；>0.05 再二分（「专家路径 RT_SKIP」vs「数值路径」）。"
     "上游对单 RT_SKIP 给 0.003-0.006，本机从未验证。"],

    ["P166", "engine", "W825 计划（`deploy/W825_ROADMAP.md`）", "P0..P4",
     "governance", "REFERENCE",
     "—", "—", "P160/P165",
     "三轮复盘 + 四个结构性问题（参数从未标定 / 数值债未量 / 测量方法学 / 登记表失真）+ 分级计划 + 明确不做清单。",
     "执行顺序：P4 治理（零停机）→ P0 calibrate（30-45 min，可并入 P1 同一窗口）→ P1 数值债总量（12-15 min）"
     "→ P2 独立速度项 → P3 移植 #3220。**P141/P147/#4105/TSUM/NIBBLE 已明确不做**（理由见文档 §5）。"],
]

# 去重：已存在同 id 就跳过
added = []
for r in NEW:
    if r[0] in ids:
        print("skip existing", r[0])
        continue
    body.append(r)
    added.append(r[0])

# 修正 4 条状态失真的旧项
FIX = {
    "P55": ("CANDIDATE", "ADOPTED", "（W825 治理）生产 env 实际已开 `STRATA_GFX906_ATTN_QUERY_SWIZZLE=1`，状态由 CANDIDATE 更正为 ADOPTED。"),
    "P56": ("CANDIDATE", "ADOPTED", "（W825 治理）与 P156 重复登记；实际已开且已验逐位等价（P158），状态更正为 ADOPTED，以 P156 为准。"),
    "P105": ("CANDIDATE", "ADOPTED", "（W825 治理）生产 env `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.5.0.txt` 实为在用，状态更正为 ADOPTED。"),
}
fixed = []
for r in body:
    if r[0] in FIX:
        old, new, note = FIX[r[0]]
        if r[5].strip() == old:
            r[5] = new
            r[10] = (r[10] + " " + note).strip()
            fixed.append(r[0])

with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(hdr)
    w.writerows(body)

print("added:", added)
print("fixed:", fixed)
print("after:", len(body), "rows; cols_ok:", all(len(r) == 11 for r in body))
