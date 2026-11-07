#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log
echo "=== 第一条（最小档）==="
docker exec $C grep -a -m1 "prefill timing:" $LOG
echo
echo "=== 最后一条（最大档）==="
docker exec $C sh -c "grep -a 'prefill timing:' $LOG | tail -1"
