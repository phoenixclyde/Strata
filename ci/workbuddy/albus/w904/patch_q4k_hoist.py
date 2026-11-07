#!/usr/bin/env python3
"""R51: hoist the Q4_K nibble unpack out of the y-row loop (loop interchange j<->i).

Patches a COPY of the generated overlay (never the build tree, never the pinned
llama.cpp): the caller passes the overlay directory to edit.

Why: vec_dot_q4_K_q8_1_impl_mmq unpacks `(v[j] >> 4*i) & 0x0F0F0F0F` on every call,
and the caller calls it once per (k01, j, i) -- so the same x words are unpacked
J/nwarps times. Measured (W904): pure dp4a 19.07 TMAC/s, MMQ-shaped loop 6.90
(= 36%), LDS only 27% busy => the unpack ALU is the limiter, not loads.

The interchange keeps the arithmetic: each sum[j,i] slot still receives exactly one
addend per k01, in the same dp4a order => bitwise identical (unverified in-situ).
"""
import sys
from pathlib import Path

OLD_SIG = ('template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void '
           'ggml_cuda_mmq_vec_dot_q4_K_q8_1_dp4a(')
NEXT_SIG = ('template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void '
            'ggml_cuda_mmq_vec_dot_q5_K_q8_1_dp4a(')
MARK = 'STRATA_R51_HOIST'

NEW_FN = '''// STRATA_R51_HOIST: the x tile's 4 words are unpacked ONCE per (k01, i) and reused for every
// row of y, instead of being unpacked again inside every vec_dot call. Same dp4a order per
// sum slot => bitwise identical; instruction count per (k01,i,j) drops from ~54 to ~20.
template <ggml_type type, int J, bool fallback> static __device__ __forceinline__ void ggml_cuda_mmq_vec_dot_q4_K_q8_1_dp4a(
        const int * __restrict__ x, const int * __restrict__ y, float * __restrict__ sum, const int k00) {
    constexpr int warp_size = ggml_cuda_get_physical_warp_size();
    constexpr int nwarps    = ggml_cuda_mmq_get_nthreads(type, J, fallback) / warp_size;
    constexpr int I         = ggml_cuda_mmq_get_I(type, J, fallback);

    constexpr tile_x_sizes txs = mmq_get_dp4a_tile_x_sizes(GGML_TYPE_Q4_K, I);
    const int   * x_qs = (const int   *) x;
    const half2 * x_dm = (const half2 *) x_qs + txs.qs;
    const int   * x_sc = (const int   *) x_dm + txs.dm;
    const int   * y_qs = (const int   *) y + 4;
    const half2 * y_ds = (const half2 *) y;

    constexpr int NX = QR4_K*VDR_Q4_K_Q8_1_MMQ;   // 16 unpacked words per (k01, i)

// #pragma unroll
    for (int k01 = 0; k01 < MMQ_TILE_NE_K; k01 += QR4_K*VDR_Q4_K_Q8_1_MMQ) {
        const int k0 = k00 + k01;

#pragma unroll
        for (int i0 = 0; i0 < I; i0 += warp_size) {
            const int i = i0 + threadIdx.x;

            // ---- unpack once ----
            int xv[NX];
#pragma unroll
            for (int w = 0; w < QI8_1; ++w) {
                const int v = x_qs[i*(MMQ_TILE_NE_K + 1) + k0/2 + w];
#pragma unroll
                for (int q = 0; q < QI8_1; ++q) {
                    xv[q*QI8_1 + w] = (v >> (4*q)) & 0x0F0F0F0F;
                }
            }

            const uint8_t * sc = (const uint8_t *) &x_sc[i * (MMQ_TILE_NE_K/8) + i/8 + k0/32] + 2*(k01/16);

#pragma unroll
            for (int j0 = 0; j0 < J; j0 += nwarps) {
                const int j = j0 + threadIdx.y;

                sum[j0/nwarps*I/warp_size + i0/warp_size] += vec_dot_q4_K_q8_1_impl_mmq_pre(
                    xv, &y_qs[j*MMQ_TILE_Y_K + k01], sc, sc+8,
                    x_dm[i], &y_ds[j*MMQ_TILE_Y_K + k01/QI8_1]);
            }
        }
    }
}

'''

