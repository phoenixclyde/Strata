# -*- coding: utf-8 -*-
"""Q1 决定性复核：**同一 prompt**（固定 nonce、greedy）在 base / nores 上各跑 3 次。
greedy + 相同 prompt => 输出逐 token 相同 => spec 接受率相同 => decode 差异就是纯速度差。
用法：python _q1_fixed.py
"""
import re, sys, json, base64, subprocess

HOST = "albus@192.168.50.166"
PY = sys.executable
ARM = r"D:/workbuddy_space/strata_ws/albus/tune/_q1_arm.py"


def sh(script, timeout=1200):
    b64 = base64.b64encode(script.encode()).decode("ascii")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=15",
                        "-o", "ConnectTimeout=15", HOST, "base64 -d | bash"],
                       input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.stdout.decode("utf-8", "replace")


REMOTE = r'''
cd /home/albus/strata166/tmp
python3 - <<'PY'
import sys, time, json, urllib.request
sys.path.insert(0, '/home/albus/strata166/tmp')
import importlib.util
spec = importlib.util.spec_from_file_location("b", "/home/albus/strata166/tmp/w776_bench.py")
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
NONCE = "Q1FIX"           # 固定：两个臂必须看到逐字相同的 prompt
txt = b.build(NONCE, 23000, 1.62)
for i in range(3):
    r, dt = b.post("/v1/chat/completions", {"model": b.MODEL,
        "messages": [{"role": "user", "content": txt}],
        "max_tokens": 320, "temperature": 0})
    lr = b.last_req()
    print("FIX run%d ptok=%s reused=%s prompt_ms=%.0f prompt_tps=%.1f decode_tps=%s out=%s wall=%.1f"
          % (i + 1, lr.get("prompt_tokens"), lr.get("reused"), lr.get("prompt_ms") or -1,
             (lr.get("prompt_tokens") or 0) / ((lr.get("prompt_ms") or 1) / 1000.0),
             lr.get("decode_tok_s"), lr.get("output_tokens"), dt))
PY
'''


def set_arm(arm):
    r = subprocess.run([PY, ARM, arm], capture_output=True, text=True, timeout=1200)
    return "READY" in r.stdout


out_rows = []
for arm in ("base", "nores", "base"):
    ok = set_arm(arm)
    print("=== %s ready=%s ===" % (arm, ok), flush=True)
    if not ok:
        sys.exit(2)
    out = sh(REMOTE)
    print(out.strip(), flush=True)
    dec = [float(m.group(1)) for m in re.finditer(r"decode_tps=([0-9.]+)", out)]
    prm = [float(m.group(1)) for m in re.finditer(r"prompt_tps=([0-9.]+)", out)]
    out_rows.append((arm, dec, prm))

print("\n==== 汇总（同一 prompt，greedy）====")
for arm, dec, prm in out_rows:
    if dec:
        print("%-5s decode=%s (中位 %.1f)  prompt 中位 %.1f"
              % (arm, ",".join("%.1f" % x for x in dec), sorted(dec)[len(dec) // 2],
                 sorted(prm)[len(prm) // 2]))
