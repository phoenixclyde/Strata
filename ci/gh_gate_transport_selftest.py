#!/usr/bin/env python3
"""Negative sample for the 5th observation-layer defect: a truncated body is not a verdict.

2026-11-14: the branch-runs response is ~600 KB; on the 166 box it reproducibly raised
http.client.IncompleteRead.  Before the fix, api() let the exception escape / the caller
folded it into "no run exists" -> GH_GATE: FAIL, i.e. a socket problem was reported as a
code problem.  Required behaviour: retry, then UNCONFIRMED -- never PASS, never FAIL.

Run: python3 ci/gh_gate_transport_selftest.py
"""
import http.client
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_gate as g  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print("  %-46s %s %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


# ---- case 1: api() retries a truncated read and returns the transport marker -------------
calls = {"n": 0}


class Truncated:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        raise http.client.IncompleteRead(b"x" * 100, 600)


def fake_urlopen(req, timeout=None):
    calls["n"] += 1
    return Truncated()


g.urllib.request.urlopen = fake_urlopen
g.time.sleep = lambda s: None
st, msg = g.api("/repos/o/r/actions/workflows/w.yml/runs", "tok")
check("api() retries 3x", calls["n"] == 3, "tries=%d" % calls["n"])
check("api() returns -1, not 200", st == -1, "st=%r" % (st,))
check("api() says transport error", "transport error" in str(msg), str(msg)[:60])

# ---- case 2: ancestor_chain labels it UNCONFIRMED, not "no run" --------------------------
got, why = g.ancestor_chain("o/r", "w.yml", "deadbeef" * 5, "tok", "gfx906/mi50", ".")
check("ancestor_chain returns no verdict", got is None, repr(got))
check("ancestor_chain says UNCONFIRMED", str(why).startswith("UNCONFIRMED"), str(why)[:60])

# ---- case 3: the main() exit path maps it to 9, not 6 (FAIL) ----------------------------
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gh_gate.py"),
           encoding="utf-8").read()
check("main() has an UNCONFIRMED branch", 'GH_GATE: UNCONFIRMED' in src)
check("UNCONFIRMED exits 9 (not 6/0)", "return 9" in src)

print("TRANSPORT_SELFTEST: %d/%d" % (6 - len(fails), 6))
sys.exit(1 if fails else 0)
