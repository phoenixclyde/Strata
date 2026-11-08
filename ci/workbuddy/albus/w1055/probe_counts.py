#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''set -u
OUT=/home/albus/strata166/build-masterp/CMakeFiles/strata_kernels.dir/src/kernels/cuda
W=/home/albus/strata166/tmp/w1055
IMG=strata-gfx906:0.2.11-101
{
for o in $OUT/*.cu.o; do
  tu=$(basename "$o" .cu.o)
  docker run --rm -v "$OUT":/out "$IMG" bash -lc '
    O=/out/'"$tu"'.cu.o
    llvm-objcopy --dump-section .hip_fatbin=/tmp/fat.bin $O 2>/dev/null
    clang-offload-bundler --type=o --unbundle --inputs=/tmp/fat.bin --outputs=/tmp/c906.o --targets=hip-amdgcn-amd-amdhsa--gfx906 2>/dev/null
    llvm-objdump -d --no-show-raw-insn /tmp/c906.o 2>/dev/null > /tmp/dis.txt
    m=$(grep -c "deadbeef" /tmp/dis.txt)
    u=$(grep -c "mad_u32_u24" /tmp/dis.txt)
    d=$(grep -c "dot4_i32_i8" /tmp/dis.txt)
    echo "$tu  marker=$m  mad_u32u24=$u  dot4=$d"
  '
done
} > "$W/probe_counts.txt" 2>&1
grep "marker" "$W/probe_counts.txt" | sort
echo "=== any marker >0? list kernels ==="
grep -l "deadbeef" "$W"/*.txt 2>/dev/null
'''
rc, out, err = _sshutil.run_remote(S, timeout=900)
open(r"D:/workbuddy_space/strata_ws/albus/w1055/probe_counts.txt", "w", encoding="utf-8").write(out)
print(out[-2000:])
