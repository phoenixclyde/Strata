# 166 侧：准备 build-ctx-404 构建上下文（源码自下 + sha256 校验 + 推补丁器/Dockerfile）
import subprocess, base64, time, os

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_prep166.out.txt"
WS = r"D:/workbuddy_space/strata_ws/deploy"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

def run_remote(script, timeout=900):
    assert "\r" not in script
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    p = subprocess.run(
        ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
         "albus@192.168.50.166", "base64 -d | bash"],
        input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

# ---- 1. 上传 Dockerfile-0.1.40.4（小文件，直接 base64 内联进脚本）----
df_b64 = base64.b64encode(open(os.path.join(WS, "docker", "Dockerfile-0.1.40.4"), "rb").read()).decode("ascii")
pt_b64 = base64.b64encode(open(os.path.join(WS, "docker", "patch_gfx906_402.py"), "rb").read()).decode("ascii")

script = r"""
set -eux
ctx=/home/albus/strata166/build-ctx-404
mkdir -p "$ctx/transfer"
echo "== ctx-402 transfer 内容（复用 llama.cpp）=="
ls -l /home/albus/strata166/build-ctx-402/transfer/
cp -n /home/albus/strata166/build-ctx-402/transfer/llama.cpp-3cf0325.tar.gz "$ctx/transfer/" || true
echo "%(df)s" | base64 -d > "$ctx/Dockerfile-0.1.40.4"
echo "%(pt)s" | base64 -d > "$ctx/patch_gfx906_402.py"
echo "== 下载 0.1.40.4 源码（gh-proxy，166 直下）=="
cd "$ctx/transfer"
if [ ! -s strata-src-0.1.40.4.zip ]; then
  curl -sSL --max-time 300 -o strata-src-0.1.40.4.zip \
    "https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/v0.1.40.4.zip" || true
fi
ls -l strata-src-0.1.40.4.zip
sha256sum strata-src-0.1.40.4.zip
echo "290OK: expect 7d19b4d5cc8922d4e558f2cddec9a28b7595775ccfb4e6085b02287d95059300"
ls -l "$ctx"
echo PREP_DONE
""" % {"df": df_b64, "pt": pt_b64}

rc, out, err = run_remote(script, timeout=900)
log("prep rc=%d" % rc)
f.write(out + "\n")
if err:
    f.write("STDERR:\n" + err + "\n")
f.close()
print(out[-3000:])
print("STDERR:", err[-500:])
