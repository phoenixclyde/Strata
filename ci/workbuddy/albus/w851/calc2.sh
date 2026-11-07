set +e
cat > /tmp/calc2.py <<'PY'
import io, re, glob
f = sorted(glob.glob("/home/albus/strata166/data/w851_tune55_*.log"))[-1]
buckets = {}
for ln in io.open(f, encoding="utf-8", errors="replace"):
    ln = ln.strip()
    m = re.match(r"^(best|keep_default) T=(\d+) N=(\d+) K=(\d+) ldy=(\d+).*?default_ms=([\d.]+)", ln)
    if not m: continue
    kind, T, N, K = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    dflt = float(m.group(6))
    best = dflt
    mb = re.search(r"\bms=([\d.]+)", ln)
    if kind == "best" and mb: best = float(mb.group(1))
    b = buckets.setdefault(T, [0.0, 0.0, 0])
    b[0] += dflt; b[1] += best; b[2] += 1
print("  桶      形状数   default合计   最优合计    节省")
for T in sorted(buckets):
    d, b, n = buckets[T]
    print("  T=%-5d %-6d %9.2f ms  %9.2f ms  %5.1f%%" % (T, n, d, b, (d-b)/d*100))
d = sum(v[0] for v in buckets.values()); b = sum(v[1] for v in buckets.values())
print("\n  全部 84 case: %.2f -> %.2f ms  (省 %.1f%% = %.2f ms/次全量投影)" % (d, b, (d-b)/d*100, d-b))
PY
python3 /tmp/calc2.py
