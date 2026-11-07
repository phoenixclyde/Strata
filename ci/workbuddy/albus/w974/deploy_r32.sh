#!/bin/bash
# 切换到 0.9.0（ggml 0.29.0）候选引擎
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]
c=json.load(open(p))
old=c["exe"]
c["exe"]="/data/bin/strata-0.1.56-090"
json.dump(c,open(p,"w"),indent=1)
print("exe:",old,"->",c["exe"])
PY
echo "--- restart ---"
docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 60); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
curl -s -m 3 localhost:8090/health | head -c 120; echo
echo "--- 运行中的引擎 ---"
docker exec strata166-407 md5sum /data/bin/strata-0.1.56-090
