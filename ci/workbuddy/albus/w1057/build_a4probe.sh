#!/bin/bash
# W1057/R74: build the int4-activation-sim probe binary (strata-0.1.57-a4probe).
# Source = production state 03509d1b (same base as hc4b) + the a4sim patch on the
# build-masterp overlay quantize.cu (the copy the build actually compiles).
# Probe only, never installed to production. Overlay restored + md5-verified after build.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1057
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
BIN=/home/albus/strata166/data/bin
Q=$OUT/ggml-tq-overlay/quantize.cu
LOG=$W/build_a4probe.log
mkdir -p "$W"
: > "$LOG"
cp -f "$Q" "$W/quantize.cu.orig"
echo "orig md5 $(md5sum "$Q" | cut -d' ' -f1)" >>"$LOG"
cd "$R" || exit 1
git checkout -f -B gfx906/a4probe 03509d1b6895b4015f03a3aa416c962e5bf56d3d >>"$LOG" 2>&1
echo "src base $(git rev-parse --short HEAD)" >>"$LOG"
python3 "$W/a4sim_patch.py" "$Q" >>"$LOG" 2>&1 || { echo PATCH_FAIL; tail -8 "$LOG"; cp -f "$W/quantize.cu.orig" "$Q"; git checkout -f ci/w1047-coverage; exit 1; }
echo "patched md5 $(md5sum "$Q" | cut -d' ' -f1)" >>"$LOG"
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_a4probe.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_a4probe.log); grep -m8 "error:" /w/ninja_a4probe.log; exit $rc' >>"$LOG" 2>&1
RC=$?
if [ "$RC" = 0 ]; then
  cp "$OUT/strata" "$BIN/strata-0.1.57-a4probe.new" && chmod 755 "$BIN/strata-0.1.57-a4probe.new" && mv -f "$BIN/strata-0.1.57-a4probe.new" "$BIN/strata-0.1.57-a4probe"
  echo "a4probe md5 $(md5sum $BIN/strata-0.1.57-a4probe | cut -d' ' -f1) bytes=$(stat -c%s $BIN/strata-0.1.57-a4probe)" >>"$LOG"
  echo "strings A4_SIM=$(strings $BIN/strata-0.1.57-a4probe | grep -c STRATA_A4_SIM)" >>"$LOG"
fi
cp -f "$W/quantize.cu.orig" "$Q"
echo "overlay restored: $(md5sum "$Q" | cut -c1-8) vs orig $(md5sum "$W/quantize.cu.orig" | cut -c1-8)" >>"$LOG"
git -C "$R" checkout -f ci/w1047-coverage >>"$LOG" 2>&1
echo "worktree back $(git -C "$R" branch --show-current)" >>"$LOG"
echo "hc4b md5 $(md5sum $BIN/strata-0.1.57-hc4b | cut -d' ' -f1)" >>"$LOG"
cat "$LOG"
