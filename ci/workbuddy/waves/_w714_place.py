# 在 166 上按 /models 规则落位：目录 + 分片（硬链接，零拷贝）+ mmproj（真传输，907 MB，分块流式）
import base64, hashlib, os, subprocess, time

LOCAL_DIR = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
REMOTE_DIR = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
SRC_WEIGHTS = "/home/albus/strata166/weights"
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SHARDS = ["Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
          "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf",
          "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf"]
MMPROJ = "mmproj-Qwen3.8-Flash-Next-BF16.gguf"


def run(script, t=300):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


# 1) 建目录 + 硬链接三个分片（同一文件系统 => 零拷贝、零额外空间；删 /weights 后 /models 仍完整）
links = "\n".join(['ln -f "%s/%s" "%s/%s" 2>/dev/null || cp -n "%s/%s" "%s/%s"' %
                   (SRC_WEIGHTS, s, REMOTE_DIR, s, SRC_WEIGHTS, s, REMOTE_DIR, s) for s in SHARDS])
rc, out, err = run("set -u\nmkdir -p '%s'\n%s\nls -l '%s' | head -10\ndf -h /home | tail -1\n"
                   % (REMOTE_DIR, links, REMOTE_DIR), 600)
print("建目录+分片落位 rc=%d" % rc)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

# 2) mmproj 真传输：分块 base64 流式写入（避免一次性吃下 900 MB 内存）
src = os.path.join(LOCAL_DIR, MMPROJ)
sz = os.path.getsize(src)
print("本机 mmproj: %.2f MB，开始传输（分块 8 MB）..." % (sz / 1e6))
remote_cmd = "base64 -d > '%s/%s'" % (REMOTE_DIR, MMPROJ)
p = subprocess.Popen(SSH + [remote_cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
t0 = time.time()
sent = 0
try:
    with open(src, "rb") as f:
        while True:
            b = f.read(8 << 20)
            if not b:
                break
            p.stdin.write(base64.b64encode(b))
            sent += len(b)
            if sent % (128 << 20) < (8 << 20):
                print("   ... %.0f / %.0f MB  (%.1f MB/s)" % (sent / 1e6, sz / 1e6, sent / (time.time() - t0) / 1e6), flush=True)
    p.stdin.close()
except Exception as e:
    print("  传输异常:", repr(e))
rc2 = p.wait(timeout=900)
p.stdout.read(); p.stderr.read()
print("  传完 rc=%d %.1fs 本地 %.2f MB" % (rc2, time.time() - t0, sent / 1e6))

# 3) 两端校验
h_local = hashlib.md5(open(src, "rb").read()).hexdigest()
rc3, out3, _ = run("md5sum '%s/%s'; ls -l '%s/'; du -sh '%s'" % (REMOTE_DIR, MMPROJ, REMOTE_DIR, REMOTE_DIR), 300)
print("本地 mmproj md5 =", h_local)
print(out3)
