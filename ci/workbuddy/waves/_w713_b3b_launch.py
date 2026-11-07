# B3 复跑（真实 chat 结构）：改 label -> b3b，推探针 + 复用脚本但换 log 名，再启动
import base64, hashlib, os, subprocess

WS = r"D:/workbuddy_space/strata_ws"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]


def load(rel):
    raw = open(os.path.join(WS, rel), "rb").read()
    t = raw.decode("utf-8")
    nb = sum(1 for c in t if ord(c) in BAN)
    print("%-42s md5=%s bytes=%d CR=%d BAN=%d" % (rel, hashlib.md5(raw).hexdigest(), len(raw), raw.count(b"\r"), nb))
    assert raw.count(b"\r") == 0 and nb == 0, "本地自检未过: " + rel
    return base64.b64encode(raw).decode("ascii")


pb = load("deploy/data/bench_conv.py")
# 复用同一个 A/B 脚本，但把日志指向 b3b.log（避免覆盖第一轮证据）
bs_raw = open(os.path.join(WS, "deploy/scripts/_w713_b3_convcache.sh"), "rb").read().decode("utf-8")
bs = bs_raw.replace("LOG=$W/b3.log", "LOG=$W/b3b.log")
assert "b3b.log" in bs and bs.count("b3.log") == 0, "日志名替换失败"
bs_enc = base64.b64encode(bs.encode("utf-8")).decode("ascii")

REMOTE = """set -u
D=/home/albus/strata166/w712
base64 -d > /home/albus/strata166/data/bench_conv.py <<'__PB_EOF__'
%(pb)s
__PB_EOF__
base64 -d > "$D/b3b_convcache.sh" <<'__BS_EOF__'
%(bs)s
__BS_EOF__
chmod +x "$D/b3b_convcache.sh"
echo "probe md5: $(md5sum /home/albus/strata166/data/bench_conv.py | cut -d' ' -f1)"
echo "bash -n: $(bash -n $D/b3b_convcache.sh && echo OK || echo FAIL)"
if pgrep -f b3b_convcache.sh >/dev/null; then echo ALREADY; else
  setsid nohup bash "$D/b3b_convcache.sh" > /dev/null 2>&1 < /dev/null &
  sleep 8; echo "launched:"; pgrep -af b3b_convcache.sh | head -2
fi
head -n 8 "$D/b3b.log" 2>/dev/null
""" % {"pb": pb, "bs": bs_enc}

p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n", capture_output=True, timeout=300)
print("rc=%d" % p.returncode)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
