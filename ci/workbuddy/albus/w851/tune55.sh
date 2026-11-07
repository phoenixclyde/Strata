#!/bin/bash
# W851: 同一份 tuner 在 rocBLAS 5.5（生产 7.14）上生成 6 桶表 —— 与 5.7 表逐行对照，
# 判断「小桶收益」是否与 ROCm 版本无关（若无关，就不必为它换 10.1）
set -u
OUT=/home/albus/strata166/data/w851_tune55_$(date +%H%M%S).log
TB=/home/albus/strata166/tuner-build-r714
IMG=strata-gfx906:0.2.9t2
req(){ curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null; }
B=$(req)
{
  echo "== start $(date +%F' '%T)  requests_before=$B"
  docker run --rm --name strata-tune55 \
    --device /dev/kfd --device /dev/dri --group-add video \
    --security-opt label=disable -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$TB":/tb:ro -v /home/albus/strata166/data:/data "$IMG" bash -lc "
      /tb/tune_rocblas --tokens 256,512,1024,2048,4096,8192 --min-gain 1.05 \
        --tuning-out /data/gfx906-rocblas-5.5.0-6b.txt
    "
  echo "== end $(date +%F' '%T)"
} >> "$OUT" 2>&1
A=$(req)
echo "== requests_after=$A delta=$((A-B))" >> "$OUT" 2>&1
