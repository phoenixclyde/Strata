#!/bin/bash
# W1060/R60: build the stream-k probe (strata-0.1.57-strk).
# Base = production state 03509d1b (same base as hc4b) + 11 Q4_K rows stream_k=false->true
# in mmq-config-gcn.cuh. The effective file for the mmq-instance TUs is the llama-master
# copy (relative include ../mmq.cuh -> sibling config, W1058 include trap); the overlay
# copy is kept in sync. Two-pass ninja (W1059 CMake-reconfigure trap). Restored after.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1060
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
L=/home/albus/strata166/tmp/w1037/llama-master
BIN=/home/albus/strata166/data/bin
V=$L/ggml/src/ggml-cuda/mmq-config-gcn.cuh
VO=$OUT/ggml-tq-overlay/mmq-config-gcn.cuh
OBJ=CMakeFiles/strata_mmq.dir/llama.cpp/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o
LOG=$W/build_strk.log
mkdir -p "$W"
: > "$LOG"
cp -f "$V" "$W/gcn.cuh.orig"
cp -f "$VO" "$W/gcn.overlay.orig"
OBJ0=$(md5sum "$OUT/$OBJ" | cut -d' ' -f1)
echo "orig md5 L=$(md5sum "$V" | cut -c1-8) overlay=$(md5sum "$VO" | cut -c1-8) obj0=$OBJ0" >>"$LOG"
cd "$R" || exit 1
git checkout -f -B gfx906/strkprobe 03509d1b6895b4015f03a3aa416c962e5bf56d3d >>"$LOG" 2>&1
echo "src base $(git rev-parse --short HEAD)" >>"$LOG"
# PASS 1: let CMake reconfigure settle (checkout changes /src globs; overlay is rewritten at
# configure time from the pinned tree -- our patch lives in the pinned tree so it SURVIVES).
docker run --rm -v "$R":/src -v "$OUT":/out -v "$L":/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_pass1.log 2>&1; echo PASS1_BLD=$?; echo PASS1_FAILED=$(grep -c "^FAILED" /w/ninja_pass1.log)' >>"$LOG" 2>&1
# PATCH both copies, then PASS 2
python3 "$W/strk_patch.py" "$V" "$VO" >>"$LOG" 2>&1 || { echo PATCH_FAIL; cp -f "$W/gcn.cuh.orig" "$V"; cp -f "$W/gcn.overlay.orig" "$VO" 2>/dev/null || true; git checkout -f ci/w1047-coverage; exit 1; }
echo "patched md5 L=$(md5sum "$V" | cut -c1-8) overlay=$(md5sum "$VO" | cut -c1-8)" >>"$LOG"
docker run --rm -v "$R":/src -v "$OUT":/out -v "$L":/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_strk.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_strk.log); echo RECONF=$(grep -c "Re-running CMake" /w/ninja_strk.log); grep -m6 "error:" /w/ninja_strk.log; exit $rc' >>"$LOG" 2>&1
RC=$?
if [ "$RC" = 0 ]; then
  cp "$OUT/strata" "$BIN/strata-0.1.57-strk.new" && chmod 755 "$BIN/strata-0.1.57-strk.new" && mv -f "$BIN/strata-0.1.57-strk.new" "$BIN/strata-0.1.57-strk"
  echo "strk md5 $(md5sum $BIN/strata-0.1.57-strk | cut -d' ' -f1) bytes=$(stat -c%s $BIN/strata-0.1.57-strk)" >>"$LOG"
  OBJ1=$(md5sum "$OUT/$OBJ" | cut -d' ' -f1)
  echo "obj1=$OBJ1 obj_changed=$([ "$OBJ0" != "$OBJ1" ] && echo YES || echo NO)" >>"$LOG"
  [ "$OBJ0" != "$OBJ1" ] || { echo "OBJ_UNCHANGED"; RC=9; }
fi
cp -f "$W/gcn.cuh.orig" "$V"
cp -f "$W/gcn.overlay.orig" "$VO" 2>/dev/null || echo "overlay restore skipped (root-owned, untouched)"
echo "restored L=$(md5sum "$V" | cut -c1-8) overlay=$(md5sum "$VO" | cut -c1-8)" >>"$LOG"
git -C "$R" checkout -f ci/w1047-coverage >>"$LOG" 2>&1
echo "worktree back $(git -C "$R" branch --show-current)" >>"$LOG"
cat "$LOG"
