set -e
cd /home/albus/strata166
WMT=${1:-auto}
TAG=${2:-028}
docker rm -f build$TAG >/dev/null 2>&1 || true
# the build dir was made by root inside a container: remove it the same way
docker run --rm -v /home/albus/strata166/src028:/src strata-gfx906:0.2.4p4 rm -rf /src/build-$TAG
docker run --rm --name build$TAG \
  -v /home/albus/strata166/src028:/src \
  -w /src \
  strata-gfx906:0.2.4p4 \
  bash -lc "set -e
    cmake -S /src -B /src/build-$TAG -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
      -DCMAKE_HIP_ARCHITECTURES=gfx906 \
      -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
      -DSTRATA_ENABLE_CUDA=ON -DSTRATA_HIP_GFX906=ON \
      -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_MMQ_TQ_OVERLAY=ON \
      -DSTRATA_NATIVE_EXPERTS=ON \
      -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF \
      -DSTRATA_BUILD_CONVERSATION_TESTS=OFF \
      -DSTRATA_PREFILL_MMQ=OFF -DSTRATA_Q6K_EXPERTS=OFF \
      -DSTRATA_ORCA_Q4KS_MMQ=OFF \
      -DSTRATA_WINDOW_MAX_T=$WMT 2>&1 | tail -20
    echo '--- cache ---'
    grep -E 'WINDOW_MAX_T:|HIP_GFX906|ENABLE_CUDA:|ENABLE_HIP:|GGML_DIR' /src/build-$TAG/CMakeCache.txt"
