#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1041: raw fp32 logits comparison (the R104 sampling surface applied to R103).

  python3 cmp_logits.py <ref_dir> <run_dir> [run_dir...]

Per prompt index: prompt length, max|delta logit| (nats), mean|delta|, argmax agreement, identical-bytes flag.
KL is reported too, but as a derived quantity -- the raw delta is the primary number.
"""
import json
import math
import pathlib
import sys

import numpy as np


def load(d, i):
    return np.fromfile(pathlib.Path(d) / ("first.%d" % i), dtype=np.float32).astype(np.float64)


def main():
    ref = pathlib.Path(sys.argv[1])
    runs = [pathlib.Path(x) for x in sys.argv[2:]]
    idx = json.loads((ref / "index.json").read_text())["requests"]
    print("%-14s %8s %12s %12s %10s %9s %10s" %
          ("run", "tokens", "max|dlogit|", "mean|dlogit|", "argmax", "KL(nats)", "bytes"))
    for r in runs:
        for i, meta in enumerate(idx):
            a, b = load(ref, i), load(r, i)
            if a.shape != b.shape:
                print("%-14s %8d  SHAPE MISMATCH %s vs %s" % (r.name, meta["tokens"], a.shape, b.shape))
                continue
            d = np.abs(a - b)
            la = a - a.max()
            lb = b - b.max()
            pa = np.exp(la); pa /= pa.sum()
            pb = np.exp(lb); pb /= pb.sum()
            kl = float((pa * (np.log(pa) - np.log(pb))).sum())
            same_bytes = bool(np.array_equal(a.view(np.uint32), b.view(np.uint32)))
            print("%-14s %8d %12.3e %12.3e %9s %10.5f %10s" % (
                r.name, meta["tokens"], float(d.max()), float(d.mean()),
                "same" if a.argmax() == b.argmax() else "DIFF", kl,
                "IDENT" if same_bytes else "%d/%d" % (int((a.view(np.uint32) != b.view(np.uint32)).sum()), a.size)))


if __name__ == "__main__":
    main()
