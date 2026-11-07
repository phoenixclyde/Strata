set +e
D=/home/albus/strata166/gfx029
echo "===== [1] 锁文件在不在 ====="
ls -l "$D/packaging/locks/" 2>/dev/null | head
echo
echo "===== [2] 网络可达性（从容器内） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9 -lc '
  for u in https://github.com https://pypi.org/simple/ https://gh-proxy.com/https://github.com; do
    printf "  %-46s " "$u"
    curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 "$u" || echo FAIL
  done'
echo
echo "===== [3] 本机 python3 版本（打包脚本自身要 3.12+？） ====="
python3 -V 2>&1
echo "===== [4] 现成的 terminal 包在哪（也许之前打过） ====="
find /home/albus/strata166 -maxdepth 3 -name "strata-terminal-*" 2>/dev/null | head -5
ls -l /home/albus/strata166/release 2>/dev/null | head -5
