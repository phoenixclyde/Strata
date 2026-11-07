#!/bin/bash
# W1039/P457: .hip_fatbin is a clang offload *bundle*, not an ELF.  Unbundle to the gfx906 code object first.
set -u
OBJ=/out/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o
LLVM=/opt/rocm/lib/llvm/bin
W=/w
B=$LLVM/clang-offload-bundler

echo "=== bundle contents ==="
$B -list -type=o -input=$W/fat.bin 2>&1 | head -6

echo "=== unbundle gfx906 ==="
$B -type=o -unbundle -targets=hipv4-amdgcn-amd-amdhsa--gfx906 -input=$W/fat.bin -output=$W/code906.o 2>&1 | head -4
if [ ! -s $W/code906.o ]; then
  # fall back: try every target the bundle lists
  for t in $($B -list -type=o -input=$W/fat.bin 2>/dev/null); do
    echo "  try $t"; $B -type=o -unbundle -targets=$t -input=$W/fat.bin -output=$W/code906.o 2>/dev/null && break
  done
fi
ls -l $W/code906.o 2>&1

echo "=== disassemble ==="
$LLVM/llvm-objdump -d --mcpu=gfx906 $W/code906.o > $W/code906.s 2>$W/code906.err
echo "rc=$? lines=$(wc -l < $W/code906.s)"
head -2 $W/code906.err

echo "=== instantiations ==="
grep -o 'attn_chunk_kernelILi3ELb[01]ELb[01]ELb[01]ELi[0-9]*E' $W/code906.s | sort | uniq -c
