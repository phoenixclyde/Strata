import io
import re
import statistics as st

txt = io.open("albus/w1039/decode_timing.txt", encoding="utf-8").read()
pat = re.compile(
    r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = "
    r"adapt wait ([\d.]+) \+ verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+) "
    r"\[plan ([\d.]+) actq ([\d.]+) jobs ([\d.]+) CPU ([\d.]+)\] \+ stage ([\d.]+)\) \+ "
    r"commit/emit ([\d.]+) \+ draft ([\d.]+) \+ adapt join ([\d.]+) \+ other ([\d.]+); per layer-window: "
    r"CPU experts ([\d.]+) \(([\d.]+) entries\), VRAM hits ([\d.]+), PCIe ([\d.]+)")

L = 48
rows = []
for ln in txt.splitlines():
    m = pat.search(ln)
    if not m:
        continue
    w = int(m.group(1))
    cpu_ms = float(m.group(12))           # per window
    vram = float(m.group(20))             # per layer-window
    cpu_exp = float(m.group(18))          # per layer-window
    gpu_ms = float(m.group(7))
    rows.append({
        "w": w,
        "cpu_total": cpu_ms * w,          # ms over the whole request
        "cpu_n": cpu_exp * L * w,         # experts over the whole request
        "gpu_total": gpu_ms * w,
        "vram_n": vram * L * w,
    })

print("requests parsed:", len(rows))
keep = [r for r in rows if r["cpu_n"] >= 1.0]
print("requests with >=1 CPU expert:", len(keep))

if keep:
    def slope_intercept(xs, ys):
        n = len(xs)
        mx, my = st.mean(xs), st.mean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        b = sxy / sxx if sxx else 0.0
        return b, my - b * mx

    xs = [r["cpu_n"] for r in keep]
    ys = [r["cpu_total"] for r in keep]
    b, a = slope_intercept(xs, ys)
    mx, my = st.mean(xs), st.mean(ys)
    r2 = 1 - sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys)) / sum((y - my) ** 2 for y in ys)
    print("\nCPU total (ms) vs missed experts (count), per request:")
    print("   fit: cpu_ms = %.4f * experts + %.2f ms   (R^2 = %.3f)" % (b, a, r2))
    print("   slope = %.0f us per missed expert   (the engine's model constant is 81 us)" % (1000 * b))
    print("   intercept = %.1f ms of fixed cost per request" % a)
    print("   means: %.1f experts, %.1f ms" % (mx, my))
    # throughput view: GPU expert vs CPU expert
    xs2 = [r["vram_n"] for r in keep]
    ys2 = [r["gpu_total"] for r in keep]
    b2, a2 = slope_intercept(xs2, ys2)
    print("\n   for reference, GPU: %.0f us per VRAM-hit expert (fit), %.1f ms fixed" % (1000 * b2, a2))
    print("   ratio CPU/GPU per expert = %.1fx" % (b / b2 if b2 else 0))

# distribution of CPU experts per request, to show the bimodality
allx = sorted(r["cpu_n"] for r in rows)
if allx:
    def q(p):
        return allx[min(len(allx) - 1, int(p * len(allx)))]
    print("\nmissed experts per request: p10 %.0f  p50 %.0f  p90 %.0f  max %.0f  (zeros: %d of %d)" % (
        q(0.1), q(0.5), q(0.9), allx[-1], sum(1 for v in allx if v < 1), len(allx)))
