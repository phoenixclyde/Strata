import io, re, sys

P = "/home/albus/strata166/pr/strata-fork/ci/cfg_apply.py"
s = io.open(P, encoding="utf-8").read()

HELPER = '''def compare_arms(base, dec, tt, extra):
    """The verdict arithmetic, pure: (worse, better, lines).

    Extracted because it failed once in production.  `better` used to be bound only inside the
    per-length loop, so a run where no length moved past its band raised UnboundLocalError
    *after* the candidate config had been installed and the engine restarted -- leaving an
    unvetted config live, with no record and no rollback.  Pure and covered by
    ci/test_cfg_verdict.py instead of retyped in the reporting path.
    """
    lines = []
    band_d = 2 * max(base["decode"]["cv_pct"] or 0, dec["cv_pct"] or 0)
    band_t = 2 * max(base["ttft"]["cv_pct"] or 0, tt["cv_pct"] or 0)
    dd = 100.0 * (dec["median"] - base["decode"]["median"]) / base["decode"]["median"]
    dt = 100.0 * (tt["median"] - base["ttft"]["median"]) / base["ttft"]["median"]
    lines.append("decode %+.2f%% (band %.2f%%), ttft %+.2f%% (band %.2f%%)" % (dd, band_d, dt, band_t))
    worse = dd < -band_d or dt > band_t
    better = dd > band_d or dt < -band_t
    for L, cur in sorted((extra or {}).items(), key=lambda kv: int(kv[0])):
        b2 = (base.get("prefill") or {}).get(str(L)) or (base.get("prefill") or {}).get(L)
        if not (b2 and cur):
            continue
        band = 2 * max(b2["cv_pct"] or 0, cur["cv_pct"] or 0)
        d = 100.0 * (cur["median"] - b2["median"]) / b2["median"]
        lines.append("prefill@%s %+.2f%% (band %.2f%%)" % (L, d, band))
        if d < -band:
            worse = True
        if d > band:
            better = True
    return worse, better, lines


'''

if "def compare_arms(" not in s:
    i = s.index("def main():")
    s = s[:i] + HELPER + s[i:]

START = '    print("== measure (decode n=%d, ttft n=%d)" % (a.n, a.n))'
END = '    print("== verdict: %s (%s)" % (verdict, why))'
i = s.index(START)
j = s.index(END)

NEW = '''    try:
        print("== measure (decode n=%d, ttft n=%d)" % (a.n, a.n))
        dec = stats(decode(a.n))
        tt = stats(ttft(a.n))
        extra = {}
        for L in [int(x) for x in a.lengths.split(",") if x.strip()]:
            extra[L] = stats(prefill_at(L, max(3, a.n // 2)))
            print("   prefill@%d: %s" % (L, extra[L]))

        rec = {"label": a.label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "args": cand["args"], "env": cand["env"], "deltas_args": changed, "deltas_env": env_changed,
               "decode": dec, "ttft": tt, "prefill": extra, "gate": "PASS"}
        json.dump(rec, open(os.path.join(STATE, a.label + ".json"), "w"), indent=1)
        print("   decode: %s" % dec)
        print("   ttft  : %s" % tt)

        verdict, why = "REVERT", "inconclusive: no change beyond 2x CV, so the live value stays"
        if a.force_keep:
            verdict, why = "KEEP", "forced (restoring a known-good value)"

        if a.baseline:
            b = json.load(open(os.path.join(STATE, a.baseline + ".json")))
            if b.get("decode") and dec:
                worse, better, lines = compare_arms(b, dec, tt, extra)
                for l in lines:
                    print("   vs %s: %s" % (a.baseline, l))
                if worse:
                    verdict, why = "ROLLBACK", "regression beyond 2x CV"
                elif better:
                    verdict, why = "KEEP", "improvement beyond 2x CV"
    except BaseException as e:            # the candidate is LIVE at this point: roll back, never fall through
        print("!! crashed after install: %r -> ROLLBACK" % (e,))
        shutil.copy2(bak, CFG)
        up3, _ = restart()
        with open(os.path.join(STATE, a.label + ".crash"), "w") as f:
            f.write("crashed after install: %r\\nrestored_health=%s\\n" % (e, up3))
        return 4
'''

s = s[:i] + NEW + s[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched; compare_arms present:", "def compare_arms(" in s)
