"""R54: rewrite megakernel_gdn.cu's gemv_q80_body into the wave64 form.

The RDNA3 original assigns one 32-lane group a row (lane = vtid & 31) and folds four
per-lane accumulators before a 32-lane butterfly.  native_mmvq's native_mmvq_wave_kernel
uses a 64-lane wave, kbx = lane / T stepping by 64 / T, one accumulator a column, and a
64-lane butterfly.  The products and the (d0 * d1 * sumi) grouping are identical, so only
the reduction tree differs - which is exactly what mk_gdn_parity reports.
"""
from pathlib import Path
import sys

SRC = Path('D:/workbuddy_space/strata_ws/albus/w896/forks/rdna3/src/kernels/cuda/megakernel_gdn.cu')
OUT = Path('D:/workbuddy_space/strata_ws/albus/w899/megakernel_gdn.cu')

text = SRC.read_text(encoding='utf-8')
start_marker = '__device__ __forceinline__ void gemv_q80_body'
end_marker = '// ---- gdn_conv_l2_body'
i = text.index(start_marker)
j = text.index(end_marker)
# the original template line (`template <int NCOLS, bool MAP = false>`) sits right above the
# function; the replacement carries its own, so take that line out of the kept prefix too.
prev_line_start = text.rfind('\n', 0, i - 1) + 1
if text[prev_line_start:i].startswith('template <int NCOLS, bool MAP'):
    i = prev_line_start

new_fn = '''// [r54] the Q8_0 GEMV in the wave64 form: this reproduces native_mmvq's native_mmvq_wave_kernel
// exactly - a 64-lane wave, kbx = lane / T stepping by 64 / T, one accumulator a column, then a
// 64-lane butterfly - so the persistent kernel and the stock kernels are bitwise equal.
// (The RDNA3 original gave a row to a 32-lane group and folded four accumulators a lane: same
// products, different tree, i.e. parity 220,746 values.)  R = 2 rows a wave keeps the "8 rows a
// 256-thread virtual block" grid the launcher already computes (4 waves x 2 rows), which is also
// what kWaveRows returns for the qkv / z / out shapes at eight columns - the same rows a wave as
// the reference.  The per-row sum does not depend on R, so a different table entry stays bitwise.
template <int NCOLS, bool MAP>
__device__ __forceinline__ void gemv_q80_body(const Q80Block* __restrict__ w, const Q81Block* __restrict__ x,
                                              float* __restrict__ y, int n_in, int n_out, int vb, int vtid,
                                              int xs_zero = 0, const MkMat* __restrict__ mm = nullptr) {
    using F = Q80Traits;
    constexpr int R = 2;
    constexpr int BPIW = 64 / F::T;
    const int lane = vtid & 63;
    const int row0 = (vb * 4 + (vtid >> 6)) * R;
    if (row0 >= n_out) return;
    const int blocks_per_row = n_in / F::DIV;
    const int x_stride = xs_zero ? 0 : n_in / Q8K;
    const int kqs = F::kqs(lane);
    float tmp[NCOLS][R] = {};
    for (int kbx = lane / F::T; kbx < blocks_per_row; kbx += BPIW) {
        const int kby = kbx * F::KBY;
#pragma unroll
        for (int i = 0; i < R; ++i) {
            const int row = row0 + i;
            if (row >= n_out) continue;
            const Q80Block* wsrc = w + std::size_t(row) * blocks_per_row + kbx;
            if (MAP && mm->pitch > 0) {
                int add = mm->radd[0], cshift = 30, cgap = 0;
#pragma unroll
                for (int k = 1; k < 8; ++k) if (k < mm->nr && row >= mm->rlo[k]) add = mm->radd[k];
                if (mm->cw > 0) { cshift = __ffs(mm->cw) - 1; cgap = mm->cgap; }
                wsrc = w + std::size_t(row + add) * mm->pitch + kbx + mm->cadd + (kbx >> cshift) * cgap;
            }
            const typename F::W wv = F::load(wsrc, kqs);
#pragma unroll
            for (int j = 0; j < NCOLS; ++j) tmp[j][i] += F::apply(wv, x + std::size_t(j) * x_stride + kby, kqs);
        }
    }
#pragma unroll
    for (int j = 0; j < NCOLS; ++j)
#pragma unroll
        for (int i = 0; i < R; ++i) {
            float v = tmp[j][i];
#pragma unroll
            for (int off = 32; off > 0; off >>= 1) v += __shfl_xor(v, off, 64);
            if (lane == 0 && row0 + i < n_out) y[std::size_t(j) * n_out + row0 + i] = v;
        }
}

'''
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text[:i] + new_fn + text[j:], encoding='utf-8')
print('written', OUT, len((text[:i] + new_fn + text[j:]).splitlines()), 'lines')
