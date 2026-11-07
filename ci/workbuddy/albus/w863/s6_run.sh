#!/bin/bash
echo "=== cleanup stray dir from path-converted push ==="
rm -rf "/home/albus/strata166/D:" 2>/dev/null
ls -d /home/albus/strata166/D* 2>/dev/null
echo "=== model dir visible on host? ==="
ls -d /models 2>/dev/null || echo "no /models on host"
M=/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL
ls -l "$M" 2>/dev/null | head
echo "=== run enum (host) ==="
cd /home/albus/strata166/w863 && timeout 180 python3 r22_enum.py 2>&1 | head -80
