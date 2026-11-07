#!/bin/bash
# W839-38 终检：量化状态 + 横幅 + 门禁
D=/home/albus/strata166/data
date +%H:%M:%S
echo "=== 容器 / 镜像 / exe ==="
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
docker inspect strata166-407 --format 'img={{.Config.Image}}'
python3 -c "import json;c=json.load(open('$D/strata-huihui-ud-iq4_xs.json'));print('exe',c['exe'],'args',len(c['args']),'env',len(c['env']))"
echo
echo "=== 生产日志里的架构横幅（入口生效的证据）==="
grep -a 'MI50-class' $D/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-230
echo
echo "=== 量化状态 ==="
python3 /home/albus/strata166/tmp/state_q.py --no-probe 2>&1 | sed -n '4,12p'
echo
echo "=== 门禁 ==="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -22
