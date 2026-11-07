#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 · W805 相位账的完整性核查。
   1) 每档把 PH 行的**全部字段**列出，验证加总 == GPU timeline（字段是否被盗用/漏项）。
   2) 与文档 W805 §2 的表逐项对比，列出「文档没写但占比 >=2%」的字段。
"""
import re
import sys

FIELD = re.compile(r"([a-z][a-z+ ]*(?:/[a-z+ ]+)?) ([0-9]+) \(([0-9.]+)%\)")


def parse(path):
    cur, out = None, []
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^=== ARM (\S+)", ln)
        if m:
            cur = m.group(1); continue
        m = re.search(r"prefill timing: (\d+) tokens, GPU timeline ([0-9.]+) ms, wall ([0-9.]+) ms, host staging ([0-9.]+) ms: (.*)$", ln)
        if not m:
            continue
        tok, tl, wall, stage, rest = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)
        f = {}
        for mm in FIELD.finditer(rest):
            f[mm.group(1).strip()] = float(mm.group(2))
        out.append({"arm": cur, "tok": tok, "tl": tl, "wall": wall, "stage": stage, "f": f})
    return out


DOC = {1881: {"gemm gate/up": 22.7, "qsa attn": 7.7, "gdn": 8.6, "gemm down": 10.9, "hc read": 8.4,
              "dequant": 6.1, "wait copy": 0.9},
       3313: {"gemm gate/up": 22.1, "qsa attn": 10.7, "gdn": 10.8, "gemm down": 10.6, "hc read": 6.7,
              "dequant": 8.5, "wait copy": 0.7},
       6152: {"gemm gate/up": 20.6, "qsa attn": 14.5, "gdn": 10.2, "gemm down": 9.9, "hc read": 7.2,
              "dequant": 4.9, "wait copy": 0.4}}

rows = parse(sys.argv[1] if len(sys.argv) > 1 else "albus/audit10/w805_phase_20261026_191927.txt")
seen = set()
for r in rows:
    if r["tok"] in seen:
        continue
    seen.add(r["tok"])
    tot = sum(r["f"].values())
    print("\n=== %d tokens: timeline %.0f  wall %.0f  stage %.0f | 字段和 %.0f (差 %.0f)"
          % (r["tok"], r["tl"], r["wall"], r["stage"], tot, r["tl"] - tot))
    order = sorted(r["f"].items(), key=lambda kv: -kv[1])
    for n, v in order:
        if 100 * v / r["tl"] < 1.0:
            continue
        doc = DOC.get(r["tok"], {}).get(n)
        mark = "   " if doc is not None else ("**漏**" if 100 * v / r["tl"] >= 2 else "     ")
        cmp = "" if doc is None else ("  文档 %4.1f%% %s" % (doc, "OK" if abs(doc - 100 * v / r["tl"]) < 0.15 else "**不符**"))
        print("  %s %-16s %6.0f ms %5.1f%%%s" % (mark, n, v, 100 * v / r["tl"], cmp))
print("\n图例：**漏** = 文档未列且占比 >=2%；文档列了但数值不符会标 **不符**")
