// W861: 最小验证 -- 只调 hipblasLtCreate，不碰任何矩阵。
// 目的：把"崩在哪"从我们的探针代码里彻底摘出去。三组：
//   A 系统 hipblaslt + 不设库路径（镜像基线）
//   B 自编 hipblaslt(LAZY_LOAD=OFF) + 非 lazy 库
//   C 自编 hipblaslt + 不设库路径
#include <hip/hip_runtime.h>
#include <hipblaslt/hipblaslt.h>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
  const char* tag = (argc > 1) ? argv[1] : "?";
  fprintf(stderr, "[%s] start\n", tag);
  hipblasLtHandle_t h{};
  hipblasStatus_t st = hipblasLtCreate(&h);
  fprintf(stderr, "[%s] hipblasLtCreate status=%d\n", tag, (int) st);
  if (st == HIPBLAS_STATUS_SUCCESS) {
    hipblasLtDestroy(h);
    fprintf(stderr, "[%s] destroy ok -> CREATE_OK\n", tag);
    return 0;
  }
  return 1;
}
