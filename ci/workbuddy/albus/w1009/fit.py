#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1009: is the 2K penalty a per-chunk constant, or a smooth efficiency curve?

W1008 said 90% of it is outside the GEMM kernel.  Two points cannot say more than that: a
straight line through 2K and 16K always "finds" a constant term.  With six lengths the
question becomes answerable -- if the per-token cost is flat from 4K up and only rises below
~4K, it is a curve (occupancy / launch granularity); if the absolute time is flat per chunk
and grows linearly with tokens above it, it is a constant (per-group bookkeeping).

  python3 albus/w1009/fit.py phases.txt
"""
import io
import re
import statistics
import sys

HEAD = re.compile(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:")
PH = re.compile(r"([A-Za-z][A-Za-z0-9+: /]*?) (\d+) \(\d+\.\d%\)")
WANT = ["gemm gate/up", "gemm down", "dequant", "wait copy", "host grouping", "combine",
        "router+shared", "gdn", "qsa attn"]


def parse(path):
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = HEAD.search(line)
        if not m:
            continue
        tok, gpu = int(m.group(1)), int(m.group(2))
        d = {k.strip(): int(v) for k, v in PH.findall(line[m.end():])}
        d["_gpu"] = gpu
        d["_tok"] = tok
        out.append(d)
    return out


def cluster(rows, tol=0.03):
    groups = []
    for r in rows:
        for g in groups:
            med = statistics.median([x["_tok"] for x in g])
            if abs(r["_tok"] - med) <= tol * med:
                g.append(r)
                break
        else:
            groups.append([r])
    return sorted(groups, key=lambda g: statistics.median([x["_tok"] for x in g]))


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx
    b = my - a * mx
    ss = sum((y - my) ** 2 for y in ys)
    res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return a, b, (1 - res / ss if ss else 0.0)


def main():
    rows = parse(sys.argv[1])
    gs = cluster(rows)
    med = [(int(statistics.median([x["_tok"] for x in g])),
            {k: statistics.median([x[k] for x in g]) for k in g[0]}) for g in gs if len(g) >= 2]
    print("# %d length clusters" % len(med))
    print("tokens\t" + "\t".join(WANT))
    for tok, d in med:
        print("%d\t" % tok + "\t".join("%.0f" % d.get(k, 0) for k in WANT))

    print("\n# per 1k tokens")
    print("tokens\t" + "\t".join(WANT))
    for tok, d in med:
        print("%d\t" % tok + "\t".join("%.2f" % (d.get(k, 0) / tok * 1000) for k in WANT))

    # the test: fit the three longest points (linear region) and extrapolate to the shortest
    if len(med) >= 4:
        tail = med[-3:]
        xs = [t for t, _ in tail]
        print("\n# fit on the last three lengths, extrapolated to the shortest")
        print("phase\tintercept_ms\tslope_ms_per_tok\tr2\tpredicted@%d\tmeasured\terror" % med[0][0])
        for k in WANT:
            ys = [d.get(k, 0) for _, d in tail]
            a, b, r2 = fit(xs, ys)
            pred = a * med[0][0] + b
            got = med[0][1].get(k, 0)
            print("%s\t%.1f\t%.5f\t%.4f\t%.0f\t%.0f\t%s"
                  % (k, b, a, r2, pred, got,
                     ("%.0f%%" % (100.0 * (got - pred) / pred)) if pred else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
