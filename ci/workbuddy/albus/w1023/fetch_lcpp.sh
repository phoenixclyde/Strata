#!/bin/bash
# Fetch the newest llama.cpp tag and check the symbols our fork actually depends on.
# No guessing: the four API surfaces that broke or nearly broke the last bump are grepped here.
set -uo pipefail
SHA=3259ab6e5dd86fad1931962d784702cb53c7877b      # b12129
DST=/home/albus/strata166/ref/llama_b12129
TAR=/home/albus/strata166/ref/llama-b12129.tar.gz

df -h /home/albus/strata166 | tail -1
if [ ! -d "$DST" ]; then
  curl -sSL -o "$TAR" "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$SHA" || { echo DOWNLOAD_FAIL; exit 3; }
  ls -l "$TAR"
  mkdir -p "$DST"
  tar xzf "$TAR" -C "$DST" --strip-components=1 || { echo UNTAR_FAIL; exit 4; }
fi
echo "files=$(find "$DST" -type f | wc -l) bytes=$(du -sb "$DST" | cut -f1)"

echo "=== 1. mul_mat_q_case 签名"
grep -rn "mul_mat_q_case(" "$DST/ggml/src/ggml-cuda/mmq.cuh" | head -4
echo "=== 2. ggml_cuda_mmq_get_config 签名"
grep -rn "ggml_cuda_mmq_config ggml_cuda_mmq_get_config(" "$DST/ggml/src/ggml-cuda/"*.cuh | head -3
echo "=== 3. new_pool_for_device 签名"
grep -rn "new_pool_for_device" "$DST/ggml/src/ggml-cuda/common.cuh" | head -3
echo "=== 4. iqp.cpp 还在吗"
ls -l "$DST/ggml/src/ggml-cpu/iqp.cpp" 2>/dev/null || echo NO_IQP
echo "=== 5. 其他我们可能用的内部符号"
for s in ggml_cuda_pool_alloc ggml_cuda_mmq_config ggml_cuda_mmq_get_config mul_mat_q_case; do
  printf "%-28s %s\n" "$s" "$(grep -rl "$s" "$DST/ggml/src/ggml-cuda/" 2>/dev/null | wc -l) file(s)"
done
