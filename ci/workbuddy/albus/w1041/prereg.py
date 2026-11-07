#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: pre-register the reopened R103 (before running anything)."""
import io

P = r"D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
NOTE = (
 "**W1041 立（机主 14:29「按 r104，重开 r103」）**。"
 "**为什么重开**：`P467` 把 attn 一支结案成「现有数值门不可测」——七组两两 KL 全在 0.0354–0.0465，"
 "而探针证明读法/算术只差 1e-6 量级 ⇒ 当时判的是「门坏了」，不是「改动坏了」。"
 "**R104 给出了替代取样面**：`STRATA_DUMP_FIRST_LOGITS` 的 float32 全词表 logits 可以直接 `cmp -s`，"
 "也能算 **max|Δlogit|**（单位 nats、可解释），KL 只是它的派生量。"
 "**设计（四臂，跑之前写死）**：A = `b12180`（k8v4）、B = `pa5` 无开关（**build floor**，必须与 A 逐字节相同）、"
 "C = `pa5` + `STRATA_GFX906_ATTN_DP4A=1`（`P452` 测到 attn −11.3% / 整条 −1.78% 的那一支）、"
 "D = `b12180` + `--kv f16`（**锚**：量出我们**已经在跑**的 k8v4 自己的数值成本，单位与 C 相同）。"
 "**判据（预注册）**：① A≡B 逐字节，否则 C 的差异里混着 build 差异、整轮作废；"
 "② 报 C−A 与 D−A 的 max|Δlogit| / KL / top-1（四个长度 1000/8000/16000/20000）；"
 "③ **C 的成本 ≤ D 的成本即采纳**——D 这一档我们已经在生产里跑了几个月，拿它当预算线比拿 0.0139 当绝对门槛更站得住；"
 "另加 top-1 ≥ 99% 的硬条件；④ 若 C 反超 D，则判否并把差距记进 `R103`。"
 "**外证（本轮上网核，用于校准尺度而不是代替测量）**：同族 llama.cpp 实测 KV q8_0 vs f16 = "
 "**平均 KLD 0.000587 / top-1 98.76%**（rx7900xtx `kv-quality.md`）；另一份实测 K=Q5_0 ≈ **0.008**、"
 "K=Q4_0 **>0.03 即「破坏」**（sergiiob）；运维建议 **KL>0.05 视为可感知退化**（hotdry）。"
 "**关键不匹配**：我们 `P04` 记录 k8v4 vs f16 = **KL 中位 0.0704**，比社区的 q5_0 大一个量级 ⇒ "
 "**我们的 KL 轴与社区不是同一把尺子**，所以本轮必须自带锚（臂 D），不能直接引用 0.0139 或 0.05。"
 "**停机**：一次停/起 + 四臂（估 8–12 min）。"
)
row = ["B5本机缺口", "P497",
       "**R103 重开（attn 一支）**：判决改用 R104 的取样面——fp32 全词表 logits 直比 + **自带锚臂**（k8v4 vs f16），"
       "不再拿 0.0139 的 KL 摘要当第一判据",
       "W1041", "count", "1", "0", "OPEN", NOTE, "P467;P452",
       "KW:R103 重开|全词表|锚臂"]
assert len(row) == 11, len(row)
for i, x in enumerate(row):
    assert "\t" not in x, (i, x[:40])

lines = io.open(P, encoding="utf-8").read().splitlines()
assert not any(l.split("\t")[1] == "P497" for l in lines if l.count("\t") >= 9)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines + ["\t".join(row)]) + "\n")

tot = done = 0
for l in io.open(P, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
print("pre-registered OK; totals", tot, done)
