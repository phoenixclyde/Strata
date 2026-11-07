#!/usr/bin/env python3
"""W1039/P457: is the ~0.04 KL common-mode (a bug the two OPT paths share) or per-path rounding?

Three questions, all answered from data already on disk (no GPU, no window):
  1. floor:        g2_A vs run_A  == same binary, same config, two runs  -> must be 0 everywhere
  2. per-path:     run_A vs run_B  (int8)   g2_A vs g2_B  (fp16)
  3. common mode:  correlate the two arms' per-position |dlogp| .  Rounding is independent per path, so
                   correlation ~0 means "two separate roundings"; high correlation means "one shared cause".
Also: do the changed positions cluster by chunk offset (pos % 64)?  A LDS/index bug hits a fixed lane or
group, so it would concentrate; global rounding would not.
"""
import io
import sys


def load(path):
    rows = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            if len(f) < 16:
                continue
            try:
                pos = int(f[0]); tgt = int(f[1]); lp_t = float(f[2]); am = int(f[3])
            except ValueError:
                continue
            top = []
            for x in f[8:8 + 64]:
                if ":" in x:
                    a, b = x.split(":", 1)
                    try:
                        top.append((int(a), float(b)))
                    except ValueError:
                        pass
            rows.append((pos, tgt, lp_t, am, top))
    return rows


def pair(name, A, B):
    n = min(len(A), len(B))
    d = []
    ch = 0
    for i in range(n):
        a, b = A[i], B[i]
        if a[0] != b[0]:
            print("  !! pos mismatch at row %d" % i)
            n = i
            break
        d.append(a[2] - b[2])
        if a[3] != b[3]:
            ch += 1
    ad = sorted(abs(x) for x in d)
    def q(p):
        return ad[min(len(ad) - 1, int(p / 100.0 * len(ad)))]
    print("  %-10s n=%d  argmax changed %d (%.2f%%)  |dlogp| med %.5f p90 %.5f p99 %.5f max %.3f"
          % (name, n, ch, 100.0 * ch / n, q(50), q(90), q(99), ad[-1]))
    for thr in (0.001, 0.01, 0.05, 0.1, 0.5):
        c = sum(1 for x in ad if x > thr)
        print("      |dlogp| > %-6.3f : %5d (%.2f%%)" % (thr, c, 100.0 * c / n))
    return d, n


def corr(x, y):
    n = min(len(x), len(y))
    mx = sum(x[:n]) / n; my = sum(y[:n]) / n
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sxx = sum((x[i] - mx) ** 2 for i in range(n))
    syy = sum((y[i] - my) ** 2 for i in range(n))
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else float("nan")


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    A1 = load(base + "/run_A.tsv"); B1 = load(base + "/run_B.tsv")     # int8
    A2 = load(base + "/g2_A.tsv");  B2 = load(base + "/g2_B.tsv")     # fp16
    A3 = load(base + "/g2_Ab.tsv")
    print("rows: int8 %d/%d  fp16 %d/%d  floor %d" % (len(A1), len(B1), len(A2), len(B2), len(A3)))
    print("\n[1] floor (same binary, two runs):")
    pair("floor", A2, A3)
    print("\n[2] each arm against its own control:")
    d1, n1 = pair("int8", A1, B1)
    d2, n2 = pair("fp16", A2, B2)
    print("\n[3] common mode: corr(|dlogp| int8, |dlogp| fp16) = %.4f" % corr([abs(x) for x in d1], [abs(x) for x in d2]))
    print("    corr(signed)                                   = %.4f" % corr(d1, d2))
    same = sum(1 for i in range(min(len(d1), len(d2))) if abs(d1[i]) > 0.001 and abs(d2[i]) > 0.001)
    print("    positions wrong in BOTH arms (>0.001 nats): %d / %d" % (same, min(len(d1), len(d2))))

    print("\n[4] do changed positions cluster by chunk offset (pos %% 64)?")
    for nm, A, B in (("int8", A1, B1), ("fp16", A2, B2)):
        hist = [0] * 8
        tot = [0] * 8
        for i in range(min(len(A), len(B))):
            b = A[i][0] % 64 // 8
            tot[b] += 1
            if A[i][3] != B[i][3]:
                hist[b] += 1
        print("    %-5s per 8-cell bucket: %s   total %s"
              % (nm, ["%d(%.1f%%)" % (h, 100.0 * h / max(1, t)) for h, t in zip(hist, tot)], tot))


if __name__ == "__main__":
    main()
