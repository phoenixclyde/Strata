import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

old = '''    verdict, why = "KEEP", "no baseline"
    if a.baseline:
        b = json.load(open(os.path.join(STATE, a.baseline + ".json")))
        if b.get("decode") and dec:
            cv = max(b["decode"]["cv_pct"] or 0, dec["cv_pct"] or 0)
            lim = 2 * cv
            dd = 100.0 * (dec["median"] - b["decode"]["median"]) / b["decode"]["median"]
            dt2 = 100.0 * (tt["median"] - b["ttft"]["median"]) / b["ttft"]["median"]
            print("   vs %s: decode %+.2f%% (band %.2f%%), ttft %+.2f%% (band %.2f%%)"
                  % (a.baseline, dd, lim, dt2, 2 * b["ttft"]["cv_pct"]))
            if dd < -lim or dt2 > 2 * b["ttft"]["cv_pct"]:
                verdict, why = "ROLLBACK", "regression beyond 2x CV"'''

new = '''    verdict, why = "REVERT", "inconclusive: no change beyond 2x CV, so the live value stays"

    if a.baseline:
        b = json.load(open(os.path.join(STATE, a.baseline + ".json")))
        if b.get("decode") and dec:
            band_d = 2 * max(b["decode"]["cv_pct"] or 0, dec["cv_pct"] or 0)
            band_t = 2 * max(b["ttft"]["cv_pct"] or 0, tt["cv_pct"] or 0)
            dd = 100.0 * (dec["median"] - b["decode"]["median"]) / b["decode"]["median"]
            dt2 = 100.0 * (tt["median"] - b["ttft"]["median"]) / b["ttft"]["median"]
            print("   vs %s: decode %+.2f%% (band %.2f%%), ttft %+.2f%% (band %.2f%%)"
                  % (a.baseline, dd, band_d, dt2, band_t))
            worse = dd < -band_d or dt2 > band_t
            better = dd > band_d or dt2 < -band_t
            if worse:
                verdict, why = "ROLLBACK", "regression beyond 2x CV"
            elif better:
                verdict, why = "KEEP", "improvement beyond 2x CV"
            else:
                verdict, why = "REVERT", "inconclusive: nowhere beyond 2x CV, so the live value stays"'''

assert old in s
s = s.replace(old, new, 1)

# REVERT must restore the backup and restart, like ROLLBACK
s = s.replace('''    if verdict == "ROLLBACK":
        shutil.copy2(bak, CFG)''', '''    if verdict in ("ROLLBACK", "REVERT"):
        shutil.copy2(bak, CFG)''', 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched verdict policy (inconclusive -> REVERT)")
