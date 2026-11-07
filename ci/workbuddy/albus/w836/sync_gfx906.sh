#!/bin/bash
# sync_gfx906.sh -- make the build tree carry exactly what our branch says.
#
#   source of truth : /home/albus/strata166/gfx906   (git, branch gfx906/0.2.8-mi50)
#   build tree      : /home/albus/strata166/src028   (has build-028r/ and third_party/, not a repo)
#
# Usage:
#   ./sync_gfx906.sh            # pull, then sync the patched files into src028 and gate
#   ./sync_gfx906.sh --check    # no writes: only report drift
#
# Why only these files: they are the ones our branch changes. Everything else in
# src028 must stay byte-identical to the branch's base, or the build is not what
# we shipped.
set -u
SRC=/home/albus/strata166/gfx906
DST=/home/albus/strata166/src028
GATE=/home/albus/strata166/tmp/verify_patches.sh
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

FILES="src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js include/strata/platform/hip_compat/strata_hip.h include/strata/kernels/gfx_arch.hpp include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp"

PATCHERS='apply_w839_generate.py:src/program/generate.cpp'
PATCHDIR=/home/albus/strata166/patches

say() { echo "[$(date +%H:%M:%S)] $*"; }

say "=== 1. branch state ==="
git -C "$SRC" fetch origin gfx906/0.2.8-mi50 2>&1 | tail -2
git -C "$SRC" log -1 --format='  %h %ad %s' --date=short origin/gfx906/0.2.8-mi50 2>/dev/null

if [ "$CHECK" -eq 0 ]; then
  say "=== 2. fast-forward the working copy ==="
  git -C "$SRC" checkout gfx906/0.2.8-mi50 2>&1 | tail -1
  git -C "$SRC" reset --hard origin/gfx906/0.2.8-mi50 2>&1 | tail -1
fi

say "=== 3. drift between branch and build tree ==="
# CMakeLists.txt is deliberately NOT synced as a file: the branch carries upstream main's copy plus our
# hunks, while src028 carries v0.2.8's plus the same hunks.  Copying it would drag upstream's later
# changes into the build tree.  Check the patch markers instead.
cm_ok=1
for m in W793 "W776 local"; do
  n=$(grep -c "$m" "$DST/CMakeLists.txt" 2>/dev/null || echo 0)
  [ "$n" -ge 1 ] && printf "  marker %-12s present in src028\n" "$m" || { printf "  marker %-12s MISSING in src028\n" "$m"; cm_ok=0; }
done
[ "$cm_ok" -eq 1 ] || drift_note="CMakeLists.txt markers missing"
drift=0
for f in $FILES; do
  a=$(md5sum "$SRC/$f" 2>/dev/null | cut -d' ' -f1)
  b=$(md5sum "$DST/$f" 2>/dev/null | cut -d' ' -f1)
  if [ "$a" = "$b" ]; then
    printf "  same   %s\n" "$f"
  else
    printf "  DIFF   %s  branch=%s src028=%s\n" "$f" "${a:0:8}" "${b:0:8}"
    drift=$((drift+1))
    if [ "$CHECK" -eq 0 ]; then
      cp -a "$SRC/$f" "$DST/$f" && printf "         -> copied into src028\n"
    fi
  fi
done
say "files with drift: $drift"

say "=== 3b. anchor patchers (files whose upstream copy differs between the two bases) ==="
# Those files cannot be copied: the branch holds upstream main's copy, the build tree holds v0.2.8's, and
# copying would put main's engine into a v0.2.8 build.  They are patched by an anchor script instead.
pdrift=0
for spec in $PATCHERS; do
  f=${spec#*:}
  p=$PATCHDIR/${spec%%:*}
  if [ "$CHECK" -eq 1 ]; then
    n=$(grep -c -F "W839 local" "$DST/$f" 2>/dev/null || echo 0)
    [ "$n" -ge 1 ] && printf "  applied %s\n" "$f" || { printf "  MISSING %s\n" "$f"; pdrift=$((pdrift+1)); }
  else
    if [ ! -f "$p" ]; then printf "  patcher missing: %s\n" "$p"; pdrift=$((pdrift+1)); continue; fi
    python3 "$p" "$DST/$f" && printf "  ok %s\n" "$f" || { printf "  FAILED %s\n" "$f"; pdrift=$((pdrift+1)); }
  fi
done
say "patchers with drift: $pdrift"
drift=$((drift+pdrift))

if [ "$CHECK" -eq 1 ]; then
  say "(--check: nothing written)"
  exit $([ "$drift" -eq 0 ] && echo 0 || echo 2)
fi

say "=== 4. patch gate ==="
if [ -f "$GATE" ]; then
  bash "$GATE" 2>&1 | tail -20
else
  say "  gate script missing: $GATE"
fi

say "=== 5. next step for a rebuild ==="
cat <<'EOF'
  cmake --build /home/albus/strata166/src028/build-028r -j   # ~40 min
  then deploy: cp build-028r/strata /data/bin/strata-<ver>  (keep the old one)
  then run:    bash /home/albus/strata166/tmp/verify_patches.sh
EOF
