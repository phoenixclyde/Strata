#!/bin/bash
S=/home/albus/strata166
echo "=== A. llama-master 身份 ==="
grep -rn "LLAMA_BUILD_NUMBER" $S/tmp/w1037/llama-master/CMakeLists.txt | head -3
grep -rn "set(LLAMA_BUILD_NUMBER" $S/tmp/w1037/llama-master/CMakeLists.txt | head -3
cat $S/tmp/w1037/llama-master/.git/HEAD 2>/dev/null
cd $S/tmp/w1037/llama-master && git log --oneline -1 2>/dev/null
echo
echo "=== B. b12180 用的树是不是它（比 mmq.cuh 与 common.cuh）==="
md5sum $S/tmp/w1037/llama-master/ggml/src/ggml-cuda/mmq.cuh $S/llama.cpp/ggml/src/ggml-cuda/mmq.cuh 2>/dev/null
md5sum $S/tmp/w1037/llama-master/ggml/src/ggml-cuda/common.cuh $S/llama.cpp/ggml/src/ggml-cuda/common.cuh 2>/dev/null
echo
echo "=== C. port-all 未提交改动的内容（只看 diffstat 与关键行）==="
cd $S/pr/port-all && git diff --stat
git diff src/kernels/cuda/qsa_decode_attn.cu | head -60
