#!/bin/bash
set -u
echo "=== 1) 容器 /src 是 bind 还是镜像内容 ==="
docker inspect -f '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} rw={{.RW}}{{"\n"}}{{end}}' strata166-407
echo "--- /src 是否在容器内独立存在 ---"
docker exec strata166-407 sh -lc 'ls -ld /src; ls /src/serve/server.py 2>/dev/null; md5sum /src/serve/server.py 2>/dev/null'

echo
echo "=== 2) 仓库里的 server.py 与容器内是否同一份 ==="
md5sum ~/strata166/pr/strata-fork/serve/server.py 2>/dev/null
echo "--- 行数对比 ---"
wc -l ~/strata166/pr/strata-fork/serve/server.py 2>/dev/null

echo
echo "=== 3) HIP 下 cudaPeekAtLastError / cudaGetErrorString 是否可用 ==="
cd ~/strata166/pr/strata-fork || exit 1
grep -rn "cudaPeekAtLastError" include/strata/platform/hip_compat/*.h 2>/dev/null | head -5
grep -rn "cudaGetErrorString" include/strata/platform/hip_compat/*.h 2>/dev/null | head -5
echo "--- 树内既有使用 ---"
grep -rn "cudaPeekAtLastError" --include=*.cpp --include=*.hpp --include=*.h --include=*.cu src/ include/ | head -5

echo
echo "=== 4) 我们树里 generate.cpp 是否已有 fatal GPU 处理 ==="
grep -c "fatal GPU error" src/program/generate.cpp
grep -c "STRATA_INJECT_FATAL" src/program/generate.cpp
grep -n "cudaPeekAtLastError" src/program/generate.cpp | head -3
