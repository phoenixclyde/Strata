#!/bin/bash
# Print the metadata block (sgpr/vgpr/lds) of the J=64, fallback=false Q4_K kernel for both objects.
set -u
B=/opt/rocm/llvm/bin/clang-offload-bundler
o1=$1
o2=$2
llvm-objcopy --dump-section=.hip_fatbin=f1.bin "$o1"
llvm-objcopy --dump-section=.hip_fatbin=f2.bin "$o2"
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f1.bin -output=u1.o >/dev/null 2>&1
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f2.bin -output=u2.o >/dev/null 2>&1
echo "=== 070 (no fusion): J=64 fallback=false ==="
llvm-readelf -n u1.o | grep -A6 "Li64ELb0EL9ggml_prec30EE" | head -8
echo "=== 080 (fusion): J=64 fallback=false ==="
llvm-readelf -n u2.o | grep -A6 "Li64ELb0EL9ggml_prec30ELb0EE" | head -8
echo "=== 080 (fusion): J=64 fallback=false has_fusion=true ==="
llvm-readelf -n u2.o | grep -A6 "Li64ELb0EL9ggml_prec30ELb1EE" | head -8
