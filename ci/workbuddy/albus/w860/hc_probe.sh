#!/bin/bash
T=/home/albus/strata166/gfx029
echo "=== 'hc read' 埋点位置 ==="
grep -rn 'hc read' $T/src | head -5
echo "=== hc write 埋点 ==="
grep -rn 'hc write' $T/src | head -3
