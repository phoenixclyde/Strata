// W851: hipBLASLt 在 gfx906 上到底有没有可用解？——它是"表"存在的前提。
// 判据：hipblasLtMatmulAlgoGetHeuristic 返回的 algo 数量；>0 才能谈调优表。
#include <hip/hip_runtime.h>
#include <hipblaslt/hipblaslt.h>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { auto _e = (x); if (_e != HIPBLAS_STATUS_SUCCESS) { \
  std::printf("  hipblaslt call failed: %s -> status=%d\n", #x, (int)_e); return 2; } } while (0)

int main() {
    int dev = 0; hipDeviceProp_t prop{};
    if (hipGetDevice(&dev) != hipSuccess || hipGetDeviceProperties(&prop, dev) != hipSuccess) {
        std::printf("hipGetDeviceProperties failed\n"); return 1;
    }
    std::printf("device: %s  arch=%s%c  gcnArchName=%s\n", prop.name,
                prop.gcnArchName, 0, prop.gcnArchName);

    hipblasLtHandle_t h{};
    if (hipblasLtCreate(&h) != HIPBLAS_STATUS_SUCCESS) { std::printf("hipblasLtCreate failed\n"); return 1; }

    // 与引擎 f16_inplace 同形：FP16 in, FP16 out, FP32 累加, C = A^T(W) * B(X)，形状取引擎的 14 个之一
    const int N = 10240, K = 2560, T = 256, ldy = N;
    void *dW = nullptr, *dX = nullptr, *dY = nullptr;
    hipMalloc(&dW, (size_t)K * N * 2); hipMalloc(&dX, (size_t)T * K * 2); hipMalloc(&dY, (size_t)T * ldy * 2);
    hipMemset(dW, 0, (size_t)K * N * 2); hipMemset(dX, 0, (size_t)T * K * 2); hipMemset(dY, 0, (size_t)T * ldy * 2);

    hipblasLtMatmulDesc_t op{}; hipblasLtMatrixLayout_t a{}, b{}, c{};
    CK(hipblasLtMatmulDescCreate(&op, HIPBLAS_COMPUTE_32F, HIP_R_32F));
    hipblasOperation_t ta = HIPBLAS_OP_T, tb = HIPBLAS_OP_N;
    CK(hipblasLtMatmulDescSetAttribute(op, HIPBLASLT_MATMUL_DESC_TRANSA, &ta, sizeof ta));
    CK(hipblasLtMatmulDescSetAttribute(op, HIPBLASLT_MATMUL_DESC_TRANSB, &tb, sizeof tb));
    CK(hipblasLtMatrixLayoutCreate(&a, HIP_R_16F, K, N, K));
    CK(hipblasLtMatrixLayoutCreate(&b, HIP_R_16F, K, T, K));
    CK(hipblasLtMatrixLayoutCreate(&c, HIP_R_32F, N, T, ldy));

    hipblasLtMatmulPreference_t pref{};
    CK(hipblasLtMatmulPreferenceCreate(&pref));
    size_t ws = (size_t)512 << 20; void* dws = nullptr; hipMalloc(&dws, ws);
    CK(hipblasLtMatmulPreferenceSetAttribute(pref, HIPBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws, sizeof ws));

    hipblasLtMatmulHeuristicResult_t res[32]{};
    int found = 0;
    auto st = hipblasLtMatmulAlgoGetHeuristic(h, op, a, b, c, c, pref, 32, res, &found);
    std::printf("\n== T=%d N=%d K=%d (engine shape #1) ==\n", T, N, K);
    std::printf("   hipblasLtMatmulAlgoGetHeuristic -> status=%d  algos=%d\n", (int)st, found);
    for (int i = 0; i < found && i < 3; ++i)
        std::printf("   algo[%d] ws=%zu ms=%.4f\n", i, res[i].workspaceSize, res[i].algo);

    // 若一个都没有，试试小形状（有些 arch 只对小 tile 有解）
    if (found == 0) {
        hipblasLtMatrixLayoutDestroy(a); hipblasLtMatrixLayoutDestroy(b); hipblasLtMatrixLayoutDestroy(c);
        CK(hipblasLtMatrixLayoutCreate(&a, HIP_R_16F, 256, 256, 256));
        CK(hipblasLtMatrixLayoutCreate(&b, HIP_R_16F, 256, 256, 256));
        CK(hipblasLtMatrixLayoutCreate(&c, HIP_R_32F, 256, 256, 256));
        int f2 = 0; auto st2 = hipblasLtMatmulAlgoGetHeuristic(h, op, a, b, c, c, pref, 32, res, &f2);
        std::printf("   小形状 256x256x256 -> status=%d algos=%d\n", (int)st2, f2);
    }
    std::printf("\nVERDICT: %s\n", found > 0 ? "gfx906 上 hipBLASLt 有可用解 => 表有意义" :
                                              "gfx906 上 hipBLASLt 无可用解 => 表无从谈起");
    return 0;
}
