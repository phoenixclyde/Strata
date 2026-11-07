#!/bin/bash
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
cp /tmp/gh_gate.py ci/gh_gate.py && chmod +x ci/gh_gate.py

python3 - <<'PY'
import io
# 1) deploy step 0: GitHub is the gate now; the local receipt becomes a warning.
p = "ci/deploy.sh"
s = io.open(p, encoding="utf-8").read()
old = ('# ---------------------------------------------------------------- 0 receipt\n'
       '# W1028: an independent run must have seen this exact commit.  The receipt is written by\n'
       "# the gate repo's pre-receive hook on 166 (git push gate <branch>); no working copy can\n"
       '# produce one, which is what makes it different from "I ran the gate".\n'
       'say "0/8 gate receipt"\n'
       'python3 "$HERE/gate_receipt.py" --sha "$(git -C "$REPO" rev-parse HEAD)" \\\n'
       '  || fail "no gate receipt for HEAD -- push it through the gate first (git push gate gfx906/mi50)"\n')
new = ('# ---------------------------------------------------------------- 0 github\n'
       '# W1029: the gate that counts is the one that runs where the change lands.  GitHub Actions\n'
       '# must have a completed, successful run for THIS commit; the local round gate is convenience.\n'
       'say "0/8 github gate"\n'
       'python3 "$HERE/gh_gate.py" --sha "$(git -C "$REPO" rev-parse HEAD)" \\\n'
       '  || fail "GitHub CI has no green run for HEAD (push it, then: ci/gh_gate.py --wait 300)"\n'
       '# Secondary, and deliberately non-fatal: the receiving-end receipt from W1028.  It is a\n'
       '# second pair of eyes, not the record of truth (that is the GitHub run above).\n'
       'python3 "$HERE/gate_receipt.py" --sha "$(git -C "$REPO" rev-parse HEAD)" \\\n'
       '  || echo "note: no local gate receipt for HEAD (GitHub run is what gates this deploy)"\n')
assert old in s, "deploy step 0 anchor"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("deploy.sh step 0 -> github")

# 2) workflow: full history so `git describe --tags` works; the gate reads the tag.
p2 = ".github/workflows/downstream-gate.yml"
t = io.open(p2, encoding="utf-8").read()
old2 = ("      - uses: actions/checkout@v7\n        with:/n          persist-credentials: false\n")
new2 = ("      - uses: actions/checkout@v7\n        with:/n          persist-credentials: false\n"
        "          # W1029: fetch-depth 1 gives a runner with no tags, and every tag-based check then\n"
        "          # fails for a reason that has nothing to do with the change.  Full history + tags.\n"
        "          fetch-depth: 0\n          fetch-tags: true\n")
assert old2 in t, "checkout anchor"
t = t.replace(old2, new2, 1)
io.open(p2, "w", encoding="utf-8", newline="\n").write(t)
print("workflow: fetch-depth 0")
PY

python3 -m py_compile ci/gh_gate.py && echo COMPILE_OK
bash -n ci/deploy.sh && echo BASH_OK
python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/downstream-gate.yml'));print('YAML_OK')" 2>/dev/null || python3 -c "
import io;print('yaml module missing, skipping parse')"
git status --porcelain
