set -eu
D=/home/albus/strata166/gfx029
O=/home/albus/strata166/tuner-build-r714
IMG=strata-gfx906:0.2.9t2
echo "== 在 7.14 镜像里编 tune_rocblas（对照用，rocBLAS 5.5）"
mkdir -p "$O"
docker run --rm --name strata-tunebuild55 \
  -v "$D":/src:ro -v "$O":/out \
  -v /home/albus/strata166/src028/third_party/llama.cpp:/llama.cpp:ro \
  "$IMG" bash -lc '
set -eu
cd /src
cmake -S . -B /out -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_ENABLE_CUDA=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_ENABLE_SYCL=OFF \
  -DSTRATA_GGML_DIR=/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF \
  -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PREFILL_MMQ=OFF \
  -DSTRATA_Q6K_EXPERTS=OFF -DSTRATA_WERROR=OFF >/dev/null 2>&1
ninja -C /out -j 8 tune_rocblas 2>&1 | tail -3
ls -l /out/tune_rocblas
' 2>&1 | tail -8
