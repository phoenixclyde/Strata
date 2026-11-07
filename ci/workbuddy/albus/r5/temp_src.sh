#!/bin/bash
# temperature==0 是不是真的贪心？在 serve 层与采样器里各查一遍
echo "=== serve 层怎么传 temperature"
docker exec strata166-407 bash -lc "grep -rn 'temperature' /src/serve/server.py | head -12"
echo
echo "=== 引擎侧 temperature 的落点（argv/参数）"
docker exec strata166-407 bash -lc "grep -rn 'temperature' /src/src/program/generate.cpp | head -12"
echo
echo "=== 采样器：temp<=0 的分支"
docker exec strata166-407 bash -lc "grep -rn 'temp' /src/src/kernels/sampler.cu 2>/dev/null | head -20; ls /src/src/kernels | grep -i sample"
