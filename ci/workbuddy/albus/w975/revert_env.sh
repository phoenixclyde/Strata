#!/bin/bash
set -u
python3 - <<'PY'
import json
p="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c=json.load(open(p))
c["env"]=[e for e in c["env"] if not e.startswith("STRATA_PLE_AUTO_RAM=")]
json.dump(c,open(p,"w"),indent=1)
print("env count:", len(c["env"]))
PY
docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 40); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
curl -s -m 3 localhost:8090/health | head -c 90; echo
echo "--- B 臂启动失败原因（容器日志）---"
docker logs --tail 25 strata166-407 2>&1 | tail -20
