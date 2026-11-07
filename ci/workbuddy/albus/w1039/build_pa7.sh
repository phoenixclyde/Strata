#!/bin/bash
set -u
S=/home/albus/strata166
IMG=strata-gfx906:0.2.11-101
B=$S/build-pa3
LOG=$S/tmp/w1039/build_pa7.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

log "=== build pa7 ==="
docker run --rm -v "$S/pr/port-all":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo BLD=$?; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m10 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' 2>&1 | tee -a "$LOG"

log "=== stage as pa7 ==="
if [ -f "$B/strata" ]; then
  cp -f "$B/strata" "$S/data/bin/strata-0.1.57-pa7.new" && chmod 755 "$S/data/bin/strata-0.1.57-pa7.new" \
    && mv -f "$S/data/bin/strata-0.1.57-pa7.new" "$S/data/bin/strata-0.1.57-pa7"
  md5sum "$S/data/bin/strata-0.1.57-pa7" | tee -a "$LOG"
fi
log DONE
