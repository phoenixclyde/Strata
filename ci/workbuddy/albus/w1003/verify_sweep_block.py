# 6. W1003 width/type sweep: the production types and shapes, all three arms.
#
# Why this group exists: RESULTS.tsv holds exactly four Q5_1 shapes, which is
# not what the pack contains. On its own it let a "repack everything" plan look
# viable. This group pins the sweep that showed otherwise, and refuses a file
# whose timing columns disagree with its own ratio columns.
sw = HERE / "WIDTH_SWEEP.tsv"
need(sw.is_file(), "missing artifact: WIDTH_SWEEP.tsv")
if sw.is_file():
    s = text(sw)
    need("TIMING-ONLY" in s,
         "WIDTH_SWEEP.tsv must keep the TIMING-ONLY disclaimer (random weights)")
    need("QK_K=256" in s and "K=640" in s,
         "WIDTH_SWEEP.tsv must keep the pack mapping that explains why K-quants cannot be on down")
    srows = [l for l in s.splitlines() if l.strip() and not l.startswith("#")
             and not l.startswith("shape")]
    need(len(srows) >= 20, "WIDTH_SWEEP.tsv must carry >= 20 measured rows, got %d" % len(srows))
    combos, pts = set(), {}
    for l in srows:
        c = l.split("\t")
        need(len(c) == 10, "bad column count: %s" % l[:60])
        if len(c) != 10:
            continue
        shape, tid, tname, npr = c[0], c[1], c[2], c[3]
        try:
            canon, w32, r32, w64, r64 = (float(c[4]), float(c[5]), float(c[6]),
                                        float(c[7]), float(c[8]))
            n = int(npr)
        except ValueError:
            FAILS.append("non-numeric row: %s" % l[:60])
            continue
        combos.add((shape, tid, tname))
        pts.setdefault((shape, tid), set()).add(n)
        need(abs(w32 / canon - r32) < 0.02,
             "ratio32 %.4f disagrees with %.4f/%.4f (%s %s rows=%d)" % (r32, w32, canon, shape, tname, n))
        need(abs(w64 / canon - r64) < 0.02,
             "ratio64 %.4f disagrees with %.4f/%.4f (%s %s rows=%d)" % (r64, w64, canon, shape, tname, n))
        need(canon > 0 and w32 > 0 and w64 > 0,
             "non-positive timing (%s %s rows=%d)" % (shape, tname, n))
        best = min((canon, "canonical"), (w32, "w32"), (w64, "w64"))[1]
        need(c[9] == best,
             "recorded winner %r is not the fastest arm %r (%s %s rows=%d)"
             % (c[9], best, shape, tname, n))
    # the four production combinations, and the five row counts each
    for want in (("gu", "12", "Q4_K"), ("gu", "13", "Q5_K"),
                 ("dn", "7", "Q5_1"), ("dn", "8", "Q8_0")):
        need(want in combos, "WIDTH_SWEEP.tsv lost the production combination %s" % (want,))
        got = pts.get(want[:2], set())
        need(got == {32, 128, 320, 512, 1024},
             "WIDTH_SWEEP.tsv %s must cover 32/128/320/512/1024, got %s"
             % (want[2], sorted(got)))
    # the whole point of the sweep: gate/up must NOT be repacked, down must be
    gu = [float(l.split("\t")[6]) for l in srows
          if l.startswith("gu\t") and len(l.split("\t")) == 12]
    dn = [float(l.split("\t")[6]) for l in srows
          if l.startswith("dn\t") and len(l.split("\t")) == 12]
    need(gu and min(gu) > 1.5,
         "gate/up repack suddenly pays off (min ratio32 %.3f) — re-read PORT_STATUS.md" % (min(gu) if gu else -1))
    need(dn and max(dn) < 0.90,
         "down repack no longer pays (max ratio32 %.3f) — re-read PORT_STATUS.md" % (max(dn) if dn else -1))

