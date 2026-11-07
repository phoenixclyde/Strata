# -*- coding: utf-8 -*-
"""把 W778 的 12 项扫描结论一次性登记为 P80（避免以后重试）。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_p80_" + time.strftime("%Y%m%d_%H%M%S"))

EV = (
    "【W778 2026-10-24 全测】`src/core/arch_defaults.cpp` 里 gfx1151/gfx12 的默认表共 12 项**通用 env**，"
    "本机逐个强制开后实测（基线 = 0.2.3+HC_Q8，M 档 prompt 486.6 / decode 61.3，唯一 nonce、reused=0、3 runs）："
    "Q8_PACKED +0.02/+0.49、Q6_PACKED -0.08/+0.33、MMVF_ROWS -0.08/+0.16、LFUSE +0.23/-0.16、"
    "QFUSE -0.08/+0.33、PLE_BATCH +0.02/+0.33、TOPK_REG_MIN_BLOCKS -0.08/+0.16(%) => **7/7 全在 +-0.5% 内，无效**。"
    "机理：这批是给 RDNA3/4（wave32/大 L2/新指令）写的调度与打包优化，gfx906 走 `IS_GCN` 分派吃不到。"
    "**5 项无代码路径**：GDN_HEAD/GDN_PP/GDN_CONVL2/GDN_NOY/GDN_SPLIT（pack index.txt 里 `gdn` 出现 0 次，"
    "只有 ssm 252/conv 38 => 模型无 GDN 层）、CVEC_FUSE（不用 control vector）。"
    "**3 项硬不兼容**：RDNA3/4 MMQ（mmq.cuh:229 按硬件 cc 分派，common.cuh:71 VEGA20=OFFSET_AMD+0x906 先命中 IS_GCN，无 env 可改）、"
    "hipBLASLt 调优表（CMakeLists:729 只在 STRATA_ENABLE_HIP 下链接 roc::hipblaslt，本机是 STRATA_HIP_GFX906 另一后端 => 二进制里没有）、"
    "Metal/SYCL（不同后端）。历史已判：EXPERT_V2(P36)/TSUM(P37)/SH_STREAM(P40)/ATTN_LANECELL(W6)。"
)

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
if any(l.startswith("P80\t") for l in lines):
    print("P80 exists, skip")
else:
    idx = max(i for i, l in enumerate(lines) if l.startswith("P7"))
    lines.insert(idx + 1, "\t".join([
        "P80", "ENV", "gfx1151/gfx12 默认表 12 项（gfx906 强制开）", "(不设)", "all", "REJECTED",
        "-", "-", "-", EV, "全测：7 项有路径全无效(+-0.5%)，5 项无代码路径，3 项硬不兼容 => 一律不设",
    ]))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("P80 added at line", idx + 2)

# 校验列数
for ln in io.open(REG, encoding="utf-8-sig").read().splitlines():
    if ln.startswith("P80\t"):
        print("cols", len(ln.split("\t")), "ev_len", len(ln.split("\t")[9]))
