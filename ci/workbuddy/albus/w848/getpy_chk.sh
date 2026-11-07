set +e
C="/home/albus/strata166/pkgcache/cpython-3.12.15_20261009-x86_64-unknown-linux-gnu-install_only.tar.gz"
ls -l "$C" 2>/dev/null || echo "no file"
echo "-- 是否有下载进程在跑:"; pgrep -af "curl.*python-build-standalone" | head -3
echo "-- 直连测试 5s:"; curl -sS -o /dev/null -w '%{http_code} %{time_total}\n' --max-time 5 https://github.com 2>&1 | head -2
echo "-- gh-proxy 测试 8s（小文件）:"
curl -sS -o /dev/null -w '%{http_code} %{time_total}\n' --max-time 8 "https://gh-proxy.com/https://raw.githubusercontent.com/astral-sh/python-build-standalone/main/README.md" 2>&1 | head -2
