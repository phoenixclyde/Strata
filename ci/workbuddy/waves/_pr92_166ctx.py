import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

script = r'''
echo "===== [1] 找 0.1.40.1 构建上下文 ====="
find /home/albus -maxdepth 5 -name 'strata-src-0.1.40.1.zip' 2>/dev/null | head -5
find /home/albus -maxdepth 5 -name 'llama.cpp-3cf0325.tar.gz' 2>/dev/null | head -5
find /home/albus -maxdepth 5 -name 'Dockerfile-0.1.40.1' 2>/dev/null | head -5
find /home/albus -maxdepth 5 -name 'patch_gfx906.py' 2>/dev/null | head -5

echo
echo "===== [2] 可能的构建目录（含 docker/ 与 transfer/ 的） ====="
for d in $(find /home/albus -maxdepth 4 -type d -name docker 2>/dev/null | head -6); do
  P=$(dirname "$d")
  echo "--- $P ---"
  ls -la "$P" 2>&1 | head -10
  echo "   transfer/:"; ls -la "$P/transfer" 2>&1 | head -8
done

echo
echo "===== [3] 166 能否直连 gh-proxy 下载（测速）====="
cd /tmp
rm -f /tmp/strata-src-0.1.40.2.zip
S=$(date +%s)
curl -sSL --max-time 280 -o /tmp/strata-src-0.1.40.2.zip \
  https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/v0.1.40.2.zip
rc=$?
E=$(date +%s)
echo "curl_rc=$rc  elapsed=$((E-S))s"
ls -l /tmp/strata-src-0.1.40.2.zip 2>&1
if [ -f /tmp/strata-src-0.1.40.2.zip ]; then
  echo -n "sha256 = "; sha256sum /tmp/strata-src-0.1.40.2.zip | cut -d' ' -f1
fi

echo
echo "===== [4] 磁盘 ====="
df -h / | tail -2
echo
echo "===== [5] docker 版本 / buildx ====="
docker version --format '{{.Server.Version}}' 2>&1
docker buildx version 2>&1 | head -2
'''
rc, out, err = _sshutil.run_remote(script, timeout=420, host="192.168.50.166")
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1500])
