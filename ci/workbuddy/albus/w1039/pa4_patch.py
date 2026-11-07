#!/usr/bin/env python3
"""W1039 pa4: put the gfx906 OPT dispatch INSIDE the query-swizzle branch.

Why: production runs with STRATA_GFX906_TUNED=1, whose rounding-level recipe turns
GFX906_ATTN_QUERY_SWIZZLE on (engine banner: "the rounding-level recipe is on ... GFX906_ATTN_QUERY_SWIZZLE").
The W1037 wiring sits before the dispatch and is guarded by `!use_query_swizzle`, so on the production path it
was skipped again -- which is exactly what the W1039 window measured: `qsa attn` 2238 -> 2235 ms at 8K,
4731 -> 4718 ms at 16K with ATTN_DP4A=1 (both inside noise).

Also fixes a latent correctness hole: STRATA_ATTN_OPT_DISPATCH only had cases 1/2/4, so a combination
(e.g. DPP|LDS_PAD = 5) fell through `default: break;` and the function returned without launching anything.
"""
import io
import shutil

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"

OLD_DISPATCH = """#define STRATA_ATTN_OPT_DISPATCH(LAUNCH, M)                                                              \\
    switch (opt) {                                                                                        \\
        case 1: LAUNCH(M, 1); break;                                                                      \\
        case 2: LAUNCH(M, 2); break;                                                                      \\
        case 4: LAUNCH(M, 4); break;                                                                      \\
        default: break;                                                                                   \\
    }
"""

NEW_DISPATCH = """#define STRATA_ATTN_OPT_DISPATCH(LAUNCH, M)                                                              \\
    switch (opt) {                                                                                        \\
        case 1: LAUNCH(M, 1); break;                                                                      \\
        case 2: LAUNCH(M, 2); break;                                                                      \\
        case 3: LAUNCH(M, 3); break;                                                                      \\
        case 4: LAUNCH(M, 4); break;                                                                      \\
        case 5: LAUNCH(M, 5); break;                                                                      \\
        case 6: LAUNCH(M, 6); break;                                                                      \\
        case 7: LAUNCH(M, 7); break;                                                                      \\
        default: break;                                                                                   \\
    }

// W1039: the same dispatch for the query-swizzle path -- the production recipe keeps GFX906_ATTN_QUERY_SWIZZLE on,
// so the switches above were still unreachable.  Swizzle and reduce12 stay what production uses; only OPT differs.
#define STRATA_ATTN_OPT_SWZ(M, O)                                                                         \\
    attn_chunk_kernel<M, false, true, true, O><<<grid, THREADS, 0, st>>>(                                 \\
        q, pools, ids, steps, (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l,       \\
        n_chunks, (int) cap, stride)
"""

ANCHOR = """        static const bool reduce12 = [] {
            const char* v = std::getenv("STRATA_GFX906_ATTN_REDUCE12");
            return v && v[0] == '1' && v[1] == '\\0';
        }();
        if (reduce12) {
"""

INSERT = """        static const bool reduce12 = [] {
            const char* v = std::getenv("STRATA_GFX906_ATTN_REDUCE12");
            return v && v[0] == '1' && v[1] == '\\0';
        }();
        // W1039: this is the instantiation production actually runs (swizzle + reduce12), so the OPT switch has to
        // be applied here, not only on the plain <M> path above.
        if (const int opt_sw = gfx906_attn_opt(); opt_sw != 0) {
            if (kv_mode == 3) STRATA_ATTN_OPT_DISPATCH_SWZ(STRATA_ATTN_OPT_SWZ, 3)
            else              STRATA_ATTN_OPT_DISPATCH_SWZ(STRATA_ATTN_OPT_SWZ, 1)
            return;
        }
        if (reduce12) {
"""

DISPATCH_SWZ = """
#define STRATA_ATTN_OPT_DISPATCH_SWZ(LAUNCH, M)                                                           \\
    switch (opt_sw) {                                                                                     \\
        case 1: LAUNCH(M, 1); break;                                                                      \\
        case 2: LAUNCH(M, 2); break;                                                                      \\
        case 3: LAUNCH(M, 3); break;                                                                      \\
        case 4: LAUNCH(M, 4); break;                                                                      \\
        case 5: LAUNCH(M, 5); break;                                                                      \\
        case 6: LAUNCH(M, 6); break;                                                                      \\
        case 7: LAUNCH(M, 7); break;                                                                      \\
        default: break;                                                                                   \\
    }
"""


def main():
    s = io.open(P, encoding="utf-8").read()
    shutil.copy2(P, P + ".bak_pa4")

    assert OLD_DISPATCH in s, "dispatch macro anchor missing"
    s = s.replace(OLD_DISPATCH, NEW_DISPATCH + DISPATCH_SWZ, 1)

    assert ANCHOR in s, "swizzle anchor missing"
    s = s.replace(ANCHOR, INSERT, 1)

    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("patched:", P)
    for k in ("STRATA_ATTN_OPT_SWZ", "STRATA_ATTN_OPT_DISPATCH_SWZ", "opt_sw"):
        print("  %-28s %d" % (k, s.count(k)))


if __name__ == "__main__":
    main()
