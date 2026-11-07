# -*- coding: utf-8 -*-
"""[W863] Narrow the two push-triggered workflows to long-lived branches, add concurrency.

Why (all three are the usual recommendations for a downstream fork):
  * default-deny branches: gfx906/* experiments and release tags must not spend runner
    minutes -- and a tag run re-tests code that is already tested.  `ci/**` stays open so
    an experiment can still ask for CI on purpose.
  * concurrency + cancel-in-progress: three pushes in a row used to queue three 9-minute
    suites; the first one in this round waited 50 minutes for a runner.
  * paths stay as upstream wrote them -- this patch only touches the trigger, so a rebase
    onto a new upstream version is a 4-line conflict at worst.

Run on 166; edits pr/strata-fork/.github/workflows/, keeps .w863bak copies.
"""
import os
import shutil

BASE = "/home/albus/strata166/pr/strata-fork/.github/workflows"
FILES = ["terminal-minimal-server.yml", "terminal-portable-monitor.yml"]

SUBS = [
    ("  push:\n    paths:\n",
     "  push:\n    branches: [main, gfx906/mi50, 'ci/**']\n    paths:\n"),
    ("  pull_request:\n    paths:\n",
     "  pull_request:\n    branches: [main]\n    paths:\n"),
    ("permissions:\n  contents: read\n",
     "concurrency:\n"
     "  group: ${{ github.workflow }}-${{ github.ref }}\n"
     "  cancel-in-progress: true\n\n"
     "permissions:\n  contents: read\n"),
]

for name in FILES:
    p = os.path.join(BASE, name)
    src = open(p, encoding="utf-8").read()
    if "branches: [main, gfx906/mi50" in src:
        print("ALREADY PATCHED:", name)
        continue
    bak = p + ".w863bak"
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    for old, new in SUBS:
        if src.count(old) != 1:
            print("ABORT %s: anchor %r found %d times" % (name, old[:24], src.count(old)))
            raise SystemExit(2)
        src = src.replace(old, new, 1)
    open(p, "w", encoding="utf-8").write(src)
    print("patched:", name)

print("\n--- new trigger block ---")
for name in FILES:
    src = open(os.path.join(BASE, name), encoding="utf-8").read().splitlines()
    print("##", name)
    for i, line in enumerate(src[:34], 1):
        print("%3d %s" % (i, line))
        if line.startswith("permissions:"):
            break
    print()
