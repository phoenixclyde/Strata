#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W939: flip the 5 calculation-only verdicts back to OPEN, and add them to the plan queue."""
import io, os

D = "D:/workbuddy_space/strata_ws/deploy"
P = os.path.join(D, "PROGRESS.tsv")

REASON = {
    "R60": ("【W939 重开 2026-11-04 13:0x】原判「不做」的依据是 ki 的外部实测 + 我们用 ISA 反推的 VALU 81%，"
            "**本机从未运行过 stream_k=true 的二进制**（只有单编 rc=0）。依据级别 C（推算）⇒ 重开。"
            "最低结题：实验树 11 行翻 true → 换对象重链 → 32K/64K 各 3 rep（必须 0 reused）+ KL 门（≤0.005，分辨率 0.0032）"),
    "R61": ("【W939 重开 2026-11-04 13:0x】三次注入全部静默失败 ⇒ 判 DONE_NEG 等于「没测到」，依据级别 无数据。"
            "重开方式改为**不碰生产**：把 libstrata_mmq.a 链进独立驱动，在单独进程里 rocprofv3 采 VALUBusy/MemUnitStalled/FetchSize"),
    "R63": ("【W939 重开 2026-11-04 13:0x】原判依据是 W925 的 Amdahl 上限（端到端 1.74%），**一行代码都没改过**，依据级别 C。"
            "重开：readfirstlane 提 SGPR → 先断言 ISA 里 v_mul_lo_u32 显著下降（路径断言）→ 再跑 prefill A/B（2×CV）"),
    "R64": ("【W939 重开 2026-11-04 13:0x】原判依据是日志拟合 + 源码格式事实 + Amdahl，**改动从未编译**，依据级别 C。"
            "重开并窄化：只做 Q·K（k8v4 的 K 已是 int8，把 Q 量化成 int8 走 v_dot4；V 是 4-bit 确实用不上 dp4a），"
            "测 32K/131K 的 qsa attn 绝对 ms + KL 门"),
    "R72": ("【W939 重开 2026-11-04 13:0x】原判是容量换算（+145 槽 = +0.13pp），**一次重启都没做过**，依据级别 C。"
            "重开：--vram-reserve-mib 832→600 一次重启，读 cache 槽数 / 命中率 / decode tok/s；红线 VRAM free ≥ 300 MiB"),
}

rows = io.open(P, encoding="utf-8").read().split("\n")
out, flipped = [], []
for ln in rows:
    f = ln.split("\t")
    if len(f) == 10 and f[1] in REASON and f[7] != "OPEN":
        f[6] = "0"
        f[7] = "OPEN"
        f[8] = f[8].rstrip() + " " + REASON[f[1]]
        flipped.append(f[1])
    out.append("\t".join(f) if len(f) > 1 else ln)
io.open(P, "w", encoding="utf-8").write("\n".join(out))
print("flipped to OPEN:", flipped)

# ---------------- W832: 重开区 + 队列 ----------------
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()

anchor = "> **执行顺序（2026-11-04 11:3x 修）"
block = (
    "> **重开区（`W939` 2026-11-04 13:0x）**：以下 5 条的「不做」是算出来的、不是测出来的，已全部翻回 OPEN —— \n"
    "> **R60**（stream-k：VALU 81% 是 ISA 反推，二进制从未跑过）、**R61**（PMC：三次注入失败，等于没测到）、\n"
    "> **R63**（readfirstlane：Amdahl 1.74%，代码未改）、**R64**（attention int8：Amdahl + 日志，内核未编译）、\n"
    "> **R72**（扩 cache：容量换算，未重启）。每条的最低结题测量见 `W939 §2`。\n> \n"
    "> **依据分级（此后所有条目强制标注）**：A 本机实测 / B 本机离线实测（ISA、微基准、单编）/ "
    "C 推算（Amdahl、容量、噪声门）/ D 阅读。**只有 A，或 B + 已有的 A 先例，才允许写「不做」；C 一律重开。**\n>\n")
assert anchor in s
s = s.replace(anchor, block + anchor, 1)

old_seq = [l for l in s.split("\n") if l.startswith("> **执行顺序（2026-11-04 11:3x")]
if old_seq:
    new_seq = ("> **执行顺序（2026-11-04 13:0x 修，含 W939 重开区）：R61（先拿 PMC，独立进程）→ R60（stream-k A/B）→ "
               "R63（readfirstlane）→ R72（reserve 600，一次重启）→ R64（Q·K int8，窄化）→ R81（窗口 12 归因）→ "
               "R79（重启后会话）→ R80（gate provenance）→ R74（W4A4 精度门）→ R49 → R50 → R30′")
    s = s.replace(old_seq[0], new_seq, 1)
    print("queue rewritten")
io.open(r, "w", encoding="utf-8").write(s)
print("W832 updated")
