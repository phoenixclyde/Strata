#!/bin/bash
# W966: WARM prefill comparison through the production wrapper (serve/server.py) + the project's own probe.
# Only %s differs between arms: cfg exe = production 0.1.56  vs  /b/strata (0.8.0 port).
set -u
H=/home/albus/strata166
OUT=$H/data/w966
mkdir -p "$OUT"

python3 - <<'PY'
import json
src = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c = json.load(open(src))
for name, exe in (("cfgA", "/data/bin/strata-0.1.56"), ("cfgB", "/b/strata")):
    d = dict(c)
    d["exe"] = exe
    d["log"] = "/data/w966/%s.log" % name
    json.dump(d, open("/home/albus/strata166/data/w966/%s.json" % name, "w"), indent=1)
print("cfgs written")
PY

echo "== stop prod =="
docker stop strata166-407 >/dev/null

run_arm () {
  local name=$1 extra=${2:-}
  echo "== arm $name =="
  docker run -d --rm --name "w966_$name" --device=/dev/kfd --device=/dev/dri -p 8099:8090 \
    -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models $extra \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
    -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
    -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
    strata-gfx906:0.2.10-101 bash -lc \
    "cd /src && python3 serve/server.py --engine strata --config /data/w966/cfg$name.json --port 8090" >/dev/null
  for i in $(seq 1 100); do
    r=$(curl -s -m 2 localhost:8099/health || true)
    case "$r" in *'"loaded": true'*) echo "  up after $((i*4))s"; break;; esac
    sleep 4
  done
  docker exec "w966_$name" python3 /src/ci/prefill_probe.py --quick 2>&1 | tail -18
  docker rm -f "w966_$name" >/dev/null 2>&1
}

run_arm A
run_arm B "-v $H/build-080c:/b"

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
