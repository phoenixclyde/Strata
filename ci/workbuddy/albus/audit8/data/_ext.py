import io, re, sys

def dump(fn, arm_re=r"===\s*(?:ARM\s*)?([A-Z0-9]+)\b"):
    t = io.open(fn, encoding="utf-8", errors="replace").read().splitlines()
    cur = "?"
    rows = []
    for l in t:
        m = re.match(r"===\s*(?:ARM\s*)?([A-Z0-9]+)[\s=]", l)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r"prompt_ms=(\d+).*?wall=([\d.]+)s", l)
        if m:
            rows.append([cur, int(m.group(1)), float(m.group(2)), None, None, None, None, None])
            continue
        m = re.match(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms", l)
        if m and rows:
            def g(k):
                mm = re.search(re.escape(k) + r" (\d+) \(", l)
                return int(mm.group(1)) if mm else None
            rows[-1][3] = int(m.group(1))
            rows[-1][4] = int(m.group(2))
            rows[-1][5] = g("hc read")
            rows[-1][6] = g("gemm gate/up")
            rows[-1][7] = g("gemm down")
    print("---", fn)
    print("  %-4s %8s %7s %7s %6s %8s %8s" % ("arm", "prompt", "wall", "tokens", "GPU", "hcRead", "gemmGU"))
    for r in rows:
        print("  %-4s %8s %7s %7s %6s %8s %8s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))

for f in sys.argv[1:]:
    dump(f)
