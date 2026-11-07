import json
import statistics as st
import subprocess

REMOTE = "/home/albus/strata166/tmp/w1039/"


def get(a):
    r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166",
                        "cat " + REMOTE + "arm_%s.json" % a], capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout)


arms = {a: get(a) for a in ("ctl", "ctl2", "dp4a", "dp4a2", "dpp", "dpp2")}

for a, d in arms.items():
    rows = [(r["target"], r["tokens"], r["gpu_ms"], r["phases"].get("qsa attn"), r["phases"].get("dequant"))
            for r in d["prefill"]]
    print(a, " ".join("t%d/%d/%d/attn%s" % (t, tk, g, at) for t, tk, g, at, _ in rows))
    print("   decode", ["%.1f" % x["tok_s"] for x in d["decode"]])

print()
groups = {"ctl": ("ctl", "ctl2"), "dp4a": ("dp4a", "dp4a2"), "dpp": ("dpp", "dpp2")}
stats = {}
for name, members in groups.items():
    for shape in (2500, 8000, 16000):
        vals, attn, gpu = [], [], []
        for a in members:
            for r in arms[a]["prefill"]:
                if r["target"] == shape:
                    vals.append(r["gpu_ms"] * 1000.0 / r["tokens"])
                    attn.append(r["phases"].get("qsa attn"))
                    gpu.append(r["gpu_ms"])
        stats[(name, shape)] = dict(us=st.mean(vals), cv=100 * st.stdev(vals) / st.mean(vals), n=len(vals),
                                    attn=st.mean(attn), gpu=st.mean(gpu))

for shape in (2500, 8000, 16000):
    b = stats[("ctl", shape)]
    print("%5d ctl %.1f (cv %.2f%%, n=%d) attn %.0f" % (shape, b["us"], b["cv"], b["n"], b["attn"]))
    for name in ("dp4a", "dpp"):
        x = stats[(name, shape)]
        print("      %-5s %.1f (cv %.2f%%) d=%+.2f%%  2xCV=%.2f%%  attn %.0f (%+.2f%%)" % (
            name, x["us"], x["cv"], 100 * (x["us"] - b["us"]) / b["us"], 2 * x["cv"],
            x["attn"], 100 * (x["attn"] - b["attn"]) / b["attn"]))

for name in groups:
    ds = [x["tok_s"] for a in groups[name] for x in arms[a]["decode"]]
    print("%-5s decode %.2f (cv %.1f%%, n=%d)" % (name, st.mean(ds), 100 * st.stdev(ds) / st.mean(ds), len(ds)))
