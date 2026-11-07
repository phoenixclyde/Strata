# -*- coding: utf-8 -*-
"""Append W863's new ledger rows: the spec-min-p negative, and the two real targets."""
import io
import shutil

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
shutil.copy2(P, P + ".w863c")

lines = io.open(P, encoding="utf-8").read().split("\n")
# keep the trailing empty element
while lines and lines[-1] == "":
    lines.pop()

existing = {ln.split("\t")[1] for ln in lines if "\t" in ln}

rows = [
    ("B1参数轴", "R24",
     "草稿链长度：--spec-min-p 0.40 是否比 0.70 快",
     "W863 §5", "count", "1", "1", "DONE_NEG",
     "四臂交错（0.70/0.40/0.70/0.40），每臂 3×480 tok 固定贪心。**打平**：48.9 vs 49.0 tok/s；"
     "但草稿/窗口从 0.78 拉到 1.43、接受率 86%→66%、tokens/窗口 1.73→1.98 ⇒ 窗口开销跟着 T 一起涨。"
     "外证同形：vLLM 在 MI300X 用 EAGLE-3 实测 N=1/3/5/7 吞吐比 0.71/0.99/**1.18**/1.17、接受率 86.3%→46.5%；"
     "arXiv 2610.34440 证 MoE 去重只在 5–8 token/pass 才赢。⇒ 0.70 已在甜区，不要再投这个方向",
     "W863-4"),
    ("B1参数轴", "R25",
     "HC（hyper-connection）读：6.89 ms 搬 644 MiB = 98 GB/s，只有峰值的 14%",
     "W863 §2", "count", "1", "0", "OPEN",
     "相位表里 `hc0/hc1 norm+down+up` 合计 6.89 ms/窗口，是全表**最差的带宽**（head 搬同样字节只要 1.73 ms）。"
     "同一对矩阵在孤立微基准（ncols=2）只要 14.7+13.7 µs/层 ×48 ≈ 2.7 ms ⇒ 生产比微基准慢 2.5×，"
     "开销在分步/同步/发射而非 kernel。**上限 5 ms/窗口 ≈ 11% 墙钟**，是单流 decode 的第一靶心",
     "W863-5"),
    ("B6判定探针", "R26",
     "专家读（VRAM hits 14.3 ms/窗口，占 32%）的有效带宽从未算过",
     "W863 §2", "count", "1", "0", "OPEN",
     "相位表 `VRAM hits 10.51 + waitB 2.84 + PCIe grp 0.94 = 14.3 ms` 是窗口里**最大的一块**，"
     "但只有时间没有字节。做法：路由轨迹 × native_experts.txt（每专家 3.13 MB）逐层枚举，"
     "再乘实测带宽 ⇒ 得到和 R22 同规格的「每窗口专家字节」。纯读，零干扰",
     "W863-6"),
]

for r in rows:
    if r[1] in existing:
        continue
    lines.append("\t".join(r))

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

for ln in io.open(P, encoding="utf-8").read().split("\n"):
    f = ln.split("\t")
    if len(f) > 9 and f[1] in ("R22", "R23", "R24", "R25", "R26"):
        print("%s\t%s\tcols=%d" % (f[1], f[7], len(f)))
