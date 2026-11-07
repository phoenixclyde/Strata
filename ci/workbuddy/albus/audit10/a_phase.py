#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT10 · PH 行（strata prefill timing）解析与复算。
   用于 W804（读长扫描五臂）与 W805（8192 档相位账）。
   字段：<n> tokens, GPU timeline <T> ms, wall <W> ms, host staging <H> ms: <name> <ms> (<pct>%) ...
"""
import re
import statistics as st
import sys

NAME = re.compile(r"([a-z()+ /]+?) ([0-9]+) \(([0-9.]+)%\)")


def ph_lines(path):
    out = []
    cur = None
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^=== ARM (\S+)", ln)
        if m:
            cur = m.group(1)
            continue
        if "strata prefill timing:" not in ln:
            continue
        g = lambda p: float(re.search(p, ln).group(1)) if re.search(p, ln) else None
        rec = {"arm": cur, "tok": int(g(r"prefill timing: (\d+) tokens")),
               "tl": g(r"GPU timeline ([0-9.]+) ms"), "wall": g(r"wall ([0-9.]+) ms"),
               "stage": g(r"host staging ([0-9.]+) ms"), "f": {}}
        for mm in NAME.finditer(ln):
            rec["f"][mm.group(1).strip()] = (float(mm.group(2)), float(mm.group(3)))
        out.append(rec)
    return out


def show_phase(path, label):
    rows = ph_lines(path)
    print("\n== %s  (%d PH lines)" % (label, len(rows)))
    if not rows:
        return
    names = ["embed+steps", "hc read", "gdn", "qsa proj", "qsa attn", "qsa indexer", "gemm gate/up",
             "gemm down", "dequant", "wait copy", "combine", "shared expert", "router+plan+bell"]
    for r in rows:
        tl = r["tl"] or 1
        parts = []
        for n in names:
            if n in r["f"]:
                parts.append("%s %.1f%%" % (n.replace("gemm ", "gemm_").replace(" ", ""), 100 * r["f"][n][0] / tl))
        print("  %-4s %5d tok tl=%6.0f wall=%6.0f | %s" % (r["arm"], r["tok"], tl, r["wall"], "  ".join(parts)))
        print("       每 1k token: " + "  ".join("%s %.0fms" % (n.replace(" ", "_"), 1000.0 * r["f"][n][0] / r["tok"])
                                                for n in ("gemm gate/up", "qsa attn", "gdn", "gemm down", "hc read") if n in r["f"]))


if __name__ == "__main__":
    show_phase("albus/audit10/w805_phase_20261026_191927.txt", "W805 phase (18/3/6K)")
    show_phase("albus/audit10/w804_read_20261026_000306.txt", "W804 A/B/C")
