// q8_wave_lab.cu -- W862: a self-contained stand-in for the production Q8_0 wave kernel, so the
// rows-per-wave / weight-layout question can be measured without rebuilding a 3 000-line TU.
//
// The arithmetic is copied from SmallTraits<Q80Block,8> in native_mmvq.cu:
//   34-byte block { half d; int8 qs[32] }; four lanes cover one block, each taking two ints
//   (eight int8) out of `qs`, which sits at byte offset 2 -> every 8-byte read is two u16 loads.
//   One wavefront (64 lanes) handles R rows and NCOLS activation columns; the reduction is a
//   64-lane butterfly and lane 0 stores d_w * d_x * sum(q_w . q_x).
//
// Three things are swept:
//   R        rows per wavefront        (1 = production; the activation loads and the dp4a work of
//                                       one weight block are shared by R rows)
//   layout   L0 = GGUF's 34-byte blocks (offset 2, 2-byte aligned, 4 x u16 per 8 bytes)
//            L1 = the same bytes split into a scale array + 32-byte-aligned qs (one 8-byte load)
//   NCOLS    1 (plain decode) vs 6 (a --spec 4 verify window, what a single request actually runs)
//
//   q8_wave_lab [--iters 40] [--bw 711] [--check]
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>

#define CK(x)                                                                 \
    do {                                                                      \
        hipError_t e_ = (x);                                                  \
        if (e_ != hipSuccess) {                                               \
            std::printf("%s:%d %s\n", __FILE__, __LINE__, hipGetErrorString(e_)); \
            std::exit(1);                                                     \
        }                                                                     \
    } while (0)

struct Q80 { __half d; signed char qs[32]; };   // 34 B, GGUF layout
static_assert(sizeof(Q80) == 34, "Q80 must be 34 bytes");
struct Q81 { __half2 ds; unsigned char qs[32]; };   // 36 B
static_assert(sizeof(Q81) == 36, "Q81 must be 36 bytes");

// L1: the same quantised bytes, but scales split out so qs lands on a 32-byte boundary.
struct Split {
    const __half* d;          // one scale per 32 elements
    const signed char* qs;    // 32-byte blocks, aligned
};

__device__ __forceinline__ int dot4(int a, int b, int c) { return __builtin_amdgcn_sdot4(a, b, c, false); }

template <int NCOLS, int R, int LAYOUT>
__global__ void wave_kernel(const Q80* __restrict__ w34, const Split wsplit,
                            const Q81* __restrict__ x, float* __restrict__ y, int n_in, int n_out) {
    const int lane = int(threadIdx.x) & 63;
    const int row0 = (int(blockIdx.x) * 4 + (int(threadIdx.x) >> 6)) * R;
    if (row0 >= n_out) return;
    const int bpr = n_in / 32;
    const int kqs = 2 * (lane % 4);
    float tmp[NCOLS][R] = {};
    for (int kbx = lane / 4; kbx < bpr; kbx += 16) {
#pragma unroll
        for (int i = 0; i < R; ++i) {
            if (row0 + i >= n_out) continue;
            const int row = row0 + i;
            int v[2];
            float d0;
            if (LAYOUT == 0) {
                const Q80* wb = w34 + (size_t) row * bpr + kbx;
                const unsigned short* p = reinterpret_cast<const unsigned short*>(wb->qs);
                // production uses ldg_nc_u16 (__ldg): non-coherent, no L1 write-allocate
                v[0] = int(__ldg(p + kqs + 0)) | (int(__ldg(p + kqs + 1)) << 16);
                v[1] = int(__ldg(p + kqs + 2)) | (int(__ldg(p + kqs + 3)) << 16);
                d0 = __half2float(__ldg(&wb->d));
            } else {
                const long base = (long) row * bpr + kbx;
                const int2 vv = *reinterpret_cast<const int2*>(wsplit.qs + base * 32 + kqs * 4);
                v[0] = vv.x; v[1] = vv.y;
                d0 = __half2float(wsplit.d[base]);
            }
#pragma unroll
            for (int j = 0; j < NCOLS; ++j) {
                const Q81* xb = x + (size_t) j * bpr + kbx;
                const int* u = reinterpret_cast<const int*>(xb->qs);
                int sumi = dot4(v[0], __ldg(u + kqs + 0), 0);
                sumi = dot4(v[1], __ldg(u + kqs + 1), sumi);
                tmp[j][i] += d0 * __low2float(xb->ds) * float(sumi);
            }
        }
    }
#pragma unroll
    for (int j = 0; j < NCOLS; ++j)
#pragma unroll
        for (int i = 0; i < R; ++i) {
            float v = tmp[j][i];
#pragma unroll
            for (int off = 32; off > 0; off >>= 1) v += __shfl_xor(v, off, 64);
            if (lane == 0 && row0 + i < n_out) y[(size_t) j * n_out + row0 + i] = v;
        }
}

