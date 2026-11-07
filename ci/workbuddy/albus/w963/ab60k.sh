#!/bin/bash
# W963: production-length prefill (60K tokens) for both arms.
# Production's own log: 60,330 tokens -> 804.1 tok/s, 60,008 -> 800.2, 15,734 -> 704.4, 2,047 -> ~604.
# So throughput grows with length; the earlier A/B at 2K was the worst case and is not the production regime.
set -u
H=/home/albus/strata166
OUT=$H/data/w963
mkdir -p "$OUT"
python3 - <<'PY'
ids = [1000 + (i * 37) % 200000 for i in range(60000)]
open("/home/albus/strata166/data/w963/prompt60k.tok", "w").write(",".join(map(str, ids)))
print("prompt tokens:", len(ids))
PY
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
COMMON="--pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
--max-context 262144 --kv k8v4 --prefill auto:16384 --expert-cache auto --pcie-frac 0.20 \
--tokens-file /data/w963/prompt60k.tok --max-new 1 --top-k 1"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {
  local name=$1 bin=$2 extra=${3:-}
  echo "== arm $name =="
  docker run --rm --device=/dev/kfd --device=/dev/dri \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models $extra \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    strata-gfx906:0.2.10-101 bash -lc \
    "$bin $COMMON > /data/w963/$name.out 2>&1; echo ARM_${name}_RC=\$?; grep -E '^prefill |^decode ' /data/w963/$name.out"
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
