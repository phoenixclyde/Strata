#!/usr/bin/env python3
"""Wire ci/selftest_pin.py into round_gate --ci, next to the cfg verdict self-test."""
import io

P = "/home/albus/strata166/pr/strata-fork/ci/round_gate.py"
s = io.open(P, encoding="utf-8").read()

old = '''    tv = run([PY, str(HERE / "test_cfg_verdict.py")])
    if tv.returncode != 0:
        fails.append("test_cfg_verdict.py: " + (tv.stdout + tv.stderr).strip().replace("\\n", " | "))
    else:
        print("  " + tv.stdout.strip().splitlines()[-1])
'''
new = '''    tv = run([PY, str(HERE / "test_cfg_verdict.py")])
    if tv.returncode != 0:
        fails.append("test_cfg_verdict.py: " + (tv.stdout + tv.stderr).strip().replace("\\n", " | "))
    else:
        print("  " + tv.stdout.strip().splitlines()[-1])
    # W1022: release_check's fifth pointer (llama.cpp pin) -- the negative cases prove it can fail.
    # Skips itself when there is no docker daemon (GitHub runners), loudly.
    sp = run([PY, str(HERE / "selftest_pin.py")])
    if sp.returncode != 0:
        fails.append("selftest_pin.py: " + (sp.stdout + sp.stderr).strip().replace("\\n", " | "))
    else:
        print("  " + sp.stdout.strip().splitlines()[-1])
'''
assert old in s, "anchor"
io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("gate patched")
