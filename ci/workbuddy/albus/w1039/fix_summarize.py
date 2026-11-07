import io

p = "albus/w1039/summarize_kvg.py"
s = io.open(p, encoding="utf-8").read()

old = '''    pa, pb = pool(arms_a), pool(arms_b)
    print("%-7s %10s %10s %8s %8s %10s %s" % ("target", "A us/tok", "B us/tok", "delta", "2xCV(B)", "n(A/B)", "verdict"))
    for t in sorted(set(pa) & set(pb)):
        xa, xb = pa[t], pb[t]
        ma, mb = st.mean(xa), st.mean(xb)
        cvb = 100.0 * st.stdev(xb) / mb if len(xb) > 1 else 0.0
        delta = 100.0 * (mb - ma) / ma
        verdict = "INCONCLUSIVE" if abs(delta) <= 2 * cvb else ("SLOWER" if delta > 0 else "FASTER")
        print("%-7d %10.1f %10.1f %+7.2f%% %7.2f%% %6d/%-3d %s" % (t, ma, mb, delta, 2 * cvb, len(xa), len(xb), verdict))'''

new = '''    pa, pb = pool(arms_a), pool(arms_b)
    # per-run means: the noise that matters is run-to-run drift, not sample-to-sample inside one run
    pa_r = [per_target(d) for d in arms_a]
    pb_r = [per_target(d) for d in arms_b]
    print("%-7s %10s %10s %8s %8s %10s %s" % ("target", "A us/tok", "B us/tok", "delta", "2xCV(run)", "n(A/B)", "verdict"))
    for t in sorted(set(pa) & set(pb)):
        ra = [st.mean(d[t]) for d in pa_r if t in d]
        rb = [st.mean(d[t]) for d in pb_r if t in d]
        ma, mb = st.mean(ra), st.mean(rb)
        runs = ra + rb
        cvr = 100.0 * st.stdev(runs) / st.mean(runs) if len(runs) > 1 else 0.0
        delta = 100.0 * (mb - ma) / ma
        verdict = "INCONCLUSIVE" if abs(delta) <= 2 * cvr else ("SLOWER" if delta > 0 else "FASTER")
        print("%-7d %10.1f %10.1f %+7.2f%% %7.2f%% %6d/%-3d %s" % (t, ma, mb, delta, 2 * cvr, len(pa[t]), len(pb[t]), verdict))
        if len(ra) > 1 or len(rb) > 1:
            print("        runs A %s | B %s" % (" ".join("%.1f" % v for v in ra), " ".join("%.1f" % v for v in rb)))'''

assert old in s
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("summarize_kvg.py: between-run 2xCV + per-run means printed")
