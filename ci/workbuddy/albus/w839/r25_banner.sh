#!/bin/bash
# W839-25 从引擎日志取架构横幅（setenv 不写回 /proc/environ，横幅才是证据）
D=/home/albus/strata166/data
for f in w839_A.log w839_B.log; do
  echo "=== $f ==="
  ls -la $D/$f 2>/dev/null | cut -c1-70
  grep -aE 'gfx906|exact speed switches|recipe is on|TUNED' $D/$f 2>/dev/null | head -8 | cut -c1-240
  echo
done
echo "=== 对照：生产日志里的同类行 ==="
grep -aE 'gfx906|exact speed' $D/strata-huihui-ud-iq4_xs.log 2>/dev/null | head -4 | cut -c1-200
echo
echo "=== B 臂日志开头 12 行（看它启动时说了什么） ==="
head -12 $D/w839_B.log 2>/dev/null | cut -c1-180
