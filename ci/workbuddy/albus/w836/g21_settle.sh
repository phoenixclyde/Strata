#!/bin/bash
# W836: settle the one missing patch (W830-COMPAT) and sample-verify the other diffs are upstream progress
W=/home/albus/strata166/gfx906
S=/home/albus/strata166/src028
echo "=== A. W830-COMPAT: strata_hip.h, src028 vs branch ==="
diff -u "$W/include/strata/platform/hip_compat/strata_hip.h" "$S/include/strata/platform/hip_compat/strata_hip.h" 2>/dev/null | head -40
echo
echo "=== B. does src028's copy carry the stream-priority macros? ==="
grep -nE "StreamCreateWithPriority|StreamGetPriority|stream priority" "$S/include/strata/platform/hip_compat/strata_hip.h" 2>/dev/null | head -6
echo
echo "=== C. sample: is src/core/verify.cpp newer on the branch? (upstream progress test) ==="
diff -u "$S/src/core/verify.cpp" "$W/src/core/verify.cpp" 2>/dev/null | head -14
echo
echo "=== D. sample: dsv41 (we never touched it) -- what changed ==="
diff -u "$S/src/dsv41/ds4_model.cu" "$W/src/dsv41/ds4_model.cu" 2>/dev/null | head -14
