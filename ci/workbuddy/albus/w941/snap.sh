#!/bin/bash
# W941 production snapshot (8 fields, REPORT_STANDARD.md)
C=strata166-407
echo "F1_container_id=$(docker inspect -f '{{.Id}}' $C | cut -c1-12)"
echo "F1_image_tag=$(docker inspect -f '{{.Config.Image}}' $C)"
echo "F1_image_id=$(docker inspect -f '{{.Image}}' $C | cut -c8-19)"
echo "F4_health=$(curl -s localhost:8090/health)"
echo "F4_started=$(docker inspect -f '{{.State.StartedAt}}' $C)"
PID=$(docker exec $C sh -c 'pgrep -f "strata-0.1.56" | head -1')
echo "PID=$PID"
echo "F2_running_md5=$(docker exec $C sh -c "md5sum /proc/$PID/exe | cut -d' ' -f1")"
echo "F2_running_bytes=$(docker exec $C sh -c "stat -Lc %s /proc/$PID/exe")"
echo "F2_running_version=$(docker exec $C sh -c "/proc/$PID/exe --version 2>&1 | head -1")"
echo "F3_config_md5=$(docker exec $C md5sum /data/strata-huihui-ud-iq4_xs.json | cut -d' ' -f1)"
echo "F5_ulimit=$(docker exec $C sh -c 'ulimit -l')"
echo "F5_VmLck=$(docker exec $C sh -c "grep VmLck /proc/$PID/status")"
echo "F6_layout=$(docker exec $C sh -c "grep -E 'expert cache|prompt path borrows' /data/strata-huihui-ud-iq4_xs.log | tail -2")"
echo "F6_vram=$(docker exec $C sh -c "rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -2")"
echo "F8_disk_md5=$(docker exec $C md5sum /data/bin/strata-0.1.56 | cut -d' ' -f1)"
echo "F8_build_md5=$(md5sum /home/albus/strata166/build-r28/strata 2>/dev/null | cut -d' ' -f1)"
