import json
import statistics as st
import subprocess

D = "/home/albus/strata166/tmp/w1039"
pairs = [("arm_ctl", "arm_ctl2"), ("arm_dp4a", "arm_dp4a2"), ("arm_dpp", "arm_dpp2"),
         ("arm_b", "arm_b2"), ("arm_c", "arm_c2"), ("arm_kv_int8", "arm_kv_int8b"),
         ("arm_kv_k8v4", "arm_kv_k8v4b"), ("arm_b12180", "arm_b12180b")]


def get(name):
    r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166",
                        "cat %s/%s.json" % (D, name)], capture_output=True, text=True, timeout=90)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


print("%-22s %-6s %10s %10s %8s" % ("pair", "target", "pass1", "pass2", "delta"))
rows = {}
for a, b in pairs:
    da, db = get(a), get(b)
    if not da or not db:
        continue
    for tgt in (2500, 8000, 16000):
        def m(d):
            xs = [r["gpu_ms"] * 1000.0 / r["tokens"] for r in d["prefill"] if r["target"] == tgt]
            return st.mean(xs) if xs else None
        x, y = m(da), m(db)
        if x is None or y is None:
            continue
        rows.setdefault(tgt, []).append((a, 100.0 * (y - x) / x))
        print("%-22s %-6d %10.1f %10.1f %+7.2f%%" % (a.replace("arm_", ""), tgt, x, y, 100.0 * (y - x) / x))

print()
for tgt in sorted(rows):
    v = [d for _, d in rows[tgt]]
    print("target %-6d n=%d  pass2-vs-pass1: median %+.2f%%  mean %+.2f%%  (negative = pass1 was slower)" % (
        tgt, len(v), st.median(v), st.mean(v)))
