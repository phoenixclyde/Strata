#!/bin/bash
# W1042: dump DEVICE ISA the right way.  A HIP executable/object keeps the
# device code inside a .hip_fatbin clang offload bundle; llvm-objdump on the
# host file only shows x86 and reports 0 GPU instructions (a trap we fell into
# twice in W1042).  Unbundle first, then disassemble the gfx906 code object.
set -u
LLVM=/opt/rocm/lib/llvm/bin
D=/w/isa
mkdir -p "$D"

dump() {
  F=$1; T=$2
  if ! $LLVM/llvm-objcopy --dump-section .hip_fatbin="$D/$T.bin" "$F" 2>/dev/null; then
    echo "$T: NO_FATBIN"; return 1
  fi
  TGT=$($LLVM/clang-offload-bundler -list -type=o -input="$D/$T.bin" 2>/dev/null | grep gfx906 | head -1)
  [ -n "$TGT" ] || { echo "$T: NO_GFX906_TARGET"; return 1; }
  $LLVM/clang-offload-bundler -type=o -unbundle -targets="$TGT" \
      -input="$D/$T.bin" -output="$D/$T.o" 2>/dev/null || { echo "$T: UNBUNDLE_FAIL"; return 1; }
  $LLVM/llvm-objdump -d --mcpu=gfx906 "$D/$T.o" > "$D/$T.s" 2>/dev/null
  printf "%-11s fatbin=%9s disasm=%7s " "$T" "$(stat -c%s "$D/$T.bin")" "$(wc -l < "$D/$T.s")"
  for op in v_dot4_i32_i8 v_dot8_i32_i4 v_dot2_f32_f16 v_fmac_f32; do
    printf "%s=%s " "$op" "$(grep -c "$op" "$D/$T.s")"
  done
  echo
}

dump /w/dot48_selfcheck                                                        selfcheck
dump /out/CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o   attn_tu
