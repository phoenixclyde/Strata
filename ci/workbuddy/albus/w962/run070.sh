#!/bin/bash
# W962: one 0.7.0 run (J_best + prec, no fusion) -- the bisect point for the -6%.
set -u
H=/home/albus/strata166
OUT=$H/data/w962
mkdir -p "$OUT"
cp -n "$H/data/w957/prompt.tok" "$OUT/prompt.tok" 2>/dev/null || true
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf

docker stop strata166-407 >/dev/null
docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models -v "$H/build-070":/b \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
  -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
  strata-gfx906:0.2.10-101 bash -lc \
  "/b/strata --pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
   --max-context 262144 --kv k8v4 --prefill auto:16384 --expert-cache auto --pcie-frac 0.20 \
   --tokens-file /data/w962/prompt.tok --max-new 64 --top-k 1 > /data/w962/C070.out 2>&1; echo RC=\$?; \
   grep -E '^prefill |^decode |^output' /data/w962/C070.out | head -3" 2>&1 | tail -6

docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
