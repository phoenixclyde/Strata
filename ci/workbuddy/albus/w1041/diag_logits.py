#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: why a max|dlogit| of 3-4 nats sits next to a KL of 0.0004 -- and what the decision should read.

  python3 diag_logits.py <ref_dir> <run_dir> [run_dir...]

For every prompt: entropy of the reference distribution, top-1 probability, the top-1/top-2 margin,
KL over the full vocabulary, KL over the reference's top-64 tokens, and the top-10 set overlap.
A max|delta| in the tail is not a quality signal; these are.
"""
import json
import pathlib
import sys

import numpy as np


def load(d, i):
    return np.fromfile(pathlib.Path(d) / ("first.%d" % i), dtype=np.float32).astype(np.float64)


def softmax(x):
    z = x - x.max()
    p = np.exp(z)
    return p / p.sum()


def main():
    ref = pathlib.Path(sys.argv[1])
    runs = [pathlib.Path(x) for x in sys.argv[2:]]
    idx = json.loads((ref / "index.json").read_text())["requests"]
    print("%-8s %7s %8s %9s %9s %9s %9s %9s" %
          ("run", "tokens", "H(ref)", "p(top1)", "margin", "KL_all", "KL_top64", "top10"))
    for r in runs:
        for i, meta in enumerate(idx):
            a, b = load(ref, i), load(r, i)
            pa, pb = softmax(a), softmax(b)
            H = float(-(pa * np.log(np.maximum(pa, 1e-300))).sum())
            o = np.argsort(-pa)[:64]
            qa, qb = pa[o] / pa[o].sum(), pb[o] / pb[o].sum()
            kl64 = float((qa * (np.log(qa) - np.log(qb))).sum())
            kl_all = float((pa * (np.log(np.maximum(pa, 1e-300)) - np.log(np.maximum(pb, 1e-300)))).sum())
            top10 = len(set(np.argsort(-pa)[:10]) & set(np.argsort(-pb)[:10]))
            s = np.sort(pa)[::-1]
            print("%-8s %7d %8.2f %9.4f %9.5f %9.5f %9.5f %5d/10" %
                  (r.name.replace("lg_", ""), meta["tokens"], H, s[0], s[0] - s[1], kl_all, kl64, top10))


if __name__ == "__main__":
    main()
