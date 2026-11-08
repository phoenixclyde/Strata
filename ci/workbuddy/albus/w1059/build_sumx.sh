#!/bin/bash
# W1059/R101: build the Sigma-x revert probe (strata-0.1.57-sumx).
# Base = production state 03509d1b (same base as hc4b) + the sumx patch on the overlay
# quantize.cu. Probe only, never installed to production. Overlay restored + md5-verified.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1059
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
BIN=/home/albus/strata166/data/bin
Q=$OUT/ggml-tq-overlay/quantize.cu
LOG=$W/build_sumx.log
mkdir -p "$W"
: > "$LOG"
cp -f "$Q" "$W/quantize.cu.orig"
echo "orig md5 $(md5sum "$Q" | cut -d' ' -f1)" >>"$LOG"
cd "$R" || exit 1
git checkout -f -B gfx906/sumxprobe 03509d1b6895b4015f03a3aa416c962e5bf56d3d >>"$LOG" 2>&1
echo "src base $(git rev-parse --short HEAD)" >>"$LOG"
# PASS 1: let CMake reconfigure settle. The overlay under /out/ggml-tq-overlay is written AT
# CONFIGURE TIME (cmake/strata_ggml_tq_overlay.cmake) -- a checkout triggers "Re-running CMake"
# which REGENERATES the overlay and silently wipes any patch applied before it (W1059 实测).
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_pass1.log 2>&1; echo PASS1_BLD=$?; echo PASS1_FAILED=$(grep -c "^FAILED" /w/ninja_pass1.log)' >>"$LOG" 2>&1
# PASS 2: patch the now-settled overlay, rebuild (no reconfigure expected), assert the marker landed.
python3 "$W/sumx_patch.py" "$Q" >>"$LOG" 2>&1 || { echo PATCH_FAIL; tail -8 "$LOG"; cp -f "$W/quantize.cu.orig" "$Q"; git checkout -f ci/w1047-coverage; exit 1; }
echo "patched md5 $(md5sum "$Q" | cut -d' ' -f1)" >>"$LOG"
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_sumx.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_sumx.log); echo RECONF=$(grep -c "Re-running CMake" /w/ninja_sumx.log); grep -m8 "error:" /w/ninja_sumx.log; exit $rc' >>"$LOG" 2>&1
RC=$?
if [ "$RC" = 0 ]; then
  cp "$OUT/strata" "$BIN/strata-0.1.57-sumx.new" && chmod 755 "$BIN/strata-0.1.57-sumx.new" && mv -f "$BIN/strata-0.1.57-sumx.new" "$BIN/strata-0.1.57-sumx"
  echo "sumx md5 $(md5sum $BIN/strata-0.1.57-sumx | cut -d' ' -f1) bytes=$(stat -c%s $BIN/strata-0.1.57-sumx)" >>"$LOG"
  MARK=$(strings $BIN/strata-0.1.57-sumx | grep -c STRATA_SUMX)
  echo "strings SUMX=$MARK" >>"$LOG"
  if [ "$MARK" -lt 1 ]; then echo "PATCH_NOT_IN_BINARY" >>"$LOG"; RC=9; fi
fi
cp -f "$W/quantize.cu.orig" "$Q"
echo "overlay restored: $(md5sum "$Q" | cut -c1-8) vs orig $(md5sum "$W/quantize.cu.orig" | cut -c1-8)" >>"$LOG"
git -C "$R" checkout -f ci/w1047-coverage >>"$LOG" 2>&1
echo "worktree back $(git -C "$R" branch --show-current)" >>"$LOG"
echo "hc4b md5 $(md5sum $BIN/strata-0.1.57-hc4b | cut -d' ' -f1)" >>"$LOG"
cat "$LOG"
