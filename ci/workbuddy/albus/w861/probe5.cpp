// W861: probe4 -- 不只查 heuristic，**真跑一次 f16 GEMM 并校验数值**。
// 为什么必须跑：comgr 的 JIT 缺陷可能只在执行路径上致命；heuristic 通过不代表能算。
// A、B 全填 f16 的 1.0，C = A^T·B 每个元素应等于 K（浮点加法，允许小误差）。
// 用法: ./probe4 <libpath|-> [M] [N] [K]
#include <hip/hip_runtime.h>
#include <hipblaslt/hipblaslt.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>

int main(int argc, char** argv) {
  const char* lib = (argc > 1) ? argv[1] : "-";
  int M = (argc > 2) ? atoi(argv[2]) : 256;
  int N = (argc > 3) ? atoi(argv[3]) : 512;
  int K = (argc > 4) ? atoi(argv[4]) : 256;
  if (strcmp(lib, "-") != 0) setenv("HIPBLASLT_TENSILE_LIBPATH", lib, 1);

  int dev = 0;
  hipGetDevice(&dev);
  hipDeviceProp_t prop;
  hipGetDeviceProperties(&prop, dev);
  printf("device: %s  M=%d N=%d K=%d\n", prop.gcnArchName, M, N, K);

  hipblasLtHandle_t h{};
  hipblasStatus_t st = hipblasLtCreate(&h);
  printf("  hipblasLtCreate           status=%d\n", (int) st);
  if (st != HIPBLAS_STATUS_SUCCESS) return 1;

  hipblasLtMatrixLayout_t a = nullptr, b = nullptr, c = nullptr;
  hipblasLtMatmulDesc_t d = nullptr;
  hipblasLtMatmulPreference_t pref = nullptr;
  void *A = nullptr, *B = nullptr, *C = nullptr, *ws = nullptr;

  hipblasLtMatrixLayoutCreate(&a, HIP_R_16F, K, M, K);
  hipblasLtMatrixLayoutCreate(&b, HIP_R_16F, K, N, K);
  hipblasLtMatrixLayoutCreate(&c, HIP_R_16F, N, M, N);
  hipblasLtMatmulDescCreate(&d, HIPBLAS_COMPUTE_16F, HIP_R_16F);
  hipblasLtMatmulPreferenceCreate(&pref);
  size_t wsMax = 64u << 20;
  hipblasLtMatmulPreferenceSetAttribute(pref, HIPBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,
                                        &wsMax, sizeof(wsMax));

  size_t asz = (size_t) M * K * 2, bsz = (size_t) N * K * 2, csz = (size_t) M * N * 2;
  printf("  A=%zu B=%zu C=%zu bytes\n", asz, bsz, csz);
  if (hipMalloc(&A, asz) || hipMalloc(&B, bsz) || hipMalloc(&C, csz)) {
    printf("  hipMalloc FAILED\n");
    return 1;
  }
  std::vector<uint16_t> hv;
  hv.assign((asz > bsz ? asz : bsz) / 2, 0x3C00);   // f16 的 1.0
  hipMemcpy(A, hv.data(), asz, hipMemcpyHostToDevice);
  hipMemcpy(B, hv.data(), bsz, hipMemcpyHostToDevice);
  hipMemset(C, 0, csz);

  hipblasLtMatmulHeuristicResult_t res[32];
  int found = 0;
  st = hipblasLtMatmulAlgoGetHeuristic(h, d, a, b, c, c, pref, 32, res, &found);
  printf("  AlgoGetHeuristic         status=%d algos=%d\n", (int) st, found);
  if (found == 0) {
    printf("RESULT: NO_ALGO\n");
    return 2;
  }
  for (int i = 0; i < found && i < 3; ++i)
    printf("     algo[%d] ws=%zu\n", i, res[i].workspaceSize);

  if (hipMalloc(&ws, res[0].workspaceSize ? res[0].workspaceSize : 1024)) {
    printf("  ws malloc FAILED\n");
    return 1;
  }

  float alpha = 1.f, beta = 0.f;
  st = hipblasLtMatmul(h, d, &alpha, A, a, B, b, &beta, C, c, C, c,
                       &res[0].algo, ws, wsMax, nullptr);
  printf("  hipblasLtMatmul          status=%d\n", (int) st);
  hipError_t se = hipDeviceSynchronize();
  printf("  hipDeviceSynchronize     status=%d (%s)\n", (int) se, hipGetErrorString(se));

  std::vector<uint16_t> out((size_t) M * N);
  (void)hipMemcpy(out.data(), C, csz, hipMemcpyDeviceToHost);
  // f16 -> float
  auto f16 = [](uint16_t v) {
    uint32_t s = (v >> 15) & 1, e = (v >> 10) & 0x1F, m = v & 0x3FF;
    float val;
    if (e == 0) val = m * 5.9604645e-8f;
    else if (e == 31) val = m ? NAN : INFINITY;
    else val = (1.f + m / 1024.f) * ldexpf(1.f, (int) e - 15);
    return s ? -val : val;
  };
  float c0 = f16(out[0]), cN = f16(out[(size_t) M * N - 1]);
  double sum = 0;
  int nz = 0;
  for (auto v : out) {
    float f = f16(v);
    sum += f;
    if (f != 0.f) ++nz;
  }
  printf("  C[0]=%.3f  C[last]=%.3f  nonzero=%d/%zu  mean=%.3f  (expect %.1f)\n",
         c0, cN, nz, out.size(), sum / out.size(), (double) K);
  bool ok = (std::fabs(c0 - K) <= K * 0.02f) && (nz == (int) out.size());
  printf("RESULT: %s\n", ok ? "COMPUTED_OK" : "MISMATCH_OR_ZERO");
  return ok ? 0 : 3;
}
