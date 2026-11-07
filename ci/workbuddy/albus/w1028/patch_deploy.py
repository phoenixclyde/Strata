import io
p = "/home/albus/strata166/pr/strata-fork/ci/deploy.sh"
s = io.open(p, encoding="utf-8").read()
anchor = "# ---------------------------------------------------------------- 1 gate\n"
add = ("# ---------------------------------------------------------------- 0 receipt\n"
       "# W1028: an independent run must have seen this exact commit.  The receipt is written by\n"
       "# the gate repo's pre-receive hook on 166 (git push gate <branch>); no working copy can\n"
       "# produce one, which is what makes it different from \"I ran the gate\".\n"
       "say \"0/8 gate receipt\"\n"
       "python3 \"$HERE/gate_receipt.py\" --sha \"$(git -C \"$REPO\" rev-parse HEAD)\" \\\n"
       "  || fail \"no gate receipt for HEAD -- push it through the gate first (git push gate gfx906/mi50)\"\n"
       "\n")
assert anchor in s and "gate_receipt.py" not in s
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(anchor, add + anchor, 1))
print("deploy.sh step 0 added")

q = "/home/albus/strata166/pr/strata-fork/deploy/W838_REMOTE_POLICY.md"
t = io.open(q, encoding="utf-8").read()
note = """
## Push order since W1028 (the gate repo is the enforcement point)

GitHub Actions on this fork answer `422 Actions has been disabled for this repository` to every
dispatch, so the only independent gate is local.  That gate now sits in a bare repo on 166 and
runs on the tree that actually arrives:

```
git push gate gfx906/mi50     # pre-receive runs ci/round_gate.py --ci; rejected = nothing lands
git push origin gfx906/mi50   # mirror to GitHub (the forge of record, not the gate)
```

A green run writes `receipts/<sha>.json` with the md5 of every gate script; `ci/deploy.sh` step 0
refuses a deploy whose HEAD has no receipt, or whose receipt predates a gate edit.
`git push --no-verify` skips the client hooks but **not** the receiving end -- proven by pushing a
deliberately broken BUNDLE.tsv: `! [remote rejected] (pre-receive hook declined)`.
"""
if "the gate repo is the enforcement point" not in t:
    t = t.rstrip("\n") + "\n" + note
io.open(q, "w", encoding="utf-8", newline="\n").write(t)
print("W838 updated")
