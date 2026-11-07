#!/usr/bin/env python3
"""H1: 0.9.0 树里把 #31247 的 Q8_1 修正和手写回退成 pin 的语义（Σx，量化前，float）。

只改 quantize_mmq_q8_1 的 DS4/D2S6 分支，别的一律不动；这样 4% 若回来就说明这条是元凶。
"""
import pathlib, sys

p = pathlib.Path("/home/albus/strata166/w1031/llama_v090_h1/ggml/src/ggml-cuda/quantize.cu")
s = p.read_text()

new = """    float sum = 0.0f;
    if (ds_layout != MMQ_Q8_1_DS_LAYOUT_D4) {
        int sum_q = int(q.x) + int(q.y) + int(q.z) + int(q.w);

        // Calculate sums across vals_per_sum/4 threads.
#pragma unroll
        for (int offset = vals_per_sum/8; offset > 0; offset >>= 1) {
            sum_q += __shfl_xor_sync(0xFFFFFFFF, sum_q, offset, WARP_SIZE);
        }

        sum = d * float(sum_q);
    }
"""
old = """    float sum;
    if (ds_layout != MMQ_Q8_1_DS_LAYOUT_D4) {
        sum = xi.x + xi.y + xi.z + xi.w;

        // Calculate sums across vals_per_sum/4 threads.
#pragma unroll
        for (int offset = vals_per_sum/8; offset > 0; offset >>= 1) {
            sum += __shfl_xor_sync(0xFFFFFFFF, sum, offset, WARP_SIZE);
        }
    }
"""
n = s.count(new)
print("hits:", n)
if n != 1:
    sys.exit(1)
p.write_text(s.replace(new, old, 1))
print("patched quantize_mmq_q8_1 -> pin semantics")
