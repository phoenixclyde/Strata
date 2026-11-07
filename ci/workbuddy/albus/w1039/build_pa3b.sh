#!/bin/bash
# W1039 step 2: commit the API adaptation, then rebuild pa3.
set -u
S=/home/albus/strata166
PB=$S/pr/port-all
B=$S/build-pa3
IMG=strata-gfx906:0.2.11-101
LOG=$S/tmp/w1039/build_pa3b.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

cd "$PB" || exit 1
git add -A src/prefill/moe_mmq.cu src/prefill/mmq_kq_lib.cu src/prefill/mmq_nvfp4_w4a4.cu src/prefill/mmq_nvfp4_w4a8.cu src/prefill/ggml_cuda_host.cu
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: follow the b12110 API delta (mul_mat_q_case prec, get_config prec, new_pool_for_device ctx)

Needed to build this tree against llama.cpp b12180: upstream #30168 turned
mul_mat_q_case into <type, ggml_prec> and added the precision argument to
ggml_cuda_mmq_get_config; b12110 also gave new_pool_for_device a context
parameter.  26 call sites + 5 + 1, no behaviour change (the precision argument
is GGML_PREC_Q8, which is what this tree compiled to before the split).
MSG
git log --oneline -1

log "=== configure ==="
docker run --rm -v "$PB":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'cmake -S /src -B /out -DSTRATA_MMQ_TQ_OVERLAY=ON > /tmp/c.log 2>&1; echo CFG=$?; grep -i "trellis\|overlay" /tmp/c.log | head -3' 2>&1 | tee -a "$LOG"

log "=== build ==="
docker run --rm -v "$PB":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo BLD=$?; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m10 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' 2>&1 | tee -a "$LOG"

log "=== switches ==="
for v in STRATA_GFX906_ATTN_DP4A STRATA_GFX906_ATTN_DPP STRATA_GFX906_ATTN_LDS_PAD STRATA_GFX906_ROUTE_DPP STRATA_GFX906_Q8_GATHER8; do
  printf "%s=%s " "${v#STRATA_GFX906_}" "$(strings "$B/strata" | grep -c "$v")" | tee -a "$LOG"
done
echo | tee -a "$LOG"
log "DONE"
