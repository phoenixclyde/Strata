#!/bin/bash
set -euo pipefail
cd /home/albus/strata166/pr/strata-fork
cat > /tmp/m25.txt <<'MSG'
report_lint: the container table must name ROCm and llama.cpp, checked per row (W1025)

The gate was whole-text: mentioning "llama.cpp" anywhere in the prose satisfied it, which is
exactly how the two dependency versions stayed out of the 10-field table while the report
passed.  Two new fields, both LINE-level and scoped to section 一:

  F9  ROCm        one row with ROCm + a version + HIP/hipconfig/.info/version
  F10 llama.cpp   one row with llama.cpp + bNNNNN + the full 40-hex sha

Why per row: this box carries three different ROCm numbers (packaged 10.1.0, build id
7.14.0-gfx906+…, HIP runtime 7.16.26323), so a whole-text match would accept any of them;
and a 7-char llama.cpp prefix cannot be verified against anything.

report_lint is now 14 checks.  Measured: before adding the rows the same report fails with
"表内 0 行", after adding them PASS (14 fields).  round_gate's positive sample carries the two
rows so its self-test stays honest.
MSG
git add ci/report_lint.py ci/round_gate.py
git -c user.name=albus -c user.email=a@b commit -q -F /tmp/m25.txt
git tag -a mi50-0.2.11-r33-9 -m "report gate: F9 ROCm / F10 llama.cpp as per-row fields" HEAD
git push -q origin gfx906/mi50 mi50-0.2.11-r33-9
git describe --tags; git log --oneline -1; git status --porcelain | wc -l
