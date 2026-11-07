echo "--- build ---"
tail -2 /home/albus/strata166/src028/build-028.log
grep -c 'Building' /home/albus/strata166/src028/build-028.log || true
grep -oE '^\[[0-9]+/[0-9]+\]' /home/albus/strata166/src028/build-028.log | tail -1
docker ps --format '{{.Names}}' | grep buildrun || echo "container gone"
echo "--- prod cfg keys ---"
python3 - <<'PY'
import json
p='/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'
c=json.load(open(p))
for k,v in c.items():
    if k in ('args','env'): print(k, 'len', len(v)); continue
    print(k, '=', repr(v)[:120])
PY
