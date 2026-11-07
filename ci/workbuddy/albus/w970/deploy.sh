#!/bin/bash
# W970: switch production to the 0.8.0 build (tag mi50-0.2.10-r31 / 304bd3be, build-r29, overlay ON).
# Keeps the previous binary and config for an immediate rollback.
set -u
H=/home/albus/strata166
NEW=/data/bin/strata-0.1.56-080
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "== stage the binary =="
docker cp "$H/build-r29/strata" strata166-407:$NEW
docker exec strata166-407 bash -lc "chmod +x $NEW; md5sum $NEW; ls -l $NEW | awk '{print \$5}'"
echo "build md5: $(md5sum "$H/build-r29/strata" | cut -d' ' -f1)"

echo "== back up + repoint the config =="
docker exec strata166-407 bash -lc "cp -n $CFG ${CFG}.bak_w970; python3 - <<'PY'
import json
p='$CFG'
c=json.load(open(p))
print('old exe:', c['exe'])
c['exe']='$NEW'
json.dump(c, open(p,'w'), indent=1)
print('new exe:', c['exe'])
PY"

echo "== restart =="
docker restart strata166-407 >/dev/null
for i in $(seq 1 150); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after $((i*4))s"; echo "$r" | head -c 160; break;; esac
  sleep 4
done

echo "== verify =="
docker exec strata166-407 md5sum $NEW
python3 - <<'PY'
import json, time, urllib.request
txt = "verify " + "The quick brown fox jumps over the lazy dog. " * 230
body = json.dumps({"model": "x", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": 16, "temperature": 0.0}).encode()
t0 = time.time()
r = json.load(urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8090/v1/chat/completions", data=body,
    headers={"Content-Type": "application/json"}), timeout=300))
u = r.get("usage", {})
print("  %.2fs  prompt=%s out=%s" % (time.time() - t0, u.get("prompt_tokens"), u.get("completion_tokens")))
print("  head=%r" % (r["choices"][0]["message"].get("content") or r["choices"][0]["message"].get("reasoning_content") or "")[:80])
PY
grep -oE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" "$H/data/strata-huihui-ud-iq4_xs.log" | tail -2
