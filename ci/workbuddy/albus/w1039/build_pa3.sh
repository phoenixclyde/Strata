#!/bin/bash
# W1039: rebuild port-all against the b12180 llama tree -> pa3.
# Recipe: same build dir flags as pa2 (copied from build-port2), only /llama.cpp swapped to llama-master
# (that is the tree b12180 was built from: mmq.cuh = 627c4c62).  Requires the W1037 overlay-probe fix,
# which pr/port-all did not have.
set -u
S=/home/albus/strata166
PB=$S/pr/port-all
B=$S/build-pa3
M=$S/tmp/w1039/llama-master
IMG=strata-gfx906:0.2.11-101
LOG=$S/tmp/w1039/build_pa3.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

log "=== 0. preconditions ==="
[ -d "$PB" ] || { log "FAIL no port-all"; exit 1; }
[ -f "$S/tmp/w1037/llama-master/ggml/src/ggml-cuda/mmq.cuh" ] || { log "FAIL no llama-master"; exit 1; }
md5sum "$S/tmp/w1037/llama-master/ggml/src/ggml-cuda/mmq.cuh" | cut -c1-12
df -h /home/albus | tail -1

log "=== 1. port the W1037 overlay-probe fix into port-all ==="
cp -f "$S/pr/k10/cmake/strata_ggml_tq_overlay.cmake" "$PB/cmake/strata_ggml_tq_overlay.cmake" || exit 1
md5sum "$PB/cmake/strata_ggml_tq_overlay.cmake" | cut -c1-12
grep -c "write_back_mma<type, J, fallback, prec_src1, " "$PB/cmake/strata_ggml_tq_overlay.cmake"

log "=== 2. commit the two pending changes ==="
cd "$PB" || exit 1
git add cmake/strata_ggml_tq_overlay.cmake
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: probe the write-back's own signature for the TQ overlay (W1037 fix)

The overlay inferred the 5th template argument of ggml_cuda_mmq_write_back_mma
from ggml_cuda_mmq_get_nthreads' signature.  Upstream b12110 dropped that
argument, so configuring against any tree after it produced
"no matching constructor for ggml_cuda_mmq_util_funcs".  Probe the write-back's
signature directly instead.
MSG
git add src/kernels/cuda/qsa_decode_attn.cu
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: wire the ATTN_* switches into the prefill dispatch (W1037)

Prefill attention goes qsa_decode_attn_batch -> launch_chunks_batch ->
attn_chunk_kernel<M>, which had no OPT parameter: the DP4A/DPP/LDS switches
only reached qsa_decode_attn_batch_rows and _slots.  With all four switches on,
the measured `qsa attn` phase did not move (578.3 -> 577.3 ms at 2.5K), which is
what dead code looks like.  Dispatch to the OPT instantiation here too.
MSG
git log --oneline -3

log "=== 3. copy the pa2 build dir (same flags) ==="
if [ -d "$B" ]; then mv "$B" "$B.prev.$(date +%H%M%S)"; fi
cp -a "$S/build-port2" "$B" || { log "FAIL copy build dir"; exit 1; }
log "copied; size=$(du -sh "$B" | cut -f1)"

log "=== 4. configure against llama-master ==="
docker run --rm -v "$PB":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'cmake -S /src -B /out -DSTRATA_MMQ_TQ_OVERLAY=ON > /tmp/c.log 2>&1; echo CFG=$?; grep -i "trellis\|overlay" /tmp/c.log | head -5' 2>&1 | tee -a "$LOG"

log "=== 5. build ==="
docker run --rm -v "$PB":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo BLD=$?; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; ls -l /out/strata' 2>&1 | tee -a "$LOG"

log "=== 6. switches in the binary ==="
for v in STRATA_GFX906_ATTN_DP4A STRATA_GFX906_ATTN_DPP STRATA_GFX906_ATTN_LDS_PAD STRATA_GFX906_ROUTE_DPP STRATA_GFX906_Q8_GATHER8; do
  printf "%s=%s " "${v#STRATA_GFX906_}" "$(strings "$B/strata" | grep -c "$v")"
done
echo | tee -a "$LOG"
log "DONE"
