import json
import statistics as st
import subprocess

R = "/home/albus/strata166/tmp/w1039/"


def get(a):
    r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166", "cat " + R + a],
                       capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout)


arms = {a: get("w3_%s.json" % a) for a in ("ctl", "ctl2", "pa5", "pa52")}
groups = {"ctl": ("ctl", "ctl2"), "pa5+dp4a": ("pa5", "pa52")}


def agg(mem, t, key):
    vals = []
    for a in mem:
        for r in arms[a]["prefill"]:
            if r["target"] == t:
                vals.append(r[key])
    return st.mean(vals)


print("%-5s %-10s %10s %10s %8s %8s" % ("shape", "arm", "us/tok", "attn_ms", "cv%", "n"))
for t in (2500, 8000, 16000):
    for name, mem in groups.items():
        us = [r["gpu_ms"] * 1000.0 / r["tokens"] for a in mem for r in arms[a]["prefill"] if r["target"] == t]
        print("%-5d %-10s %10.1f %10.0f %8.2f %8d" % (
            t, name, st.mean(us), agg(mem, t, "phases").get("qsa attn") if False else
            st.mean([r["phases"].get("qsa attn") for a in mem for r in arms[a]["prefill"] if r["target"] == t]),
            100 * st.stdev(us) / st.mean(us), len(us)))

print()
for t in (2500, 8000, 16000):
    b_us = st.mean([r["gpu_ms"] * 1000.0 / r["tokens"] for a in groups["ctl"] for r in arms[a]["prefill"] if r["target"] == t])
    b_at = st.mean([r["phases"].get("qsa attn") for a in groups["ctl"] for r in arms[a]["prefill"] if r["target"] == t])
    x_us = st.mean([r["gpu_ms"] * 1000.0 / r["tokens"] for a in groups["pa5+dp4a"] for r in arms[a]["prefill"] if r["target"] == t])
    x_at = st.mean([r["phases"].get("qsa attn") for a in groups["pa5+dp4a"] for r in arms[a]["prefill"] if r["target"] == t])
    x_cv = 100 * st.stdev([r["gpu_ms"] * 1000.0 / r["tokens"] for a in groups["pa5+dp4a"] for r in arms[a]["prefill"] if r["target"] == t]) / x_us
    print("%5d  prefill %+.2f%% (2xCV %.2f%%)   attn %+.2f%% (%.0f -> %.0f ms)" % (
        t, 100 * (x_us - b_us) / b_us, 2 * x_cv, 100 * (x_at - b_at) / b_at, b_at, x_at))

for name, mem in groups.items():
    ds = [x["tok_s"] for a in mem for x in arms[a]["decode"]]
    print("%-10s decode %.2f tok/s (cv %.1f%%, n=%d)" % (name, st.mean(ds), 100 * st.stdev(ds) / st.mean(ds), len(ds)))
