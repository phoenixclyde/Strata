#!/bin/bash
cd /home/albus/strata166/pr/strata-fork
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | awk '{print "config", $1}'
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print("prefill", a[a.index("--prefill")+1], "| args", len(a), "| env", type(c["env"]).__name__, len(c["env"]))
PY
curl -s -m 3 localhost:8090/health | head -c 50; echo
docker inspect strata166-407 --format 'StartedAt={{.State.StartedAt}} restarts={{.RestartCount}}'
git log -1 --format='HEAD %h'
git rev-list --left-right --count @{u}...HEAD | awk '{printf "behind %s / ahead %s\n", $1, $2}'
