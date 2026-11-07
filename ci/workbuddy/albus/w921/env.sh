#!/bin/bash
echo "=== 宿主 /src ==="
ls -ld /src 2>&1 | head -2
ls /src 2>/dev/null | head -5

echo
echo "=== 宿主 ROCm 工具链 ==="
ls -l /opt/rocm/bin/clang++ 2>&1 | head -2
/opt/rocm/bin/clang++ --version 2>/dev/null | head -1
which ninja cmake 2>/dev/null

echo
echo "=== 历史构建容器 ==="
docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Image}}' | grep -iE "ci-build|build" | head -6

echo
echo "=== strata-ci-build 的配置（若存在）==="
docker inspect strata-ci-build -f '{{json .HostConfig.Binds}} | {{json .Config.Cmd}} | {{.Config.Image}} | {{json .HostConfig.Devices}}' 2>&1 | head -3

echo
echo "=== /data/bin 里的引擎与时间 ==="
ls -l --time-style=+%Y-%m-%d_%H:%M /data/bin/ 2>/dev/null | head -8
ls -l --time-style=+%Y-%m-%d_%H:%M ~/strata166/data/bin/ 2>/dev/null | head -8
