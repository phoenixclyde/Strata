#!/bin/bash
echo "=== [E1] rocBLAS 是否在三个二进制里（有/无/有 才符合事实） ==="
for b in strata-0.1.53 strata-0.1.54n strata-0.1.54n2; do
  f=/home/albus/strata166/data/bin/$b
  if [ -f "$f" ]; then
    printf '  %-16s rocblas=%-4s ROCBLAS_TUNING=%-4s solution=%-4s size=%s\n' \
      "$b" "$(grep -a -c -F rocblas "$f")" "$(grep -a -c -F ROCBLAS_TUNING "$f")" \
      "$(grep -a -c -F 'rocblas_solution' "$f")" "$(stat -c %s "$f")"
  else
    echo "  $b  MISSING"
  fi
done
echo
echo "=== [E1b] 0.1.54n 的构建日志里 rocblas_state_ 警告（丢 W793 的直接特征） ==="
for lg in /home/albus/strata166/src028/build-028*.log; do
  echo "  $(basename $lg): $(grep -c 'rocblas_state_.*not used' $lg 2>/dev/null)"
done
echo
echo "=== [E4] arch_defaults.cpp 是否存在 / 15 项表在哪 ==="
for p in /home/albus/strata166/src028/src/core/arch_defaults.cpp /home/albus/strata166/src028/docs/STRIX_HALO.md /home/albus/strata166/src028/docs/AMD_HIP.md; do
  [ -f "$p" ] && echo "  EXISTS $(stat -c %s "$p") $p" || echo "  MISSING $p"
done
echo
echo "--- STRIX_HALO 里的 exact/byte-identical 表（前后文） ---"
if [ -f /home/albus/strata166/src028/docs/STRIX_HALO.md ]; then
  grep -n "bitwise\|byte-identical\|Exact" /home/albus/strata166/src028/docs/STRIX_HALO.md | head -12
  echo "  --- 表体行数与条目数 ---"
  sed -n '170,196p' /home/albus/strata166/src028/docs/STRIX_HALO.md
fi
echo
echo "--- arch_defaults.cpp 里 gfx1151 段落 ---"
if [ -f /home/albus/strata166/src028/src/core/arch_defaults.cpp ]; then
  grep -n "gfx1151\|gfx906\|HC_UPMIX\|GDN_HEAD\|Exact" /home/albus/strata166/src028/src/core/arch_defaults.cpp | head -20
fi
