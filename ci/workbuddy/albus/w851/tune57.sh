#!/bin/bash
# W851: 为 ROCm 10.1 / rocBLAS 5.7 生成 gfx906 的 f16o 调优表（切 10.1 的前置条件）
# 桶集：256,512,1024,2048,4096,8192（现有 5.5 表只有 1024/2048/4096/8192；多出的 256/512 是小 chunk 主战场）
set -u
OUT=/home/albus/strata166/data/w851_tune57_$(date +%H%M%S).log
TB=/home/albus/strata166/tuner-build-r101
TBL=/home/albus/strata166/data/gfx906-rocblas-5.7.0.txt
IMG=strata-gfx906:0.2.9r1

req(){ curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null; }

B=$(req)
{
  echo "== start $(date +%F' '%T)  requests_before=$B"
  docker run --rm --name strata-tune57 \
    --device /dev/kfd --device /dev/dri --group-add video \
    --security-opt label=disable \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$TB":/tb:ro -v /home/albus/strata166/data:/data \
    "$IMG" bash -lc "
      /tb/tune_rocblas --tokens 256,512,1024,2048,4096,8192 --min-gain 1.05 \
        --tuning-out /data/gfx906-rocblas-5.7.0.txt
    "
  echo "== end $(date +%F' '%T)"
} >> "$OUT" 2>&1
A=$(req)
{
  echo "== requests_after=$A  delta=$((A-B))"
  echo "== 表:"
  wc -l "$TBL" 2>/dev/null
  head -5 "$TBL" 2>/dev/null
} >> "$OUT" 2>&1
