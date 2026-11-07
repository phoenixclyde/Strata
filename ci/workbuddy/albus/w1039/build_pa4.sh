#!/bin/bash
set -u
S=/home/albus/strata166
IMG=strata-gfx906:0.2.11-101
B=$S/build-pa3
LOG=$S/tmp/w1039/build_pa4.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

log "=== build pa4 (incremental) ==="
docker run --rm -v "$S/pr/port-all":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo BLD=$?; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' 2>&1 | tee -a "$LOG"

log "=== switches ==="
for v in STRATA_GFX906_ATTN_DP4A STRATA_GFX906_ATTN_DPP STRATA_GFX906_ATTN_LDS_PAD STRATA_GFX906_ROUTE_DPP STRATA_GFX906_Q8_GATHER8; do
  printf "%s=%s " "${v#STRATA_GFX906_}" "$(strings "$B/strata" | grep -c "$v")" | tee -a "$LOG"
done
echo | tee -a "$LOG"

log "=== stage as pa4 ==="
cp -f "$B/strata" "$S/data/bin/strata-0.1.57-pa4.new" && chmod 755 "$S/data/bin/strata-0.1.57-pa4.new" \
  && mv -f "$S/data/bin/strata-0.1.57-pa4.new" "$S/data/bin/strata-0.1.57-pa4"
md5sum "$S/data/bin/strata-0.1.57-pa4" | tee -a "$LOG"
log DONE
