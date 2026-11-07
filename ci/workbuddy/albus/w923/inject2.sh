#!/bin/bash
set -u
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 加 ROCPROF_LOG_LEVEL=debug 并清空输出目录 ==="
docker exec strata166-407 rm -rf /data/w923/* 2>/dev/null
docker exec strata166-407 python3 -c "
import json
p='$CFG'
d=json.load(open(p))
d['env']['ROCPROF_LOG_LEVEL']='debug'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('env count:', len(d['env']))
"

echo "=== 重启 ==="
docker restart strata166-407 >/dev/null && echo RESTARTED
for i in $(seq 1 180); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo
echo "=== profiler 的 debug 输出（关键）==="
docker exec strata166-407 sh -c "tail -600 /data/strata-huihui-ud-iq4_xs.log | grep -iE 'rocprof|profiler|HSA_TOOLS|tool lib|counter|dlopen|rocp' | head -25 | cut -c1-190"

echo
echo "=== 发一个小请求 ==="
curl -s -m 240 http://127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"x","messages":[{"role":"user","content":"What is a cache line?"}],"max_tokens":32,"temperature":0}' -o /dev/null -w "http=%{http_code} time=%{time_total}s\n"

echo
echo "=== 输出目录 ==="
docker exec strata166-407 sh -c "ls -la /data/w923/ 2>&1 | head -10"
