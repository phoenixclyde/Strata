#!/bin/bash
# W1003: build + run the width sweep (32-wide vs 64-wide vs canonical).
# Same mounts as ci/repack_ab/run.sh, only the bench TU differs. GPU is shared
# with production; this never touches the container or the production config.
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
  width_sweep.cu -o width_sweep.o
/opt/rocm/bin/hipcc width_sweep.o /bt/libstrata_mmq.a /bt/libstrata_mmq_w4a4.a \
  /bt/ggml/src/libggml-base.a -lamdhip64 -o width_sweep
echo BUILD_OK
STRATA_MMQ_KQ=1 ./width_sweep 16 5 640 2560
STRATA_MMQ_KQ=1 ./width_sweep 16 5 2560 640
'
