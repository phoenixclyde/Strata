import json
import statistics as st
import subprocess

R = "/home/albus/strata166/tmp/w1039/"


def get(a):
    r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166", "cat " + R + a],
                       capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout)


arms = {a: get("w2_%s.json" % a) for a in ("ctl", "ctl2", "dp4a", "dp4a2", "dpp", "dpp2")}
groups = {"ctl": ("ctl", "ctl2"), "dp4a": ("dp4a", "dp4a2"), "dpp": ("dpp", "dpp2")}

for name, mem in groups.items():
    per = {}
    for a in mem:
        for r in arms[a]["prefill"]:
            per.setdefault(r["target"], []).append((r["tokens"], r["gpu_ms"], r["phases"].get("qsa attn"),
                                                    r["phases"].get("gemm gate/up")))
    print("##", name)
    for t in sorted(per):
        v = per[t]
        us = [g * 1000.0 / tk for tk, g, _, _ in v]
        print("   %5d  gpu %.0f  us/tok %.1f (cv %.2f%%)  attn %.0f (%.1f%% of gpu)  gu %.0f" % (
            t, st.mean([g for _, g, _, _ in v]), st.mean(us), 100 * st.stdev(us) / st.mean(us),
            st.mean([a for _, _, a, _ in v]), 100 * st.mean([a for _, _, a, _ in v]) / st.mean([g for _, g, _, _ in v]),
            st.mean([gu for _, _, _, gu in v])))
    ds = [x["tok_s"] for a in mem for x in arms[a]["decode"]]
    print("   decode %.2f tok/s (cv %.1f%%, n=%d)" % (st.mean(ds), 100 * st.stdev(ds) / st.mean(ds), len(ds)))

print()
print("=== 相对 ctl ===")
for t in (2500, 8000, 16000):
    def agg(mem):
        us, at = [], []
        for a in mem:
            for r in arms[a]["prefill"]:
                if r["target"] == t:
                    us.append(r["gpu_ms"] * 1000.0 / r["tokens"])
                    at.append(r["phases"].get("qsa attn"))
        return st.mean(us), 100 * st.stdev(us) / st.mean(us), st.mean(at)
    b, bcv, bat = agg(groups["ctl"])
    for name in ("dp4a", "dpp"):
        x, xcv, xat = agg(groups[name])
        print("%5d %-5s us/tok %+.2f%% (2xCV %.2f%%)   attn %+.2f%% (%d -> %d ms)" % (
            t, name, 100 * (x - b) / b, 2 * xcv, 100 * (xat - bat) / bat, bat, xat))
