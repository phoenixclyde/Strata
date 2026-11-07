#!/bin/bash
# W1039: prove pa3 is reproducible and free of stale objects from the old llama tree.
# Copy the build dir, wipe every object, rebuild, compare md5 with the incremental result.
set -u
S=/home/albus/strata166
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
R=$S/build-pa3r
LOG=$S/tmp/w1039/repro.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

log "indelible md5: $(md5sum $S/build-pa3/strata | cut -d' ' -f1)"
if [ -d "$R" ]; then mv "$R" "$R.prev.$(date +%H%M%S)"; fi
cp -a "$S/build-pa3" "$R" || { log "FAIL copy"; exit 1; }
log "copied $(du -sh "$R" | cut -f1); cleaning objects"

docker run --rm -v "$SRC":/src -v "$R":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -t clean > /dev/null 2>&1; echo CLEAN=$?; ninja -j 12 > /tmp/r.log 2>&1; echo BLD=$?; echo "FAILED=$(grep -c "^FAILED" /tmp/r.log)"; md5sum /out/strata; stat -c%s /out/strata' 2>&1 | tee -a "$LOG"

a=$(md5sum "$S/build-pa3/strata" | cut -d' ' -f1)
b=$(md5sum "$R/strata" | cut -d' ' -f1)
if [ "$a" = "$b" ]; then log "REPRO-DUP: identical ($a)"; else log "REPRO-DIFF: $a vs $b"; fi
