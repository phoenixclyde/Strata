#!/bin/bash
# W835: discover what llama.cpp-family trees exist on 166, and the production state
echo "=== 1. /home/albus top level ==="
ls -la /home/albus/ 2>/dev/null | head -40
echo
echo "=== 2. candidate llama.cpp trees (depth<=4) ==="
find /home/albus /opt /srv -maxdepth 4 -type d \( -iname "*llama.cpp*" -o -iname "*llamacpp*" -o -iname "*ik_llama*" -o -iname "*kobold*" -o -iname "*ktransformers*" \) 2>/dev/null | head -40
echo
echo "=== 3. any dir literally named ki / KI ==="
find /home/albus /opt -maxdepth 3 -type d -iname "ki" 2>/dev/null | head -10
echo
echo "=== 4. git remotes of those trees ==="
for d in $(find /home/albus /opt -maxdepth 4 -type d -name ".git" 2>/dev/null | head -30); do
  p=$(dirname "$d")
  url=$(git -C "$p" config --get remote.origin.url 2>/dev/null)
  br=$(git -C "$p" rev-parse --abbrev-ref HEAD 2>/dev/null)
  sha=$(git -C "$p" rev-parse --short HEAD 2>/dev/null)
  echo "$p | $url | $br@$sha"
done
echo
echo "=== 5. docker images / containers ==="
docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null | head -25
echo "--- containers ---"
docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}}' 2>/dev/null | head -25
echo
echo "=== 6. production snapshot (quick) ==="
date +%H:%M:%S
docker inspect strata166-407 --format 'img={{.Config.Image}} started={{.State.StartedAt}}' 2>/dev/null
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 160; echo
python3 -c "
import json
c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
a=c['args']
print('nargs',len(a),'nenv',len(c.get('env') or {}))
print('exe',a[0] if a else '?')
"
