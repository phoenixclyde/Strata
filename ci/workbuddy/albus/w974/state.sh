#!/bin/bash
echo "== 容器 =="
docker inspect strata166-407 --format '{{.State.StartedAt}} restart={{.RestartCount}} status={{.State.Status}}'
docker ps --format '{{.Names}} {{.Status}}' | grep strata
echo
echo "== config =="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
python3 - <<'PY'
import json
p="/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c=json.load(open(p))
print("exe:", c["exe"])
print("args:", len(c["args"]), "env:", len(c["env"]), "vision:", c["vision"]["exe"])
PY
echo
echo "== 引擎 =="
docker exec strata166-407 md5sum /data/bin/strata-0.1.56-090
echo
echo "== 显存 =="
docker exec strata166-407 bash -lc 'grep -oE "expert cache [0-9]+ slots[^,]*, [0-9.]+ GiB|VRAM free [0-9]+ MiB" /data/strata-huihui-ud-iq4_xs.log | tail -3'
