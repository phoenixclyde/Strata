# -*- coding: utf-8 -*-
"""登记 P81：0.2.4.2（0.1.49.2）源码评估结论，避免下次重查。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_p81_" + time.strftime("%Y%m%d_%H%M%S"))

EV = (
    "【W780 2026-10-25 升版评估】上游 v0.2.4.2 tag（引擎 0.1.49.2，我们原 0.1.48.1）。"
    "**0.2.4 全系列对 Qwen 引擎没有发布新二进制**：release note 两处原文「every Qwen engine package stays as it was」"
    "「every engine package is still the 0.1.48 file, byte for byte」；新东西是 DeepSeek V4.1-Flash（独立包 strata-dsv41 0.1.49.x）。"
    "目录级 diff（build023 vs build024，排除 llama.cpp）：共 92 项，**引擎核心 src/ 只有 10 个文件，全部在 kernels/cpu/**"
    "（iq_avx2.cpp/.inl、iq_avx512.cpp、tq_*、native_expert.cpp、expert_layout.cpp）。"
    "iq_avx2_rows.inl 的实质改动是模板加 `bool EX = false`，源码注释逐字 'Without EX the order of the main engine's rows (unchanged)' "
    "=> 那批 CPU 加速（release note 说 decode +25%/prompt +26%）只走 EX=true，是 DeepSeek 的，Qwen 路径不变。"
    "dflash2.cpp / serve/telemetry.py / serve/web/app.js 与 0.2.3 **逐字节相同** => 遥测移植件原样复用(f045648a/a31f4544)，"
    "dflash2 的 STRATA_USE_HIP=1 补丁仍必须打（否则 gfx906 编不过）。llama.cpp pin 仍 3cf03257。"
    "基线（S/M/L，唯一 nonce、reused=0）：408.7/485.6/465.2 vs 0.2.3 的 410.2/486.6/465.5 = -0.37%/-0.21%/-0.06%，全在分辨率内 => 等价，"
    "已落生产（0.2.4），回滚位 strata166-407.bak023。"
)

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
if any(l.startswith("P81\t") for l in lines):
    print("P81 exists")
else:
    idx = max(i for i, l in enumerate(lines) if l.startswith("P8"))
    lines.insert(idx + 1, "\t".join([
        "P81", "REF", "上游 0.2.4.2 / 引擎 0.1.49.2 升版评估", "(不适用)", "load", "REFERENCE",
        "-", "-", "-", EV, "已升版落地；结论：Qwen 路径零变化，收益 0，仅为版本同步",
    ]))
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("P81 added")
for ln in io.open(REG, encoding="utf-8-sig").read().splitlines():
    if ln.startswith("P81\t"):
        print("cols", len(ln.split("\t")), "ev", len(ln.split("\t")[9]))
