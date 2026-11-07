#!/usr/bin/env python3
"""W795: let the operator cap llama.cpp's MMQ tile width (J) on gfx906.

`mul_mat_q_switch_J()` picks the widest tile that fits `smpbo`, which on a GCN part with 64 KB of
LDS per CU (gfx906) leaves exactly one workgroup resident: the IQ3_S/IQ4_NL config it selects is
I=128 / J=64 / 512 threads and takes ~46 KB. Upstream made the same trade the other way for RDNA3.5
(#28195: 64-row tiles "leave enough LDS free for a second workgroup per CU"), but GCN was not touched.

Two env knobs, both no-ops when unset:

    STRATA_MMQ_TILE_J=48     cap the width search at J=48 (any of 8,16,24,32,40,48,64)
    STRATA_MMQ_TILE_LOG=1    print the pick (type, J, LDS bytes, smpbo, cap) once per call site

It only changes which instantiation is launched; every J is already compiled and the arithmetic is
the same, so the answer is bit-identical to that J being chosen by the heuristic.
"""
import io
import sys

MARK = "W795"
SIG = "void mul_mat_q_switch_J(ggml_backend_cuda_context & ctx, const mmq_args & args, cudaStream_t stream) {"
SIG_NEW = SIG + """
    // W795: the width search below takes the widest tile that fits smpbo; on a CU with 64 KB of LDS
    // that leaves a single workgroup resident. Two knobs, both inert when unset.
    static const int  w795_j_cap = [] { const char * e = std::getenv("STRATA_MMQ_TILE_J"); return e ? std::atoi(e) : 0; }();
    static const bool w795_j_log = [] { const char * e = std::getenv("STRATA_MMQ_TILE_LOG"); return e != nullptr && e[0] == '1'; }();"""

LOOP_OLD = """    for (int J = 8; J <= 128 && ntiles_J_best > 1; J += 8) {
        const ggml_cuda_mmq_config config = ggml_cuda_mmq_get_config(type, J, fallback, cc);"""
LOOP_NEW = """    for (int J = 8; J <= 128 && ntiles_J_best > 1; J += 8) {
        if (w795_j_cap > 0 && J > w795_j_cap) {
            break;
        }
        const ggml_cuda_mmq_config config = ggml_cuda_mmq_get_config(type, J, fallback, cc);"""

SW_OLD = """    switch (J_best) {
        case   8:"""
SW_NEW = """    if (w795_j_log) {   // W795
        static bool w795_said = false;   // one line per instantiation, not per dispatch
        if (!w795_said) {
            w795_said = true;
            std::fprintf(stderr, "strata: MMQ tile: type %d -> J=%d (%zu B of shared, smpbo %zu, cap %d)\\n",
                         (int) type, J_best,
                         J_best > 0 ? mmq_get_nbytes_shared(ggml_cuda_mmq_get_config(type, J_best, fallback, cc), cc) : (size_t) 0,
                         smpbo, w795_j_cap);
        }
    }
    switch (J_best) {
        case   8:"""


def main() -> int:
    path = sys.argv[1]
    src = io.open(path, encoding="utf-8").read()
    if MARK in src:
        print("already patched: %s" % path)
        return 0
    assert src.count(SIG) == 1, "anchor count %d != 1" % src.count(SIG)
    assert src.count(LOOP_OLD) == 1, "loop anchor not unique"
    assert src.count(SW_OLD) == 1, "switch anchor not unique"
    # std::getenv / std::atoi are not pulled in by common.cuh
    inc_old = "#include <cstdint>\n"
    assert src.count(inc_old) == 1, "include anchor not unique"
    src = src.replace(inc_old, inc_old + "#include <cstdlib>\n", 1)
    src = src.replace(SIG, SIG_NEW, 1)
    src = src.replace(LOOP_OLD, LOOP_NEW, 1)
    src = src.replace(SW_OLD, SW_NEW, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(src)
    print("patched %s (%d occurrences of %s)" % (path, src.count(MARK), MARK))
    return 0


if __name__ == "__main__":
    sys.exit(main())