// plain one-lane-per-row reference, for the parity check only
__global__ void ref_kernel(const Q80* __restrict__ w, const Q81* __restrict__ x, float* __restrict__ y,
                           int n_in, int n_out, int ncols) {
    const int row = int(blockIdx.x) * int(blockDim.x) + int(threadIdx.x);
    if (row >= n_out) return;
    const int bpr = n_in / 32;
    for (int j = 0; j < ncols; ++j) {
        double acc = 0;
        for (int b = 0; b < bpr; ++b) {
            const Q80* wb = w + (size_t) row * bpr + b;
            const Q81* xb = x + (size_t) j * bpr + b;
            int sumi = 0;
            for (int e = 0; e < 32; ++e) sumi += int(wb->qs[e]) * int((signed char) xb->qs[e]);
            acc += double(__half2float(wb->d)) * double(__low2float(xb->ds)) * double(sumi);
        }
        y[(size_t) j * n_out + row] = float(acc);
    }
}

struct Shape { const char* what; int n_in, n_out; };
static const Shape SHAPES[] = {
    {"qkv  2560->10240", 2560, 10240},
    {"g/u  2560->640  ", 2560, 640},
    {"down  640->2560 ", 640, 2560},
    {"hcup  320->10240", 320, 10240},
};
static const int NSH = 4;

template <int NCOLS, int R, int LAYOUT>
static float run(const Q80* w, const Split& sp, const Q81* x, float* y, const Shape& s, int iters) {
    const unsigned blocks = unsigned((s.n_out + 4 * R - 1) / (4 * R));
    for (int i = 0; i < 3; ++i) wave_kernel<NCOLS, R, LAYOUT><<<blocks, 256>>>(w, sp, x, y, s.n_in, s.n_out);
    hipEvent_t a, b; hipEventCreate(&a); hipEventCreate(&b);
    hipEventRecord(a);
    for (int i = 0; i < iters; ++i) wave_kernel<NCOLS, R, LAYOUT><<<blocks, 256>>>(w, sp, x, y, s.n_in, s.n_out);
    hipEventRecord(b);
    CK(hipEventSynchronize(b));
    float ms = 0; hipEventElapsedTime(&ms, a, b);
    hipEventDestroy(a); hipEventDestroy(b);
    return 1000.0f * ms / iters;
}

