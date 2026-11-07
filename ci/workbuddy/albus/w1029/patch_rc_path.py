import io
p = "/home/albus/strata166/pr/strata-fork/ci/selftest_pin.py"
s = io.open(p, encoding="utf-8").read()
old = 'RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"'
new = ('# Relative to THIS file, never the work repo: the absolute path made every CI run fail with\n'
       '# rc=2 "cannot open file" (runs #42-#44, 9-11 s each), which the test then reported as\n'
       '# "[BAD] baseline ... rc=2" -- a path bug wearing a pin bug clothes.\n'
       'RC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "release_check.py")')
assert old in s, "RC anchor"
s = s.replace(old, new, 1)
old2 = 'def run(tmp):\n    r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp)'
new2 = ('def run(tmp):\n'
        '    if not os.path.isfile(RC):\n'
        '        raise SystemExit("selftest_pin: release_check.py not found next to this file (%s)" % RC)\n'
        '    r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp)')
assert old2 in s, "run anchor"
s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
