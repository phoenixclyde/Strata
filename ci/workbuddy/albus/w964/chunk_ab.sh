#!/bin/bash
# W964: same binary (0.1.56), same 9707-token prompt, only the chunk ceiling differs:
#   arm P8  : --prefill auto        (auto cap 8192, what production had until 11-04 04:34)
#   arm P16 : --prefill auto:16384  (what production has now)
# W863 (11-01) measured 1404 tok/s at 9707 tokens; today's runs sit at ~600-790.
set -u
H=/home/albus/strata166
OUT=$H/data/w964
mkdir -p "$OUT"
python3 - <<'PY'
ids = [1000 + (i * 37) % 200000 for i in range(9707)]
open("/home/albus/strata166/data/w964/p9707.tok", "w").write(",".join(map(str, ids)))
print("prompt tokens:", len(ids))
PY
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
BASE="--pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
--max-context 262144 --kv k8v4 --expert-cache auto --pcie-frac 0.20 \
--tokens-file /data/w964/p9707.tok --max-new 1 --top-k 1"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {
  local name=$1 chunk=$2
  echo "== arm $name ($chunk) =="
  docker run --rm --device=/dev/kfd --device=/dev/dri \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    strata-gfx906:0.2.10-101 bash -lc \
    "/data/bin/strata-0.1.56 $BASE --prefill $chunk > /data/w964/$name.out 2>&1; echo ARM_${name}_RC=\$?; \
     grep -E '^prefill |^decode ' /data/w964/$name.out"
}

run_arm P8  auto
run_arm P16 auto:16384

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