int main(int argc, char** argv) {
    int iters = 40, do_check = 0;
    double bw = 711.0;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--iters" && i + 1 < argc) iters = std::atoi(argv[++i]);
        if (a == "--bw" && i + 1 < argc) bw = std::atof(argv[++i]);
        if (a == "--check") do_check = 1;
    }
    hipDeviceProp_t prop; CK(hipGetDeviceProperties(&prop, 0));
    int cus = 0; CK(hipDeviceGetAttribute(&cus, hipDeviceAttributeMultiprocessorCount, 0));
    std::printf("q8_wave_lab: %s | %d CU | ref %.0f GB/s\n", prop.name, cus, bw);

    std::mt19937 rng(7);
    // one layer's worth, allocated once per shape (small: the card is 97%% full)
    for (int si = 0; si < NSH; ++si) {
        const Shape& s = SHAPES[si];
        const size_t bpr = s.n_in / 32, nblk = bpr * s.n_out;
        const size_t wbytes = nblk * 34;
        std::vector<unsigned char> hw(wbytes);
        for (size_t b = 0; b < nblk; ++b) {
            hw[b * 34] = 0x1f; hw[b * 34 + 1] = 0x21;
            for (int k = 0; k < 32; ++k) hw[b * 34 + 2 + k] = (unsigned char) (rng() & 0xff);
        }
        std::vector<__half> hd(nblk);
        std::vector<signed char> hqs(nblk * 32);
        for (size_t b = 0; b < nblk; ++b) {
            std::memcpy(&hd[b], &hw[b * 34], 2);
            std::memcpy(&hqs[b * 32], &hw[b * 34 + 2], 32);
        }
        Q80* w = nullptr; Split sp{}; signed char* dq = nullptr; __half* dd = nullptr;
        CK(hipMalloc(&w, wbytes));
        CK(hipMemcpy(w, hw.data(), wbytes, hipMemcpyHostToDevice));
        CK(hipMalloc(&dq, nblk * 32)); CK(hipMemcpy(dq, hqs.data(), nblk * 32, hipMemcpyHostToDevice));
        CK(hipMalloc(&dd, nblk * 2));  CK(hipMemcpy(dd, hd.data(), nblk * 2, hipMemcpyHostToDevice));
        sp.qs = dq; sp.d = dd;

        const int maxc = 6;
        std::vector<float> hx((size_t) s.n_in * maxc);
        for (auto& v : hx) v = std::normal_distribution<float>(0.f, 1.f)(rng);
        // quantise on the host into Q8_1 (d = max/127, s = sum, both fp16)
        std::vector<unsigned char> hq((size_t) (s.n_in / 32) * maxc * 36);
        for (int j = 0; j < maxc; ++j)
            for (size_t b = 0; b < bpr; ++b) {
                const float* src = hx.data() + (size_t) j * s.n_in + b * 32;
                float amax = 0, sum = 0;
                for (int k = 0; k < 32; ++k) { amax = std::max(amax, std::fabs(src[k])); sum += src[k]; }
                const float d = amax / 127.0f;
                __half dh = __float2half(d), sh = __float2half(sum);
                unsigned char* dst = hq.data() + ((size_t) j * bpr + b) * 36;
                std::memcpy(dst, &dh, 2); std::memcpy(dst + 2, &sh, 2);
                for (int k = 0; k < 32; ++k)
                    dst[4 + k] = (unsigned char) (signed char) (d != 0 ? (int) std::lround(src[k] / d) : 0);
            }
        Q81* x = nullptr; float* y = nullptr;
        CK(hipMalloc(&x, hq.size())); CK(hipMemcpy(x, hq.data(), hq.size(), hipMemcpyHostToDevice));
        CK(hipMalloc(&y, (size_t) s.n_out * maxc * 4));

        std::printf("\n%s  %.2f MB  bpr=%zu\n", s.what, wbytes / 1e6, bpr);
        std::printf("  %-8s %-4s %-6s %9s %10s %8s\n", "layout", "R", "ncols", "us", "GB/s", "%bw");
        for (int lay = 0; lay < 2; ++lay) {
            for (int r : {1, 2, 4}) {
                for (int c : {1, 6}) {
                    float us = 0;
                    if (lay == 0) {
                        us = (c == 1) ? (r == 1 ? run<1, 1, 0>(w, sp, x, y, s, iters)
                                                : r == 2 ? run<1, 2, 0>(w, sp, x, y, s, iters)
                                                         : run<1, 4, 0>(w, sp, x, y, s, iters))
                                      : (r == 1 ? run<6, 1, 0>(w, sp, x, y, s, iters)
                                                : r == 2 ? run<6, 2, 0>(w, sp, x, y, s, iters)
                                                         : run<6, 4, 0>(w, sp, x, y, s, iters));
                    } else {
                        us = (c == 1) ? (r == 1 ? run<1, 1, 1>(w, sp, x, y, s, iters)
                                                : r == 2 ? run<1, 2, 1>(w, sp, x, y, s, iters)
                                                         : run<1, 4, 1>(w, sp, x, y, s, iters))
                                      : (r == 1 ? run<6, 1, 1>(w, sp, x, y, s, iters)
                                                : r == 2 ? run<6, 2, 1>(w, sp, x, y, s, iters)
                                                         : run<6, 4, 1>(w, sp, x, y, s, iters));
                    }
                    // weight bytes per column-vector / 6 so ncols=6 stays comparable per position
                    const double gbs = wbytes / (us * 1e3);
                    std::printf("  %-8s %-4d %-6d %9.1f %10.1f %7.1f%%\n", lay ? "split" : "gguf", r, c, us,
                                gbs * (c == 6 ? 6.0 : 1.0), 100.0 * gbs * (c == 6 ? 6.0 : 1.0) / bw);
                }
            }
        }

        if (do_check) {
            // R must be a pure scheduling change: same per-row reduction order, so the outputs
            // have to be bitwise equal.  (An external reference is not needed for that claim, and
            // a hand-rolled one only adds its own bugs.)
            const int c = 6;
            std::vector<float> base((size_t) s.n_out * c), got((size_t) s.n_out * c);
            wave_kernel<6, 1, 0><<<(s.n_out + 3) / 4, 256>>>(w, sp, x, y, s.n_in, s.n_out);
            CK(hipMemcpy(base.data(), y, base.size() * 4, hipMemcpyDeviceToHost));
            for (int r : {2, 4}) {
                if (r == 2) wave_kernel<6, 2, 0><<<(s.n_out + 7) / 8, 256>>>(w, sp, x, y, s.n_in, s.n_out);
                else        wave_kernel<6, 4, 0><<<(s.n_out + 15) / 16, 256>>>(w, sp, x, y, s.n_in, s.n_out);
                CK(hipMemcpy(got.data(), y, got.size() * 4, hipMemcpyDeviceToHost));
                size_t diff = 0; double m = 0;
                for (size_t i = 0; i < base.size(); ++i)
                    if (base[i] != got[i]) { ++diff; m = std::max(m, (double) std::fabs(base[i] - got[i])); }
                std::printf("  R=%d vs R=1: %s  diff=%zu/%zu  max|d|=%.3g\n", r,
                            diff ? "MISMATCH" : "bitwise-equal", diff, base.size(), m);
            }
        }
        hipFree(w); hipFree(dq); hipFree(dd); hipFree(x); hipFree(y);
    }
    return 0;
}
