#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci/plan_retired.py -- numbers that were retired must not come back as current facts.

Why (W1006): the same figure lives in three places in the plan (the definition row, the
priority table, the execution-order table).  W1005 corrected the definition row and left the
other two quoting 1.91x/1.87x/3.9x/14x as if they were measured today.  A human re-reading the
plan cannot tell which of the three is current, and the next round quotes whichever it hits
first -- that is exactly how a number survives five rounds.

So: a retired figure may appear only struck through (~~...~~), which reads as history.  Anywhere
else in a *fact table* (a row that starts with an id or a rank) it fails.

  python3 ci/plan_retired.py            # check
  python3 ci/plan_retired.py --self-test
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "..", "deploy", "W832_OPT_PLAN_V2.md")

RETIRED = [
    ("1.91×", "W1005: 2K/16K gate/up is 1.57x"),
    ("1.87×", "W1005: down is 1.52x"),
    ("dequant 3.9×", "W1005: dequant is 161 ms per chunk, not per token"),
    ("wait copy 14×", "W1005: wait copy is 37 ms"),
    ("双 3090 +17%", "W1006: #22174 measured +9.67% by *disabling* stream-k"),
    ("DGX Spark +17.2%", "AUDIT28: PR #31188 DOES have a benchmark (2911.4->3410.8); retired because CUDA/MoE-fusion path is N/A on gfx906, NOT because the number is unverifiable"),
]

# A "fact table" row: it asserts a current value.  Narrative blocks (correction records) are
# exempt -- they have to be able to name the retired figure to explain it.
FACT_ROW = re.compile(r"^\|\s*(\*\*新\d+\*\*|\*\*R\d+[a-z]?\*\*|\d+)\s*\|")
STRIKE = re.compile(r"~~[^~]*~~")


def check(path=PLAN, quiet=False):
    fails = []
    for i, line in enumerate(io.open(path, encoding="utf-8"), 1):
        if not FACT_ROW.match(line):
            continue
        bare = STRIKE.sub("", line)
        for tok, why in RETIRED:
            if tok in bare:
                fails.append("line %d: '%s' is retired (%s)" % (i, tok, why))
    if not quiet:
        if fails:
            print("PLAN_RETIRED: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("PLAN_RETIRED: PASS (%d retired figures, none quoted as current)" % len(RETIRED))
    return fails


def self_test():
    """Negative tests: put each retired figure back into a fact row, expect a failure."""
    src = io.open(PLAN, encoding="utf-8").read()
    ok = 0
    cases = [
        ("| 5 | R95 小批 GEMM | 2K 的 gate/up 1.91×； |", "1.91×"),
        ("| 1 | **R95** | down 1.87× |", "1.87×"),
        ("| **新30** | **R95** | dequant 3.9× |", "dequant 3.9×"),
        ("| 2 | R95 | wait copy 14× |", "wait copy 14×"),
    ]
    import tempfile
    for row, tok in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8",
                                         delete=False, newline="\n") as f:
            f.write(src + "\n" + row + "\n")
            p = f.name
        fails = check(p, quiet=True)
        os.unlink(p)
        if any(tok in x for x in fails):
            ok += 1
        else:
            print("  self-test MISS: %s was not caught" % tok)
    # and the struck-through form must pass
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False, newline="\n") as f:
        f.write(src + "\n| 5 | R95 | ~~1.91×~~ → 1.57× |\n")
        p = f.name
    if not check(p, quiet=True):
        ok += 1
    else:
        print("  self-test MISS: a struck-through figure was flagged")
    os.unlink(p)
    print("SELF_TEST: %d/%d" % (ok, len(cases) + 1))
    return 0 if ok == len(cases) + 1 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if check() else 0)
