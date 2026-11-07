#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose why the 32K point has near-zero KL: is the reference distribution
degenerate (near-certain top-1) because the ids set repeats?"""
import json
import pathlib
import sys
import numpy as np

W = pathlib.Path("/w")
for arm in ("A", "C", "D"):
    print("=== arm", arm, "===")
    idx = json.loads((W / ("L_" + arm) / "index.json").read_text())["requests"]
    for i, meta in enumerate(idx):
        x = np.fromfile(W / ("L_" + arm) / ("first.%d" % i), dtype=np.float32).astype(np.float64)
        l = x - x.max()
        p = np.exp(l)
        p /= p.sum()
        order = np.argsort(p)[::-1]
        print("  n=%-6d top1=%.6f top2=%.6f margin=%.6f entropy=%.4f  argmax=%d"
              % (meta["tokens"], p[order[0]], p[order[1]], p[order[0]] - p[order[1]],
                 float(-(p[p > 0] * np.log(p[p > 0])).sum()), int(order[0])))
