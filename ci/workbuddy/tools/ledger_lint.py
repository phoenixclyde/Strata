# -*- coding: utf-8 -*-
"""ledger_lint.py -- AUDIT24 discipline 21/22, repaired by AUDIT29.

AUDIT29 found this gate had been blind for ~40 rounds:
  * it required exactly 10 columns while every row since W1035 carries an 11th
    (`kw`), so 160 rows were reported as "11 columns" on every run;
  * it printed problems and then fell off the end -- **no exit code at all**;
  * round_close had it in SOFT, so even a failure would not have blocked.
  209 problems per run, zero of them able to stop anything: "门自己瞎了" in its
  purest form.

Now:
  21) every row has 10 columns (legacy) or 11 (kw era); a closed row needs an
      evidence body >= 8 chars or a document reference.  Legacy rows before W1000
      with a short verdict are counted separately, not failed (history, not debt).
  22) markdown tables in the plan/audit docs must keep the header's cell count.
      The 47 legacy breaks in W832 are baselined in deploy/TABLE_SHAPE_BASELINE.tsv;
      the gate fails when a file *exceeds* its baseline -- new damage is caught,
      old damage is registered instead of pretending the file is clean.
  * when the kw column is present it must start with `KW:` and carry >= 1 token
    (claim_homes.py separately checks that the tokens really occur in the row).
  * rc 1 on any failure; --self-test covers the three row shapes + the baseline.

  python tools/ledger_lint.py
  python tools/ledger_lint.py --self-test
"""
import glob
import hashlib
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
BASELINE = os.path.join(ROOT, "deploy", "TABLE_SHAPE_BASELINE.tsv")
COLS = (10, 11)
CLOSED = ("DONE", "DONE_NEG", "NA", "WITHDRAWN")
ERA = 1000


def read_rows(path=P):
    rows = [ln.split("\t") for ln in io.open(path, encoding="utf-8").read().splitlines() if ln.strip()]
    return [r for r in rows if not r[0].startswith("#") and r[0] != "block"]


def round_of(row):
    m = re.search(r"\bW(\d{3,4})\b", row[3] if len(row) > 3 else "")
    return int(m.group(1)) if m else None


def check_rows(rows):
    fails, legacy_short = [], 0
    for i, r in enumerate(rows, 1):
        if len(r) not in COLS:
            fails.append("row %-3d %-6s: %d columns (want 10 or 11 -- 11 = kw era)"
                         % (i, r[1] if len(r) > 1 else "?", len(r)))
            continue
        note = r[8].strip()
        ref = r[9] if len(r) > 9 else ""
        short = re.fullmatch(r"\d+", note) or (r[7] in CLOSED and len(note) < 8 and "W" not in ref)
        if short:
            n = round_of(r)
            if n is not None and n < ERA:
                legacy_short += 1
            else:
                fails.append("row %-3d %-6s: evidence %r (closed rows need a body or a W ref)"
                             % (i, r[1], note[:24]))
        if len(r) == 11:
            kw = r[10].strip()
            if kw and not kw.startswith("KW:"):
                fails.append("row %-3d %-6s: kw column does not start with KW:" % (i, r[1]))
            elif kw and not kw[3:].strip("| "):
                fails.append("row %-3d %-6s: kw column carries no token" % (i, r[1]))
    return fails, legacy_short


def broken_tables(paths):
    """per-file count of rows whose cell count differs from their table header"""
    out = {}
    for p in paths:
        if not os.path.isfile(p):
            continue
        want, n_bad = None, 0
        for ln in io.open(p, encoding="utf-8", errors="replace").read().split("\n"):
            if not ln.startswith("|"):
                want = None
                continue
            cells = ln.count("|") - ln.count("\\|")
            if want is None:
                want = cells
                continue
            if cells != want and not set(ln.replace("|", "").strip()) <= set("-: "):
                n_bad += 1
        if n_bad:
            out[os.path.basename(p)] = n_bad
    return out


def load_baseline(path=BASELINE):
    base = {}
    if os.path.isfile(path):
        for ln in io.open(path, encoding="utf-8"):
            if not ln.strip() or ln.startswith("#"):
                continue
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 2 and f[1].isdigit():
                base[f[0]] = int(f[1])
    return base


def check(quiet=False, plan=PLAN, baseline=BASELINE, rows_path=P):
    fails, legacy_short = check_rows(read_rows(rows_path))
    targets = [plan] + sorted(glob.glob(os.path.join(ROOT, "deploy", "AUDIT2*.md")))
    bad = broken_tables(targets)
    base = load_baseline(baseline)
    for name, n in sorted(bad.items()):
        allowed = base.get(name, 0)
        if n > allowed:
            fails.append("%s: %d broken table rows (baseline %d) -- escape the stray | inside the cell"
                         % (name, n, allowed))
    if not quiet:
        print("ledger rows %d | problems %d | legacy-short %d | tables %s"
              % (len(read_rows(rows_path)), len(fails), legacy_short,
                 ", ".join("%s=%d/%d" % (k, v, base.get(k, 0)) for k, v in sorted(bad.items())) or "clean"))
        for f in fails[:40]:
            print("  " + f)
        print("LEDGER_LINT: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
        print("md5(PROGRESS) =", hashlib.md5(io.open(rows_path, "rb").read()).hexdigest())
    return fails


def self_test():
    import tempfile
    ok = 0
    cases = [
        ("good 11-col row", "b\tP1\titem\tW1053\tcount\t1\t1\tDONE\tevidence body here\tref\tKW:x", True),
        ("good legacy 10-col row", "b\tP1\titem\tW900\tcount\t1\t1\tDONE\tevidence body here\tref", True),
        ("12 columns", "b\tP1\titem\tW1053\tcount\t1\t1\tDONE\tevidence body here\tref\tKW:x\textra", False),
        ("closed without evidence", "b\tP1\titem\tW1053\tcount\t1\t1\tDONE\tshort\tr", False),
        ("kw without KW: prefix", "b\tP1\titem\tW1053\tcount\t1\t1\tDONE\tevidence body here\tref\tx|y", False),
    ]
    for name, line, want in cases:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8")
        tmp.write(line + "\n")
        tmp.close()
        got = not check_rows(read_rows(tmp.name))[0]
        os.unlink(tmp.name)
        ok += 1 if got == want else 0
        if got != want:
            print("  SELFTEST FAIL: %s (want %s got %s)" % (name, want, got))
    tmpdir = tempfile.mkdtemp()
    good = os.path.join(tmpdir, "good.md")
    bad = os.path.join(tmpdir, "bad.md")
    io.open(good, "w", encoding="utf-8").write("| a | b |\n|---|---|\n| 1 | 2 |\n")
    io.open(bad, "w", encoding="utf-8").write("| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")
    bl = os.path.join(tmpdir, "base.tsv")
    io.open(bl, "w", encoding="utf-8").write("good.md\t0\nbad.md\t1\n")
    ok += 1 if broken_tables([good]) == {} else 0
    f2 = check(quiet=True, plan=bad, baseline=bl, rows_path=P)
    ok += 1 if not any("bad.md" in x for x in f2) else 0
    io.open(bl, "w", encoding="utf-8").write("good.md\t0\nbad.md\t0\n")
    f3 = check(quiet=True, plan=bad, baseline=bl, rows_path=P)
    ok += 1 if any("bad.md" in x for x in f3) else 0
    print("LEDGER_LINT_SELF_TEST: %d/8" % ok)
    return 0 if ok == 8 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
