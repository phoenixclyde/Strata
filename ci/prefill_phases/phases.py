#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci/prefill_phases/phases.py -- the 2K/8K/16K phase table of the prompt path, and the numbers
the tuning plan quotes from it.

Why this exists (W1005): R95 carried "gemm gate/up 1.91x, down 1.87x, dequant 3.9x, wait copy
14x" for five rounds.  All four were computed from *one* 2056-token line and *one* 15757-token
line of a log that spans a dozen builds, and the last two are excesses against a 16K-normalised
rate -- so a per-chunk cost that saturates (dequant) reads as a per-token penalty, and a cost
that a later build already fixed (wait copy 170 -> 30 ms) keeps its old size.

So the table is now produced by a probe (same binary, same config, cold prompts, n=3 per length)
and stored as a TSV.  Every number the plan quotes is re-derived here: `--check` fails when the
plan's figure is not the TSV's figure.

  phases.py --raw phases_w1005.txt > PRE_FILL_PHASES.tsv
  phases.py --check PRE_FILL_PHASES.tsv
"""
import argparse
import re
import statistics
import sys

HEAD = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:")
# name, integer ms, percentage -- the log prints them space separated
PH = re.compile(r"([A-Za-z][A-Za-z0-9+: /]*?) (\d+) \((\d+\.\d)%\)")

# The plan's claims (W832 6.2 new30).  Each is recomputed from the TSV; --check fails when a
# recomputed value is not the quoted one, i.e. the table changed and the plan did not.
# Lengths are the *measured* token counts: the probe overshoots the request by ~1.19x, so 1735
# asked -> 2084 measured.  They are also the cluster anchors (tolerance 2%).
EXPECTED = {
    # label                   value   tol   how
    "gu_rate_2K_over_16K":   (1.57, 0.04, "rate"),   # gemm gate/up ms/token at 2K / at 16K
    "dn_rate_2K_over_16K":   (1.52, 0.04, "rate"),   # same for gemm down
    "dequant_ms_2K":         (161,   4.0, "ms"),     # the group gather kernel, absolute ms
    "dequant_ms_8K":         (525,  10.0, "ms"),
    "dequant_ms_16K":        (491,  10.0, "ms"),
    "wait_copy_ms_2K":       (37,    8.0, "ms"),
    "host_grouping_ms_2K":   (91,    6.0, "ms"),
    "gpu_ms_2K":             (3191,  20.0, "ms"),
    "tokens_2K":             (2084,  10.0, "ms"),
    "prefill_ms_per_tok_2K_over_16K": (1.23, 0.04, "rate"),  # gpu/tokens
}


def parse(lines):
    rows = []
    for line in lines:
        m = HEAD.search(line)
        if not m:
            continue
        tok, gpu, wall, host = (int(x) for x in m.groups())
        d = {"tokens": tok, "gpu": gpu, "wall": wall, "host": host}
        for name, ms, pct in PH.findall(line[m.end():]):
            d[name.strip()] = int(ms)
        rows.append(d)
    return rows


def names(rows):
    out = []
    for r in rows:
        for k in r:
            if k not in ("tokens", "gpu", "wall", "host") and k not in out:
                out.append(k)
    return out


def to_tsv(rows):
    cols = names(rows)
    print("\t".join(["tokens", "host_ms", "wall_ms", "gpu_ms"] + cols))
    for r in rows:
        cells = [str(r["tokens"]), str(r["host"]), str(r["wall"]), str(r["gpu"])]
        cells += [str(r.get(c, "")) for c in cols]
        print("\t".join(cells))


def load_tsv(path):
    with open(path, encoding="utf-8") as f:
        head = f.readline().rstrip("\n").split("\t")
        rows = []
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            c = line.split("\t")
            r = {}
            for k, v in zip(head, c):
                if v == "":
                    continue
                k = {"gpu_ms": "gpu", "wall_ms": "wall", "host_ms": "host"}.get(k, k)
                r[k] = int(v)
            rows.append(r)
    return rows


def cluster(rows, tol=0.025):
    """Group by measured token count; keys are the cluster's median (so 8173/8271/8289 merge)."""
    groups = []
    for r in rows:
        for g in groups:
            if abs(r["tokens"] - statistics.median([x["tokens"] for x in g])) <= tol * r["tokens"]:
                g.append(r)
                break
        else:
            groups.append([r])
    return {int(statistics.median([x["tokens"] for x in g])): g for g in groups if len(g) >= 2}


