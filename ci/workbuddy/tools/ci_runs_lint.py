#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI_RUNS lint -- the coverage table must be verifiable, not just typed.

Why this exists (AUDIT29, W1052-W1053):
  `deploy/CI_RUNS.tsv` is what `deploy_gate.py` D7 reads to answer "is this exe's
  build sha covered by a CI run?".  D7 only looks at the *status* column, so a
  mistyped run id passes silently.  AUDIT29 found exactly that: the production
  exe row (`strata-0.1.57-hc4b`, sha 03509d1b) carried run `4238161670`, which
  returns 404 -- the real run is `42378161670` (one digit dropped).  The gate
  said PASS on evidence that does not exist.

Checks (any FAIL -> rc 1):
  1 status is one of success / failure / cancelled / exempt
  2 non-exempt rows carry an 11-digit run id (GitHub run ids; a 10-digit id is
    always a typo -- this is the exact AUDIT29 failure)
  3 the key is either a 7-40 hex sha or an exe name that exists in REBUILD_RECIPE
  4 (key, ref) pairs are unique -- two rows for one sha hide which run is real
  5 --live: every non-exempt run exists upstream, its conclusion equals the
    recorded status, and its head_sha starts with the recorded sha

  python tools/ci_runs_lint.py
  python tools/ci_runs_lint.py --live
  python tools/ci_runs_lint.py --self-test
"""
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNS = os.path.join(ROOT, "deploy", "CI_RUNS.tsv")
RECIPE = os.path.join(ROOT, "deploy", "REBUILD_RECIPE.tsv")
TOKEN = os.path.join(ROOT, "deploy", "tmp", "_tok.txt")
REPO = "phoenixclyde/Strata"
STATUS = {"success", "failure", "cancelled", "exempt"}
HEX = re.compile(r"^[0-9a-f]{7,40}$")
RUNID = re.compile(r"^\d{11}$")


def rows(path=RUNS):
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if not line.strip() or line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 4:
            out.append((f[0] if f else "", "", "", "SHORT", line.strip()))
            continue
        out.append((f[0], f[1], f[2], f[3], f[4] if len(f) > 4 else ""))
    return out


def recipe_exes(path=RECIPE):
    out = set()
    if not os.path.isfile(path):
        return out
    for line in io.open(path, encoding="utf-8-sig", errors="replace"):
        if not line.strip() or line.startswith("#"):
            continue
        out.add(line.split("\t")[0])
    return out


def fetch_run(run_id, token):
    url = "https://api.github.com/repos/%s/actions/runs/%s" % (REPO, run_id)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "albus-ci-runs-lint"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def check(path=RUNS, live=False, fetch=None, quiet=False, recipe=RECIPE):
    fails = []
    rs = rows(path)
    exes = recipe_exes(recipe)
    seen = {}
    if not rs:
        fails.append("table is empty or unreadable: %s" % path)
    for key, ref, rid, status, note in rs:
        tag = "%s@%s" % (key[:9] or "?", ref or "?")
        if status not in STATUS:
            fails.append("%s: status %r not in %s" % (tag, status, sorted(STATUS)))
            continue
        if status == "exempt":
            continue
        if not RUNID.match(rid):
            fails.append("%s: run id %r is not 11 digits (typo -> 404 downstream; "
                         "D7 only reads the status column)" % (tag, rid))
        if not (HEX.match(key) or key in exes):
            fails.append("%s: key is neither a hex sha nor an exe named in REBUILD_RECIPE" % tag)
        if (key, ref) in seen:
            fails.append("%s: duplicate (key, ref) rows %s and %s" % (tag, seen[(key, ref)], rid))
        seen[(key, ref)] = rid
    live_n = 0
    if live:
        token = ""
        if os.path.isfile(TOKEN):
            token = io.open(TOKEN, encoding="utf-8").read().strip()
        if not token:
            fails.append("--live needs a GitHub token at deploy/tmp/_tok.txt")
        else:
            fetcher = fetch or (lambda i: fetch_run(i, token))
            for key, ref, rid, status, note in rs:
                if status == "exempt":
                    continue
                try:
                    d = fetcher(rid)
                except Exception as e:
                    fails.append("%s: run %s not retrievable (%s)" % (key[:9], rid, e))
                    continue
                live_n += 1
                concl = d.get("conclusion")
                sha = (d.get("head_sha") or "")
                if concl != status:
                    fails.append("%s: run %s conclusion %r != recorded %r"
                                 % (key[:9], rid, concl, status))
                if HEX.match(key) and not sha.startswith(key):
                    fails.append("%s: run %s head_sha %s does not match the recorded sha"
                                 % (key[:9], rid, sha[:9]))
    if not quiet:
        print("CI_RUNS: rows=%d live_checked=%d" % (len(rs), live_n))
        if fails:
            print("CI_RUNS_LINT: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("CI_RUNS_LINT: PASS (%d rows, %d live)" % (len(rs), live_n))
    return fails


def self_test():
    import tempfile
    ok = 0
    cases = [
        ("good row", "abcdef1234\tci/x\t42378161670\tsuccess\tok\tW1", True),
        ("10-digit id (AUDIT29 shape)", "abcdef1234\tci/x\t4238161670\tsuccess\tok\tW1", False),
        ("bad status", "abcdef1234\tci/x\t42378161670\tgreen\tok\tW1", False),
        ("duplicate pair", "abcdef1234\tci/x\t42378161670\tsuccess\tok\tW1\n"
                           "abcdef1234\tci/x\t42378161671\tsuccess\tok\tW1", False),
        ("exempt row needs no id", "deadbeef99\t(exempt)\t-\texempt\twhy\tW1", True),
        ("bogus live run", "abcdef1234\tci/x\t42378161699\tsuccess\tok\tW1", False),
    ]
    for name, body, want in cases:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8")
        tmp.write("# hdr\n" + body + "\n")
        tmp.close()
        live = name.startswith("bogus live")
        def fake(i):
            if i == "42378161670":
                return {"conclusion": "success", "head_sha": "abcdef1234ffff"}
            raise RuntimeError("HTTP 404")
        got = not check(path=tmp.name, live=live, fetch=fake, quiet=True)
        os.unlink(tmp.name)
        ok += 1 if got == want else 0
        if got != want:
            print("  SELFTEST FAIL: %s (want %s got %s)" % (name, want, got))
    print("CI_RUNS_LINT_SELF_TEST: %d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    fails = check(live="--live" in sys.argv)
    sys.exit(1 if fails else 0)
