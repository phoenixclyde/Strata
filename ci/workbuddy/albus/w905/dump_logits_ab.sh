#!/bin/bash
# W905: is our "rounding-level recipe" buying speed with accuracy?
# Dumps logits for the SAME 128 tokens twice, changing only STRATA_GFX906_TUNED
# (the 7-switch bundle the engine's own startup banner calls "rounding-level").
# Everything else - pack, weights, kv format, expert cache, rocBLAS table - is identical.
set -u
BIN=/data/bin/strata-0.1.55t
NATIVE=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
COMMON="--pack /data/packs/ud-q4_k_xl --native $NATIVE --expert-profile /src/data/expert-profile.bin --expert-cache auto --pcie-frac 0.20 \
--max-context 32768 --prefill 8192 --spec 4 --vram-reserve-mib 832 --tokens-file /work/tokens.txt --max-new 1"

BASEENV="HSA_OVERRIDE_GFX_VERSION=9.0.6 STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt \
STRATA_CKPT_MOVE_PARK=1 STRATA_PREFILL_CPU_SHARE=auto STRATA_PREFILL_CPU_SHARE_MAX=3072 \
STRATA_RESIDENT_HEADROOM_GIB=0.5"

mkdir -p /data/tmp
rm -f /data/tmp/logits_a.txt /data/tmp/logits_b.txt

echo "===== A: STRATA_GFX906_TUNED=1 (production recipe) ====="
t0=$SECONDS
env $BASEENV STRATA_GFX906_TUNED=1 \
  $BIN $COMMON --kv k8v4 --dump-logits /data/tmp/logits_a.txt > /work/a.log 2>&1
rc=$?
echo "rc=$rc wall=$((SECONDS-t0))s lines=$(wc -l < /data/tmp/logits_a.txt 2>/dev/null || echo 0)"
tail -3 /work/a.log | cut -c1-160

echo "===== B: STRATA_GFX906_TUNED=0 (bundle off, same everything else) ====="
t0=$SECONDS
env $BASEENV STRATA_GFX906_TUNED=0 \
  $BIN $COMMON --kv k8v4 --dump-logits /data/tmp/logits_b.txt > /work/b.log 2>&1
rc=$?
echo "rc=$rc wall=$((SECONDS-t0))s lines=$(wc -l < /data/tmp/logits_b.txt 2>/dev/null || echo 0)"
tail -3 /work/b.log | cut -c1-160

echo "===== sizes ====="
ls -l /data/tmp/logits_a.txt /data/tmp/logits_b.txt 2>/dev/null | awk '{print $5, $9}'
echo "done"
