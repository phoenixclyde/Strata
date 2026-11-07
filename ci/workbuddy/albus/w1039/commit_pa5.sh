#!/bin/bash

cd /home/albus/strata166/pr/port-all || exit 1
git add src/kernels/cuda/qsa_decode_attn.cu
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: quantize the dp4a query with one warp per 64-value group (W1041)

The OPT&2 path quantized the query with 48 of the 256 threads, each running a
serial 64-element amax scan and 64 converts (~448 instructions) while the other
208 waited at __syncthreads -- in every one of the 64 blocks of a query.  That
made the dp4a score net slower (+6.8% attn, P447/P449).

One warp per group instead: 48 groups over 8 warps, 2 values per lane, amax by a
butterfly.  max is order-independent, so d and every code are bit-identical to
the scan; only the scheduling changes.  Pattern taken from llama.cpp's
quantize_q8_1 (one warp per block, each lane its own element).

Measured (W1041, ctl vs this + ATTN_DP4A): attn 2234 -> 1982 ms at 8K (-11.3%),
4714 -> 4212 ms at 16K (-10.7%), whole prefill -1.78% / -1.61% (2xCV 0.50/0.11).
MSG
git log --oneline -1
