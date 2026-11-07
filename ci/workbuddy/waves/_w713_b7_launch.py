# 推 B7 脚本并 nohup 启动（本机先自检 CR/BAN/bash -n）
import base64, hashlib, os, subprocess

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

p = os.path.join(WS, "deploy", "scripts", "_w713_b7_stager.sh")
raw = open(p, "rb").read()
t = raw.decode("utf-8")
nb = sum(1 for c in t if ord(c) in BAN)
print("local md5=%s bytes=%d CR=%d BAN=%d" % (hashlib.md5(raw).hexdigest(), len(raw), raw.count(b"\r"), nb))
assert raw.count(b"\r") == 0 and nb == 0, "本地自检未过"

b64 = base64.b64encode(raw).decode("ascii")

REMOTE = """set -u
D=/home/albus/strata166/w712
base64 -d > "$D/b7_stager.sh" <<'__B7_EOF__'
%(b64)s
__B7_EOF__
chmod +x "$D/b7_stager.sh"
echo "remote md5: $(md5sum $D/b7_stager.sh | cut -d' ' -f1)"
echo "remote CR: $(tr -cd '\\r' < $D/b7_stager.sh | wc -c)"
echo "bash -n: $(bash -n $D/b7_stager.sh && echo OK || echo FAIL)"
if pgrep -f b7_stager.sh >/dev/null; then
  echo ALREADY_RUNNING
else
  setsid nohup bash "$D/b7_stager.sh" > /dev/null 2>&1 < /dev/null &
  sleep 8
  echo "launched:"; pgrep -af b7_stager.sh | head -2
fi
echo "--- log head ---"; head -n 10 "$D/b7.log" 2>/dev/null
""" % {"b64": b64}

pr = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                     "albus@192.168.50.166", "base64 -d | bash"],
                    input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n", capture_output=True, timeout=300)
print("ssh rc=%d" % pr.returncode)
print(pr.stdout.decode("utf-8", "replace"))
if pr.stderr.strip():
    print("STDERR:", pr.stderr.decode("utf-8", "replace")[-300:])
