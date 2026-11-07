#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse `strata prefill timing` lines (STRATA_PREFILL_TIMING) into a per-length phase table.

Why: R95-C is "the gather/dequant side of the 2K penalty".  The claim has been quoted as
"dequant +191 ms (3.9x), wait copy +136 ms (14x)" for several rounds, but those are *excesses*
against a 16K-normalised rate, not measured phase times.  The absolute times are in the log.

This turns 506 log lines into: tokens -> per-phase ms (median), so that each phase can be
classified as per-token (scales linearly) or per-request (flat), which is what decides whether
a fix exists at all.
"""
import re
import statistics
import sys

NAMES = ["embed+steps", "hc read", "gdn", "qsa proj", "qsa indexer", "qsa select", "qsa attn",
         "router+shared", "host grouping", "gather", "wait copy", "dequant", "gemm gate/up",
         "gemm down", "combine", "ple", "kv stage", "gdn conv+gates", "gdn recurrence",
         "gdn out proj", "hc write", "hc read: down+silu", "hc read: up", "hc read: inject",
         "hc read: mix", "qsa: indexer gemms", "qsa: norm/rope/kv append/q prep"]
# longest first so "hc read: up" wins over "hc read"
ORDER = sorted(NAMES, key=len, reverse=True)
HEAD = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:")
PH = re.compile("(%s) (\\d+) \\((\\d+\\.\\d)%%\\)" % "|".join(re.escape(n) for n in ORDER))


def parse(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = HEAD.search(line)
        if not m:
            continue
        tok, gpu, wall, host = (int(x) for x in m.groups())
        d = {}
        for name, ms, pct in PH.findall(line[m.end():]):
            d[name] = float(ms)
        if len(d) < 8:
            continue
        d["_tokens"] = tok
        d["_gpu"] = float(gpu)
        d["_wall"] = float(wall)
        d["_host"] = float(host)
        rows.append(d)
    return rows


def cluster(rows, tol=0.02):
    """Group by token count (the probe asks for approximate lengths; usage is exact)."""
    out = {}
    for r in rows:
        for k in out:
            if abs(r["_tokens"] - k) <= tol * k:
                out[k].append(r)
                break
        else:
            out[r["_tokens"]] = [r]
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "phases_raw.txt"
    rows = parse(path)
    groups = cluster(rows)
    print("# parsed %d lines, %d length clusters" % (len(rows), len(groups)))
    keys = sorted(groups)
    # only keep clusters with >=3 samples for a median worth printing
    keys = [k for k in keys if len(groups[k]) >= 3]
    print("# clusters with n>=3: %s" % ", ".join("%d(n=%d)" % (k, len(groups[k])) for k in keys))

    cols = ["_gpu"] + [n for n in NAMES if any(n in r for r in rows)]
    hdr = ["tokens", "n"] + cols
    print("\t".join(hdr))
    for k in keys:
        g = groups[k]
        line = ["%d" % k, "%d" % len(g)]
        for c in cols:
            vals = [r[c] for r in g if c in r]
            line.append("%.1f" % statistics.median(vals) if vals else "")
        print("\t".join(line))

    # per-token view, relative to the largest cluster
    if len(keys) >= 2:
        print("\n# ms per 1k tokens (median ms / tokens * 1000)")
        hdr2 = ["tokens"] + cols
        print("\t".join(hdr2))
        for k in keys:
            g = groups[k]
            line = ["%d" % k]
            for c in cols:
                vals = [r[c] for r in g if c in r]
                line.append("%.2f" % (statistics.median(vals) / k * 1000) if vals else "")
            print("\t".join(line))


if __name__ == "__main__":
    main()
