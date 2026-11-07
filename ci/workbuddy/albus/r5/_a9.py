import sys
sys.path.insert(0, "albus/r5")
from _rsh import sh
print(sh(r'''
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
cp $CFG /tmp/cfg_a9.bak
python3 - <<'PY'
import json
p="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d=json.load(open(p)); d["env"].pop("STRATA_SELECT_SIMT", None)
json.dump(d, open(p,"w"), indent=2, ensure_ascii=False)
print("PROBE env_n=%d simt=%s" % (len(d["env"]), d["env"].get("STRATA_SELECT_SIMT")))
PY
N0=$(wc -l < $L)
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 240); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s"; break; }; sleep 1; done
sleep 5
curl -s --max-time 400 http://127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs-abliterated","messages":[{"role":"user","content":"回复一个字：好"}],"max_tokens":4,"temperature":0}' >/dev/null 2>&1
echo "== probe process lines (banner count) =="
tail -n +$((N0+1)) $L | grep -c "FP32 tiled scorer"
echo "== tail-skip line =="
tail -n +$((N0+1)) $L | grep -c "ROUTE_TAIL_SKIP=7"
cp /tmp/cfg_a9.bak $CFG
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 240); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('RESTORED env_n',len(d['env']),d['env'].get('STRATA_SELECT_SIMT'))"
''', t=560))
