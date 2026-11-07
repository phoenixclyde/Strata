# 固化审计：register(唯一真值) 三面比对 —— ADOPTED 行 vs 生产 config vs 引擎启动行
import io, json, os, hashlib, subprocess, base64

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
GEN = os.path.join(WS, "deploy", "params", "generated", "strata-ud-iq4_xs.json")

t = io.open(REG, encoding="utf-8-sig").read().splitlines()
hdr = t[0].split("\t")
rows = [dict(zip(hdr, l.split("\t"))) for l in t[1:] if l.strip()]
print("register md5(local) =", hashlib.md5(open(REG, "rb").read()).hexdigest())
print("register rows = %d" % len(rows))
import collections
print("status:", dict(collections.Counter(r["status"] for r in rows)))
print()
cfg = json.load(io.open(GEN, encoding="utf-8"))
args = cfg["args"]
env = cfg.get("env", {})
print("生产 config md5 =", hashlib.md5(open(GEN, "rb").read()).hexdigest())
print("生产 args =", " ".join(args))
print("生产 env  =", env)
print()
print("== ADOPTED / CANDIDATE 逐条（固化状态）==")
for st in ("ADOPTED", "CANDIDATE"):
    print("-- %s --" % st)
    for r in rows:
        if r["status"] != st:
            continue
        sc, nm, val = r["scope"], r["name"], r["value"]
        if st == "ADOPTED":
            if sc == "CLI":
                if val == "(flag)":
                    hit = nm in args
                else:
                    hit = nm in args and args[args.index(nm) + 1] == val
            elif sc == "ENV":
                hit = env.get(nm) == val
            else:
                hit = "n/a(%s)" % sc
        else:
            hit = "-"
        print("  %-5s %-6s %-30s %-22s in_LIVE=%s" % (r["id"], sc, nm, val[:22], hit))
print()
# 166 侧 register
s = "md5sum /home/albus/strata166/params/PARAM_REGISTER.tsv /home/albus/strata166/params/generated/strata-ud-iq4_xs.json /home/albus/strata166/data/strata-ud-iq4_xs.json"
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(s.encode()) + b"\n", capture_output=True, timeout=60)
print("== 166 侧三方 md5 ==")
print(p.stdout.decode("utf-8", "replace"))
