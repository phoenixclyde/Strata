# -*- coding: utf-8 -*-
"""W776-C1 收尾两件：
 1) register 加 B08 args_written=(不设)（上游 setup.py 的写回标记，非引擎项）
 2) 把 166 上 patches/*.patched 留档更新为 0.2.2 移植件（旧留档是 0.1.42 的，导致 verify 假 FAIL）
先备份两侧。
"""
import io, os, shutil, time, subprocess, base64, hashlib

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
TP = r"D:/workbuddy_space/strata_ws/deploy/tmp/_tpatch"
HOST = "albus@192.168.50.166"
ts = time.strftime("%Y%m%d_%H%M%S")

# ---- 1) register 加 B08 ----
shutil.copy2(REG, REG + ".bak_w776c1b_" + ts)
txt = io.open(REG, encoding="utf-8-sig").read()
lines = txt.splitlines()
if any(l.split("\t")[0] == "B08" for l in lines if l.strip()):
    print("B08 already exists, skip")
else:
    row = "\t".join([
        "B08", "CFG", "args_written", "(不设)", "serving", "REJECTED", "-", "-", "-",
        ("src022/setup.py:5982 逐字 'args_written (strata_control/user_args.py) is setup's own'；"
         "6147 行 `user_args.stamp(cfg)  # args_written: what setup wrote, for the next hand-edit check`；"
         "6038 行说明缺该键只影响 setup 自己判『手改』。=> **引擎不读**，我们的 config 由 gen_config.py 产出、不经 setup.py，故不设。"
         "加本行是为了让 (数据面5) SETUP_KEYS 覆盖判定的『已声明』集合完整，而不是把它塞进黑名单。"),
        "不设（上游 setup 的写回标记，非引擎配置项）",
    ])
    idx = max(i for i, l in enumerate(lines) if l.startswith("B0"))
    lines.insert(idx + 1, row)
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("B08 added after line", idx + 1)

# ---- 2) 更新 166 留档 ----
def run(script, timeout=120):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

P = "/home/albus/strata166/patches"
rc, o, e = run("cd %s && for f in serve-telemetry.py serve-web-app.js; do cp -a $f.patched $f.patched.bak0142_%s 2>/dev/null; done; echo BACKED" % (P, ts))
print("[bak] rc=%d %s%s" % (rc, o, e))

for nm, local in (("serve-telemetry.py", os.path.join(TP, "serve-telemetry.py.patched.022")),
                  ("serve-web-app.js", os.path.join(TP, "serve-web-app.js.patched.022"))):
    data = open(local, "rb").read()
    b64 = base64.b64encode(data).decode("ascii")
    s = "echo '%s' | base64 -d > %s/%s.patched && md5sum %s/%s.patched && wc -c %s/%s.patched" % (
        b64, P, nm, P, nm, P, nm)
    rc, o, e = run(s)
    print("[push %s] want=%s got=%s | %s%s" % (nm, hashlib.md5(data).hexdigest()[:8], o.split()[0][:8] if o.split() else "?", o.replace("\n", " "), e[:200]))
