#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: find out which compile-time guards are actually true for a gfx906
HIP device compilation.  The first self-check reported HW=0; do not guess why.
"""
import io
import os
import sys

sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

W = r"D:/workbuddy_space/strata_ws/albus/w1042"
CU = r'''
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
'''

def main():
    loc = os.path.join(W, "probe_macros.cu")
    io.open(loc, "w", encoding="utf-8", newline="\n").write(CU.lstrip("\n"))
    _sshutil.push_b64(loc, "/home/albus/strata166/tmp/w1042/probe_macros.cu")
    S = (
        "docker run --rm --device=/dev/kfd --device=/dev/dri "
        "-v /home/albus/strata166/tmp/w1042:/w strata-gfx906:0.2.11-101 bash -lc '"
        "hipcc -x hip -O2 --offload-arch=gfx906 /w/probe_macros.cu -o /w/probe_macros "
        "2>/w/probe.err && /w/probe_macros; echo BUILD_RC=$?; head -8 /w/probe.err' 2>&1 | tail -15"
    )
    rc, out, err = _sshutil.run_remote(S, timeout=300)
    print(out)
    if err.strip():
        print("ERR", err[-300:])

if __name__ == "__main__":
    main()
