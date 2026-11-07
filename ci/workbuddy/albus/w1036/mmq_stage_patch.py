#!/usr/bin/env python3
"""W1036/R51b: stage the Q4_K weight-tile loads into registers (gfx906), bit-identically.

Why: `ggml_cuda_mmq_load_tiles_q4_K`'s dp4a branch (the only one gfx906 builds) does, per iteration,
ONE dependent global load (`get_int_b4(bxi->qs, txi)`) immediately consumed by one LDS store.  A thread
therefore has a single load in flight.  iacopPBK's gfx906 fork splits the same loop into
"GFX906_LOAD_TILES_Q8_0_ASYNC" / "GFX906_STORE_TILES_Q8_0_LDS_LEGACY" - load every iteration into
registers first, then store them all - so the memory system sees N loads at once.  Same values, same LDS
content, same order of stores: bit-identical; only the memory-level parallelism changes.

This ports the technique to Q4_K (their macro is Q8_0-specific, our MoE weights are Q4_K).

Usage:  python3 mmq_stage_patch.py <llama.cpp root> [--revert]
"""
import io
import os
import sys

MARK = "STRATA_GFX906_MMQ_STAGE"
ANCHOR_HEAD = """#pragma unroll
    for (int i0 = 0; i0 < I; i0 += nrows*nwarps) {
        int i = i0 + (nrows == 1 ? threadIdx.y : threadIdx.y*nrows + threadIdx.x/threads_per_row);

        if (fallback) {
            i = min(i, i_max);
        }

        const block_q4_K * bxi = (const block_q4_K *) x + kbx0 + i*stride;
        const int qs0 = get_int_b4(bxi->qs, txi);
"""

STAGED = """#if defined(__gfx906__) && defined(STRATA_GFX906_MMQ_STAGE)
    // W1036/R51b: every iteration's weight load is issued before any LDS store, so this thread has
    // `N` loads in flight instead of one dependent load per iteration.  Values, store order and the
    // LDS layout are unchanged: bit-identical, memory-level parallelism only.
    {
        constexpr int STEP = nrows*nwarps;
        constexpr int N    = (I + STEP - 1) / STEP;
        int qs_cache[N];
#pragma unroll
        for (int k = 0, i0 = 0; i0 < I; ++k, i0 += STEP) {
            int i = i0 + (nrows == 1 ? threadIdx.y : threadIdx.y*nrows + threadIdx.x/threads_per_row);
            if (fallback) {
                i = min(i, i_max);
            }
            const block_q4_K * bxi = (const block_q4_K *) x + kbx0 + i*stride;
            qs_cache[k] = get_int_b4(bxi->qs, txi);
        }
#pragma unroll
        for (int k = 0, i0 = 0; i0 < I; ++k, i0 += STEP) {
            int i = i0 + (nrows == 1 ? threadIdx.y : threadIdx.y*nrows + threadIdx.x/threads_per_row);
            if (fallback) {
                i = min(i, i_max);
            }
            x_qs[i*(MMQ_TILE_NE_K + 1) + txi] = qs_cache[k];
        }
    }
#else
#pragma unroll
    for (int i0 = 0; i0 < I; i0 += nrows*nwarps) {
        int i = i0 + (nrows == 1 ? threadIdx.y : threadIdx.y*nrows + threadIdx.x/threads_per_row);

        if (fallback) {
            i = min(i, i_max);
        }

        const block_q4_K * bxi = (const block_q4_K *) x + kbx0 + i*stride;
        const int qs0 = get_int_b4(bxi->qs, txi);
"""


def main():
    root = sys.argv[1]
    revert = "--revert" in sys.argv
    p = os.path.join(root, "ggml/src/ggml-cuda/mmq-load-tiles.cuh")
    s = io.open(p, encoding="utf-8").read()

    if revert:
        assert "STRATA_GFX906_MMQ_STAGE" in s, "nothing to revert"
        i = s.index('#if defined(__gfx906__) && defined(STRATA_GFX906_MMQ_STAGE)')
        j = s.index('#else\n' + ANCHOR_HEAD, i)
        k = s.index('#endif\n', j + len('#else\n' + ANCHOR_HEAD))
        s = s[:i] + ANCHOR_HEAD + s[k + len('#endif\n'):]
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("reverted")
        return

    assert MARK not in s, "already patched"
    assert s.count(ANCHOR_HEAD) == 1, "anchor appears %d times" % s.count(ANCHOR_HEAD)
    i = s.index(ANCHOR_HEAD)
    # the for loop ends at the first 4-space closing brace after the anchor
    j = s.index("\n    }\n", i) + len("\n    }\n")
    orig = s[i:j]
    body = orig[len(ANCHOR_HEAD):]          # the store + its #endif + the loop's closing brace
    assert body.rstrip().endswith("}"), body[-80:]
    staged = STAGED + body + "#endif // defined(__gfx906__) && defined(STRATA_GFX906_MMQ_STAGE)\n"
    s = s[:i] + staged + s[j:]
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("patched:", p)


if __name__ == "__main__":
    main()
