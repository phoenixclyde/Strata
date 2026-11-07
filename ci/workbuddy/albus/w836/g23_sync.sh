#!/bin/bash
# W836: bring the 166 working copy up to the pushed head, and check the configure run
W=/home/albus/strata166/gfx906
echo "=== A. update working copy to the pushed head ==="
cd $W || exit 1
timeout 300 git fetch origin gfx906/0.2.8-mi50 2>&1 | tail -3
git reset --hard origin/gfx906/0.2.8-mi50 2>&1 | tail -2
git log -1 --format='  %h %ad %s' --date=short
echo "  files: $(git ls-files | wc -l)"
echo
echo "=== B. configure result (bg run) ==="
L=/home/albus/strata166/data/w836_cfg2.out
if [ -s "$L" ]; then
  grep -E "CMAKE_RC|DONE" "$L" | head -4
  echo "--- rocBLAS ---"; sed -n '/ROCBLAS_FOUND/,/W776_COUNT/p' "$L" | head -10
  echo "--- W776 count in build.ninja ---"; sed -n '/W776_COUNT/,/CONFIGURE_TAIL/p' "$L" | head -3
  echo "--- tail ---"; tail -4 "$L"
else
  echo "  still running / no output yet"; tail -3 "$L" 2>/dev/null
  ls -la /home/albus/strata166/gfx906-b2/build.ninja 2>/dev/null || echo "  no build.ninja yet"
fi
echo
echo "=== C. drift between branch and build tree, for the 7 patched files ==="
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js include/strata/platform/hip_compat/strata_hip.h; do
  a=$(md5sum "$W/$f" 2>/dev/null | cut -d' ' -f1); b=$(md5sum "/home/albus/strata166/src028/$f" 2>/dev/null | cut -d' ' -f1)
  [ "$a" = "$b" ] && printf "  same  %s\n" "$f" || printf "  DIFF  %s\n" "$f"
done
