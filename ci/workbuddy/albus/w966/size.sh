#!/bin/bash
# Per-kernel code size (symbol size) for the J=64 Q4_K MMQ kernel, both builds.
set -u
B=/opt/rocm/llvm/bin/clang-offload-bundler
o1=$1
o2=$2
llvm-objcopy --dump-section=.hip_fatbin=f1.bin "$o1"
llvm-objcopy --dump-section=.hip_fatbin=f2.bin "$o2"
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f1.bin -output=u1.o >/dev/null 2>&1
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f2.bin -output=u2.o >/dev/null 2>&1
for u in u1.o u2.o; do
  echo "== $u"
  llvm-readelf -s "$u" | grep -E "FUNC" | grep "mul_mat_qIL9ggml_type12ELi64ELb0" | awk '{print $3, $8}'
  echo "-- total .text:"
  llvm-readelf -S "$u" | grep -E "\.text" | head -2
done
