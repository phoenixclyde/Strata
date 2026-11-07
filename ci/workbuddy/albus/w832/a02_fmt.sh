#!/bin/bash
D=/home/albus/strata166/data
echo "=== [1] 历史 DECODE_TIMING 行的真实格式（取最近一次窗口实验） ==="
grep -a -h "strata decode timing" $D/w828_spec_ab.log 2>/dev/null | tail -3
echo
echo "--- 若上面为空，找任意带该行的日志 ---"
grep -a -rl "strata decode timing" $D/*.log 2>/dev/null | head -4
echo
echo "=== [2] decode GPU stages 段的字段 ==="
grep -a -h "decode GPU stages" $D/*.log 2>/dev/null | tail -2 | cut -c1-800
echo
echo "=== [3] 之前的臂脚本怎么算 ms/window（从 512-token 输出里取什么） ==="
grep -n "window\|tok/s\|decode_tps" /home/albus/strata166/tmp/w828_arm2.sh 2>/dev/null | head -20
