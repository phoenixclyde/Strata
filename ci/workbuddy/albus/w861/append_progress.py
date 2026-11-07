# -*- coding: utf-8 -*-
"""把 W861 的条目追加进 PROGRESS.tsv（TAB 分隔，UTF-8）。"""
import io

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"
rows = [
    ("B6判定探针", "M8", "真实流量的**时间加权**基线（条数加权会骗人）", "W861 §1", "count", 1, 1, "DONE",
     "总时间 107678.8 s = read 48001.0 (44.6%) + gen 59677.8 (55.4%)。0–128 档 766 条(14.3%) 只占 read 的 **1.2%**、总时间 3.3%；64K+ 档 1598 条(29.8%) 占 read 41.0% + gen 71.9% = **总时间 58.2%**。decode ms/token 在 19.0–25.1 之间、不随 ctx 与生成长度变化（65 倍上下文差 <5%）⇒ R19/M3 降级、decode 成第一战场。注：跨 24 天/665 次启动，当前版本(0.2.9-101)样本仅 8 条，结构稳定但绝对值宜以重启后为准",
     "P241"),
    ("B1参数轴", "R22", "decode dense GEMV 的带宽达成率只有 22–75%（head 已 98%）", "W861 §3", "count", 1, 0, "OPEN",
     "**新的第 1 序**。b6_mmvq_bench + q8_gemv_bench 实测（GPU events、500 次中位、权重超 L2 冷读）：单层 9 个矩阵合计 106.5 MB / 279.5 µs ⇒ ×48 = 13.42 ms，加 head 0.92 ms = 13.66 ms = **23 ms 的 59%**。分布：shared gate/up 22%、QSA k/v 29%、shared down 32%、HC up/down 35%、GDN gate 39%、GDN qkv 57%、GDN/QSA out 69%、QSA q 75%、**head 98%**。若非 head 项全部提到 75%（533 GB/s）⇒ 200 µs/层、9.6 ms，省 3.8 ms/token = **总时间 9.1%**。方向：split-K / 提高 wave 并行 / dwordx4 / LDS 排布 —— G8·G9 第一次有量化靶心。判据：微基准单层 ≤230 µs；落产须过提示侧 KL（另一求和顺序）",
     "W861-3"),
]
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    for r in rows:
        fh.write("\t".join(str(x) for x in r) + "\n")
print("appended", len(rows))
