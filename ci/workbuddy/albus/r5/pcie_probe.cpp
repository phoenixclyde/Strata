// W800d: H2D 拷贝带宽探针 —— pageable / pinned / file-backed mmap
// 目的：核实 prompt 路"每专家 4 MB 组装拷贝"的实际速率，判断 wait copy 334-791 ms 的成因
#include <hip/hip_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <vector>

static double now_ms() {
    using namespace std::chrono;
    return duration<double, std::milli>(steady_clock::now().time_since_epoch()).count();
}

static void report(const char* what, size_t bytes, int n, double ms) {
    printf("%-22s %7.2f MB x %d  %8.2f ms  %6.2f GB/s  %7.1f us/iter\n", what, bytes / 1048576.0, n, ms,
           (double) bytes * n / (ms * 1e6), ms * 1000.0 / n);
}

int main() {
    hipDeviceProp_t prop{};
    if (hipGetDeviceProperties(&prop, 0) != hipSuccess) { printf("no device\n"); return 1; }
    printf("device 0: %s  canMapHostMemory=%d  total=%.0f MiB\n", prop.name, prop.canMapHostMemory,
           prop.totalGlobalMem / 1048576.0);

    const size_t MB = 4u << 20;
    const int N = 50;
    void* d = nullptr;
    if (hipMalloc(&d, MB) != hipSuccess) { printf("hipMalloc failed\n"); return 1; }

    {   // 1) pageable
        std::vector<unsigned char> h(MB, 0x5a);
        for (int i = 0; i < 5; ++i) hipMemcpy(d, h.data(), MB, hipMemcpyHostToDevice);
        hipDeviceSynchronize();
        double t0 = now_ms();
        for (int i = 0; i < N; ++i) { hipMemcpyAsync(d, h.data(), MB, hipMemcpyHostToDevice, 0); hipDeviceSynchronize(); }
        report("pageable (sync each)", MB, N, now_ms() - t0);
        t0 = now_ms();
        for (int i = 0; i < N; ++i) hipMemcpyAsync(d, h.data(), MB, hipMemcpyHostToDevice, 0);
        hipDeviceSynchronize();
        report("pageable (batched)", MB, N, now_ms() - t0);
    }
    {   // 2) pinned
        void* h = nullptr;
        if (hipHostMalloc(&h, MB, 0) == hipSuccess) {
            memset(h, 0x5a, MB);
            for (int i = 0; i < 5; ++i) hipMemcpy(d, h, MB, hipMemcpyHostToDevice);
            hipDeviceSynchronize();
            double t0 = now_ms();
            for (int i = 0; i < N; ++i) { hipMemcpyAsync(d, h, MB, hipMemcpyHostToDevice, 0); hipDeviceSynchronize(); }
            report("pinned (sync each)", MB, N, now_ms() - t0);
        } else printf("hipHostMalloc failed\n");
    }
    {   // 3) file-backed mmap
        const char* p = "/tmp/w800_probe.bin";
        int fd = open(p, O_RDWR | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0) {
            ftruncate(fd, (off_t) MB);
            unsigned char* h = (unsigned char*) mmap(nullptr, MB, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
            if (h != MAP_FAILED) {
                memset(h, 0x5a, MB);
                msync(h, MB, MS_SYNC);
                for (int i = 0; i < 5; ++i) hipMemcpy(d, h, MB, hipMemcpyHostToDevice);
                hipDeviceSynchronize();
                double t0 = now_ms();
                for (int i = 0; i < N; ++i) { hipMemcpyAsync(d, h, MB, hipMemcpyHostToDevice, 0); hipDeviceSynchronize(); }
                report("file mmap (sync each)", MB, N, now_ms() - t0);
                munmap(h, MB);
            } else printf("mmap failed\n");
            close(fd);
        }
    }
    {   // 4) 2.79 MB：与上游 PR #4005 的口径对齐（其 Linux registered 205 us）
        const size_t S = (size_t) (2.79 * 1048576);
        void* dp = nullptr;
        hipMalloc(&dp, S);
        std::vector<unsigned char> h(S, 0x11);
        for (int i = 0; i < 5; ++i) hipMemcpy(dp, h.data(), S, hipMemcpyHostToDevice);
        hipDeviceSynchronize();
        double t0 = now_ms();
        for (int i = 0; i < N; ++i) { hipMemcpyAsync(dp, h.data(), S, hipMemcpyHostToDevice, 0); hipDeviceSynchronize(); }
        report("pageable 2.79MB", S, N, now_ms() - t0);
        void* hp = nullptr;
        if (hipHostMalloc(&hp, S, 0) == hipSuccess) {
            memset(hp, 0x11, S);
            for (int i = 0; i < 5; ++i) hipMemcpy(dp, hp, S, hipMemcpyHostToDevice);
            hipDeviceSynchronize();
            t0 = now_ms();
            for (int i = 0; i < N; ++i) { hipMemcpyAsync(dp, hp, S, hipMemcpyHostToDevice, 0); hipDeviceSynchronize(); }
            report("pinned 2.79MB", S, N, now_ms() - t0);
        }
        hipFree(dp);
    }
    hipFree(d);
    return 0;
}
