# 通道测速：A) 166 -> hf-mirror（Range 64MB） B) 本机 -> 166（传 128MB，走 stdin base64）
import base64, hashlib, os, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
URL = ("https://hf-mirror.com/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/"
       "resolve/main/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf")
TMP = "/home/albus/strata166/tmp_speedtest.bin"


def run(script, t=600):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== A) 166 -> hf-mirror 连通性 + 64MB Range 速度 ===")
sc = r'''set -u
echo -n 'curl : '
curl -sL -m 90 -o /dev/null -w 'http=%{http_code} bytes=%{size_download} speed=%{speed_download}B/s time=%{time_total}s\n' \
  -r 0-67108863 '@U@' || echo '(失败)'
echo -n 'tools: '
for t in aria2c curl wget axel; do command -v $t >/dev/null 2>&1 && printf '%s ' $t; done; echo
'''.replace("@U@", URL)
rc, out, err = run(sc, 200)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

print("=== B) 本机 -> 166 上传吞吐（128MB，走 ssh stdin，base64 包裹）===")
blob = os.urandom(8 << 20) * 16            # 128 MB
want = hashlib.md5(blob).hexdigest()
payload = base64.b64encode(blob) + b"\n"
t0 = time.time()
p1 = subprocess.run(SSH + ["base64 -d > " + TMP], input=payload, capture_output=True, timeout=900)
dt = time.time() - t0
print("  rc=%d  实质 %.1f MB 用时 %.1fs => %.1f MB/s（ssh 通道，已含编码开销）"
      % (p1.returncode, len(blob) / 1e6, dt, len(blob) / dt / 1e6))
if p1.stderr.strip():
    print("  stderr:", p1.stderr.decode("utf-8", "replace")[-200:])
rc, out, err = run("set -u\nsz=$(stat -c %%s %s)\nmd5=$(md5sum %s | cut -d' ' -f1)\n"
                   "echo \"远端 size=$sz md5=$md5\"\nrm -f %s\n" % (TMP, TMP, TMP), 300)
print(out.strip())
print("  本机 md5 =", want)
