# -*- coding: utf-8 -*-
"""mtp_decay.py -- R20：MTP 接受率的衰减到底由"上下文长度"还是"生成长度"驱动？

背景（W860 §2.2）：120 170 tok prompt + 4480 gen 那条 MTP 只有 59.9%，而 53 140/1456 是 82.0%。
单看两个样本分不清是哪个因素，所以做二维分桶：prompt 档 × gen 档。

只读日志，零干扰。用法：python3 mtp_decay.py [/data/strata-huihui-ud-iq4_xs.log]
"""
from __future__ import annotations

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "/data/strata-huihui-ud-iq4_xs.log"

RE = re.compile(
    r"strata serve: prompt (\d+) tokens = \d+ reused \+ \d+ read in \d+ ms "
    r"\([\d.]+ tok/s\), (\d+) generated in (\d+) ms \(([\d.]+) tok/s\), "
    r"drafts accepted (\d+) of (\d+)"
)

rows = []
with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
    for ln in fh:
        m = RE.search(ln)
        if m:
            rows.append({
                "tok": int(m.group(1)),
                "gen": int(m.group(2)),
                "gen_ms": int(m.group(3)),
                "gen_tps": float(m.group(4)),
                "ok": int(m.group(5)),
                "all": int(m.group(6)),
            })

print("样本 %d 条" % len(rows))

PB = [(0, 1024), (1024, 8192), (8192, 32768), (32768, 131072), (131072, 10 ** 9)]
GB = [(0, 64), (64, 256), (256, 1024), (1024, 4096), (4096, 10 ** 9)]


def label(lo, hi):
    return "%d-%s" % (lo, "inf" if hi > 10 ** 8 else hi)


print()
print("二维：行=prompt 长度档，列=生成 token 档；格内 = 接受率% (n)")
hdr = "%-14s" % "prompt\\gen"
for lo, hi in GB:
    hdr += " %16s" % label(lo, hi)
print(hdr)

for plo, phi in PB:
    line = "%-14s" % label(plo, phi)
    for glo, ghi in GB:
        sel = [r for r in rows if plo <= r["tok"] < phi and glo <= r["gen"] < ghi and r["all"] >= 8]
        if not sel:
            line += " %16s" % "-"
        else:
            ok = sum(r["ok"] for r in sel)
            all_ = sum(r["all"] for r in sel)
            line += " %16s" % ("%.1f (%d)" % (100.0 * ok / all_, len(sel)))
    print(line)

print()
print("只看 gen 维度（忽略 prompt）：")
for glo, ghi in GB:
    sel = [r for r in rows if glo <= r["gen"] < ghi and r["all"] >= 8]
    if not sel:
        continue
    ok = sum(r["ok"] for r in sel)
    all_ = sum(r["all"] for r in sel)
    tps = sum(r["gen"] for r in sel) / sum(r["gen_ms"] for r in sel) * 1000
    print("  gen %-12s n=%-4d 接受 %.1f%%  decode %.1f tok/s" % (label(glo, ghi), len(sel), 100.0 * ok / all_, tps))

print()
print("只看 prompt 维度：")
for plo, phi in PB:
    sel = [r for r in rows if plo <= r["tok"] < phi and r["all"] >= 8]
    if not sel:
        continue
    ok = sum(r["ok"] for r in sel)
    all_ = sum(r["all"] for r in sel)
    tps = sum(r["gen"] for r in sel) / sum(r["gen_ms"] for r in sel) * 1000
    print("  prompt %-12s n=%-4d 接受 %.1f%%  decode %.1f tok/s" % (label(plo, phi), len(sel), 100.0 * ok / all_, tps))

print()
print("最大的 8 条（按生成 token 排）：")
for r in sorted(rows, key=lambda x: -x["gen"])[:8]:
    print("  prompt %7d  gen %5d  %6.1f tok/s  接受 %.1f%% (%d/%d)" % (
        r["tok"], r["gen"], r["gen_tps"], 100.0 * r["ok"] / r["all"], r["ok"], r["all"]))
