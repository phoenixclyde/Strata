# -*- coding: utf-8 -*-
"""audit_closure.py -- machine-checkable closure for audit findings (AUDIT24+).

Each row of deploy/AUDIT_LEDGER_A24.tsv names
    id  level  doc  marker  status  fix  md5_asof
`status=RESOLVED` requires the marker string to still be present in `doc` (so a later edit
cannot silently drop a retraction). `md5_asof` is the file's md5 prefix when the fix was
verified; a drift is reported as WARN (the doc changed since), not as FAIL.

Usage: python tools/audit_closure.py [--strict]
"""
import io, os, sys, hashlib

LEDGER = "D:/workbuddy_space/strata_ws/deploy/AUDIT_LEDGER_A24.tsv"
DEPLOY = "D:/workbuddy_space/strata_ws/deploy/"


def main():
    strict = "--strict" in sys.argv
    rows = [l.split("\t") for l in io.open(LEDGER, encoding="utf-8").read().splitlines() if l.strip()]
    head, rows = rows[0], rows[1:]
    fails, warns, ok = [], [], 0
    for r in rows:
        if len(r) < 7:
            fails.append("row with %d cols: %s" % (len(r), r[:2]))
            continue
        aid, level, doc, marker, status, fix, md5 = r[:7]
        p = os.path.join(DEPLOY, doc)
        if not os.path.exists(p):
            fails.append("%s: doc missing %s" % (aid, doc))
            continue
        s = io.open(p, encoding="utf-8").read()
        if status == "RESOLVED":
            if marker not in s:
                fails.append("%s: MARKER GONE in %s (%r)" % (aid, doc, marker[:40]))
            else:
                ok += 1
                cur = hashlib.md5(io.open(p, "rb").read()).hexdigest()[:8]
                if md5 and md5 != "-" and cur != md5:
                    warns.append("%s: %s md5 %s -> %s (doc edited after fix)" % (aid, doc, md5, cur))
        elif status in ("DEFERRED", "WONTFIX"):
            ok += 1
        else:
            fails.append("%s: bad status %r" % (aid, status))
    print("closure: %d rows | RESOLVED-verified %d | FAIL %d | WARN %d" % (len(rows), ok, len(fails), len(warns)))
    for w in warns:
        print("  WARN " + w)
    for f in fails:
        print("  FAIL " + f)
    sys.exit(1 if fails or (strict and warns) else 0)


if __name__ == "__main__":
    main()
