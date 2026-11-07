#!/bin/bash
# W859-B：给 hipblasLtCreate 插桩（打印 gsuBytes/skBytes 与真实 hip 返回码，不 exit），重编再跑。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_hblt_build5.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build5 start $(date +%F" "%T)"
  docker run --rm --name strata-w859b5 -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
F=/src/projects/hipblaslt/library/src/amd_detail/hipblaslt.cpp
echo "--- 插桩前"
grep -n "CHECK_HIP_ERROR(hipMalloc(&d_Synchronizer" $F
echo "--- 插桩"
python3 - "$F" <<PYX
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
anchor = "    CHECK_HIP_ERROR(hipMalloc(&d_Synchronizer, gsuBytes));\n    CHECK_HIP_ERROR(hipMemset(d_Synchronizer, 0, gsuBytes));"
if "W859 PROBE" not in s and anchor in s:
    new = ("    fprintf(stderr, \"W859 PROBE gsuBytes=%zu skBytes=%zu\\n\", gsuBytes, skBytes);\n"
           "    { hipError_t e1 = hipMalloc(&d_Synchronizer, gsuBytes);\n"
           "      fprintf(stderr, \"W859 PROBE hipMalloc gsu=%d ptr=%p\\n\", (int)e1, d_Synchronizer);\n"
           "      if (e1 == hipSuccess) { hipError_t e2 = hipMemset(d_Synchronizer, 0, gsuBytes);\n"
           "        fprintf(stderr, \"W859 PROBE hipMemset gsu=%d\\n\", (int)e2); } }\n"
           "    CHECK_HIP_ERROR(hipMalloc(&d_Synchronizer, gsuBytes));\n"
           "    CHECK_HIP_ERROR(hipMemset(d_Synchronizer, 0, gsuBytes));")
    s = s.replace(anchor, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("  patched")
else:
    print("  anchor missing or already patched")
PYX
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja > /dev/null 2>&1
cd /out/build
timeout 1200 nice -n 10 ninja -j 14 hipblaslt 2>&1 | tail -6
echo "--- ninja done $(date +%H:%M:%S)"
'
  echo "=== build5 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
grep -E "插桩|patched|ninja done|build5 end|FAILED" "$LOG" | tail -8
