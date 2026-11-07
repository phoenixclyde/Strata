#!/usr/bin/env python3
"""Negative self-test for the W1002 gates. Run ON 166, inside the fork root.

Each case injects a realistic breakage, asserts the gate FAILS, restores the
original bytes, and asserts the gate is green again. A gate that never fails
is worse than no gate (W980's exact failure mode).
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/albus/strata166/pr/strata-fork")
PY = sys.executable


def run(*args):
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True).returncode


def case(name, path, mutate, gate):
    p = ROOT / path
    orig = p.read_bytes()
    try:
        p.write_bytes(mutate(orig))
        broken = run(*gate)
        ok = broken != 0
    finally:
        p.write_bytes(orig)
    restored = run(*gate)
    print("  %-34s broken_rc=%-2d restored_rc=%-2d %s"
          % (name, broken, restored, "PASS" if ok and restored == 0 else "FAIL"))
    return ok and restored == 0


GATE_V = ("ci/repack_ab/verify.py",)
GATE_R = ("ci/round_gate.py", "--ci")

cases = [
    ("ratio falsified in RESULTS.tsv", "ci/repack_ab/RESULTS.tsv",
     lambda b: b.replace(b"\t0.659\t", b"\t9.999\t"), GATE_V),
    ("PORT_STATUS.md emptied", "ci/repack_ab/PORT_STATUS.md",
     lambda b: b"empty\n", GATE_V),
    ("fair-AB marker removed", "ci/repack_ab/ab_bench.cu",
     lambda b: b.replace(b"mmq::quantize", b"mmq_disabled"), GATE_V),
    ("workflow no longer calls verify", ".github/workflows/downstream-gate.yml",
     lambda b: b.replace(b"python3 ci/repack_ab/verify.py", b"echo skipped"), GATE_V),
    ("report_lint always passes", "ci/report_lint.py",
     lambda b: b"import sys; sys.exit(0)\n", GATE_R),
]

results = [case(*c) for c in cases]
print("NEGATIVE_TEST: %s (%d/%d)" % ("PASS" if all(results) else "FAIL",
                                     sum(results), len(results)))
sys.exit(0 if all(results) else 1)