def near(groups, target, tol=0.06):
    """The cluster whose median token count is closest to `target` (None if none is close)."""
    if not groups:
        return None
    k = min(groups, key=lambda x: abs(x - target))
    return k if abs(k - target) <= tol * target else None


def med(rows, key):
    v = [r[key] for r in rows if key in r]
    return statistics.median(v) if v else None


def check(path):
    rows = load_tsv(path)
    fails = []
    groups = cluster(rows)
    if len(groups) < 3:
        fails.append("expected >=3 length clusters, got %d: %s" % (len(groups), sorted(groups)))
    L2K, L8K, L16K = near(groups, 2080), near(groups, 8200), near(groups, 16300)
    if None in (L2K, L8K, L16K):
        fails.append("no cluster near 2K/8K/16K: %s" % sorted(groups))
        return fails, {}, groups

    # 1. every row's phases must add up to the GPU timeline (integer ms, 26 phases)
    for r in rows:
        s = sum(v for k, v in r.items() if k not in ("tokens", "host", "wall", "gpu"))
        g = r["gpu"]
        if abs(s - g) > 0.03 * g:
            fails.append("%d tokens: phases sum to %d ms, timeline %d ms (%.1f%%)"
                         % (r["tokens"], s, g, 100.0 * (s - g) / g))

    # 2. the plan's numbers
    def rate(name, tok):
        g = groups.get(tok)
        if not g:
            return None
        return med(g, name) / float(tok)

    got = {
        "gu_rate_2K_over_16K": (rate("gemm gate/up", L2K) or 0) / (rate("gemm gate/up", L16K) or 1),
        "dn_rate_2K_over_16K": (rate("gemm down", L2K) or 0) / (rate("gemm down", L16K) or 1),
        "prefill_ms_per_tok_2K_over_16K": (rate("gpu", L2K) or 0) / (rate("gpu", L16K) or 1),
        "dequant_ms_2K": med(groups[L2K], "dequant"),
        "dequant_ms_8K": med(groups[L8K], "dequant"),
        "dequant_ms_16K": med(groups[L16K], "dequant"),
        "wait_copy_ms_2K": med(groups[L2K], "wait copy"),
        "host_grouping_ms_2K": med(groups[L2K], "host grouping"),
        "gpu_ms_2K": med(groups[L2K], "gpu"),
        "tokens_2K": med(groups[L2K], "tokens"),
    }
    for k, (want, tol, _how) in EXPECTED.items():
        have = got.get(k)
        if have is None:
            fails.append("%s: missing" % k)
        elif abs(have - want) > tol:
            fails.append("%s: table says %.3f, plan says %.3f (tol %.2f)" % (k, have, want, tol))
    return fails, got, groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw")
    ap.add_argument("--check")
    a = ap.parse_args()
    if a.raw:
        with open(a.raw, encoding="utf-8", errors="replace") as f:
            rows = parse(f)
        to_tsv(rows)
        return 0
    if a.check:
        fails, got, groups = check(a.check)
        for k, v in got.items():
            print("  %-18s %s" % (k, ("%.3f" % v) if isinstance(v, float) else v))
        for k in sorted(groups):
            print("  cluster %5d  n=%d" % (k, len(groups[k])))
        if fails:
            print("PHASES: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
            return 1
        print("PHASES: PASS")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
