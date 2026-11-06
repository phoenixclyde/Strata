#!/usr/bin/env python3
"""A deploy needs a receipt saying an independent gate run saw this exact commit.

The gate is a pre-receive hook in the 166 gate repo (`/home/albus/strata166/gate/strata-gate.git`):
it unpacks the pushed tree, runs `ci/round_gate.py --ci` there, and writes
`receipts/<sha>.json`.  Nothing in a working copy can forge one, which is the point -- the
local run has been the only run twice (W1018: evidence files not in git; W1027: Actions
disabled and nobody noticed for five pushes).

Two things this refuses:

  * no receipt for the sha          -> the commit was never pushed to the gate repo;
  * receipt but gate scripts differ -> the gate was edited after the receipt was written, so
                                       the green does not describe the gate we have now.

Usage: gate_receipt.py [--sha SHA] [--receipts DIR] [--quiet]
Exit: 0 ok, 3 no receipt, 4 stale receipt (gate changed), 5 malformed
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_RECEIPTS = "/home/albus/strata166/gate/strata-gate.git/receipts"

# The same list the hook hashes.  Keeping it in both places is deliberate: if the two ever
# disagree the mismatch surfaces here instead of as a silent "no gate ran".
GATE_FILES = ["ci/round_gate.py", "ci/report_lint.py", "ci/bundle_budget/bundle.py",
              "ci/test_cfg_verdict.py", "ci/selftest_pin.py", "ci/repack_ab/verify.py",
              "ci/prefill_phases/phases.py"]


def head(root):
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def current_hashes(root):
    out = {}
    for f in GATE_FILES:
        p = root / f
        out[f] = hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else "missing"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default=None, help="commit to check (default: repo HEAD)")
    ap.add_argument("--receipts", default=os.environ.get("STRATA_GATE_RECEIPTS", DEFAULT_RECEIPTS))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    sha = a.sha or head(ROOT)
    if not sha:
        print("GATE_RECEIPT: FAIL (no sha, not a git tree?)")
        return 5

    path = pathlib.Path(a.receipts) / (sha + ".json")
    if not path.is_file():
        print("GATE_RECEIPT: FAIL %s has no receipt in %s" % (sha[:12], a.receipts))
        print("  -> push it through the gate first:  git push gate %s" % sha[:12])
        return 3

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:                                        # noqa: BLE001
        print("GATE_RECEIPT: FAIL malformed receipt (%s)" % exc)
        return 5
    if doc.get("sha") != sha or doc.get("result") != "pass":
        print("GATE_RECEIPT: FAIL receipt does not describe a pass for %s" % sha[:12])
        return 5

    now = current_hashes(ROOT)
    was = doc.get("gate_files") or {}
    changed = sorted(k for k in GATE_FILES if was.get(k) != now[k])
    if changed:
        print("GATE_RECEIPT: FAIL stale -- gate changed after the receipt: %s" % ", ".join(changed))
        return 4

    if not a.quiet:
        print("GATE_RECEIPT: PASS %s (receipt %s, runner %s, %s)"
              % (sha[:12], doc.get("at"), doc.get("runner"), doc.get("python")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
