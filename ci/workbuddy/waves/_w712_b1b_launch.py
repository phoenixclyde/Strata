# 推 B1b 脚本到 166 并 nohup 自跑；本地先做 CR/禁用码位自检
import subprocess, base64, hashlib, os

SH = r"D:/workbuddy_space/strata_ws/deploy/scripts/_w712_b1b_chunk.sh"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
raw = open(SH, "rb").read()
t = raw.decode("utf-8")
assert b"\r" not in raw, "script has CR"
nb = sum(1 for c in t if ord(c) in BAN)
assert nb == 0, "script has %d banned code points" % nb
md5 = hashlib.md5(raw).hexdigest()
b64 = base64.b64encode(raw).decode("ascii")
print("local md5", md5, len(raw), "bytes, BAN=0, CR=0")

script = r"""
set -u
D=/home/albus/strata166/w712
mkdir -p "$D"
base64 -d > "$D/b1b_chunk.sh" <<'__B1B_EOF__'
%(b64)s
__B1B_EOF__
chmod +x "$D/b1b_chunk.sh"
echo "remote md5: $(md5sum $D/b1b_chunk.sh | cut -d' ' -f1)"
echo "remote CR: $(tr -cd '\r' < $D/b1b_chunk.sh | wc -c)"
echo "bash -n: $(bash -n $D/b1b_chunk.sh && echo SYNTAX_OK || echo SYNTAX_FAIL)"
if pgrep -f b1b_chunk.sh >/dev/null; then echo "ALREADY_RUNNING"; else
  setsid nohup bash "$D/b1b_chunk.sh" > /dev/null 2>&1 < /dev/null &
  sleep 8
  echo "launched:"; pgrep -af b1b_chunk | head -2
fi
echo "log head:"; head -n 14 "$D/b1b.log" 2>/dev/null
""" % {"b64": b64}

p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "albus@192.168.50.166", "base64 -d | bash"],
    input=(base64.b64encode(script.encode("utf-8")) + b"\n"), capture_output=True, timeout=180)
print("ssh rc", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
