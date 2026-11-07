#!/bin/bash
echo "== 生效的内核策略 =="
printf '  swappiness            %s\n' "$(sysctl -n vm.swappiness)"
printf '  vfs_cache_pressure    %s\n' "$(sysctl -n vm.vfs_cache_pressure)"
printf '  dirty_background_bytes %s\n' "$(sysctl -n vm.dirty_background_bytes)"
printf '  dirty_bytes           %s\n' "$(sysctl -n vm.dirty_bytes)"
printf '  read_ahead_kb         %s\n' "$(cat /sys/block/nvme0n1/queue/read_ahead_kb)"
echo
echo "== 持久化文件 =="
ls -l /etc/sysctl.d/99-strata-nvme.conf /etc/udev/rules.d/60-nvme-readahead.rules
echo
echo "== 配置 =="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
print("  exe:",c["exe"],"| args:",len(c["args"]),"| env:",type(c["env"]).__name__,len(c["env"]))
print("  mmap-experts:", "--mmap-experts" in c["args"], "| PLE env:", "STRATA_PLE_AUTO_RAM" in c["env"])
PY
echo
echo "== 容器/引擎 =="
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
docker exec strata166-407 md5sum /data/bin/strata-0.1.56-090
echo
echo "== 内存/显存 =="
free -m | awk '/^Mem:/{printf "  total=%d MiB available=%d MiB cached=%d MiB\n",$2,$7,$6}'
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Used|Total" | head -2
echo
echo "== 启动日志关键行 =="
grep -aE "loaded .* GiB at|expert cache .* slots|ple-io (ram|direct)|expert arena read" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -5
