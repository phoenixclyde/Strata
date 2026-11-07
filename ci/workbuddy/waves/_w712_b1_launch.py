# 推 B1 脚本到 166 并 nohup 自跑（做完自动恢复生产 config），不等待
import subprocess, base64, hashlib, os

SH = r"D:/workbuddy_space/strata_ws/deploy/scripts/_w712_b1_cacheevery.sh"
raw = open(SH, "rb").read()
assert b"\r" not in raw, "script has CR"
md5 = hashlib.md5(raw).hexdigest()
b64 = base64.b64encode(raw).decode("ascii")
print("local md5", md5, len(raw), "bytes")

script = r"""
set -u
D=/home/albus/strata166/w712
mkdir -p "$D"
base64 -d > "$D/b1_cacheevery.sh" <<'__B1_EOF__'
%(b64)s
__B1_EOF__
chmod +x "$D/b1_cacheevery.sh"
echo "remote md5: $(md5sum $D/b1_cacheevery.sh | cut -d' ' -f1)"
echo "remote CR: $(tr -cd '\r' < $D/b1_cacheevery.sh | wc -c)"
echo "bash -n: $(bash -n $D/b1_cacheevery.sh && echo SYNTAX_OK || echo SYNTAX_FAIL)"
if pgrep -f b1_cacheevery.sh >/dev/null; then echo "ALREADY_RUNNING"; else
  setsid nohup bash "$D/b1_cacheevery.sh" > /dev/null 2>&1 < /dev/null &
  sleep 6
  echo "launched:"; pgrep -af b1_cacheevery | head -2
fi
echo "log head:"; head -n 12 "$D/b1.log" 2>/dev/null
""" % {"b64": b64}

p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "albus@192.168.50.166", "base64 -d | bash"],
    input=(base64.b64encode(script.encode("utf-8")) + b"\n"), capture_output=True, timeout=180)
print("ssh rc", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
