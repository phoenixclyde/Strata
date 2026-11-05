#!/bin/bash
# Reproduce the W1001 fair A/B for the mx Q5_1 repacked MoE GEMM.
#
# GPU: needs /dev/kfd + /dev/dri and shares the card with production. The kernels
# are millisecond-scale and this script NEVER touches the production config or
# restarts the container. Production engine md5 must be unchanged afterwards.
#
# Layout built under build-tab/repacktest (a scratch tree, not the repo):
#   ggml-cuda/          <- ggml 0.29 headers from llama_b12110
#   ggml-cuda/repack/   <- mx reference sources (external asset, not vendored)
set -euo pipefail

OUT=/home/albus/strata166/build-tab/repacktest
REF=/home/albus/strata166/ref/llama_b12110
MX=/home/albus/strata166/ref/mx
SRC=/home/albus/strata166/pr/strata-fork
IMG=strata-gfx906:0.2.10-101
HERE=$(cd "$(dirname "$0")" && pwd)

for p in "$REF/ggml/src/ggml-cuda/common.cuh" "$MX/repack-kernels.cuh" "$SRC/src/prefill/moe_mmq.cu"; do
    if [ ! -f "$p" ]; then echo "MISSING $p" >&2; exit 1; fi
done

R="$OUT/ggml-cuda"
mkdir -p "$R/repack"
cp "$REF"/ggml/src/ggml-cuda/*.cuh "$REF"/ggml/src/ggml-cuda/*.h "$R"/ 2>/dev/null || true
cp -r "$REF"/ggml/src/ggml-cuda/vendors "$R"/ 2>/dev/null || true
cp "$REF"/ggml/src/ggml-common.h "$REF"/ggml/src/ggml-impl.h "$R"/ 2>/dev/null || true
cp "$MX"/*.cuh "$MX"/*.cu "$R/repack"/

# mx calls ggml_cuda_q8_1_cache_acquire(), added in its own fork. In 0.29 the
# host helper is absent; nullptr/hit=false selects the fallback path, which is
# what a standalone bench needs (it supplies its own activations).
python3 - "$R/repack/repack-common.cuh" <<'PY'
import sys
p = sys.argv[1]
lines = open(p).read().split("\n")
out, i = [], 0
while i < len(lines):
    if "ggml_cuda_q8_1_cache_acquire" in lines[i]:
        out.append("    char * cached = nullptr; hit = false;   // bench stub: no q8_1 cache")
        i += 2
        continue
    out.append(lines[i]); i += 1
open(p, "w").write("\n".join(out))
PY

docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$OUT:/out" -v "$REF:/ref" -v "$SRC:/src" -v "$HERE:/bench:ro" \
  --entrypoint bash "$IMG" -c '
set -e
R=/out/ggml-cuda
cd /out
INC="-I. -I$R -I$R/repack -I/ref/ggml/src -I/ref/ggml/include -I/src/include -I/src/include/strata/platform/hip_compat -I/src/src"
/opt/rocm/bin/hipcc -c -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -DGGML_USE_HIP $INC \
  /bench/ab_bench.cu -o /out/ab_bench.o
/opt/rocm/bin/hipcc /out/ab_bench.o /out/libstrata_mmq.a /out/libstrata_mmq_w4a4.a \
  /out/ggml/src/libggml-base.a -lamdhip64 -o /out/ab_bench
echo BUILD_OK
for r in 32 128 320 1024; do
  echo "--- rows/expert=$r"
  STRATA_MMQ_KQ=1 /out/ab_bench 16 "$r" 3 | grep -E "dispatch|MEDIAN"
done
'

echo "REPRO_DONE -- compare against ci/repack_ab/RESULTS.tsv"
