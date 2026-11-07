#!/bin/bash
# W968: same probe, same 1916-token prompt, engine 0.1.56, ONLY --prefill differs:
#   cfgAuto : --prefill auto        (what production had until 2026-11-04 04:34)
#   cfg16k  : --prefill auto:16384  (what production has now; already measured 503 tok/s)
set -u
H=/home/albus/strata166
OUT=$H/data/w968
mkdir -p "$OUT"

python3 - <<'PY'
import json
src = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c = json.load(open(src))
args = list(c["args"])
i = args.index("--prefill")
print("old chunk arg:", args[i + 1])
args[i + 1] = "auto"
d = dict(c)
d["args"] = args
d["exe"] = "/data/bin/strata-0.1.56"
d["log"] = "/data/w968/cfgAuto.log"
json.dump(d, open("/home/albus/strata166/data/w968/cfgAuto.json", "w"), indent=1)
print("cfgAuto written")
PY

echo "== stop prod =="
docker stop strata166-407 >/dev/null

docker run -d --rm --name w968_A --device=/dev/kfd --device=/dev/dri -p 8099:8090 \
  -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
  -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
  strata-gfx906:0.2.10-101 bash -lc \
  "cd /src && python3 serve/server.py --engine strata --config /data/w968/cfgAuto.json --port 8090" >/dev/null

for i in $(seq 1 100); do
  r=$(curl -s -m 2 localhost:8099/health || true)
  case "$r" in *'"loaded": true'*) echo "up after $((i*4))s"; break;; esac
  sleep 4
done

docker exec w968_A python3 /src/ci/prefill_probe.py --quick 2>&1 | tail -12
echo "--- engine-side numbers for the same requests ---"
grep -oE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" "$H/data/w968/cfgAuto.log" | tail -8
docker rm -f w968_A >/dev/null 2>&1

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
