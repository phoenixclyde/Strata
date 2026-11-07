#!/bin/sh
# W797 采纳后的生产复核（无仪器）：needle 32k 三深度 + M x2 + L x1
set -u
OUT=/home/albus/strata166/data/w797_prod_$(date +%Y%m%d_%H%M%S).txt
CONT=strata166-407
{
  echo "=== needle 32k d10/50/90 $(date +%H:%M:%S) ==="
  docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 10,50,90 --url http://127.0.0.1:8090 2>&1 | tail -6
  echo "=== prod M x2 $(date +%H:%M:%S) ==="
  cd /home/albus/strata166/tmp && python3 w776_bench.py M 2 2>&1 | grep -E "run[12]|median"
  echo "=== prod L x1 ==="
  python3 w776_bench.py L 1 2>&1 | grep -E "run1|median"
  echo "=== env ==="
  python3 -c "import json;print(sorted(json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json')).get('env',{}).items()))"
  echo "=== DONE $(date +%H:%M:%S) ==="
} > "$OUT" 2>&1
