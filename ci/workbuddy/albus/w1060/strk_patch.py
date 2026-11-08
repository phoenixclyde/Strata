#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1060/R60 probe: flip stream_k=false -> true on the 11 GGML_TYPE_Q4_K rows of
# mmq-config-gcn.cuh (both copies: llama-master pinned tree = the effective one for the
# mmq-instance TUs via relative include, and the build overlay copy for consistency).
# CASE(type_, nthreads_, occupancy_, I_, J_, sram_layout_, K_vram_, stream_k_, fallback_).
# Scratch-only: both files restored + md5-verified after build.
import io
import sys

PATHS = sys.argv[1:] or [
    "/home/albus/strata166/tmp/w1037/llama-master/ggml/src/ggml-cuda/mmq-config-gcn.cuh",
    "/home/albus/strata166/build-masterp/ggml-tq-overlay/mmq-config-gcn.cuh",
]
OLD = "GGML_TYPE_Q4_K, 256, 2,"
ANCHOR = "MMQ_ITER_K, false,"

for idx, P in enumerate(PATHS):
    s = io.open(P, encoding="utf-8").read()
    n_flip = 0
    out_lines = []
    for line in s.splitlines(keepends=True):
        if OLD in line and ANCHOR in line:
            line = line.replace(ANCHOR, "MMQ_ITER_K, true,", 1)
            n_flip += 1
        out_lines.append(line)
    assert n_flip == 11, (P, n_flip)
    s2 = "".join(out_lines)
    assert s2.count("GGML_TYPE_Q4_K") == 11
    try:
        io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
        print("PATCHED", P, "rows_flipped=", n_flip,
              "residual_false=", sum(1 for l in s2.splitlines() if OLD in l and "MMQ_ITER_K, false," in l))
    except PermissionError as e:
        # W1060: overlay copies are rewritten by CMake as root (docker) -> not writable.
        # The llama-master copy (idx 0) is the EFFECTIVE one for the mmq-instance TUs
        # (relative include ../mmq.cuh -> sibling config, W1058 trap) -- the overlay copy
        # only serves the TQ overlay TUs (trellis types, not Q4_K). Best-effort only.
        if idx == 0:
            raise
        print("SKIP(perm)", P, e)
