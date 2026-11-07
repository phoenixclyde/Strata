#!/bin/bash
cd /home/albus/strata166/pr/strata-fork
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | awk '{print "config", $1}'
grep -o '"pcie-frac"[^,]*' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | head -1
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print(" pcie-frac =", a[a.index("--pcie-frac")+1], "| args", len(a), "| env", type(c["env"]).__name__, len(c["env"]))
PY
docker inspect strata166-407 --format 'StartedAt={{.State.StartedAt}} restarts={{.RestartCount}}'
curl -s -m 3 localhost:8090/health | head -c 60; echo
git log -1 --format='HEAD %h %s' | cut -c1-55
git rev-list --left-right --count @{u}...HEAD | awk '{printf "behind %s / ahead %s | ", $1, $2}'
printf 'dirty %s\n' "$(git status --porcelain | wc -l)"
tail -4 ci/state/cfg/ledger.tsv
