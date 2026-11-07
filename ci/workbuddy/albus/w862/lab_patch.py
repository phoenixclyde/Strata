#!/usr/bin/env python3
"""W862: make the Q8_0 wave kernel's rows-per-wave (R) selectable, in a COPY of native_mmvq.cu.

The production kernel hardcodes `constexpr int R = 1` in wave_launch_n, i.e. one row per
wavefront, so at ncols=6 every row re-reads the six activation vectors (6 x 2560 x 36/32 =
17.3 KB, larger than a gfx906 CU's 16 KB L1).  This copy keeps R as a template parameter and
picks it from STRATA_MMVQ_WAVE_ROWS / native_mmvq_set_wave_rows, defaulting to 1 = the exact
production behaviour.  Nothing in the production tree is touched.
"""
import os
import shutil
import sys

SRC = "/home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu"
DST_DIR = "/home/albus/w862_lab"
DST = DST_DIR + "/native_mmvq_lab.cu"

os.makedirs(DST_DIR, exist_ok=True)
s = open(SRC, encoding="utf-8").read()

# 1) knob next to the existing g_wave_off
anchor = 'bool g_wave_off = std::getenv("STRATA_MMVQ_WAVE") && std::string(std::getenv("STRATA_MMVQ_WAVE")) == "0";'
assert anchor in s, "anchor g_wave_off not found"
add = anchor + """
// W862 lab: rows per wavefront (1 = production behaviour).
int g_wave_rows = -1;
int wave_rows() {
    if (g_wave_rows < 0) { const char* v = std::getenv("STRATA_MMVQ_WAVE_ROWS"); g_wave_rows = v ? std::atoi(v) : 1; }
    return g_wave_rows;
}
"""
s = s.replace(anchor, add, 1)

# 2) R as a template parameter + runtime dispatch
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
    switch (wave_rows()) {
        case 2: wave_launch_r<F, NCOLS, 2>(weights, x_q8_1, y, n_in, n_out, s); break;
        case 4: wave_launch_r<F, NCOLS, 4>(weights, x_q8_1, y, n_in, n_out, s); break;
        default: wave_launch_r<F, NCOLS, 1>(weights, x_q8_1, y, n_in, n_out, s); break;
    }
}"""
assert old in s, "wave_launch_n body not found"
s = s.replace(old, new, 1)

# 3) 导出符号必须落在 strata::kernels 的文件作用域（wave 那一族在匿名命名空间里，
#    放进去就导出不了），所以挂在已有的 set_b6_rows 定义旁边。
b6 = "void native_mmvq_set_b6_rows(int mode) { g_b6_rows = mode; }"
assert b6 in s, "set_b6_rows anchor not found"
s = s.replace(b6, b6 + """
// W862 lab: rows per wavefront for the AMD wave kernel (1 = production behaviour).
void native_mmvq_set_wave_rows(int n) { g_wave_rows = n; }
int native_mmvq_wave_rows() { return wave_rows(); }""", 1)

open(DST, "w", encoding="utf-8", newline="\n").write(s)
print("wrote", DST, len(s), "bytes")
