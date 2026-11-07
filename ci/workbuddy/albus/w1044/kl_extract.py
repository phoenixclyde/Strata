#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1044: turn four arms' fp32 full-vocabulary logits into the G1/G2/G3 inputs.

Usage (inside the 166 container, numpy available):
  python3 kl_extract.py A B C D --out kl.json --floor floor.txt

  A = kvg (reference / baseline)
  B = attn, no switch        -> build floor, must be byte-identical to A
  C = attn + ATTN_DP4A=1     -> candidate
  D = kvg + QQ_KV=fp16       -> anchor (the KV precision we gave up)

kl_cand   = KL(A || C),  kl_anchor = KL(A || D)   (same convention as W1041 cmp_logits.py)
Length keys come from index.json requests: 1000/8000/20000/32768 -> 1K/8K/20K/32K.
"""
import argparse
import io
import json
import pathlib

import numpy as np

KEY = {1000: "1K", 8000: "8K", 20000: "20K", 32768: "32K"}


def load(d, i):
    return np.fromfile(pathlib.Path(d) / ("first.%d" % i), dtype=np.float32).astype(np.float64)


def kl(a, b):
    la, lb = a - a.max(), b - b.max()
    pa, pb = np.exp(la), np.exp(lb)
    pa /= pa.sum()
    pb /= pb.sum()
    return float((pa * (np.log(pa) - np.log(pb))).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("A")
    ap.add_argument("B")
    ap.add_argument("C")
    ap.add_argument("D")
    ap.add_argument("--out", required=True)
    ap.add_argument("--floor", required=True)
    a = ap.parse_args()
    idx = json.loads((pathlib.Path(a.A) / "index.json").read_text())["requests"]
    out, floor = {}, []
    for i, meta in enumerate(idx):
        n = meta["tokens"]
        key = KEY.get(n, str(n))
        A, B, C, D = (load(x, i) for x in (a.A, a.B, a.C, a.D))
        ident = bool(np.array_equal(A.view(np.uint32), B.view(np.uint32)))
        floor.append(ident)
        out[key] = {"tokens": n, "kl_cand": kl(A, C), "kl_anchor": kl(A, D),
                    "argmax_cand_same": bool(A.argmax() == C.argmax()),
                    "argmax_anchor_same": bool(A.argmax() == D.argmax()),
                    "bytes_identical_floor": ident}
        print("%-5s n=%-6d KL(C)=%.5f  KL(D)=%.5f  ratio=%.3f  floor=%s"
              % (key, n, out[key]["kl_cand"], out[key]["kl_anchor"],
                 out[key]["kl_cand"] / out[key]["kl_anchor"] if out[key]["kl_anchor"] else float("nan"),
                 ident), flush=True)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
    io.open(a.floor, "w", encoding="utf-8", newline="\n").write("1" if all(floor) and len(floor) >= 4 else "0")
    print("FLOOR=%s (%d/%d identical)" % (all(floor) and len(floor) >= 4, sum(floor), len(floor)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
