#!/bin/bash
cd /home/albus/strata166/pr/strata-fork
echo "== config =="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | awk '{print " md5", $1}'
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print(" args", len(a), "| pool-tasks:", "--pool-tasks" in a, "| ple:", a[a.index("--ple-io")+1],
      "| env:", type(c["env"]).__name__, len(c["env"]), "| exe:", c["exe"])
PY
echo "== git =="
git log -1 --format=' %h %s' | cut -c1-60
printf ' tag %s | ' "$(git describe --tags --abbrev=0)"
git rev-list --left-right --count @{u}...HEAD | awk '{printf "behind %s / ahead %s | ", $1, $2}'
printf 'dirty %s\n' "$(git status --porcelain | wc -l)"
echo "== health =="
curl -s -m 3 localhost:8090/health | head -c 70; echo
docker inspect strata166-407 --format ' StartedAt={{.State.StartedAt}} restarts={{.RestartCount}}'
echo "== 显存/借用 =="
docker exec strata166-407 bash -lc 'grep -aoE "borrows [0-9]+ \([0-9.]+ GiB\)|VRAM free [0-9]+ MiB" /data/strata-huihui-ud-iq4_xs.log | tail -2'
echo "== 门账 =="
ls -t ci/state/cfg/*.json 2>/dev/null | head -3
tail -3 ci/state/cfg/ledger.tsv 2>/dev/null
