#!/bin/bash
# W1052/R112: build the PV-dump probe binary (strata-0.1.57-pvprobe).
# Tree at 03509d1b (production source state) + pv_dump_patch.  Probe only, never installed.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1052
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
BIN=/home/albus/strata166/data/bin
LOG=$W/build_pvprobe.log
: > "$LOG"
cd "$R" || exit 1
git checkout -f -B gfx906/pvprobe 03509d1b6895b4015f03a3aa416c962e5bf56d3d >>"$LOG" 2>&1
python3 "$W/pv_dump_patch.py" >>"$LOG" 2>&1 || { echo PATCH_FAIL; tail -5 "$LOG"; git checkout -f gfx906/hc-dp4a; exit 1; }
git add src/kernels/cuda/qsa_decode_attn.cu
git -c user.name=albus -c user.email=albus@localhost commit -q -m "probe(R112/W1052): env-gated one-shot P/V dump in attn_chunk_body for the PV-dot8 offline error budget

STRATA_PV_DUMP=<path> arms the capture; the first 16 kv_mode-3 chunk blocks write
their chunk-local probabilities sp[h][c] (what the PV loop feeds fmaf) plus the raw
Q4_0 V blocks and row map into a device ring, flushed once from launch_merge.
Production binaries never carry this: probe build strata-0.1.57-pvprobe only." >>"$LOG" 2>&1
echo "commit $(git rev-parse --short HEAD)" >>"$LOG"
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_pvprobe.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_pvprobe.log); grep -m8 "error:" /w/ninja_pvprobe.log; exit $rc' >>"$LOG" 2>&1
RC=$?
if [ "$RC" = 0 ]; then
  cp "$OUT/strata" "$BIN/strata-0.1.57-pvprobe.new" && chmod 755 "$BIN/strata-0.1.57-pvprobe.new" && mv -f "$BIN/strata-0.1.57-pvprobe.new" "$BIN/strata-0.1.57-pvprobe"
  echo "pvprobe md5 $(md5sum $BIN/strata-0.1.57-pvprobe | cut -d' ' -f1) bytes=$(stat -c%s $BIN/strata-0.1.57-pvprobe)" >>"$LOG"
  echo "strings PV_DUMP=$(strings $BIN/strata-0.1.57-pvprobe | grep -c STRATA_PV_DUMP)" >>"$LOG"
fi
echo "hc4b md5 $(md5sum $BIN/strata-0.1.57-hc4b | cut -d' ' -f1)" >>"$LOG"
git checkout -f gfx906/hc-dp4a >>"$LOG" 2>&1
cat "$LOG"
