# A) 166 本机真拷贝 3 分片 -> /models（断开硬链接，独立 inode），后台跑
# B) 并行：读 --vision 的 help 与 setup.py 里的 vision 段 schema
import base64, hashlib, io, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
SRC = "/home/albus/strata166/weights"
DST = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]


def run(script, t=300):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


# ---------- A) 真拷贝（后台 nohup，落日志）----------
script = """set -u
W=/home/albus/strata166/w712
mkdir -p "$W"
if pgrep -f 'cp -f /home/albus/strata166/weights' >/dev/null; then echo ALREADY_COPYING; else
  setsid nohup bash -c 'cp -f %(src)s/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf %(dst)s/ && \
    cp -f %(src)s/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf %(dst)s/ && \
    cp -f %(src)s/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf %(dst)s/ && echo COPY_DONE' \
    > "$W/modelcopy.log" 2>&1 < /dev/null &
  sleep 5
fi
echo '--- 拷贝进程 ---'; pgrep -af 'cp -f /home/albus/strata166/weights' | head -2 || echo NO_CP
echo '--- 当前进度（dst 大小）---'; ls -l %(dst)s/ | tail -4
echo '--- 链接数（拷完应变 1）---'; stat -c '%%h %%n' %(dst)s/*.gguf
echo '--- 盘 ---'; df -h /home | tail -1
""" % {"src": SRC, "dst": DST}
rc, out, err = run(script, 300)
print("A) 启动真拷贝 rc=%d" % rc)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

# ---------- B) vision schema ----------
print("=== B) --vision 的 help 原文 ===")
rc2, out2, _ = run("docker exec strata166-405 bash -lc '/src/build-906/strata --help 2>&1 | grep -A8 -E \"^   --vision|mmproj\"' | head -30", 120)
print(out2 or "(无命中)")

print("=== B) setup.py 里 vision 段的构造 ===")
B = r"D:/workbuddy_space/strata_ws/deploy/tmp/src411/Strata-0.1.41"
p = os.path.join(B, "setup.py")
L = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
hits = 0
for i, l in enumerate(L):
    if '"vision"' in l or "'vision'" in l or "vision\":" in l:
        for j in range(max(0, i - 6), min(i + 10, len(L))):
            print("  %5d %s" % (j + 1, L[j][:150]))
        print("  ---")
        hits += 1
        if hits >= 3:
            break
