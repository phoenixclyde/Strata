// W860: 参数化探针 -- 查指定 (M,N,K) 的 f16 GEMM 能否在 gfx906 上拿到 algo
// 用法: ./probe_shape <libpath|-> <M> <N> <K> [f16|f32]
#include <hip/hip_runtime.h>
#include <hipblaslt/hipblaslt.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv) {
  const char* lib = (argc > 1) ? argv[1] : "-";
  int M = (argc > 2) ? atoi(argv[2]) : 64;
  int N = (argc > 3) ? atoi(argv[3]) : 5056;
  int K = (argc > 4) ? atoi(argv[4]) : 256;
  int is16 = !(argc > 5 && strcmp(argv[5], "f32") == 0);
  if (strcmp(lib, "-") != 0) setenv("HIPBLASLT_TENSILE_LIBPATH", lib, 1);

  fprintf(stderr, "probe: lib=%s M=%d N=%d K=%d %s\n", lib, M, N, K, is16 ? "f16" : "f32");
  hipblasLtHandle_t h{};
  auto st = hipblasLtCreate(&h);
  fprintf(stderr, "  hipblasLtCreate status=%d\n", (int) st);
  if (st != HIPBLAS_STATUS_SUCCESS) return 1;

  hipDataType io = is16 ? HIP_R_16F : HIP_R_32F;
  size_t esz = is16 ? 2 : 4;
  hipblasLtMatrixLayout_t a = nullptr, b = nullptr, c = nullptr;
  hipblasLtMatmulDesc_t d = nullptr;
  hipblasLtMatmulPreference_t pref = nullptr;
  void *A = nullptr, *B = nullptr, *C = nullptr;

  hipblasLtMatrixLayoutCreate(&a, io, K, M, K);
  hipblasLtMatrixLayoutCreate(&b, io, K, N, K);
  hipblasLtMatrixLayoutCreate(&c, io, N, M, N);
  hipblasLtMatmulDescCreate(&d, HIPBLAS_COMPUTE_32F, HIP_R_32F);
  hipblasLtMatmulPreferenceCreate(&pref);
  size_t ws = 64u << 20;
  hipblasLtMatmulPreferenceSetAttribute(pref, HIPBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &ws, sizeof(ws));
  hipMalloc(&A, (size_t) M * K * esz);
  hipMalloc(&B, (size_t) N * K * esz);
  hipMalloc(&C, (size_t) M * N * 4);

  hipblasLtMatmulHeuristicResult_t res[32];
  int found = 0;
  st = hipblasLtMatmulAlgoGetHeuristic(h, d, a, b, c, c, pref, 32, res, &found);
  printf("RESULT M=%d N=%d K=%d %s : status=%d algos=%d\n", M, N, K, is16 ? "f16" : "f32", (int) st, found);
  for (int i = 0; i < found && i < 3; ++i)
    printf("   algo[%d] workspace=%zu\n", i, res[i].workspaceSize);

  if (pref) hipblasLtMatmulPreferenceDestroy(pref);
  if (d) hipblasLtMatmulDescDestroy(d);
  if (a) hipblasLtMatrixLayoutDestroy(a);
  if (b) hipblasLtMatrixLayoutDestroy(b);
  if (c) hipblasLtMatrixLayoutDestroy(c);
  if (A) hipFree(A);
  if (B) hipFree(B);
  if (C) hipFree(C);
  hipblasLtDestroy(h);
  return found > 0 ? 0 : 2;
}
