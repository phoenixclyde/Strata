#include <hip/hip_runtime.h>
#include <cstdio>
__global__ void k(int* o) {
  int v = 0;
#if defined(__gfx906__)
  v |= 1;
#endif
#if __has_builtin(__builtin_amdgcn_sdot4)
  v |= 2;
#endif
#if __has_builtin(__builtin_amdgcn_sdot8)
  v |= 4;
#endif
#if defined(__HIP_DEVICE_COMPILE__)
  v |= 8;
#endif
#if defined(__HIPCC__)
  v |= 16;
#endif
#if defined(__HIP_PLATFORM_AMD__)
  v |= 32;
#endif
  o[0] = v;
}
int main() {
  int *d, h = 0;
  hipMalloc(&d, 4);
  k<<<1, 1>>>(d);
  hipMemcpy(&h, d, 4, hipMemcpyDeviceToHost);
  printf("MACROS=%d gfx906=%d sdot4=%d sdot8=%d devcompile=%d HIPCC=%d AMD=%d\n",
         h, h & 1, (h >> 1) & 1, (h >> 2) & 1, (h >> 3) & 1, (h >> 4) & 1, (h >> 5) & 1);
  return 0;
}
