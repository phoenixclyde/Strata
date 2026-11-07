#!/bin/bash
# W948: one-shot snapshot for the 8 required fields — no hand typing, so nothing gets dropped.
set -u
C=strata166-407
CFG=/data/strata-huihui-ud-iq4_xs.json
echo "F1_container_id=$(docker inspect -f '{{.Id}}' $C | cut -c1-12)"
echo "F1_image_tag=$(docker inspect -f '{{.Config.Image}}' $C)"
echo "F1_image_id=$(docker inspect -f '{{.Image}}' $C | cut -c8-19)"
echo "F2_version=$(docker exec $C /data/bin/strata-0.1.56 --version 2>&1 | head -1)"
PID=$(docker exec $C sh -c 'pgrep -f "strata-0.1.56" | head -1')
echo "F2_running_md5=$(docker exec $C sh -c "md5sum /proc/$PID/exe | cut -d' ' -f1")"
echo "F2_running_bytes=$(docker exec $C sh -c "stat -Lc %s /proc/$PID/exe")"
echo "F3_config_md5=$(docker exec $C md5sum $CFG | cut -d' ' -f1)"
echo "F3_config_counts=$(docker exec $C python3 -c "import json;d=json.load(open('$CFG'));print('args=%d env=%d exe=%s'%(len(d['args']),len(d['env']),d['exe']))")"
echo "F3_args=$(docker exec $C python3 -c "import json;d=json.load(open('$CFG'));print(' '.join(d['args']))")"
echo "F3_env=$(docker exec $C python3 -c "import json;d=json.load(open('$CFG'));print(' '.join(k+'='+v for k,v in d['env'].items()))")"
echo "F4_health=$(curl -s localhost:8090/health)"
echo "F4_restarts=$(docker inspect -f '{{.RestartCount}}' $C)"
echo "F4_started=$(docker inspect -f '{{.State.StartedAt}}' $C)"
echo "F5_ulimit_l=$(docker exec $C sh -c 'ulimit -l')"
echo "F5_vmlck=$(docker exec $C sh -c "grep VmLck /proc/$PID/status | tr -s ' '")"
echo "F6_layout=$(docker exec $C sh -c "grep -E 'expert cache [0-9]+ slots|prompt path borrows|VRAM free' /data/strata-huihui-ud-iq4_xs.log | tail -3 | tr '\n' '|'")"
echo "F8_disk_md5=$(docker exec $C md5sum /data/bin/strata-0.1.56 | cut -d' ' -f1)"
echo "F8_build_md5=$(md5sum /home/albus/strata166/build-r28/strata 2>/dev/null | cut -d' ' -f1)"
