#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kernel_curve.py -- what the MMQ kernel itself costs per row, at the two production shapes.

Why (W1008): R95 has said for six rounds that the 2K penalty is "small-batch GEMM".  W1005 showed
the phrase was wrong about *where*; this turns the question into arithmetic: `WIDTH_SWEEP.tsv`
already contains the canonical (un-repacked) kernel at rows-per-expert 32..1024 for both shapes
and every type the pack uses.  Divide by rows and the curve is nearly flat above 320 rows --
so the kernel can only explain a few points of the measured 1.52-1.57x, and the rest is outside
it.  That is what makes the next step an instrument rather than a port.

  python3 ci/prefill_phases/kernel_curve.py            # print the curve + the verdict
  python3 ci/prefill_phases/kernel_curve.py --check    # fail if the plan's numbers drift
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# the repo copy first (166 / CI), then the workspace's own copy (laptop)
CANDIDATES = [os.path.join(HERE, "..", "repack_ab", "WIDTH_SWEEP.tsv"),
              os.path.join(HERE, "..", "..", "albus", "w1003", "WIDTH_SWEEP.tsv")]
TSV = next((p for p in CANDIDATES if os.path.exists(p)), CANDIDATES[0])

# production: gate/up = Q4_K(12) @[1280,2560]; down = Q5_1(7) @[2560,640]
CASES = [("gu", 12, "Q4_K", 1280, 2560, 16), ("dn", 7, "Q5_1", 2560, 640, 16)]
# mean tokens per expert at the two lengths (top-k 8 over the experts the chunk touches;
# W991 measured p50 331 / p90 742 for 2K, and the 16K union saturates near 1024)
ROWS_2K, ROWS_16K = 411, 1015
# the plan quotes these (W832 6.5 W1008)
EXPECT = {"gu": 1.06, "dn": 1.00}

# W1009: the second axis.  rows per launch was the only one W1008 looked at; experts per launch
# matters too (2 / 4 / 8 / 16, Q4_K gate/up, canonical, reps=20, ci/repack_ab/GROUP_SWEEP.tsv).
GROUP = {2: [(32, 0.002078), (128, 0.001104), (320, 0.000548), (512, 0.000556), (1024, 0.000481)],
         4: [(32, 0.001079), (128, 0.000688), (320, 0.000535), (512, 0.000481), (1024, 0.000436)],
         8: [(32, 0.000668), (128, 0.000558), (320, 0.000461), (512, 0.000434), (1024, 0.000425)],
         16: [(32, 0.000504), (128, 0.000499), (320, 0.000441), (512, 0.000426), (1024, 0.000411)]}
EXPECT_GROUP = 1.27          # 16 -> 2 experts per launch, at 411 rows


def group_at(n, rows):
    pts = GROUP[n]
    return at(dict(pts), rows)


def load(path=TSV):
    out = {}
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 5 or not c[3].isdigit():
                continue
            out[(c[0], int(c[1]), int(c[3]))] = float(c[4])   # canonical_ms
    return out


def per_row(rows, shape, tid, experts):
    """ms per token-row, with the expert count divided out (rows_per is per expert)."""
    return {r: ms / float(experts * r) for (s, t, r), ms in rows.items() if s == shape and t == tid}


def at(curve, rows):
    """linear interpolation between the measured points; the curve is monotone here."""
    ks = sorted(curve)
    if rows <= ks[0]:
        return curve[ks[0]]
    if rows >= ks[-1]:
        return curve[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= rows <= b:
            return curve[a] + (curve[b] - curve[a]) * (rows - a) / float(b - a)
    return curve[ks[-1]]


def main():
    rows = load()
    verdict = {}
    for shape, tid, name, out_rows, cols, experts in CASES:
        c = per_row(rows, shape, tid, experts)
        if not c:
            print("missing rows for %s type=%d" % (shape, tid))
            return 2
        ratio = at(c, ROWS_2K) / at(c, ROWS_16K)
        verdict[shape] = ratio
        print("%s %s @[%d,%d]  (n=%d experts per launch)" % (shape, name, out_rows, cols, experts))
        for r in sorted(c):
            print("   %5d rows  %.6f ms/row  x%.3f vs 1024" % (r, c[r], c[r] / c[max(c)]))
        print("   -> kernel predicts 2K/16K = %.3f  (rows %d vs %d)" % (ratio, ROWS_2K, ROWS_16K))
    print()
    MEASURED = {"gu": 1.57, "dn": 1.52}     # W1005, PREFILL_PHASES.tsv
    for shape, ratio in verdict.items():
        m = MEASURED[shape]
        share = 100.0 * (1.0 - (ratio - 1.0) / (m - 1.0))
        print("%s: rows axis alone predicts %.2fx, measured %.2fx -> %.0f%% is outside that axis"
              " (the group axis below explains part of it)" % (shape, ratio, m, share))
    g16, g2 = group_at(16, ROWS_2K), group_at(2, ROWS_2K)
    g8 = group_at(8, ROWS_2K)
    print("group axis @%d rows: n=16 %.6f | n=8 %.6f (x%.2f) | n=2 %.6f (x%.2f)"
          % (ROWS_2K, g16, g8, g8 / g16, g2, g2 / g16))
    prod = verdict["gu"] * (g2 / g16)
    print("two axes together: %.2f x %.2f = %.2f  (measured 1.57 -> %.0f%% still unexplained)"
          % (verdict["gu"], g2 / g16, prod, 100.0 * (1.0 - (prod - 1) / 0.57)))
    if "--check" in sys.argv:
        bad = [k for k, v in verdict.items() if abs(v - EXPECT[k]) > 0.02]
        if abs(g2 / g16 - EXPECT_GROUP) > 0.03:
            bad.append("group axis %.2f" % (g2 / g16))
        if bad:
            print("\nKERNEL_CURVE: FAIL (%s)" % ", ".join(
                "%s says %.3f, plan says %.2f" % (k, verdict[k], EXPECT[k]) for k in bad))
            return 1
        print("\nKERNEL_CURVE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
