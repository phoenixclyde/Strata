#!/bin/bash
set -u
echo "=== 1. 最新 prefill timing 完整行（当前 run）==="
docker exec strata166-407 sh -c "grep -n 'strata prefill timing' /data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-400"

echo
echo "=== 2. 历史上不同 prompt 长度的 qsa proj 占比 ==="
docker exec strata166-407 sh -c "grep -oE 'strata prefill timing: [0-9]+ tokens.*' /data/strata-huihui-ud-iq4_xs.log | sed -E 's/qsa proj ([0-9]+) \(([0-9.]+)%\)/QSA=\1(\2%)/' | grep -oE '[0-9]+ tokens|QSA=[0-9]+\([0-9.]+%\)' | paste - - 2>/dev/null | tail -12"

echo
echo "=== 3. 源码：hybrid K8V4 的分支（gfx906 走哪条）==="
cd ~/strata166/pr/strata-fork || exit 1
sed -n '2431,2480p' src/kernels/cuda/qsa_prompt_attn.cu
