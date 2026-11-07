#!/bin/bash
# W835c: are those 4 switches actually READ anywhere? (avoid another "env is a no-op" trap)
S=/home/albus/strata166/src028
cd $S || exit 1
for pat in "TSUM" "EXP_DEC" "EXPDEC" "LANECELL" "MERGE_V2" "ATTN_MERGE"; do
  echo "######## grep -i '$pat'"
  grep -rn "$pat" src include 2>/dev/null | grep -v "arch_defaults" | head -5 | cut -c1-175
  echo "   count(non-arch_defaults)=$(grep -rl "$pat" src include 2>/dev/null | grep -vc arch_defaults)"
done
echo
echo "=== how are env switches read in kernels? sample ==="
grep -rn "getenv(\"STRATA_" src/kernels/cuda/*.cu 2>/dev/null | head -8 | cut -c1-160
echo
echo "=== env helper names ==="
grep -rhoE "env_on\(|env_int\(|env_flag\(|std::getenv\(" src/kernels/cuda/*.cu src/prefill/*.cpp 2>/dev/null | sort | uniq -c | head
