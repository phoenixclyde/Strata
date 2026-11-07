#!/bin/bash
set -u
S=/home/albus/strata166
IMG=strata-gfx906:0.2.11-101
docker run --rm -v "$S/tmp/w1041":/w -w /w "$IMG" sh -c '
/opt/rocm/lib/llvm/bin/llvm-objdump -d --mcpu=gfx906 t_fdot2.o 2>&1 | head -40
echo "---- any v_dot / fma ----"
/opt/rocm/lib/llvm/bin/llvm-objdump -d --mcpu=gfx906 t_fdot2.o 2>/dev/null | grep -oE "v_[a-z0-9_]+" | sort | uniq -c | sort -rn | head -12
'
