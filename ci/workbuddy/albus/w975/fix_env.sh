#!/bin/bash
# 从 .bak_w974 恢复 env（dict），保留当前 exe
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
B=$P.bak_w974
echo "--- 备份里的 env 类型与内容 ---"
python3 - "$B" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print("type:",type(c["env"]).__name__,"count:",len(c["env"]))
for k,v in c["env"].items(): print("  ",k,"=",v)
PY
echo "--- 当前（已损坏）---"
python3 - "$P" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print("type:",type(c["env"]).__name__)
print("exe:",c["exe"])
PY
echo "--- 恢复 ---"
python3 - "$P" "$B" <<'PY'
import json,sys
p,b=sys.argv[1],sys.argv[2]
cur=json.load(open(p)); bak=json.load(open(b))
cur["env"]=bak["env"]
json.dump(cur,open(p,"w"),indent=1)
chk=json.load(open(p))
print("restored type:",type(chk["env"]).__name__,"count:",len(chk["env"]),"exe:",chk["exe"])
PY
docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 40); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
curl -s -m 3 localhost:8090/health | head -c 90; echo