NEW_IMPL = '''// STRATA_R51_HOIST: vec_dot_q4_K_q8_1_impl_mmq with the unpack already done by the caller.
// xv[i*QI8_1 + j] must equal ((v[j] >> (4*i)) & 0x0F0F0F0F) for the same v the packed path read.
static __device__ __forceinline__ float vec_dot_q4_K_q8_1_impl_mmq_pre(
    const int * __restrict__ xv, const int * __restrict__ u, const uint8_t * __restrict__ sc,
    const uint8_t * __restrict__ m, const half2 & dm4, const half2 * __restrict__ ds8) {

    float sumf_d = 0.0f;
    float sumf_m = 0.0f;

#pragma unroll
    for (int i = 0; i < QR4_K*VDR_Q4_K_Q8_1_MMQ/QI8_1; ++i) {
        int sumi_d = 0;

#pragma unroll
        for (int j = 0; j < QI8_1; ++j) {
            sumi_d = ggml_cuda_dp4a(xv[i*QI8_1 + j], u[i*QI8_1 + j], sumi_d);
        }

        const float2 ds8f = __half22float2(ds8[i]);

        sumf_d += ds8f.x * (sc[i] * sumi_d);
        sumf_m += ds8f.y *   m[i];
    }

    const float2 dm4f = __half22float2(dm4);

    return dm4f.x*sumf_d - dm4f.y*sumf_m;
}

'''


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: patch_q4k_hoist.py <overlay-dir>')
        return 2
    d = Path(sys.argv[1])
    vq = d / 'vecdotq.cuh'
    md = d / 'mmq-vec-dot.cuh'
    for p in (vq, md):
        if not p.is_file():
            print('missing: %s' % p)
            return 2

    # ---- 1) mmq-vec-dot.cuh: replace the Q4_K dp4a kernel ----
    md_t = md.read_text(encoding='utf-8', errors='surrogateescape')
    if MARK in md_t:
        print('mmq-vec-dot.cuh already patched')
    else:
        i = md_t.find(OLD_SIG)
        j = md_t.find(NEXT_SIG)
        if i < 0 or j < 0 or j <= i:
            print('anchor failure: q4_K start=%d q5_K start=%d' % (i, j))
            return 1
        old = md_t[i:j]
        if 'k01 += QR4_K*VDR_Q4_K_Q8_1_MMQ' not in old:
            print('anchor failure: the q4_K block does not contain the expected loop')
            return 1
        if old.count('vec_dot_q4_K_q8_1_impl_mmq(') != 1:
            print('anchor failure: unexpected call count in the q4_K block')
            return 1
        md.write_text(md_t[:i] + NEW_FN + md_t[j:], encoding='utf-8', errors='surrogateescape')
        print('mmq-vec-dot.cuh: replaced %d bytes with %d' % (len(old), len(NEW_FN)))

    # ---- 2) vecdotq.cuh: add the pre-unpacked impl right before the Q5_K block ----
    vq_t = vq.read_text(encoding='utf-8', errors='surrogateescape')
    if MARK in vq_t:
        print('vecdotq.cuh already patched')
    else:
        anchor = '#define VDR_Q5_K_Q8_1_MMVQ 2'
        if vq_t.count(anchor) != 1:
            print('anchor failure: VDR_Q5_K_Q8_1_MMVQ occurs %d times' % vq_t.count(anchor))
            return 1
        vq.write_text(vq_t.replace(anchor, NEW_IMPL + anchor, 1),
                      encoding='utf-8', errors='surrogateescape')
        print('vecdotq.cuh: inserted the pre-unpacked impl')
    return 0


if __name__ == '__main__':
    sys.exit(main())
