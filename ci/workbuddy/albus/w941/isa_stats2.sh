#!/bin/bash
# W942 / R63: instruction census of one kernel window (objdump puts the mnemonic first after a tab).
set -u
F=/tmp/co/co_011_off5943296.elf
START=0x47400
SIZE=$((0x5a7c))
END=$(printf '0x%x' $((START + SIZE)))
echo "kernel window: $START..$END  ($SIZE bytes)"
llvm-objdump -d --no-show-raw-insn --start-address=$START --stop-address=$END "$F" > /tmp/k.asm 2>/dev/null
awk -F'\t' 'NF>1 { split($2, f, " "); if (f[1] ~ /^[a-z][a-z0-9_]*$/) print f[1] }' /tmp/k.asm > /tmp/mn.txt
echo "instructions: $(wc -l < /tmp/mn.txt)"
echo "== top 25 =="
sort /tmp/mn.txt | uniq -c | sort -rn | head -25
echo "== key =="
for m in v_dot4_i32_i8 v_fmac_f32 v_mul_lo_u32 v_lshlrev_b32 v_lshlrev_b64 v_lshrrev_b32 v_and_b32 v_or_b32 v_xor_b32 v_add_u32 v_sub_u32 v_cndmask_b32 v_cvt_f32_i32 v_mov_b32 s_load_dword ds_read_b128 ds_read_b64 ds_write_b32 global_load_dword s_cbranch_scc0 s_waitcnt; do
  printf "%-16s %s\n" "$m" "$(grep -cx "$m" /tmp/mn.txt)"
done
