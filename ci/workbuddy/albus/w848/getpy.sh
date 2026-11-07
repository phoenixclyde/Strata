set +e
mkdir -p /home/albus/strata166/pkgcache
F="cpython-3.12.15+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz"
C="/home/albus/strata166/pkgcache/cpython-3.12.15_20261009-x86_64-unknown-linux-gnu-install_only.tar.gz"
if [ -f "$C" ]; then echo "already: $(ls -l $C | awk '{print $5}')"; else
  echo "-- 直连 github:"
  curl -sSL --max-time 120 -o "$C" "https://github.com/astral-sh/python-build-standalone/releases/download/20261009/$F" || true
  sz=$(stat -c%s "$C" 2>/dev/null || echo 0)
  echo "   直连得到 $sz 字节"
  if [ "$sz" -lt 1000000 ]; then
    echo "-- 走 gh-proxy:"
    curl -sSL --max-time 300 -o "$C" "https://gh-proxy.com/https://github.com/astral-sh/python-build-standalone/releases/download/20261009/$F"
    echo "   代理得到 $(stat -c%s "$C" 2>/dev/null || echo 0) 字节"
  fi
fi
echo -n "sha256 = "; sha256sum "$C" 2>/dev/null | cut -d' ' -f1
echo "期望   = 5864001bf969db329fadc2b654c4878c6027d170c6bd77e28f88666260bcaf63"
