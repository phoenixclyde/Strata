#!/bin/bash
# W942 / R63: instruction census of one kernel window.
set -u
F=/tmp/co/co_011_off5943296.elf
START=0x47400
SIZE=$((0x5a7c))
END=$(printf '0x%x' $((START + SIZE)))
echo "kernel window: $START..$END  ($SIZE bytes)"
llvm-objdump -d --no-show-raw-insn --start-address=$START --stop-address=$END "$F" > /tmp/k.asm 2>/dev/null
echo "asm lines: $(wc -l < /tmp/k.asm)"
echo "== mnemonic histogram (top 30) =="
grep -oE '^[[:space:]]+[0-9a-f]+:[[:space:]]+[a-z][a-z0-9_]*' /tmp/k.asm \
  | awk '{print $2}' | sort | uniq -c | sort -rn | head -30
echo "== key counters =="
for m in v_dot4_i32_i8 v_dot2_f32_f16 v_fmac_f32 v_mul_lo_u32 v_mul_f32 v_lshlrev v_lshrrev v_and v_or v_xor v_add v_sub v_cndmask v_mov v_cvt s_load ds_read ds_write global_load s_cbranch s_waitcnt; do
  n=$(grep -cE "^[[:space:]]+[0-9a-f]+:[[:space:]]+$m" /tmp/k.asm)
  echo "$m $n"
done
echo "== total instructions =="
grep -cE '^[[:space:]]+[0-9a-f]+:[[:space:]]+[a-z]' /tmp/k.asm
