#!/bin/bash
B=/home/albus/strata166/gfx029-build
echo "=== engine binary mtime ==="
stat -c "%y %s %n" "$B/strata"
echo "=== objects newer than the engine binary (should be only native_mmvq) ==="
find "$B" -name "*.o" -newer "$B/strata" -printf "%TY-%Tm-%Td %TH:%TM  %10s  %p\n" 2>/dev/null | head -20
echo "=== count ==="
find "$B" -name "*.o" -newer "$B/strata" 2>/dev/null | wc -l
echo "=== the two commands ninja would run (verbatim, not hand-typed) ==="
docker run --rm --security-opt label=disable -v /home/albus/strata166/pr/strata-fork:/src -v "$B":/out strata-gfx906:0.2.9-101 \
  bash -lc 'cd /out && ninja -t commands strata 2>/dev/null | grep -n "native_mmvq.cu.o" | head -3; echo "--- link (last) ---"; ninja -t commands strata 2>/dev/null | tail -1 | cut -c1-600' 2>&1 | tail -12
