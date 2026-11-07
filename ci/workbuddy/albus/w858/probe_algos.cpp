// W858：hipBLASLt 是否能在 gfx906 上给出 algo —— 分别试 f32 / f16。
// 用法：./probe_algos [libpath]
//   libpath 存在则设 HIPBLASLT_TENSILE_LIBPATH（hipBLASLt 的自定义库目录）
#include <hip/hip_runtime.h>
#include <hipblaslt/hipblaslt.h>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { auto e_ = (x); fprintf(stderr, "  %-32s status=%d\n", #x, (int) e_); \
  if (e_ != HIPBLAS_STATUS_SUCCESS) { return 1; } } while (0)

static int try_dtype(hipblasLtHandle_t h, hipDataType io, const char* name,
                     int M, int N, int K) {
  hipblasLtMatrixLayout_t a = nullptr, b = nullptr, c = nullptr;
  hipblasLtMatmulDesc_t d = nullptr;
  hipblasLtMatmulPreference_t pref = nullptr;
  void *A = nullptr, *B = nullptr, *C = nullptr;
  const size_t esz = (io == HIP_R_16F) ? 2 : 4;

  hipblasLtMatrixLayoutCreate(&a, io, K, M, K);
  hipblasLtMatrixLayoutCreate(&b, io, K, N, K);
  hipblasLtMatrixLayoutCreate(&c, io, N, M, N);
  hipblasLtMatmulDescCreate(&d, HIPBLAS_COMPUTE_32F, HIP_R_32F);
  hipblasLtMatmulPreferenceCreate(&pref);
  size_t ws = 64u << 20;
  hipblasLtMatmulPreferenceSetAttribute(pref, HIPBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,
                                        &ws, sizeof(ws));
  hipMalloc(&A, (size_t) M * K * esz);
  hipMalloc(&B, (size_t) N * K * esz);
  hipMalloc(&C, (size_t) M * N * 4);

  hipblasLtMatmulHeuristicResult_t res[32];
  int found = 0;
  auto st = hipblasLtMatmulAlgoGetHeuristic(h, d, a, b, c, c, pref, 32, res, &found);
  printf("  %-4s M=%d N=%d K=%d : status=%d algos=%d\n", name, M, N, K, (int) st, found);
  for (int i = 0; i < found && i < 3; ++i)
    printf("      algo[%d] workspace=%zu\n", i, res[i].workspaceSize);

  if (pref) hipblasLtMatmulPreferenceDestroy(pref);
  if (d) hipblasLtMatmulDescDestroy(d);
  if (a) hipblasLtMatrixLayoutDestroy(a);
  if (b) hipblasLtMatrixLayoutDestroy(b);
  if (c) hipblasLtMatrixLayoutDestroy(c);
  if (A) hipFree(A);
  if (B) hipFree(B);
  if (C) hipFree(C);
  return found;
}

int main(int argc, char** argv) {
  if (argc > 1) {
    setenv("HIPBLASLT_TENSILE_LIBPATH", argv[1], 1);
    printf("LIBPATH=%s\n", argv[1]);
  } else {
    printf("LIBPATH=(default, from the ROCm install)\n");
  }
  fprintf(stderr, "probe start\n");
  hipblasLtHandle_t h{};
  CK(hipblasLtCreate(&h));
  int total = 0;
  total += try_dtype(h, HIP_R_32F, "f32", 256, 10240, 2560);
  total += try_dtype(h, HIP_R_16F, "f16", 256, 10240, 2560);
  total += try_dtype(h, HIP_R_16F, "f16", 2048, 2560, 640);
  hipblasLtDestroy(h);
  printf("TOTAL algos=%d\n", total);
  return total > 0 ? 0 : 2;
}
