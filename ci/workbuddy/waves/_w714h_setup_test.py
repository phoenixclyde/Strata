# A) 166 建 huihui 目录 + 复用"逐字节相同"的分片1（sha256 5ce89370…）
# B) 测通道：166 与 本机 各自对 hf-mirror 的连通性与吞吐（Range 50 MB）
import base64, hashlib, os, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
REPO_PATH = "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF"
SUBDIR = "unsloth-UD-IQ4_XS"
DST = "/models/%s/%s" % (REPO_PATH, SUBDIR)
SRC_BASE = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
F1 = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
URL = "https://hf-mirror.com/%s/resolve/main/%s/%s" % (REPO_PATH, SUBDIR, F1)


def run(script, t=600):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== A) 166 建目录 + 复用分片1（与 base 逐字节相同，sha256 5ce89370…）===")
sc = """set -u
mkdir -p '%s'
if [ -f '%s/%s' ]; then echo already; else cp --remove-destination '%s/%s' '%s/%s'; fi
ls -l '%s'
echo '--- sha256 校验（应为 5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4）'
sha256sum '%s/%s'
echo '--- 与 base 侧同名文件比对 inode/链接数 ---'
stat -c '%%h %%i %%n' '%s/%s' '%s/%s'
""" % (DST, DST, F1, SRC_BASE, F1, DST, F1, DST, DST, F1, SRC_BASE, F1, DST, F1)
rc, out, err = run(sc, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== B) 166 -> hf-mirror 连通性 + 50MB 拉取速度 ===")
sc2 = """set -u
echo -n 'DNS/HTTP: '
curl -s -m 20 -o /dev/null -w 'http=%%{http_code} size=%%{size_download} speed=%%{speed_download}\\n' \
  -r 0-52428799 '%s' || echo '(失败)'
""" % URL
rc, out, err = run(sc2, 120)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== C) 本机 -> hf-mirror 50MB 拉取速度 ===")
import urllib.request
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "Mozilla/5.0"), ("Range", "bytes=0-52428799")]
t0 = time.time()
n = 0
try:
    with op.open(URL, timeout=120) as r:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            n += len(b)
            if time.time() - t0 > 60:
                break
    dt = time.time() - t0
    print("  下载 %.1f MB / %.1f s = %.2f MB/s  (前 60s 采样)" % (n / 1e6, dt, n / dt / 1e6))
except Exception as e:
    print("  失败:", repr(e))
