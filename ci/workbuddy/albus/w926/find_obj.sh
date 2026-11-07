#!/bin/bash
set -u
ENG=~/strata166/data/bin/strata-0.1.55t
docker run --rm -v $ENG:/tmp/eng -v /tmp/carve_elf.py:/tmp/carve_elf.py -w /tmp \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
llvm-objcopy --dump-section=.hip_fatbin=fat.bin eng 2>/dev/null
ls -l fat.bin
rm -rf cos; python3 carve_elf.py fat.bin cos 2>&1 | tail -1

echo "=== 找含 prompt_attn 的 code object ==="
for f in cos/*.elf; do
  if llvm-nm "$f" 2>/dev/null | grep -qi prompt_attn; then echo "HIT $f"; fi
done
' 2>&1
