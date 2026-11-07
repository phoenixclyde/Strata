#!/bin/bash
S=/home/albus/strata166/src028
echo "=== Dockerfile.w828 full ==="
cat $S/Dockerfile.w828 2>/dev/null
echo
echo "=== size of build context (top-level entries) ==="
du -sh $S/* 2>/dev/null | sort -h | tail -12
echo
echo "=== .dockerignore? ==="
ls -la $S/.dockerignore 2>/dev/null && cat $S/.dockerignore 2>/dev/null | head -20
echo
echo "=== current run command of prod container ==="
docker inspect strata166-407 --format '{{.Config.Image}}' 2>&1
docker inspect strata166-407 --format '{{json .Config.Cmd}}' 2>&1 | head -c 400
echo
