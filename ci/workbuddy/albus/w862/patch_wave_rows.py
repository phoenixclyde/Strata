#!/usr/bin/env python3
"""W862: give the Q8_0 wave kernel a rows-per-wave table, in the production source tree.

Why: a single-request decode runs a speculative verify window, so native_mmvq is called with
ncols about 6.  Per weight block the kernel then issues NCOLS times the activation loads and
dp4a work, and wave_launch_n hardcodes R = 1, i.e. one row per wavefront, so none of that work
is shared.  Measured on the shapes that matter, R = 2 (ncols 4..8) / R = 4 (ncols 1..2) gives
1.4-1.8x and is bitwise identical (the per-row reduction order does not change).

Default = the table below; STRATA_MMVQ_WAVE_ROWS / native_mmvq_set_wave_rows(n) overrides it,
and 1 restores the old behaviour exactly.

Backs the file up to native_mmvq.cu.w862bak first and is idempotent.
"""
import os
import shutil
import sys

SRC = "/home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu"
BAK = SRC + ".w862bak"

if not os.path.exists(BAK):
    shutil.copy2(SRC, BAK)
    print("backup ->", BAK)
else:
    print("backup already there:", BAK)

s = open(SRC, encoding="utf-8").read()
if "W862 wave rows" in s:
    print("already patched")
    sys.exit(0)

# 1) the table + knob, next to the existing g_wave_off
anchor = 'bool g_wave_off = std::getenv("STRATA_MMVQ_WAVE") && std::string(std::getenv("STRATA_MMVQ_WAVE")) == "0";'
assert anchor in s, "g_wave_off anchor missing"
add = anchor + """
// W862 wave rows: one weight block's activation loads and dp4a work are shared by R rows.
// R * NCOLS <= 12 keeps the accumulators in registers (ncols=6 with R=4 spilled and lost 40 %),
// and n_out / (4*R) >= 120 keeps at least two block waves across the 60 CUs (below that a small
// matrix gets slower, e.g. 640 rows at ncols=1: R=1 5.2 us vs R=4 10.8 us).
int g_wave_rows = -1;
int wave_rows_for(int ncols, int n_in, int n_out) {
    if (g_wave_rows > 0) return g_wave_rows;
    int R = 2;
    if (ncols <= 2 && n_in / 32 >= 32 && n_out >= 2048) R = 4;
    while (R > 1 && n_out / (4 * R) < 120) R >>= 1;
    return R;
}"""
s = s.replace(anchor, add, 1)

# 2) dispatch in wave_launch_n
old = """template<typename F, int NCOLS>
void wave_launch_n(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, cudaStream_t s) {
    const auto* w = static_cast<const typename F::Block*>(weights);
    const auto* x = static_cast<const Q81Block*>(x_q8_1);
    constexpr int R = 1;
    const unsigned blocks = unsigned((std::size_t(n_out) + 4 * R - 1) / (4 * R));
    native_mmvq_wave_kernel<F, NCOLS, R><<<blocks, 256, 0, s>>>(w, x, y, n_in, n_out);
}"""
new = """template<typename F, int NCOLS, int R>
void wave_launch_r(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, cudaStream_t s) {
    const auto* w = static_cast<const typename F::Block*>(weights);
    const auto* x = static_cast<const Q81Block*>(x_q8_1);
    const unsigned blocks = unsigned((std::size_t(n_out) + 4 * R - 1) / (4 * R));
    native_mmvq_wave_kernel<F, NCOLS, R><<<blocks, 256, 0, s>>>(w, x, y, n_in, n_out);
}
template<typename F, int NCOLS>
void wave_launch_n(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, cudaStream_t s) {
    switch (wave_rows_for(NCOLS, n_in, n_out)) {   // W862 wave rows
        case 4: wave_launch_r<F, NCOLS, 4>(weights, x_q8_1, y, n_in, n_out, s); break;
        case 2: wave_launch_r<F, NCOLS, 2>(weights, x_q8_1, y, n_in, n_out, s); break;
        default: wave_launch_r<F, NCOLS, 1>(weights, x_q8_1, y, n_in, n_out, s); break;
    }
}"""
assert old in s, "wave_launch_n body not found"
s = s.replace(old, new, 1)

# 3) exported setters at file scope (the wave family lives in an anonymous namespace)
b6 = "void native_mmvq_set_b6_rows(int mode) { g_b6_rows = mode; }"
assert b6 in s, "set_b6_rows anchor missing"
s = s.replace(b6, b6 + """
// W862 wave rows: 0 = the table above, 1 = the old one-row-per-wavefront behaviour.
void native_mmvq_set_wave_rows(int n) { g_wave_rows = n; }
int native_mmvq_wave_rows() { return g_wave_rows; }""", 1)

open(SRC, "w", encoding="utf-8", newline="\n").write(s)
print("patched", SRC, len(s), "bytes")
