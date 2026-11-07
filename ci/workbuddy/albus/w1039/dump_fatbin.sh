#!/bin/bash
# W1039/P457: dump the device code out of the object and split it per kernel instantiation.
# Runs *inside* the image (whole command is a file, so nothing gets eaten by an outer shell).
set -u
OBJ=/out/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o
LLVM=/opt/rocm/lib/llvm/bin
W=/w

$LLVM/llvm-objcopy --dump-section .hip_fatbin=$W/fat.bin "$OBJ" || { echo "objcopy failed"; exit 1; }
echo "fatbin: $(stat -c%s $W/fat.bin) bytes"

$LLVM/llvm-objdump -d --mcpu=gfx906 $W/fat.bin > $W/fat.s 2> $W/fat.err
echo "objdump rc=$?  lines=$(wc -l < $W/fat.s)"
head -3 $W/fat.err

echo "=== kernel symbols in the dump ==="
grep -o 'attn_chunk_kernel<[^>]*>' $W/fat.s | sort | uniq -c | head -20
echo "=== total occurrences ==="
grep -c attn_chunk_kernel $W/fat.s
