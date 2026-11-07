// W1039 / R104 probe: does gfx906 (MI50) actually support HIP virtual memory (VMM)?
// The tree compiles the elastic K/V out on gfx906 (vmm.cpp:167  #if ... && !defined(STRATA_HIP_GFX906)),
// while the HIP implementation itself already fails closed on a runtime attribute
// (hipDeviceAttributeVirtualMemoryManagementSupported).  So the only open question is empirical:
// attribute + a full reserve/create/map/access/write/read/unmap cycle.
// Footprint: 64 MiB of address space, 2 x 2 MiB of real VRAM, ~1 s.  Does not touch the engine.
#include <hip/hip_runtime.h>

#include <cstdio>

#define CK(expr)                                                                     \
    do {                                                                             \
        hipError_t _e = (expr);                                                       \
        std::printf("%-58s -> %d %-28s\n", #expr, (int) _e, hipGetErrorString(_e));   \
        if (_e != hipSuccess) { std::fflush(stdout); hipGetLastError(); }             \
    } while (0)

static __global__ void fill(int* p, int n, int v) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) p[i] = v;
}

static __global__ void check(const int* p, int n, int v, int* bad) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n && p[i] != v) atomicAdd(bad, 1);
}

static int run_check(int* region, int n, int expect, const char* what) {
    int* bad = nullptr;
    if (hipMalloc(&bad, sizeof(int)) != hipSuccess) { std::printf("%s: hipMalloc bad FAILED\n", what); return -1; }
    if (hipMemset(bad, 0, sizeof(int)) != hipSuccess) { std::printf("%s: memset bad FAILED\n", what); return -1; }
    check<<<(n + 255) / 256, 256>>>(region, n, expect, bad);
    int host = -1;
    const hipError_t e1 = hipDeviceSynchronize();
    const hipError_t e2 = hipMemcpy(&host, bad, sizeof(int), hipMemcpyDeviceToHost);
    (void) hipFree(bad);
    if (e1 != hipSuccess || e2 != hipSuccess) { std::printf("%s: kernel/memcpy FAILED (%s)\n", what, hipGetErrorString(e1 != hipSuccess ? e1 : e2)); return -1; }
    std::printf("%-58s -> %s (mismatch=%d of %d)\n", what, host == 0 ? "OK" : "WRONG", host, n);
    return host;
}

int main() {
    int dev = 0;
    CK(hipGetDevice(&dev));

    hipDeviceProp_t prop_dev{};
    CK(hipGetDeviceProperties(&prop_dev, dev));
    std::printf("device                     = %s (gcnArchName %s)\n", prop_dev.name, prop_dev.gcnArchName);

    int vmm = -1;
    CK(hipDeviceGetAttribute(&vmm, hipDeviceAttributeVirtualMemoryManagementSupported, dev));
    std::printf("VMM attribute              = %d   <-- 1 means the runtime says yes\n", vmm);

    size_t free_before = 0, total = 0;
    CK(hipMemGetInfo(&free_before, &total));
    std::printf("VRAM free before           = %.1f MiB of %.1f MiB\n", free_before / 1048576.0, total / 1048576.0);

    hipMemAllocationProp p{};
    p.type = hipMemAllocationTypePinned;
    p.requestedHandleType = hipMemHandleTypeNone;
    p.location.type = hipMemLocationTypeDevice;
    p.location.id = dev;

    size_t gran = 0;
    CK(hipMemGetAllocationGranularity(&gran, &p, hipMemAllocationGranularityMinimum));
    std::printf("minimum granularity        = %zu B (%.2f MiB)\n", gran, gran / 1048576.0);
    if (gran == 0) { std::printf("RESULT: NO VMM (no granularity)\n"); return 2; }

    const size_t chunk = gran;                 // 2 MiB-ish
    const size_t range_bytes = 64ull << 20;    // the address range the tree would reserve for the K/V
    void* base = nullptr;
    CK(hipMemAddressReserve(&base, range_bytes, 0, 0, 0));
    if (base == nullptr) { std::printf("RESULT: NO VMM (reserve failed)\n"); return 3; }
    std::printf("reserved                   = %zu MiB at %p\n", range_bytes >> 20, base);

    hipMemGenericAllocationHandle_t h0 = nullptr, h1 = nullptr;
    CK(hipMemCreate(&h0, chunk, &p, 0));
    if (h0 == nullptr) { std::printf("RESULT: NO VMM (create failed)\n"); return 4; }
    CK(hipMemMap((hipDeviceptr_t) base, chunk, 0, h0, 0));
    hipMemAccessDesc acc{};
    acc.location.type = hipMemLocationTypeDevice;
    acc.location.id = dev;
    acc.flags = hipMemAccessFlagsProtReadWrite;
    CK(hipMemSetAccess((hipDeviceptr_t) base, chunk, &acc, 1));

    const int n = (int) (chunk / sizeof(int));
    int* r0 = (int*) base;
    fill<<<(n + 255) / 256, 256>>>(r0, n, 7);
    CK(hipDeviceSynchronize());
    const int bad0 = run_check(r0, n, 7, "chunk 0 write/read after map");

    // the second chunk, mapped at another offset of the same range: this is what the elastic K/V does as context grows
    CK(hipMemCreate(&h1, chunk, &p, 0));
    CK(hipMemMap((hipDeviceptr_t) ((char*) base + gran), chunk, 0, h1, 0));
    CK(hipMemSetAccess((hipDeviceptr_t) ((char*) base + gran), chunk, &acc, 1));
    int* r1 = (int*) ((char*) base + gran);
    fill<<<(n + 255) / 256, 256>>>(r1, n, 9);
    CK(hipDeviceSynchronize());
    const int bad1 = run_check(r1, n, 9, "chunk 1 write/read after growth");
    const int bad0b = run_check(r0, n, 7, "chunk 0 still intact after growth");

    // give the first chunk back: the expert cache takes it as a slot, the K/V keeps the address
    CK(hipMemUnmap((hipDeviceptr_t) base, chunk));
    CK(hipMemRelease(h0));
    const int bad1b = run_check(r1, n, 9, "chunk 1 intact after chunk 0 was given back");

    size_t free_after = 0;
    CK(hipMemGetInfo(&free_after, &total));
    std::printf("VRAM free after            = %.1f MiB (delta %+.1f MiB)\n", free_after / 1048576.0,
                (double) ((long long) free_after - (long long) free_before) / 1048576.0);

    CK(hipMemUnmap((hipDeviceptr_t) ((char*) base + gran), chunk));
    CK(hipMemRelease(h1));
    CK(hipMemAddressFree((hipDeviceptr_t) base, range_bytes));

    const bool ok = (vmm == 1) && bad0 == 0 && bad1 == 0 && bad0b == 0 && bad1b == 0;
    std::printf("RESULT: %s\n", ok ? "VMM WORKS on gfx906 (attribute=1, map/grow/give-back all correct)"
                                 : "VMM NOT USABLE (see the lines above)");
    return ok ? 0 : 1;
}
