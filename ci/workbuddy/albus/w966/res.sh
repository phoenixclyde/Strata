#!/bin/bash
# Compare per-kernel resources (sgpr/vgpr/lds) of the Q4_K MMQ instances: 0.7.0 (no fusion) vs 0.8.0 (fusion).
set -u
B=/opt/rocm/llvm/bin/clang-offload-bundler
o1=$1
o2=$2
for pair in "$o1" u1.o "$o2" u2.o; do :; done
llvm-objcopy --dump-section=.hip_fatbin=f1.bin "$o1"
llvm-objcopy --dump-section=.hip_fatbin=f2.bin "$o2"
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f1.bin -output=u1.o >/dev/null 2>&1
$B -unbundle -type=o -targets=hip-amdgcn-amd-amdhsa--gfx906 -input=f2.bin -output=u2.o >/dev/null 2>&1

report() {
  local f=$1 tag=$2
  llvm-readelf -n "$f" | awk -v tag="$tag" '
    /\.name:/      { nm=$0; sub(/.*_ZL9mul_mat_qI/,"",nm); sub(/EEv.*/,"",nm) }
    /\.sgpr_count:/{ s=$2 }
    /\.vgpr_count:/{ v=$2 }
    /group_segment_fixed_size/ {
      if (nm != "") printf "%s %-46s sgpr=%-3s vgpr=%-3s lds=%s\n", tag, nm, s, v, $2;
      nm=""
    }'
}

echo "===== J=64 / fallback=false (the one pick_J selects) ====="
report u1.o "070"
report u2.o "080"
echo
echo "===== all J for fallback=false ====="
report u1.o "070" | grep -E "Li(8|16|32|64|96|128)ELb0EL9ggml_prec30EE"
report u2.o "080" | grep -E "Li(8|16|32|64|96|128)ELb0EL9ggml_prec30ELb0EE"
