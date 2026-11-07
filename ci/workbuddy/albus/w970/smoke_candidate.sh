#!/bin/bash
# W970: smoke the 0.8.0 build with the EXACT production config (--mtp, --vision, spec, caches), then stop.
# Only runs the candidate; the switch is a separate step.
set -u
H=/home/albus/strata166
mkdir -p "$H/data/w970"
python3 - <<'PY'
import json
src = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c = json.load(open(src))
d = dict(c)
d["exe"] = "/b/strata"
d["log"] = "/data/w970/candidate.log"
json.dump(d, open("/home/albus/strata166/data/w970/cand.json", "w"), indent=1)
print("exe:", d["exe"], "| args:", len(d["args"]))
PY

echo "== stop prod =="
docker stop strata166-407 >/dev/null

docker run -d --rm --name w970_cand --device=/dev/kfd --device=/dev/dri -p 8099:8090 \
  -v "$H/data":/data -v "$H/pr/strata-fork":/src -v /models:/models -v "$H/build-r29":/b \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  -e STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
  -e STRATA_PREFILL_CPU_SHARE=auto -e STRATA_PREFILL_CPU_SHARE_MAX=3072 \
  strata-gfx906:0.2.10-101 bash -lc \
  "cd /src && python3 serve/server.py --engine strata --config /data/w970/cand.json --port 8090" >/dev/null

ok=0
for i in $(seq 1 100); do
  r=$(curl -s -m 2 localhost:8099/health || true)
  case "$r" in *'"loaded": true'*) echo "up after $((i*4))s"; ok=1; break;; esac
  sleep 4
done
if [ "$ok" != "1" ]; then
  echo "CANDIDATE DID NOT LOAD — last log:"; tail -12 "$H/data/w970/candidate.log"
else
  echo "== health =="; curl -s -m 3 localhost:8099/health | head -c 200; echo
  echo "== a real 2.3K-token request =="
  python3 - <<'PY'
import json, time, urllib.request
txt = "smoke " + "The quick brown fox jumps over the lazy dog. " * 230
body = json.dumps({"model": "x", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": 8, "temperature": 0.0}).encode()
t0 = time.time()
r = json.load(urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8099/v1/chat/completions", data=body,
    headers={"Content-Type": "application/json"}), timeout=300))
print("  %.2fs  usage=%s" % (time.time() - t0, r.get("usage")))
print("  text=%r" % r["choices"][0]["message"]["content"][:80])
PY
  echo "== engine-side =="
  grep -oE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" "$H/data/w970/candidate.log" | tail -3
fi
docker rm -f w970_cand >/dev/null 2>&1

echo "== restore prod (unchanged engine) =="
docker start strata166-407 >/dev/null
for i in $(seq 1 140); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
