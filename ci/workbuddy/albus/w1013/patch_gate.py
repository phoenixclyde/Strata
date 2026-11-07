import io

P = "/home/albus/strata166/pr/strata-fork/ci/round_gate.py"
s = io.open(P, encoding="utf-8").read()

anchor = '''    for payload, expect, label in ((GOOD, True, "positive"), (BAD, False, "negative")):'''
assert anchor in s and "bundle_budget" not in s

new = '''    # W1013: the bundle budget (the 5% gate, applied to a sum instead of to single items) and the
    # cfg_apply verdict arithmetic (it crashed once after installing a candidate; see the test's docstring).
    bu = run([PY, str(HERE / "bundle_budget" / "bundle.py")])
    if bu.returncode != 0:
        fails.append("bundle.py: " + (bu.stdout + bu.stderr).strip().replace("\\n", " | "))
    else:
        print("  " + bu.stdout.strip().splitlines()[-1])
    tv = run([PY, str(HERE / "test_cfg_verdict.py")])
    if tv.returncode != 0:
        fails.append("test_cfg_verdict.py: " + (tv.stdout + tv.stderr).strip().replace("\\n", " | "))
    else:
        print("  " + tv.stdout.strip().splitlines()[-1])
''' + anchor

io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(anchor, new, 1))
print("round_gate patched")
