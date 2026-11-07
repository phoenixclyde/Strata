#!/bin/bash
set -u
B=~/strata166/gfx029-build
OBJ=$(find $B -name "mmq-instance-q4_k.cu.o" 2>/dev/null | head -1)
echo "obj: $OBJ"
[ -z "$OBJ" ] && { echo "NOT FOUND"; exit 1; }

echo
echo "=== 反汇编（device code）==="
docker run --rm -v $OBJ:/tmp/q4k.o -w /tmp strata-gfx906:0.2.9-101 bash -lc '
  llvm-objdump -d q4k.o > d.txt 2>/dev/null
  echo "总指令行: $(grep -cE "^\s+[0-9a-f]+:" d.txt)"
  echo "内核数(s_endpgm): $(grep -c s_endpgm d.txt)"
  echo
  echo "=== 按类别计数 ==="
  for p in v_dot4_i32_i8 v_lshrrev_b32 v_lshlrev_b32 v_and_b32 v_perm_b32 v_cvt_f32_f16 v_cvt_f16_f32 v_mul_f32 v_fma_f32 v_mac_f32 v_add_f32 v_pk_mul_f32 v_pk_add_f32 v_pk_fma_f32 ds_read_b128 ds_read_b64 ds_read_b32 s_load_dwordx4 s_load_dwordx2 s_load_dword global_load_dwordx4 global_load_dword v_mul_lo_u32 v_mul_hi_u32 v_bfe_u32 s_bfe_u32; do
    c=$(grep -c "\b$p\b" d.txt)
    [ "$c" -gt 0 ] && printf "%-20s %6d\n" "$p" "$c"
  done
' 2>&1
