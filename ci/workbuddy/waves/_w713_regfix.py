# 按审计改 register 的 P34 表述（值/状态不动）-> gen_config -> 推 166 -> 复验
import hashlib, io, os, shutil, subprocess, base64, time, collections

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")
PY = r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

raw = open(REG, "rb").read()
print("register md5(before) =", hashlib.md5(raw).hexdigest())
shutil.copy2(REG, REG + ".bak_w713audit_" + time.strftime("%Y%m%d_%H%M%S"))

t = raw.decode("utf-8")
K1 = "机制：可复用前缀须与 prefill chunk(8192) 对齐。"
V1 = ("机制（**经验规律，非源码确证**；2026-10-08 审计 P1）：可复用前缀只认与 prefill chunk 整数倍对齐的 checkpoint "
      "---- 由 W709 三点 + W712 B1 九格支持，但引擎 help 与源码**未见显式断言**，"
      "且 every=4096/chunk=8192 得 reused=0 用源码直读解释不通（**待追**）。")
K2 = "（整条 prompt 不足一个 chunk，无 checkpoint 可放，该档换任何值都无用）"
V2 = "（该档日志确实建了 1 个 checkpoint，但**可复用边界不成立**；换任何值都无效）"

for k, v in [(K1, V1), (K2, V2)]:
    n = t.count(k)
    assert n == 1, "锚点命中 %d 次（应为 1）: %s" % (n, k[:40])
    t = t.replace(k, v)

io.open(REG, "w", encoding="utf-8", newline="\n").write(t)
raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
hdr = rows[0].split("\t")
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
print("register md5(after)  =", hashlib.md5(raw2).hexdigest(), len(raw2), "bytes")
print("rows=%d status=%s  CR=%d BAN=%d" % (len(rows) - 1, dict(st), raw2.count(b"\r"),
      sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)))

# ---- 重新生成生产 config，断言逐字节未变 ----
b4 = hashlib.md5(open(GEN, "rb").read()).hexdigest()
r = subprocess.run([PY, "-u", os.path.join(WS, "deploy", "params", "gen_config.py"), "--write"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
af = hashlib.md5(open(GEN, "rb").read()).hexdigest()
print("gen_config rc=%d  generated md5 %s -> %s  identical=%s" % (r.returncode, b4[:12], af[:12], b4 == af))

# ---- 推 register 到 166 ----
reg_b64 = base64.b64encode(raw2).decode("ascii")
s = ("set -u\nD=/home/albus/strata166/params\n"
     "base64 -d > $D/PARAM_REGISTER.tsv <<'__R_EOF__'\n%s\n__R_EOF__\n"
     "echo remote_register_md5=$(md5sum $D/PARAM_REGISTER.tsv | cut -d' ' -f1)\n"
     "echo remote_CR=$(tr -cd '\\r' < $D/PARAM_REGISTER.tsv | wc -c)\n") % reg_b64
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=120)
print(p.stdout.decode("utf-8", "replace").strip())
