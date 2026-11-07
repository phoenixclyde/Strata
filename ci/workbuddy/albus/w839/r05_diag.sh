#!/bin/bash
# W839-05 诊断：为什么入口代码没进二进制
S=/home/albus/strata166/src028
W=/home/albus/strata166/gfx906
echo "=== 源里有没有这些字面量 ==="
for f in $W/src/core/arch_defaults.cpp $S/src/core/arch_defaults.cpp; do
  echo "[$f]"
  python3 - "$f" <<'PY'
import sys,io
p=sys.argv[1]
s=io.open(p,encoding='utf-8',errors='replace').read()
for k in ('MI50-class','GFX906_TUNED','exact speed switches','gfx906'):
    print('   %-24s %d' % (k, s.count(k)))
PY
done

echo "=== 两文件是否同一份 ==="
md5sum $W/src/core/arch_defaults.cpp $S/src/core/arch_defaults.cpp
md5sum $W/include/strata/core/arch_defaults.hpp $S/include/strata/core/arch_defaults.hpp

echo "=== 编译日志里有没有编 arch_defaults ==="
grep -c arch_defaults $S/build-028r3.log 2>/dev/null
grep -o 'arch_defaults[^ ]*' $S/build-028r3.log 2>/dev/null | sort -u | head -4

echo "=== 对象文件时间戳 ==="
find $S/build-028r -name 'arch_defaults*.o' -newermt '2026-10-31 16:00' 2>/dev/null | head -4
find $S/build-028r -name 'arch_defaults*.o' 2>/dev/null | head -4 | xargs ls -la 2>/dev/null | cut -c1-100

echo "=== 对象里有没有字面量 ==="
for o in $(find $S/build-028r -name 'arch_defaults*.o' 2>/dev/null | head -2); do
  echo "[$o] MI50-class=$(grep -a -c -F 'MI50-class' $o) gfx906=$(grep -a -c -F 'gfx906' $o)"
done
