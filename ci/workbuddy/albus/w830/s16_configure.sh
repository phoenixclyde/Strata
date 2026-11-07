S=/home/albus/strata166/src028
docker run --rm --security-opt label=disable \
  -v "$S":/src -w /src strata-gfx906:0.2.8 bash -lc '
cmake -S /src -B /src/build-028r -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DSTRATA_ENABLE_CUDA=ON \
  -DSTRATA_HIP_GFX906=ON \
  -DSTRATA_NATIVE_EXPERTS=ON \
  -DSTRATA_GGML_DIR=/src/third_party/llama.cpp \
  -DSTRATA_MMQ_KQUANTS=ON \
  -DSTRATA_MMQ_TQ_OVERLAY=ON \
  -DSTRATA_MMQ_TAB=OFF \
  -DSTRATA_WINDOW_MAX_T=auto \
  -DSTRATA_BUILD_TESTS=OFF \
  -DSTRATA_BUILD_DSV41=OFF \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ 2>&1 | tail -30
echo "---- rocblas evidence ----"
grep -iE "rocblas" /src/build-028r/CMakeCache.txt | head -6
grep -E "^STRATA_ROCBLAS_AVAILABLE|^STRATA_WINDOW_MAX_T" /src/build-028r/CMakeCache.txt
'
