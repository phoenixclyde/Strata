#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: one cause or several?  Cross-correlate every arm's per-position dlogp against every other.

If the manual K read were the whole story, the four switch arms (int8 dot4, fp16 dot2, C16, D32) would
carry the SAME error vector and their pairwise |corr| would be ~1.  If each path had its own rounding,
they would be uncorrelated.  Everything here is read off TSVs already on disk.
"""
import io
import sys


def load(path):
    rows = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            if len(f) < 16:
                continue
            try:
                rows.append((int(f[0]), float(f[2]), int(f[3])))
            except ValueError:
                continue
    return rows


def corr(x, y):
    n = min(len(x), len(y))
    mx = sum(x[:n]) / n
    my = sum(y[:n]) / n
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sxx = sum((x[i] - mx) ** 2 for i in range(n))
    syy = sum((y[i] - my) ** 2 for i in range(n))
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else 0.0


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    ref = load(base + "/g3_A2.tsv")
    arms = [
        ("ctl(b12180)", base + "/g3_A2.tsv"),
        ("E(pa7)", base + "/g5_E.tsv"),
        ("R12(归约)", base + "/g3_R12.tsv"),
        ("int8 dot4", base + "/run_B.tsv"),
        ("fp16 dot2", base + "/g2_B.tsv"),
        ("C16 手写读", base + "/g5_C16.tsv"),
        ("D32 fp16q", base + "/g5_D32.tsv"),
    ]
    d = {}
    print("%-12s %6s %8s %9s %9s" % ("arm", "pos", "chg%", "KLproxy", "max|d|"))
    for name, p in arms:
        a = load(p)
        n = min(len(ref), len(a))
        dv = [ref[i][1] - a[i][1] for i in range(n)]
        ch = sum(1 for i in range(n) if ref[i][2] != a[i][2])
        rms = (sum(x * x for x in dv) / n) ** 0.5
        d[name] = dv
        print("%-12s %6d %7.2f%% %9.5f %9.3f" % (name, n, 100.0 * ch / n, rms, max(abs(x) for x in dv)))

    keys = [k for k, _ in arms]
    print("\ncross-correlation of the signed dlogp vectors:")
    print("            " + " ".join("%10s" % k[:10] for k in keys))
    for k1 in keys:
        print("%-12s" % k1[:12] + " ".join("%10.3f" % corr(d[k1], d[k2]) for k2 in keys))


if __name__ == "__main__":
    main()
