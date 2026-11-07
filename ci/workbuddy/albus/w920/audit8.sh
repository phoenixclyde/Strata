#!/bin/bash
C=strata166-407
echo "=== HSA_OVERRIDE_GFX_VERSION 是否必要：ROCm 原生识别成什么 ==="
docker exec $C sh -c 'rocminfo 2>/dev/null | grep -m4 -E "Name:|gfx|Marketing"'
echo
echo "=== 不设该 env 时的 target（子进程覆盖为空）==="
docker exec $C sh -c 'HSA_OVERRIDE_GFX_VERSION= rocminfo 2>/dev/null | grep -m2 -E "gfx"'
echo
echo "=== conversation cache 驱逐情况（最后 3 条）==="
docker exec $C sh -c "grep -oE 'parked=[0-9]+ bytes=[0-9]+ evictions=[0-9]+' /data/strata-huihui-ud-iq4_xs.log | tail -3"
