#!/bin/bash
# W1045: count gfx906 dot instructions PER TU (the only correct sampling surface).
#
# !!! W1045 INCIDENT -- READ BEFORE EDITING !!!
# `llvm-objcopy --dump-section .hip_fatbin=X FILE` with NO output argument
# REWRITES FILE IN PLACE (removes that section). On 18:20 this damaged the
# LIVE /data/bin/strata-0.1.57-attn (43,452,008 -> 43,425,632 B) and 6 build
# .o files. Same root cause as the W940 accident. Two hard rules below:
#   1. NEVER point this at /data/bin/*; always copy to a scratch path first.
#   2. ALWAYS give llvm-objcopy an explicit output file (even /dev/null).
# Mounts of /data/bin into a container MUST be :ro.
set -u
LLVM=/opt/rocm/lib/llvm/bin
D=/w/isa
B=/out/CMakeFiles
mkdir -p "$D"
OPS="v_dot4_i32_i8 v_dot8_i32_i4 v_dot2_f32_f16 v_mad_i32_i24 v_mul_lo_i32 v_fmac_f32 ds_bpermute_b32 v_mov_b32_dpp"

dump() {
  F=$1; T=$2
  [ -f "$F" ] || { printf "%-16s MISSING\n" "$T"; return; }
  case "$F" in
    */data/bin/*|/data/bin/*) printf "%-16s REFUSE: live binary\n" "$T"; return ;;
  esac
  cp -f "$F" "$D/$T.copy.o" || { printf "%-16s COPY_FAIL\n" "$T"; return; }
  # explicit output path -> the INPUT IS NEVER MODIFIED
  $LLVM/llvm-objcopy --dump-section .hip_fatbin="$D/$T.bin" \
      "$D/$T.copy.o" "$D/$T.stripped.o" 2>/dev/null \
    || { printf "%-16s NO_FATBIN\n" "$T"; return; }
  TGT=$($LLVM/clang-offload-bundler -list -type=o -input="$D/$T.bin" 2>/dev/null | grep gfx906 | head -1)
  [ -n "$TGT" ] || { printf "%-16s NO_GFX906\n" "$T"; return; }
  $LLVM/clang-offload-bundler -type=o -unbundle -targets="$TGT" \
    -input="$D/$T.bin" -output="$D/$T.o" 2>/dev/null || { printf "%-16s UNBUNDLE_FAIL\n" "$T"; return; }
  $LLVM/llvm-objdump -d --mcpu=gfx906 "$D/$T.o" > "$D/$T.s" 2>/dev/null
  printf "%-16s lines=%-7s " "$T" "$(wc -l < "$D/$T.s")"
  for op in $OPS; do printf "%s=%s " "$op" "$(grep -c "$op" "$D/$T.s")"; done
  echo
}

dump "$B/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o" attn
dump "$B/strata_kernels.dir/src/kernels/cuda/qsa_pattn.cu.o"       pattn
dump "$B/strata_kernels.dir/src/kernels/cuda/iq_kernels.cu.o"       iq
dump "$B/strata_kernels.dir/src/kernels/cuda/native_mmvq.cu.o"      mmvq
dump "$B/strata_kernels.dir/src/kernels/cuda/fused_gr.cu.o"         fused_gr
dump "$B/strata_kernels.dir/src/kernels/cuda/kv_q8.cu.o"            kv_q8
dump "$B/strata_mmq.dir/src/prefill/moe_mmq.cu.o"                    moe_mmq
echo "--- done ---"
