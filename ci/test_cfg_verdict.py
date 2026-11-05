#!/usr/bin/env python3
"""test_cfg_verdict -- the cfg_apply verdict arithmetic, without a GPU.

Why this exists: on 2026-11-05 23:52 the A/B of `STRATA_GR_V3=1` (W1013) crashed inside
cfg_apply *after* it had installed the candidate config and restarted the engine:

    UnboundLocalError: cannot access local variable 'better'

`better` was bound only inside the per-length loop, so any run where no prompt length moved
past its 2x-CV band -- i.e. every no-op or marginal change, which is most of them -- died
there, leaving an unvetted config live with no record and no rollback.  The bug was invisible
to the shell because the invocation was piped into `tail` (the pipeline's status is tail's).

So the arithmetic is now a pure function and these tests pin the cases the loop used to miss.
No engine, no config, no GPU: `python3 ci/test_cfg_verdict.py`.
"""
import importlib.util
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("cfg_apply", str(HERE / "cfg_apply.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["cfg_apply"] = m
    spec.loader.exec_module(m)
    return m


def st(median, cv):
    return {"n": 3, "median": median, "cv_pct": cv}


def case(name, base, dec, tt, extra, want_worse, want_better, want_lines):
    ok = True
    try:
        worse, better, lines = M.compare_arms(base, dec, tt, extra)
    except BaseException as e:                      # the 2026-11-05 failure, kept as a test
        print("  FAIL %-38s raised %r" % (name, e))
        return 0
    if (worse, better) != (want_worse, want_better):
        print("  FAIL %-38s got (worse=%s, better=%s), want (%s, %s)"
              % (name, worse, better, want_worse, want_better))
        ok = False
    elif want_lines is not None and len(lines) != want_lines:
        print("  FAIL %-38s %d report lines, want %d" % (name, len(lines), want_lines))
        ok = False
    else:
        print("  ok   %-38s (worse=%s, better=%s, %d lines)" % (name, worse, better, len(lines)))
    return 1 if ok else 0


M = load()
BASE = {"decode": st(35.8, 5.5), "ttft": st(4096.0, 0.55),
        "prefill": {"2000": st(513.65, 0.39), "8000": st(684.62, 0.15)}}

ok = 0
# 1. the crash case: --lengths given, nothing moves past its band
ok += case("no length moves (the 23:52 crash)",
           BASE, st(35.8, 5.5), st(4096.0, 0.55),
           {2000: st(514.09, 0.18), 8000: st(684.99, 0.53)},
           False, False, 3)
# 2. no --lengths at all: the loop body never runs, `better` must still exist
ok += case("no lengths measured at all",
           BASE, st(35.8, 5.5), st(4096.0, 0.55), {}, False, False, 1)
# 3. prefill_at() returns prompt tok/s, so LOWER is a regression.  Getting this sign wrong is the
#    other way this arithmetic fails silently: a 2% prompt win would be recorded as a rollback.
ok += case("prefill@2000 down 2.0% tok/s (band 1.0%)",
           BASE, st(35.8, 5.5), st(4096.0, 0.55),
           {2000: st(503.4, 0.5)}, True, False, 2)
# 4. ... and higher is an improvement
ok += case("prefill@8000 up 1.5% tok/s (band 0.6%)",
           BASE, st(35.8, 5.5), st(4096.0, 0.55),
           {8000: st(694.9, 0.3)}, False, True, 2)
# 5. decode alone carries the verdict (a decode-side change)
ok += case("decode +12% (band 11%)", BASE, st(40.1, 5.5), st(4096.0, 0.55), {}, False, True, 1)
# 6. a length the baseline never recorded must be skipped, not crash
ok += case("a length the baseline lacks",
           BASE, st(35.8, 5.5), st(4096.0, 0.55),
           {16000: st(767.0, 0.02)}, False, False, 1)
# 7. worse wins over better: a mixed result must roll back
ok += case("one length down, one up", BASE, st(35.8, 5.5), st(4096.0, 0.55),
           {2000: st(503.4, 0.5), 8000: st(694.9, 0.3)}, True, True, 3)

print("SELF_TEST: %d/7" % ok)
sys.exit(0 if ok == 7 else 1)
