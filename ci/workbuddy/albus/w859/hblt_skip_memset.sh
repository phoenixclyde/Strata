#!/bin/bash
# W859-B：绕开 comgr 的 OpenCL JIT —— hipblasLtCreate 里 skip 两个 memset（只做 heuristic 探测用）
#   根因（AMD_COMGR_EMIT_VERBOSE_LOGS 实测）：AMD_COMGR_ACTION_COMPILE_SOURCE_WITH_DEVICE_LIBS_TO_BC，
#   comgr 用内置 clang24 却传 -mcode-object-version=5 / -amdgpu-prelink ⇒ 内建 clang 不认。
#   这是镜像级 comgr/clang 错配，与 gfx906 无关。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_hblt_build6.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build6 start $(date +%F" "%T)"
  docker run --rm --name strata-w859b6 -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
F=/src/projects/hipblaslt/library/src/amd_detail/hipblaslt.cpp
python3 - "$F" <<PYX
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
a1 = "    CHECK_HIP_ERROR(hipMemset(d_Synchronizer, 0, gsuBytes));"
a2 = "    if(hipError_t e = hipMemset(d_StreamKFlags, 0, skBytes); e != hipSuccess)"
if "W859 skip" not in s:
    s = s.replace(a1, "    // W859 skip: comgr OpenCL JIT 在本镜像参数错配（只做 heuristic 探测）", 1)
    s = s.replace(a2, "    if(hipError_t e = hipSuccess; e != hipSuccess)  // W859 skip", 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("  patched:", s.count("W859 skip"))
else:
    print("  already patched")
PYX
cd /out/build
timeout 900 nice -n 10 ninja -j 4 hipblaslt 2>&1 | tail -8
echo "--- ninja done $(date +%H:%M:%S)"
'
  echo "=== build6 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
grep -E "patched|ninja done|build6 end|FAILED|error:" "$LOG" | tail -8
