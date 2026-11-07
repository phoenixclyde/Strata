#!/bin/bash
# W957 / R90-S4: numerical equivalence 0.4.1 (production binary) vs 0.8.0 (build-080c), same prompt, one prefill each.
# NOTE: `strata` defaults to the generate mode -- no "generate" subcommand (that was the RC=2 last time).
set -u
H=/home/albus/strata166
OUT=$H/data/w957
mkdir -p "$OUT"
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
COMMON="--pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
--max-context 262144 --kv k8v4 --prefill auto:16384 --expert-cache auto --pcie-frac 0.20 \
--tokens-file /data/w957/prompt.tok --max-new 64 --top-k 1"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {
  local name=$1 bin=$2 extra=${3:-}
  echo "== arm $name ($bin) =="
  docker run --rm --device=/dev/kfd --device=/dev/dri \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models $extra \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    strata-gfx906:0.2.10-101 bash -lc \
    "$bin $COMMON > /data/w957/$name.out 2>&1; echo ARM_${name}_RC=\$?; tail -5 /data/w957/$name.out"
}

run_arm A /data/bin/strata-0.1.56
run_arm B /b/strata "-v $H/build-080c:/b"

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
ls -l "$OUT"/*.logits 2>/dev/null
