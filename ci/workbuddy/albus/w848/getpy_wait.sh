set +e
C="/home/albus/strata166/pkgcache/cpython-3.12.15_20261009-x86_64-unknown-linux-gnu-install_only.tar.gz"
for i in $(seq 1 40); do
  pgrep -f "curl.*python-build-standalone" >/dev/null || break
  sleep 10
done
echo "now=$(date +%H:%M:%S) size=$(stat -c%s "$C" 2>/dev/null)"
echo -n "sha256 = "; sha256sum "$C" 2>/dev/null | cut -d' ' -f1
echo "期望   = 5864001bf969db329fadc2b654c4878c6027d170c6bd77e28f88666260bcaf63"
