#!/bin/bash
# W959 / R90-S4 round 3: quality via the same path the project already uses (serve + STRATA_DUMP_FIRST_LOGITS),
# because --dump-logits does not fire on a native pack and the engine is documented as not bit-exact run to run
# (generate.cpp: expert swaps between CPU and GPU "round differently").
set -u
H=/home/albus/strata166
OUT=$H/data/w959
mkdir -p "$OUT"
TXT=$(python3 -c 'print(("The quick brown fox jumps over the lazy dog. "*45).strip())')
printf '%s' "$TXT" > "$OUT/prompt.txt"
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {   # $1 name, $2 binary, $3 extra mount
  local name=$1 bin=$2 extra=${3:-}
  echo "== arm $name =="
  docker run -d --rm --name "w959_$name" --device=/dev/kfd --device=/dev/dri \
    -p 8099:8090 \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models $extra \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    -e STRATA_DUMP_FIRST_LOGITS=/data/w959/$name.first \
    strata-gfx906:0.2.10-101 bash -lc \
    "$bin serve --pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
     --max-context 262144 --kv k8v4 --prefill auto:16384 --expert-cache auto --pcie-frac 0.20 --port 8090 \
     > /data/w959/$name.serve.log 2>&1" >/dev/null

  for i in $(seq 1 100); do
    r=$(curl -s -m 2 localhost:8099/health || true)
    case "$r" in *'"loaded": true'*) echo "  up after $((i*4))s"; break;; esac
    sleep 4
  done

  python3 - "$OUT/prompt.txt" "$name" <<'PY'
import json, sys, urllib.request
text = open(sys.argv[1]).read()
body = json.dumps({"prompt": text, "n_predict": 1, "temperature": 0.0, "top_k": 1}).encode()
for path in ("/completion", "/v1/completions"):
    try:
        req = urllib.request.Request("http://127.0.0.1:8099" + path, data=body,
                                     headers={"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=180))
        print("  %s ok: %s" % (path, str(r)[:120]))
        break
    except Exception as e:
        print("  %s failed: %s" % (path, e))
PY

  sleep 3
  docker rm -f "w959_$name" >/dev/null 2>&1
  ls -l "$OUT/$name.first".* 2>/dev/null | head -3
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
ls -l "$OUT" | tail -6
