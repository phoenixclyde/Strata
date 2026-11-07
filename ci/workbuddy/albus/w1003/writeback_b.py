#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1003-b 回写：六通道分解 + 尺寸账 + 举一反三，并结 P279。"""
import os

ROOT = r"D:\workbuddy_space\strata_ws"
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
BLOCK = os.path.join(ROOT, "albus", "w1003", "w832_w1003b_append.md")


def norm(p):
    b = open(p, "rb").read()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.replace(b"\r\n", b"\n").decode("utf-8")


plan = norm(PLAN)
block = norm(BLOCK)
if "§6.5 补记 · W1003-b" in plan:
    print("PLAN: already has W1003-b, skip")
else:
    if not plan.endswith("\n"):
        plan += "\n"
    plan += block
    open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
    print("PLAN: appended")

rows = [l for l in norm(PROG).split("\n") if l.strip()]
out = []
hit = False
for l in rows:
    c = l.split("\t")
    if len(c) >= 10 and c[1] == "P279":
        hit = True
        c[5], c[6], c[7] = "1", "1", "DONE"
        c[8] = (c[8].rstrip() +
                " **W1003-b 补齐（22:3x）**：三条通道按 mx 实现拆成**六条**并各自钉 file:line——"
                "C1 权重上传（尺寸账：Q5_1 down 1,228,800 B 中性 / Q8_0 down 1,740,800→1,781,760 B +2.3%）、"
                "C2 `moe_mmq.cu:498` 的 `expert_stride`→`repack_gcn_nbytes` 与 `Product.layout`、"
                "C3 `block_q8_1_mmq` 尺寸/偏移断言（PARTIAL）、C4 `prefill.cpp:5300` 单次 1280 行 ⇒ N/A、"
                "C5 逐位+六档+2×CV+KL+灰度+回滚（未跑）、C6 解散。举一反三三条同时写入 §6.5。")
        c[9] = "deploy/W832_OPT_PLAN_V2.md §6.5（W1003-b）"
        l = "\t".join(c)
    out.append(l)
if not hit:
    print("PROG: P279 not found!")

open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

data = [l.split("\t") for l in out if l.strip() and not l.startswith("#")]
h = data[0]
ci, di, si = h.index("count"), h.index("done"), h.index("status")
tot = done = 0
for r in data[1:]:
    if len(r) <= si:
        continue
    try:
        c, d = int(r[ci]), int(r[di])
    except Exception:
        c, d = 1, (1 if r[si] in ("DONE", "DONE_NEG", "NA") else 0)
    tot += c
    done += d
print("PROGRESS: total=%d done=%d pct=%.1f%%" % (tot, done, 100.0 * done / tot))
