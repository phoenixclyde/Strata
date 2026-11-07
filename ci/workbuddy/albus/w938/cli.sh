#!/bin/bash
set -u
B=/home/albus/strata166/build-r28
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json

echo "=== 我们 config 里的 flag 列表 ==="
python3 - "$CFG" <<'PY' > /tmp/our_flags.txt
import json, sys
a = json.load(open(sys.argv[1]))["args"]
flags = [x for x in a if isinstance(x, str) and x.startswith("--")]
print("\n".join(sorted(set(flags))))
PY
cat /tmp/our_flags.txt | tr '\n' ' '; echo

echo
echo "=== 新二进制 --help 里是否都有 ==="
docker run --rm -v "$B":/b strata-gfx906:0.2.9-101 bash -lc '/b/strata --help 2>&1' > /tmp/new_help.txt
miss=0
while read -r f; do
  [ -z "$f" ] && continue
  if grep -q -- "$f" /tmp/new_help.txt; then :; else echo "  MISSING  $f"; miss=$((miss+1)); fi
done < /tmp/our_flags.txt
echo "缺失数 = $miss"

echo
echo "=== 反向：新版本新增/改名的关键 flag（与我们相关的） ==="
grep -oE "^\s+--[a-z0-9-]+" /tmp/new_help.txt | tr -d ' ' | sort -u > /tmp/new_flags.txt
echo "新二进制 flag 总数: $(wc -l < /tmp/new_flags.txt)"
echo "我们用了但新版本没有的:"; comm -23 /tmp/our_flags.txt /tmp/new_flags.txt | sed 's/^/  /'
