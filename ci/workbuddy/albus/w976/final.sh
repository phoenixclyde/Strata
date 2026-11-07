#!/bin/bash
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
echo "== 配置 =="
md5sum $P
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print("  args:",len(a),"| ple-io:", a[a.index("--ple-io")+1] if "--ple-io" in a else "(default)")
print("  mmap-experts:", "--mmap-experts" in a, "| env:",type(c["env"]).__name__,len(c["env"]))
print("  exe:",c["exe"])
PY
echo "== 容器 =="
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
docker inspect strata166-407 --format '  StartedAt={{.State.StartedAt}} restart={{.RestartCount}}'
echo "== 内存/显存 =="
free -m | awk '/^Mem:/{printf "  MemAvailable=%d MiB Cached=%d MiB\n",$7,$6}'
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
sudo awk '/^(Rss|Anonymous|Locked):/{printf "  %-12s %7.2f GiB\n",$1,$2/1048576}' /proc/$PID/smaps_rollup
rocm-smi --showmeminfo vram 2>/dev/null | grep -E "Used Memory|Total Memory" | head -2
echo "== health =="
curl -s -m 3 localhost:8090/health | head -c 90; echo
echo "== PLE/缓存关键行 =="
grep -aE "PLE table|expert cache .* slots" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -3
