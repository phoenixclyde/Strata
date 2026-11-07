set -eu
D=/home/albus/strata166/gfx029
O=/home/albus/strata166/tuner-build-r101
IMG=strata-gfx906:0.2.9r1
echo "== 在 10.1 镜像里配置并只编译 tune_rocblas（用 5.7 的 rocBLAS）"
mkdir -p "$O"
docker run --rm --name strata-tunebuild \
  -v "$D":/src:ro -v "$O":/out \
  -v /home/albus/strata166/src028/third_party/llama.cpp:/llama.cpp:ro \
  "$IMG" bash -lc '
set -eu
cd /src
cmake -S . -B /out -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_ENABLE_CUDA=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_ENABLE_SYCL=OFF \
  -DSTRATA_GGML_DIR=/llama.cpp \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_DSV41=OFF \
  -DSTRATA_MMQ_KQUANTS=ON -DSTRATA_NATIVE_EXPERTS=ON -DSTRATA_PREFILL_MMQ=OFF \
  -DSTRATA_Q6K_EXPERTS=OFF -DSTRATA_WERROR=OFF 2>&1 | tail -6
echo "--- tune_rocblas target 是否存在:"
ninja -C /out -t targets 2>/dev/null | grep -c "^tune_rocblas:" || true
echo "--- 编译:"
nice -n 15 ninja -C /out -j 8 tune_rocblas 2>&1 | tail -8
ls -l /out/tune_rocblas
' 2>&1 | tail -22
