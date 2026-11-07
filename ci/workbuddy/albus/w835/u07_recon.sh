#!/bin/bash
# W835: KI's RECON for Qwen3.8-Flash-QSA -- ISA facts and kernel timings
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. RECON-qwen38-flash-qsa.md : ISA facts ==="
git show FETCH_HEAD:docs/gfx906/RECON-qwen38-flash-qsa.md 2>/dev/null | grep -nE "v_dot|dot2|dot4|bf16|fp16|LDS|ds_|dpp|wave|GEMV|t/s|us/|ms/" | head -45
echo
echo "=== B. RECON head ==="
git show FETCH_HEAD:docs/gfx906/RECON-qwen38-flash-qsa.md 2>/dev/null | head -32
echo
echo "=== C. the bf16-emulation claim (patch 0001 summary) ==="
git show FETCH_HEAD:docs/gfx906/qsa-tester-build/HANDOVER.md 2>/dev/null | head -40
