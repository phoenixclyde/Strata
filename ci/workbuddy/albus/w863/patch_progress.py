# -*- coding: utf-8 -*-
"""Update R22 / R23 rows in PROGRESS.tsv (TAB separated). Backs up, then verifies."""
import io
import shutil
import sys

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
BAK = P + ".w863bak"
shutil.copy2(P, BAK)
print("backup ->", BAK)

lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
changed = []
for ln in lines:
    f = ln.split("\t")
    if len(f) > 9 and f[1] == "R22":
        f[7] = "DONE"
        f[8] = ("**W863 已重算（`deploy/W863_R22_DENSE_BYTES.md`）**：从 GGUF 张量表逐层枚举，"
                "GDN 层 6 张量 63.42 MiB、QSA 层 7 张量 55.45 MiB（36/12），"
                "与引擎日志 499 矩阵/3619.14 MiB 逐字节对上（301 native 2975.00 + 194 HC 644.14 + 4 scratch）。"
                "每窗口 dense Q8_0 读 = 4263.24 MiB（native 2975.00 + HC 644.14 + **head 644.10，两轮都漏**）；"
                "相位实测占 16.99/44.98 ms = **37.8%**（不是 59%，也不是 16%）。"
                "除数三分开：每窗口 4263.24 MiB / 每接受 token 2382 MiB（÷1.79）/ 每列 1886 MiB（÷2.26）。"
                "embedding 644 MiB 在 host 属实，但每 token 只 gather 一行 2720 B，不构成每 token 读")
        f[9] = "W863-1"
        changed.append(f[1])
    elif len(f) > 9 and f[1] == "R23":
        f[8] = ("已实测未部署；**W863 补**（`deploy/W863_WAVE_ROWS_TABLE.md`）：全表扫完 9 形状 × ncols 1..8 × R∈{1,2,4} = 216 格。"
                "树里的公式有真缺陷——ncols=1 选 R=4，整层 **0.982×（倒扣）**，out 单矩阵慢 10.2%；"
                "另有多格比最优慢 8–95%。实测表已生成（`albus/w863/measured_table.cpp.txt`）："
                "整层 n1 1.000× / n2 1.156× / n3 1.829× / n6 1.593×。"
                "**关键**：生产典型验证窗口是 **T≈2 不是 6**（相位 67.8 µs/层 ↔ bench n2 69.3；drafts 0.97–1.26/窗口；"
                "`spec-min-p 0.70` 在 generate.cpp:13992 截断草稿链）⇒ 墙钟收益仅 **≈2.9%**（T=6 时才 6.0%），"
                "低于「引擎级 A/B 只判 ≥5%」的地板。建议与窗口长度一并批处理")
        f[9] = "W863-2"
        changed.append(f[1])
    out.append("\t".join(f))

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("rows changed:", changed)

# immediate verification, separate read
for ln in io.open(P, encoding="utf-8").read().split("\n"):
    f = ln.split("\t")
    if len(f) > 9 and f[1] in ("R22", "R23"):
        print("%s\t%s\tcols=%d\t%s" % (f[1], f[7], len(f), f[9]))
