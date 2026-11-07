# -*- coding: utf-8 -*-
"""Q1 复核：交错 A/B（base / nores 各两轮），每臂 5 runs，
同时读 /metrics 的 drafts_offered / drafts_accepted 以量化"spec 接受率"这个混淆因子。
用法：python _q1_ab.py [rounds]
"""
import io, re, os, sys, json, time, base64, subprocess

HOST = "albus@192.168.50.166"
ARM = r"D:/workbuddy_space/strata_ws/albus/tune/_q1_arm.py"
PY = sys.executable
REMOTE_BENCH = "/home/albus/strata166/tmp/w776_bench.py"


def sh(script, timeout=900):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15",
                        "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


def counters():
    s = r'''curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "
import sys,json
d=json.load(sys.stdin); t=d['totals']
print(t['drafts_offered'], t['drafts_accepted'], t['output_tokens'], round(t['decode_ms'],1))
"'''
    out = sh(s, timeout=120).strip().splitlines()
    try:
        f = out[-1].split()
        return [float(x) for x in f]
    except Exception:
        return [0, 0, 0, 0]


def bench_m():
    out = sh("cd /home/albus/strata166/tmp && python3 %s M 2>&1" % REMOTE_BENCH, timeout=1200)
    per = [float(m.group(1)) for m in re.finditer(r"\[M\] run\d+ .*?decode_tps=([0-9.]+)", out)]
    med = re.search(r"prompt_tps median=([0-9.]+)\s+decode_tps median=([0-9.]+)", out)
    return (float(med.group(1)), float(med.group(2))) if med else (0.0, 0.0), per, out


def set_arm(arm):
    r = subprocess.run([PY, ARM, arm], capture_output=True, text=True, timeout=1200)
    ok = "READY" in r.stdout
    return ok, r.stdout[-260:]


rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
rows = []
for rd in range(rounds):
    for arm in ("base", "nores"):
        ok, tail = set_arm(arm)
        if not ok:
            print("!! %s 起不来，中止" % arm, flush=True)
            sys.exit(2)
        c0 = counters()
        (pt, dt), per, raw = bench_m()
        c1 = counters()
        dof = c1[0] - c0[0]
        dac = c1[1] - c0[1]
        acc = (dac / dof * 100.0) if dof > 0 else 0.0
        rows.append({"round": rd + 1, "arm": arm, "prompt": pt, "decode": dt, "per": per,
                     "acc": acc, "drafts": dof})
        print("R%d %-5s prompt=%7.1f decode_med=%5.1f  per=%s  accept=%.1f%% (drafts=%d)"
              % (rd + 1, arm, pt, dt, ",".join("%.1f" % x for x in per), acc, int(dof)), flush=True)

print("\n==== 汇总 ====")
for arm in ("base", "nores"):
    sub = [r for r in rows if r["arm"] == arm]
    dec = [r["decode"] for r in sub]
    prm = [r["prompt"] for r in sub]
    acc = [r["acc"] for r in sub]
    allper = [x for r in sub for x in r["per"]]
    if dec:
        print("%-5s 轮数=%d  prompt 中位=%.1f  decode 中位=%.1f  decode 逐次=%s  接受率=%.1f%%"
              % (arm, len(sub), sorted(prm)[len(prm) // 2], sorted(dec)[len(dec) // 2],
                 ",".join("%.1f" % x for x in allper), sum(acc) / len(acc)))
json.dump(rows, io.open(r"D:/workbuddy_space/strata_ws/albus/tune/_q1_ab.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved _q1_ab.json")
