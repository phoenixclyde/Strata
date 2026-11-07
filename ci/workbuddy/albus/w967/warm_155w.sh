#!/bin/bash
# W967: same warm probe, but with the rollback engine strata-0.1.55w (0.2.9 era).
# If this is ~2x faster than 0.1.56, the prefill regression is OUR engine, not llama.cpp.
set -u
H=/home/albus/strata166
OUT=$H/data/w967
mkdir -p "$OUT"

python3 - <<'PY'
import json
src = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c = json.load(open(src))
d = dict(c)
d["exe"] = "/data/bin/strata-0.1.55w"
d["log"] = "/data/w967/cfgC.log"
json.dump(d, open("/home/albus/strata166/data/w967/cfgC.json", "w"), indent=1)
print("cfgC written")
PY

echo "== stop prod =="
docker stop strata166-407 >/dev/null

docker run -d --rm --name w967_C --device=/dev/kfd --device=/dev/dri -p 8099:8090 \
  -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
  -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
  strata-gfx906:0.2.10-101 bash -lc \
  "cd /src && python3 serve/server.py --engine strata --config /data/w967/cfgC.json --port 8090" >/dev/null

for i in $(seq 1 100); do
  r=$(curl -s -m 2 localhost:8099/health || true)
  case "$r" in *'"loaded": true'*) echo "up after $((i*4))s"; break;; esac
  sleep 4
done

docker exec w967_C python3 /src/ci/prefill_probe.py --quick 2>&1 | tail -14
docker rm -f w967_C >/dev/null 2>&1

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
