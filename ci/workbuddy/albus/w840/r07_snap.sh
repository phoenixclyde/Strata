#!/bin/bash
# W840-07 落盘前的最终现状快照（只读）
D=/home/albus/strata166/data
date +%H:%M:%S
echo "--- 容器/镜像/exe/env ---"
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
docker inspect strata166-407 --format 'img={{.Config.Image}}'
python3 -c "import json;c=json.load(open('$D/strata-huihui-ud-iq4_xs.json'));print('exe',c['exe'],'args',len(c['args']),'env',len(c['env']))"
echo "--- health ---"
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 110; echo
echo "--- 量化 ---"
python3 /home/albus/strata166/tmp/state_q.py --no-probe 2>&1 | sed -n '5,10p'
echo "--- 门禁 ---"
bash /home/albus/strata166/tmp/verify_patches.sh 2>/dev/null | grep -cE 'OK$'
bash /home/albus/strata166/tmp/verify_patches.sh 2>/dev/null | tail -1
echo "--- 分支 ---"
git -C /home/albus/strata166/gfx906 rev-parse --short HEAD
git -C /home/albus/strata166/gfx906 log -1 --format='%s' | cut -c1-70
