# W713: 166 侧准备 build-ctx-411 并后台启动构建（nohup，日志落盘）
import subprocess, base64, hashlib, os, time

WS = r"D:/workbuddy_space/strata_ws"
raw = open(os.path.join(WS, "deploy", "docker", "Dockerfile-0.1.41"), "rb").read()
assert b"\r" not in raw
df_b64 = base64.b64encode(raw).decode("ascii")
pt_b64 = base64.b64encode(open(os.path.join(WS, "deploy", "docker", "patch_gfx906_402.py"), "rb").read()).decode("ascii")
print("Dockerfile-0.1.41 md5(remote target) =", hashlib.md5(raw).hexdigest(), len(raw), "bytes")

script = r"""
set -u
ctx=/home/albus/strata166/build-ctx-411
mkdir -p "$ctx/transfer"
cp -n /home/albus/strata166/build-ctx-404/transfer/llama.cpp-3cf0325.tar.gz "$ctx/transfer/" 2>/dev/null || true
echo "%(df)s" | base64 -d > "$ctx/Dockerfile-0.1.41"
echo "%(pt)s" | base64 -d > "$ctx/patch_gfx906_402.py"
echo "== 下载 0.1.41 源码（166 直下 gh-proxy）=="
cd "$ctx/transfer"
if [ ! -s strata-src-0.1.41.zip ]; then
  curl -sSL --max-time 300 -o strata-src-0.1.41.zip \
    "https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/v0.1.41.zip" || true
fi
ls -l strata-src-0.1.41.zip
sha256sum strata-src-0.1.41.zip
ls -l "$ctx/transfer/llama.cpp-3cf0325.tar.gz"
echo "== 启动构建 =="
cd "$ctx"
if pgrep -f "docker build -f Dockerfile-0.1.41" >/dev/null; then echo ALREADY_BUILDING; exit 0; fi
setsid nohup docker build -f Dockerfile-0.1.41 -t strata-gfx906:0.1.41 . > "$ctx/build-411.log" 2>&1 < /dev/null &
sleep 6
pgrep -af "docker build" | head -2
head -n 8 "$ctx/build-411.log" 2>/dev/null
""" % {"df": df_b64, "pt": pt_b64}

p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(script.encode("utf-8")) + b"\n",
                   capture_output=True, timeout=600)
print("ssh rc", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR tail:", p.stderr.decode("utf-8", "replace")[-400:])
