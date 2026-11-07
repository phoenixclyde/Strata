# register 改动后的合法通道收口：重新生成 config -> 断言生成物未变 -> 同步 register 到 166 -> 四数据面复验
import hashlib, os, subprocess, base64, sys

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GENC = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
PY = r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SSH = "C:/Program Files/Git/usr/bin/ssh.exe"


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


before = md5f(GENC)
print("generated before:", before)

r = subprocess.run([PY, "-u", os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gen_config rc =", r.returncode)
print((r.stdout or "")[-400:])
after = md5f(GENC)
print("generated after :", after, " identical =", before == after)

# 同步 register + 生成物到 166
reg_b64 = base64.b64encode(open(REG, "rb").read()).decode("ascii")
gen_b64 = base64.b64encode(open(GENC, "rb").read()).decode("ascii")
script = r"""
set -u
D=/home/albus/strata166/params
cp -f $D/PARAM_REGISTER.tsv $D/PARAM_REGISTER.tsv.bak_w712_%s 2>/dev/null || true
base64 -d > $D/PARAM_REGISTER.tsv <<'__REG_EOF__'
%s
__REG_EOF__
base64 -d > $D/generated/strata-ud-iq4_xs.json <<'__GEN_EOF__'
%s
__GEN_EOF__
echo "remote register md5: $(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)"
echo "remote generated md5: $(md5sum $D/generated/strata-ud-iq4_xs.json | cut -d' ' -f1)"
echo "remote register CR: $(tr -cd '\r' < $D/PARAM_REGISTER.tsv | wc -c)"
""" % (os.environ.get("TS", "now"), reg_b64, gen_b64)

p = subprocess.run([SSH, "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(script.encode("utf-8")) + b"\n",
                   capture_output=True, timeout=120)
print("push rc =", p.returncode)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
print("local register md5:", md5f(REG))
