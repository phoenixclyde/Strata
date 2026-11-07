import io
import json
import re
import statistics as st
import subprocess


def sh(cmd, timeout=180):
    r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166", cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout


# ---------- A. decode window breakdown ----------
txt = sh("grep -a 'strata decode timing:' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -400")
io.open("albus/w1039/decode_timing.txt", "w", encoding="utf-8", newline="\n").write(txt)

pat = re.compile(
    r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = "
    r"adapt wait ([\d.]+) \+ verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+) "
    r"\[plan ([\d.]+) actq ([\d.]+) jobs ([\d.]+) CPU ([\d.]+)\] \+ stage ([\d.]+)\) \+ "
    r"commit/emit ([\d.]+) \+ draft ([\d.]+) \+ adapt join ([\d.]+) \+ other ([\d.]+)")

rows = []
for ln in txt.splitlines():
    m = pat.search(ln)
    if m:
        v = m.groups()
        rows.append({
            "win": int(v[0]), "T": float(v[1]), "tokens": float(v[2]), "ms": float(v[3]),
            "adapt_wait": float(v[4]), "verify": float(v[5]), "gpu": float(v[6]),
            "host": float(v[7]), "stage": float(v[12]), "commit": float(v[13]),
            "draft": float(v[14]), "other": float(v[15]),
        })
print("decode-timing samples:", len(rows))
if rows:
    def agg(k):
        xs = [r[k] for r in rows]
        return st.median(xs)
    ms = agg("ms")
    print("median ms/window %.2f  tokens/window %.2f  => %.1f tok/s" % (ms, agg("tokens"), 1000 * agg("tokens") / ms))
    for k in ("verify", "gpu", "host", "stage", "draft", "adapt_wait", "commit", "other"):
        v = agg(k)
        print("   %-11s %6.2f ms  %5.1f%% of window" % (k, v, 100.0 * v / ms))
    # what draft->0 and draft-40% would buy
    print("   ceiling if draft -> 0      : %.1f%% faster decode" % (100.0 * agg("draft") / ms))
    print("   ceiling if draft -> -40%%   : %.1f%% faster decode" % (40.0 * agg("draft") / ms))
    print("   ceiling if draft -> -2.3ms : %.1f%% faster decode" % (100.0 * 2.3 / ms))

# ---------- B. first-request penalty across every arm we have ----------
files = sh("ls /home/albus/strata166/tmp/w103*/arm_*.json /home/albus/strata166/tmp/w1041/arm_*.json 2>/dev/null").split()
print("\narm files:", len(files))
first_gap = []
for f in files:
    raw = sh("cat " + f)
    if not raw.strip().startswith("{"):
        continue
    try:
        d = json.loads(raw)
    except Exception:
        continue
    pre = d.get("prefill") or []
    if len(pre) < 2:
        continue
    # compare the FIRST record of each target against the later records of the same target
    seen = {}
    for r in pre:
        seen.setdefault(r["target"], []).append(r["gpu_ms"] * 1000.0 / max(r["tokens"], 1))
    for tgt, xs in seen.items():
        if len(xs) >= 2:
            first_gap.append((100.0 * (xs[0] - st.median(xs[1:])) / st.median(xs[1:]), tgt, f.split("/")[-1]))
if first_gap:
    vals = [g[0] for g in first_gap]
    print("first-vs-rest per target: n=%d  median %+.2f%%  mean %+.2f%%  p90 %+.2f%%" % (
        len(vals), st.median(vals), st.mean(vals), sorted(vals)[int(0.9 * len(vals))]))
    pos = sum(1 for v in vals if v > 0.5)
    print("   slower by >0.5%%: %d of %d (%.0f%%)" % (pos, len(vals), 100.0 * pos / len(vals)))
    for v, tgt, f in sorted(first_gap, reverse=True)[:6]:
        print("   %+7.2f%%  target=%5d  %s" % (v, tgt, f))
