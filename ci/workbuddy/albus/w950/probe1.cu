// W950: minimal repro — one block_q4_K, one row, K=256, one thread, dump the intermediate terms.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <random>

struct BlockQ4K { _Float16 d; _Float16 dmin; unsigned char scales[12]; unsigned char qs[128]; };
static_assert(sizeof(BlockQ4K) == 144, "");

static __host__ __device__ inline void gsm(int j, const unsigned char * q, unsigned char * d, unsigned char * m) {
    if (j < 4) { *d = q[j] & 63; *m = q[j + 4] & 63; }
    else { *d = (q[j+4] & 0x0F) | ((q[j-4] >> 6) << 4); *m = (q[j+4] >> 4) | ((q[j] >> 6) << 4); }
}
static __host__ __device__ inline int nib(const unsigned char * qs, int kk) {  // value at sub-block offset kk (0..31)
    const int j = kk / 32, u = kk % 32;
    return (u < 16) ? (qs[16*j + u] & 0xF) : (qs[16*j + u - 16] >> 4);
}

struct Out { float acc; int sumi; int sa; float d; float dmin; int sc; int m; };

__global__ void probe(const BlockQ4K * w, const signed char * xq, const int * sumx, float * y, Out * o) {
    // one thread, serial over K = 256
    const BlockQ4K * b = w;
    float acc = 0.0f;
    int tot_d = 0, tot_a = 0;
    for (int j = 0; j < 8; j++) {
        unsigned char sc, m;
        gsm(j, b->scales, &sc, &m);
        int sumi = 0, sx = 0;
        for (int u = 0; u < 32; u++) {
            const int q = nib(b->qs, j * 32 + u);
            sumi += q * (int) xq[j * 32 + u];
            sx += (int) xq[j * 32 + u];
        }
        const float d = (float) b->d, dmin = (float) b->dmin;
        acc += d * sc * (float) sumi - dmin * m * (float) sx;
        tot_d += sumi; tot_a += sx;
    }
    y[0] = acc;
    o[0] = Out{acc, tot_d, tot_a, (float) b->d, (float) b->dmin, 0, 0};
}

int main() {
    std::mt19937 rng(7);
    BlockQ4K w;
    w.d = (_Float16) 0.0123f;
    w.dmin = (_Float16) 0.00456f;
    for (int i = 0; i < 12; i++) w.scales[i] = (unsigned char) (rng() & 0xFF);
    for (int i = 0; i < 128; i++) w.qs[i] = (unsigned char) (rng() & 0xFF);

    float x[256];
    for (auto & v : x) v = (float) ((int) (rng() % 2001) - 1000) / 500.0f;
    signed char xq[256];
    for (int i = 0; i < 256; i++) xq[i] = (signed char) lrintf(x[i] * 100.0f);   // fixed scale 0.01

    // host reference
    double ref = 0;
    for (int j = 0; j < 8; j++) {
        unsigned char sc, m; gsm(j, w.scales, &sc, &m);
        for (int u = 0; u < 32; u++) {
            const int q = nib(w.qs, j * 32 + u);
            const float xx = (float) xq[j * 32 + u] * 0.01f;
            ref += ((double) (float) w.d * sc * q - (double) (float) w.dmin * m) * xx;
        }
    }

    BlockQ4K * dw; signed char * dx; float * dy; Out * dout;
    hipMalloc(&dw, sizeof(BlockQ4K)); hipMalloc(&dx, 256); hipMalloc(&dy, 4); hipMalloc(&dout, sizeof(Out));
    hipMemcpy(dw, &w, sizeof(BlockQ4K), hipMemcpyHostToDevice);
    hipMemcpy(dx, xq, 256, hipMemcpyHostToDevice);
    probe<<<1, 1>>>(dw, dx, nullptr, dy, dout);
    printf("launch: %s\n", hipGetErrorString(hipGetLastError()));
    hipDeviceSynchronize();
    Out o; float y;
    hipMemcpy(&o, dout, sizeof(Out), hipMemcpyDeviceToHost);
    hipMemcpy(&y, dy, 4, hipMemcpyDeviceToHost);

    printf("host d=%.6f dmin=%.6f\n", (float) w.d, (float) w.dmin);
    printf("dev  d=%.6f dmin=%.6f  sumi=%d sa=%d\n", o.d, o.dmin, o.sumi, o.sa);
    printf("kernel y = %.6f\nhost  ref= %.6f\nratio = %.6f\n", y, ref, ref != 0 ? y / ref : 0.0);

    // decode one sub-block by hand to see where it diverges
    unsigned char sc, m; gsm(0, w.scales, &sc, &m);
    int sumi = 0; for (int u = 0; u < 32; u++) sumi += nib(w.qs, u) * (int) xq[u];
    printf("sub0: sc=%d m=%d sumi=%d  term=%.6f\n", sc, m, sumi,
           (float) w.d * sc * sumi * 0.01f - (float) w.dmin * m * (float) sumi * 0.01f);
    return 0;
}
