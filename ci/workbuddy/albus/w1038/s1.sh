#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== 1. kv 字符串在哪 ==="
grep -rn "k8v4" $S/src $S/serve 2>/dev/null | head -20
echo "=== 2. kv_mode 赋值 ==="
grep -rn "kv_mode\s*=" $S/src $S/serve 2>/dev/null | head -20
echo "=== 3. 命令行 --kv ==="
grep -rn '"kv"' $S/src $S/serve 2>/dev/null | head -10
echo "=== 4. 生产 config 的 args ==="
docker exec strata166-407 python3 -c "
import json
d=json.load(open('/data/strata-huihui-ud-iq4_xs.json'))
print('exe', d.get('exe'))
a=d.get('args') or []
print('args n=', len(a))
print(' '.join(a))
print('env', d.get('env'))
"
