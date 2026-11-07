#!/usr/bin/env python3
"""Run the deterministic gate self-tests from the WorkBuddy bundle.

This is what GitHub's static runner can execute without GPU, 166, or live
production files. Each case must be a true negative-capable self-test.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
CASES = [
    ("tools/report_lint.py", "--self-test"),
    ("tools/deploy_gate.py", "--self-test"),
    ("tools/binary_integrity.py", "--self-test"),
    ("tools/handoff_check.py", "--self-test"),
    ("tools/claim_homes.py", "--self-test"),
    ("tools/plan_single_source.py", "--self-test"),
    ("tools/plan_retired.py", "--self-test"),
    ("tools/audit_scope.py", "--self-test"),
    ("tools/audit_outputs.py", "--self-test"),
    ("tools/audit_index.py", "--self-test"),
    ("tools/pointer_lint.py", "--self-test"),
    ("tools/round_ledger.py", "--self-test"),
    ("albus/w1043/judge.py", "--self-test"),
    ("albus/w1043/longctx_needle.py", "--self-test"),
]


def main() -> int:
    failures = []
    for rel, flag in CASES:
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"{rel}: missing")
            continue
        r = subprocess.run([sys.executable, str(path), flag], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
        print(f"{rel:42s} rc={r.returncode} {tail}")
        if r.returncode != 0:
            failures.append(f"{rel}: {tail}")
    if failures:
        print(f"WORKBUDDY_SELFTEST: FAIL ({len(failures)})")
        for f in failures:
            print("  -", f)
        return 1
    print(f"WORKBUDDY_SELFTEST: PASS ({len(CASES)}/{len(CASES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
