# 把切换脚本推到 166（/home/albus/strata166/w712/switch_404.sh）并做语法自检；不执行切换
import subprocess, base64, os, hashlib

WS = r"D:/workbuddy_space/strata_ws/deploy/scripts/_w712_switch_404.sh"
raw = open(WS, "rb").read()
assert b"\r" not in raw, "script has CR"
md5 = hashlib.md5(raw).hexdigest()
b64 = base64.b64encode(raw).decode("ascii")
print("local md5", md5, len(raw), "bytes")

script = r"""
set -u
D=/home/albus/strata166/w712
mkdir -p "$D"
base64 -d > "$D/switch_404.sh" <<'__W712_EOF__'
%(b64)s
__W712_EOF__
chmod +x "$D/switch_404.sh"
echo "remote md5: $(md5sum $D/switch_404.sh | cut -d' ' -f1)"
echo "remote CR: $(tr -cd '\r' < $D/switch_404.sh | wc -c)"
echo "bash -n: $(bash -n $D/switch_404.sh && echo SYNTAX_OK || echo SYNTAX_FAIL)"
ls -l "$D"
""" % {"b64": b64}

p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "albus@192.168.50.166", "base64 -d | bash"],
    input=(base64.b64encode(script.encode("utf-8")) + b"\n"), capture_output=True, timeout=120)
print("ssh rc", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
print("STDERR:", p.stderr.decode("utf-8", "replace")[-400:])
