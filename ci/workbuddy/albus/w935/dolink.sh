#!/bin/bash
set -u
B=~/strata166/gfx029-build

echo "=== A. 清理空占位符 ==="
python3 - <<'PY'
import io
p = "/tmp/link_strata.sh"
s = io.open(p, encoding="utf-8").read()
s = s.replace("$LINK_FLAGS", "").replace("$LINK_PATH", "")
s = s.replace(": && ", "").replace(" && :\n", "\n")
# 收拢多余空格
while "  " in s:
    s = s.replace("  ", " ")
io.open(p, "w").write(s)
print(s[:260])
print("...(长度 %d)" % len(s))
PY

echo
echo "=== B. 备份当前构建产物 ==="
cp $B/strata $B/strata.bak-9d9cbe17 2>/dev/null || docker run --rm -v $B:/out -w /out strata-gfx906:0.2.9-101 cp strata strata.bak-9d9cbe17
ls -l $B/strata.bak-9d9cbe17 2>/dev/null | awk '{print "  ", $5}'

echo
echo "=== C. 链接（容器内 root） ==="
docker run --rm -v $B:/out -v /tmp/link_strata.sh:/tmp/link_strata.sh -w /out strata-gfx906:0.2.9-101 \
  bash /tmp/link_strata.sh 2>&1 | tail -12
echo "RC=$?"

echo
echo "=== D. 产物验证 ==="
ls -l $B/strata 2>/dev/null | awk '{print "  size=", $5, $6, $7, $8}'
md5sum $B/strata 2>/dev/null
echo "--- 新符号在二进制里吗 ---"
strings $B/strata 2>/dev/null | grep -c "this program may lock only"
strings $B/strata 2>/dev/null | grep -c "raised to .* for the PLE table"
