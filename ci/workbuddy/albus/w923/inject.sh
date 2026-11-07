#!/bin/bash
set -u
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 1. 备份配置 ==="
docker exec strata166-407 cp $CFG ${CFG}.bak-w923
docker exec strata166-407 md5sum ${CFG}.bak-w923

echo
echo "=== 2. 确认计数器名在 gfx906 上可用 ==="
docker exec strata166-407 sh -c 'rocprofv3-avail list --pmc 2>/dev/null | grep -cE "VALUBusy|MemUnitStalled|FetchSize"'

echo
echo "=== 3. 注入 profiler env ==="
docker exec strata166-407 mkdir -p /data/w923
docker exec strata166-407 python3 -c "
import json
p='$CFG'
d=json.load(open(p))
d['env']['HSA_TOOLS_LIB']='/opt/rocm/lib/rocprofiler-sdk/librocprofiler-sdk-tool.so'
d['env']['ROCPROF_COUNTERS']='VALUBusy MemUnitStalled FetchSize'
d['env']['ROCPROF_COUNTER_COLLECTION']='1'
d['env']['ROCPROF_OUTPUT_FORMAT']='csv'
d['env']['ROCPROF_OUTPUT_FILE_NAME']='pmc'
d['env']['ROCPROF_OUTPUT_PATH']='/data/w923'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('env count:', len(d['env']))
print([k for k in d['env'] if k.startswith('ROCPROF') or k=='HSA_TOOLS_LIB'])
"

echo
echo "=== 4. 重启并等 health（profiler 会拖慢，最多 900 s）==="
docker restart strata166-407 >/dev/null && echo RESTARTED
UP=0
for i in $(seq 1 180); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; UP=1; break;; esac
  sleep 5
done
[ "$UP" = "0" ] && echo "!!! NOT UP after 900s"

echo
echo "=== 5. 引擎是否活着 ==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo "pid=$P"; [ -n "$P" ] && grep -E "VmRSS" /proc/$P/status'
