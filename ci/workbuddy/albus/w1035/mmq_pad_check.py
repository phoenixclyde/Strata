#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 / P392 static evaluation: is the pre-#29953 padding short on OUR shapes?

Reads mmq-config-gcn.cuh (gfx906's MMQ config table, copied byte-for-byte from
/src/third_party/llama.cpp/ggml/src/ggml-cuda/ on 2026-11-07) and re-implements the
two host functions that decide the tile and the padding:

  ggml_cuda_mmq_get_J_max(type, fallback, cc, ne11)   [mmq.cuh:372, the ALLOCATION]
      ret = min(ne11, 512); ret -= ret % 8; walk down by 8 to the first existing config

  mul_mat_q_switch_J's loop                           [mmq.cuh:1484, the SELECTION]
      J = 8..128 step 8; ntiles = ceil(ncols_opt / J); keep the fewest tiles; stop at <= 1

Upstream #29953 ("CUDA: fix MMQ out-of-bounds reads") says these two disagree: the
allocation rounds ne11 DOWN, the selection effectively rounds it UP.  This script
prints, per (type, ne11), whether J_best > J_max and by how many 144-byte blocks.

No GPU, no engine, no writes outside this file.
"""
import io
import re
import sys

CFG = "mmq-config-gcn.cuh"
BLOCK_Q8_1_MMQ = 144          # sizeof(block_q8_1_mmq): 4*QK8_1 int8 + 4*(half+half) = 128 + 16
TYPES = ["GGML_TYPE_Q4_K", "GGML_TYPE_Q5_K", "GGML_TYPE_Q6_K",
         "GGML_TYPE_Q5_1", "GGML_TYPE_Q8_0"]


def load(path=CFG):
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    table = {}          # (type, J, fallback) -> (I, nthreads, occupancy)
    for m in re.finditer(r"CASE\((GGML_TYPE_\w+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),"
                         r"\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+)\)", txt):
        t, nthr, occ, I, J, _layout, _kv, _sk, fb = m.groups()
        table[(t, int(J), fb == "true")] = (int(I), int(nthr), int(occ))
    return table


def exists(table, t, J, fb):
    return (t, J, fb) in table


def j_max(table, t, fb, ne11):
    """mmq.cuh:372 verbatim (existence only; the function has no smpbo test)."""
    ret = min(int(ne11), 512)
    ret -= ret % 8
    while ret > 0:
        if exists(table, t, ret, fb):
            return ret
        ret -= 8
    return ret


def j_best(table, t, fb, ncols_opt):
    """mul_mat_q_switch_J's loop verbatim, minus the smpbo filter (see note below)."""
    best, ntiles_best = 0, 1 << 62
    J = 8
    while J <= 128 and ntiles_best > 1:
        if not exists(table, t, J, fb):
            J += 8
            continue
        ntiles = -(-int(ncols_opt) // J)          # ceil
        if ntiles < ntiles_best:
            best, ntiles_best = J, ntiles
        J += 8
    return best if best > 0 else 64               # the old dispatch falls through to 64


def main():
    table = load()
    print("config rows parsed: %d   (types: %s)" %
          (len(table), ",".join(sorted({k[0] for k in table}))[:60]))
    print()
    print("=== A. dense path: ggml_cuda_mul_mat_q allocates J_max(ne11),")
    print("       switch_J picks J_best(ne11).  overrun in blocks of %d B ===" % BLOCK_Q8_1_MMQ)
    print("%-18s %-6s %5s %6s %6s %8s %10s" %
          ("type", "fb", "ne11", "J_max", "J_best", "overrun", "bytes"))
    worst = {}
    for t in TYPES:
        for fb in (False, True):
            for ne11 in list(range(1, 129)) + [130, 200, 255, 256, 257, 512, 1000, 4096, 16384]:
                jm, jb = j_max(table, t, fb, ne11), j_best(table, t, fb, ne11)
                if jb > jm:
                    worst[(t, fb)] = max(worst.get((t, fb), 0), jb - jm)
    for (t, fb), w in sorted(worst.items()):
        print("%-18s %-6s  worst overrun: %3d blocks = %5d B" %
              (t, fb, w, w * BLOCK_Q8_1_MMQ))
    if not worst:
        print("  (none)")
    print()
    print("=== B. the same table for the shapes our experts actually call")
    print("       gu  = Q4_K/Q5_K @ [1280,2560]   down = Q5_1/Q8_0 @ [2560,640]")
    print("%-18s %-6s %6s %6s %6s %7s" % ("type", "fb", "ne11", "J_max", "J_best", "delta"))
    for t in ["GGML_TYPE_Q4_K", "GGML_TYPE_Q5_K", "GGML_TYPE_Q5_1", "GGML_TYPE_Q8_0"]:
        for ne11 in (1, 8, 16, 64, 128, 320, 1000, 16384):
            jm, jb = j_max(table, t, False, ne11), j_best(table, t, False, ne11)
            print("%-18s %-6s %6d %6d %6d %7d" % (t.replace("GGML_TYPE_", ""), "F", ne11, jm, jb, jb - jm))
    print()
    print("NOTE smpbo: the selection loop skips tiles whose shared memory exceeds the card's")
    print("     opt-in limit.  Skipping a tile can only make J_best LARGER, so the overruns")
    print("     above are a lower bound.  The MoE path is not affected: strata's own")
    print("     moe_mmq.cu q8_bytes() already adds 128 blocks (= the largest possible J).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
