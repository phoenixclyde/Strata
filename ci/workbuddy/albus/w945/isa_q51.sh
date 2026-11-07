#!/bin/bash
# W945: is the canonical Q5_1 tile load a 128-bit aligned load, or a pile of 32-bit ones?
# (repack only pays if the answer is the latter — MemUnitStalled is 0.36%, so the cost must be in instruction count.)
set -u
cp /out/kq_bench /tmp/kq_copy2
llvm-objcopy --dump-section=.hip_fatbin=/tmp/fat2.bin /tmp/kq_copy2
rm -rf /tmp/co2 && python3 /tmp/carve_elf.py /tmp/fat2.bin /tmp/co2 > /tmp/carve2.log 2>&1
echo "objects: $(ls /tmp/co2 | wc -l)"
for f in /tmp/co2/*.elf; do
  if llvm-nm -S -C --defined-only "$f" 2>/dev/null | grep -q "mul_mat_q<(ggml_type)7, 64, false>"; then
    echo "HIT $f"
    llvm-nm -S -C --defined-only "$f" | grep "mul_mat_q<(ggml_type)7, 64, false>" | head -1 > /tmp/hit7.txt
    cat /tmp/hit7.txt
    echo "$f" > /tmp/hitfile7
    break
  fi
done
read -r ADDR SIZE _ < /tmp/hit7.txt
f=$(cat /tmp/hitfile7)
END=$(printf '0x%x' $((ADDR + SIZE)))
echo "window $ADDR..$END"
llvm-objdump -d --no-show-raw-insn --start-address=$ADDR --stop-address=$END "$f" > /tmp/k7.asm 2>/dev/null
awk -F'\t' 'NF>1 { split($2, f, " "); if (f[1] ~ /^[a-z][a-z0-9_]*$/) print f[1] }' /tmp/k7.asm > /tmp/mn7.txt
echo "instructions: $(wc -l < /tmp/mn7.txt)"
echo "== loads =="
for m in global_load_dword global_load_dwordx2 global_load_dwordx4 global_load_ubyte global_load_ushort global_load_dwordx3 s_load_dwordx4 ds_read_b128 ds_read_b64 ds_read2_b32; do
  printf "%-24s %s\n" "$m" "$(grep -cx "$m" /tmp/mn7.txt)"
done
echo "== top 12 =="
sort /tmp/mn7.txt | uniq -c | sort -rn | head -12
