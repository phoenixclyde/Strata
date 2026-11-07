import io
R = "/home/albus/strata166/pr/strata-fork/"

# 1) release_check gains --offline: rows that need the live box become SKIP instead of FAIL
p = R + "ci/release_check.py"
s = io.open(p, encoding="utf-8").read()
old = '    ap.add_argument("--json", action="store_true")\n'
new = ('    ap.add_argument("--json", action="store_true")\n'
       '    ap.add_argument("--offline", action="store_true",\n'
       '                    help="skip the rows that need the live box (container, image, binary); "\n'
       '                         "the tag / pin / build rows are still judged")\n')
assert old in s, "arg anchor"
s = s.replace(old, new, 1)

old2 = '''    def add(name, value, ok, note=""):
        rows.append({"field": name, "value": value, "ok": ok, "note": note})
        if not ok:
            fails.append(name)
'''
new2 = '''    # Rows that can only be judged where the engine actually runs.  On a GitHub runner there is
    # no container and no /data/bin, and the run used to die on `docker inspect` with
    # "no such object: strata166-407" -- a host fact scored as a release failure.  --offline turns
    # those into SKIP, which is what a static run can honestly say about them.
    OFFLINE_ROWS = {"container image", "BUILD-IMAGE.json", "binary", "engine versions agree",
                    "llama.cpp tree (image)"}

    def add(name, value, ok, note=""):
        if a.offline and name in OFFLINE_ROWS:
            rows.append({"field": name, "value": "SKIP (needs the live box)",
                         "ok": True, "note": "not checkable on a runner"})
            return
        rows.append({"field": name, "value": value, "ok": ok, "note": note})
        if not ok:
            fails.append(name)
'''
assert old2 in s, "add anchor"
s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("release_check: --offline")

# 2) the pin self-test judges pin rows only, so it runs offline
p2 = R + "ci/selftest_pin.py"
t = io.open(p2, encoding="utf-8").read()
old3 = 'r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp)'
new3 = ('# --offline: the fixture has no container, and a host fact is not a pin fact.\n'
        '    r = sh(sys.executable, RC, "--repo", tmp, "--build", tmp, "--offline")')
assert old3 in t, "run anchor"
io.open(p2, "w", encoding="utf-8", newline="\n").write(t.replace(old3, new3, 1))
print("selftest_pin: --offline")
