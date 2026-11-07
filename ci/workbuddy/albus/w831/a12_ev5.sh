#!/bin/bash
echo "=== [1] 生产 env 全量（支撑 gfx1151 表里哪几项我们本来就开） ==="
python3 -c "
import json
c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
e=c.get('env') or {}
for k in sorted(e): print('  %-28s %s' % (k, e[k]))
print('  n_env=',len(e))
"
echo
echo "=== [2] 文件计数（W830 的 2824 能不能复现） ==="
for d in /home/albus/strata166/src0271 /home/albus/strata166/src028; do
  printf '  %-8s find -type f = %s\n' "$(basename $d)" "$(find $d -type f 2>/dev/null | wc -l)"
done
echo "  upstream v0.2.7.1 blobs = 5205 ; v0.2.8 blobs = 5229"
echo "  7973-5205 = $((7973-5205)) ; 8002-5229 = $((8002-5229))"
echo
echo "=== [3] 三个候选数：third_party 文件数 ==="
printf '  src028/third_party = %s\n' "$(find /home/albus/strata166/src028/third_party -type f 2>/dev/null | wc -l)"
printf '  src028/build-*     = %s\n' "$(find /home/albus/strata166/src028 -maxdepth 1 -name 'build-*' -type d -exec find {} -type f \; 2>/dev/null | wc -l)"
