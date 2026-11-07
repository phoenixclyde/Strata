#!/bin/sh
# pre-receive: one independent gate run per pushed commit.
#
# Why this exists: the fork's GitHub Actions answer 422 "Actions has been disabled for this
# repository" to every dispatch (W1028), and for four rounds the only green was the one I ran
# on my own machine.  A gate that lives in the pusher's shell is not a gate.  This one lives
# in the receiving repo: each pushed commit is unpacked into a temp dir and
# `ci/round_gate.py --ci` runs *there*, so the tree that is checked is the tree that arrived,
# not the sender's working copy.
#
# A green run writes receipts/<sha>.json (+ <sha>.log).  ci/gate_receipt.py refuses a deploy
# without a matching receipt whose gate-script hashes still match, so "I ran it later" and
# "I edited the gate afterwards" are both caught.
#
# NOTE (learned the hard way, first push): receive-pack exports GIT_DIR and the quarantine
# variables, and `git -C <dir>` does NOT override them.  Without the unset below every
# `git -C $tmp ...` inside the gate silently talked to this bare repo instead of the temp
# checkout, so `git describe --tags` answered "No names found" and the gate rejected a commit
# that was actually fine.  Read the tree with an explicit --git-dir, then clear the env.
set -u
GITD=${GIT_DIR:-$(pwd)}
GATE=$(cd "$(dirname "$0")/.." && pwd)
REC="$GATE/receipts"
mkdir -p "$REC" || exit 1
rc=0
while read -r old new ref; do
  [ "$new" = "0000000000000000000000000000000000000000" ] && continue
  case "$ref" in refs/heads/*) ;; *) continue ;; esac
  tmp=$(mktemp -d)
  if ! git --git-dir="$GITD" archive "$new" | tar -x -C "$tmp"; then
    echo "GATE: cannot unpack $new" >&2
    rm -rf "$tmp"; rc=1; continue
  fi
  out=$(cd "$tmp" && env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE \
        -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES -u GIT_QUARANTINE_PATH \
        -u GIT_COMMON_DIR python3 ci/round_gate.py --ci 2>&1); grc=$?
  if [ "$grc" -ne 0 ]; then
    echo "" >&2
    echo "GATE REJECTED: $ref -> $new" >&2
    printf '%s\n' "$out" | tail -14 >&2
    rm -rf "$tmp"; rc=1; continue
  fi
  printf '%s\n' "$out" > "$REC/$new.log"
  python3 - "$REC" "$new" "$ref" "$tmp" <<'PY'
import hashlib, json, os, sys, time
rec, sha, ref, tree = sys.argv[1:5]
files = ["ci/round_gate.py", "ci/report_lint.py", "ci/bundle_budget/bundle.py",
         "ci/test_cfg_verdict.py", "ci/selftest_pin.py", "ci/repack_ab/verify.py",
         "ci/prefill_phases/phases.py"]
gates = {}
for f in files:
    p = os.path.join(tree, f)
    gates[f] = hashlib.md5(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "missing"
doc = {"sha": sha, "ref": ref, "result": "pass",
       "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "runner": os.uname().nodename, "python": sys.version.split()[0],
       "gate_files": gates}
with open(os.path.join(rec, sha + ".json"), "w") as fh:
    fh.write(json.dumps(doc, indent=1) + "\n")
print("GATE PASS: receipt written for %s" % sha[:12], file=sys.stderr)
PY
  rm -rf "$tmp"
done
exit $rc
