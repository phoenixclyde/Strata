#!/bin/bash
# W1003b: four weight types x two production shapes x two tile widths.
set -euo pipefail
BT=/home/albus/strata166/build-tab
IMG=strata-gfx906:0.2.10-101

docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$BT:/bt" -v /home/albus/strata166/ref/llama_b12110:/ref -v /home/albus/strata166/pr/strata-fork:/src \
  --entrypoint bash "$IMG" -c '
set -e
R=/bt/repacktest/ggml-cuda
INC="-I$R -I$R/repack -I/ref/ggml/src -I/ref/ggml/include -I/src/include -I/src/include/strata/platform/hip_compat -I/src/src"
cd /bt/w1003
/opt/rocm/bin/hipcc -c -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -DGGML_USE_HIP $INC \
  type_sweep.cu -o type_sweep.o 2>&1 | grep -E "error" || true
/opt/rocm/bin/hipcc type_sweep.o /bt/libstrata_mmq.a /bt/libstrata_mmq_w4a4.a \
  /bt/ggml/src/libggml-base.a -lamdhip64 -o type_sweep
echo BUILD_OK
STRATA_MMQ_KQ=1 ./type_sweep 16 5 gu
STRATA_MMQ_KQ=1 ./type_sweep 16 5 dn
'
