#!/bin/bash
# W942 / R63: ISA census of the Q4_K MMQ kernel in the standalone bench binary (read-only copy!).
set -u
cp /out/kq_bench /tmp/kq_copy                       # discipline 16: never feed the real artifact to objcopy
llvm-objcopy --dump-section=.hip_fatbin=/tmp/fat.bin /tmp/kq_copy
ls -l /tmp/fat.bin
rm -rf /tmp/co && python3 /tmp/carve_elf.py /tmp/fat.bin /tmp/co | tail -3
echo "== objects =="
ls /tmp/co | wc -l
echo "== find the Q4_K mmq kernel =="
for f in /tmp/co/*.elf; do
  llvm-nm -S -C --defined-only "$f" 2>/dev/null | grep -m1 "mul_mat_q<(ggml_type)12, 64, false>" > /tmp/hit.txt && { echo "HIT $f"; cat /tmp/hit.txt; echo "$f" > /tmp/hitfile; break; }
done
cat /tmp/hitfile 2>/dev/null || echo "NO HIT"
