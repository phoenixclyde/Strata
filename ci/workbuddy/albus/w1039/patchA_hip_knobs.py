#!/usr/bin/env python3
"""W1039 / R105 patch A: un-gate three OPT-IN HIP knobs on gfx906.

Nothing here changes a default: every block is entered only through an explicit env var, and each has its own
"gfx12 only" default test inside.  What the patch buys is the ability to *try* them on this card:

  core/mtp.cpp:486        STRATA_MTP_HIP_PRIO=1     the draft stream gets a high-priority hardware queue
  core/verify.cpp:1213    STRATA_COPY_HIP_PRIO=1    the copy stream likewise
  program/generate.cpp    STRATA_HIP_QUEUE_PRIME=nn open two HW queues in a fixed order at start-up
  3078 (body) / 3371 (call)

The condition has to be an OR, not just "drop !GFX906": this tree's gfx906 TUs get -DSTRATA_HIP_GFX906=1 but
NOT -DSTRATA_USE_HIP (build.ninja), so `#if defined(STRATA_USE_HIP)` alone is false and nothing compiles (P473).
"""
import io
import sys

OLD = "#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)"
NEW = "#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)"

targets = [
    ("/home/albus/strata166/pr/k10/src/core/mtp.cpp", 1),
    ("/home/albus/strata166/pr/k10/src/core/verify.cpp", 1),
    ("/home/albus/strata166/pr/k10/src/program/generate.cpp", 2),
]
for path, expect in targets:
    s = io.open(path, encoding="utf-8").read()
    n = s.count(OLD)
    if n != expect:
        print("COUNT MISMATCH %s: %d (expected %d)" % (path, n, expect))
        sys.exit(1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s.replace(OLD, NEW))
    print("patched %-58s %d site(s)" % (path.split("/src/")[-1], n))

# verify: no old form left in those files, and the unrelated "NOT HIP AND NOT GFX906" guards untouched
for path, _ in targets:
    t = io.open(path, encoding="utf-8").read()
    assert OLD not in t, path
    assert "!defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)" in t or path.endswith("generate.cpp"), path
print("VERIFY: old form gone; the NOT-HIP guards still exclude gfx906 as before")
