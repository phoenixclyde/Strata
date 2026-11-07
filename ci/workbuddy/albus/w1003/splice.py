import sys
block = open("/tmp/verify_sweep_block.py").read()
p = "/home/albus/strata166/pr/strata-fork/ci/repack_ab/verify.py"
s = open(p).read()
anchor = 'if FAILS:\n    print("VERIFY: FAIL (%d)" % len(FAILS))'
if anchor not in s:
    sys.exit("anchor not found; head=%r" % s[-400:])
s = s.replace(anchor, block + anchor, 1)
old = "VERIFY: PASS (5 groups: artifacts, results, fair-AB markers, port status, CI wiring)"
new = "VERIFY: PASS (6 groups: artifacts, results, fair-AB markers, port status, CI wiring, width/type sweep)"
s = s.replace(old, new)
open(p, "w").write(s)
print("spliced")
