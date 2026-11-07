set +e
echo "=== w824_build.sh ==="
cat /home/albus/strata166/tmp/w824_build.sh 2>/dev/null | head -40
echo
echo "=== w820_build.sh ==="
cat /home/albus/strata166/tmp/w820_build.sh 2>/dev/null | head -30
echo
echo "=== /usr/bin/ninja /usr/bin/cmake 是否存在 ==="
ls -l /usr/bin/ninja /usr/bin/cmake /snap/bin/cmake 2>&1 | head
echo
echo "=== 相关容器镜像 ==="
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | head -12
