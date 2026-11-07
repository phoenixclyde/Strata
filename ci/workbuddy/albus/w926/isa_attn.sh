#!/bin/bash
set -u
B=~/strata166/gfx029-build
OBJ=$(find $B -name "qsa_prompt_attn.cu.o" 2>/dev/null | head -1)
echo "obj: $OBJ"
[ -z "$OBJ" ] && { echo NOTFOUND; exit 1; }

docker run --rm -v $OBJ:/tmp/a.o -v /tmp/carve_elf.py:/tmp/carve_elf.py -w /tmp \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
llvm-objcopy --dump-section=.hip_fatbin=fat.bin a.o 2>/dev/null
rm -rf cos; python3 carve_elf.py fat.bin cos >/dev/null 2>&1
for f in cos/*.elf; do llvm-objdump -d $f 2>/dev/null; done > dev.txt
echo "内核数: $(grep -c endpgm dev.txt)"
echo
echo "=== 内核名清单 ==="
grep -oE "<[^>]+>:" dev.txt | sed "s/[+][0-9a-fx]*//" | sort -u | head -20
echo
echo "=== 全局指令分布 ==="
for p in v_fma_f32 v_mac_f32 v_mul_f32 v_pk_fma_f16 v_pk_mul_f16 v_add_f32 v_max_f32 v_cvt_f32_f16 v_cvt_f16_f32 v_dot4_i32_i8 v_and_b32 ds_read_b128 ds_read_b64 ds_read_b32 ds_write_b128 ds_write_b32 s_load_dwordx4 global_load_dwordx4 global_store_dwordx4 v_exp_f32; do
  c=$(grep -c "$p" dev.txt); [ "$c" -gt 0 ] && printf "%-18s %6d\n" "$p" "$c"
done
' 2>&1
