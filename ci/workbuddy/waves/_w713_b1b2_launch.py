# 推答案探针 + B1b-2 脚本并 nohup 启动（自检 CR/BAN/bash -n），再挂本地监视
import base64, hashlib, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166", "base64 -d | bash"]


def load(rel):
    raw = open(os.path.join(WS, rel), "rb").read()
    nb = sum(1 for c in raw.decode("utf-8") if ord(c) in BAN)
    assert b"\r" not in raw and nb == 0, "%s CR/BAN 未过 (BAN=%d)" % (rel, nb)
    print("%-40s md5=%s bytes=%d" % (rel, hashlib.md5(raw).hexdigest(), len(raw)))
    return base64.b64encode(raw).decode("ascii")


pb = load("deploy/data/bench_answer.py")
bs = load("deploy/scripts/_w713_b1b2.sh")

script = r"""
set -u
D=/home/albus/strata166/w712
base64 -d > /home/albus/strata166/data/bench_answer.py <<'__PB_EOF__'
%(pb)s
__PB_EOF__
base64 -d > "$D/b1b2.sh" <<'__BS_EOF__'
%(bs)s
__BS_EOF__
chmod +x "$D/b1b2.sh"
echo "probe md5: $(md5sum /home/albus/strata166/data/bench_answer.py | cut -d' ' -f1)"
echo "bash -n: $(bash -n $D/b1b2.sh && echo OK || echo FAIL)"
echo "container: $(docker ps --filter name=strata --format '{{.Names}}' | head -1)"
if pgrep -f b1b2.sh >/dev/null; then echo ALREADY_RUNNING; else
  setsid nohup bash "$D/b1b2.sh" > /dev/null 2>&1 < /dev/null &
  sleep 8
  echo "launched:"; pgrep -af b1b2.sh | head -2
fi
head -n 6 "$D/b1b2.log" 2>/dev/null
""" % {"pb": pb, "bs": bs}

p = subprocess.run(SSH, input=base64.b64encode(script.encode()) + b"\n", capture_output=True, timeout=300)
print("rc=%d" % p.returncode)
print(p.stdout.decode("utf-8", "replace"))
print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
