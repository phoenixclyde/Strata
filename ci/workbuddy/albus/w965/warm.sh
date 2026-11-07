#!/bin/bash
# W965: WARM prefill comparison (the way W863 measured: serve + real text + a discarded warm-up).
# Cold runs (generate, first prompt after load) sit at ~600-700; W863's 1231@2.5K / 1404@9.7K were warm.
set -u
H=/home/albus/strata166
OUT=$H/data/w965
mkdir -p "$OUT"
GGUF=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {   # $1 name  $2 binary  $3 extra mount
  local name=$1 bin=$2 extra=${3:-}
  echo "== arm $name =="
  docker run -d --rm --name "w965_$name" --device=/dev/kfd --device=/dev/dri -p 8099:8090 \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models $extra \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    strata-gfx906:0.2.10-101 bash -lc \
    "$bin serve --pack /data/packs/ud-q4_k_xl --native $GGUF --spec 4 --expert-profile /src/data/expert-profile.bin \
     --max-context 262144 --kv k8v4 --prefill auto:16384 --expert-cache auto --pcie-frac 0.20 --port 8090 \
     > /data/w965/$name.serve.log 2>&1" >/dev/null

  for i in $(seq 1 100); do
    r=$(curl -s -m 2 localhost:8099/health || true)
    case "$r" in *'"loaded": true'*) echo "  up after $((i*4))s"; break;; esac
    sleep 4
  done

  python3 - "$name" <<'PY'
import json, sys, time, urllib.request, statistics
name = sys.argv[1]
FILLER = "The quick brown fox jumps over the lazy dog. "
def probe(approx_tokens, reps):
    text = FILLER * max(1, int(approx_tokens / 11))
    body = lambda: json.dumps({"prompt": text, "n_predict": 1, "temperature": 0.0, "top_k": 1,
                               "stream": False}).encode()
    # warm-up, discarded (W863: "the first call of each cell is discarded")
    req = urllib.request.Request("http://127.0.0.1:8099/completion", data=body(),
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    n = r.get("usage", {}).get("prompt_tokens") or r.get("tokens_evaluated")
    ts = []
    for _ in range(reps):
        t0 = time.time()
        req = urllib.request.Request("http://127.0.0.1:8099/completion", data=body(),
                                     headers={"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=600))
        ts.append(time.time() - t0)
    med = statistics.median(ts)
    print("  %s n=%s warm med=%.3fs -> %.1f tok/s  (all: %s)" %
          (name, n, med, (n or 0) / med, ",".join("%.2f" % t for t in ts)))
for L in (2400, 9700):
    probe(L, 3)
PY

  docker rm -f "w965_$name" >/dev/null 2>&1
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
