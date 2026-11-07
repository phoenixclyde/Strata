#!/bin/bash
# W839-04 校验新二进制并把 n3 部署到 /data/bin（保留 n2）
S=/home/albus/strata166/src028
B=/home/albus/strata166/data/bin
date +%H:%M:%S
echo "=== 新二进制 ==="
ls -la $S/build-028r/strata | cut -c1-90
$S/build-028r/strata --version 2>&1 | head -2

echo "=== 入口是否编进去（字面量体检） ==="
for s in "MI50-class" "GFX906_ATTN_REDUCE12" "STRATA_GFX906_TUNED" "exact speed switches" "rocblas"; do
  printf '  %-26s %s\n' "$s" "$(grep -a -c -F -- "$s" "$S/build-028r/strata" 2>/dev/null)"
done
echo "--- 对照 n2 ---"
for s in "MI50-class" "STRATA_GFX906_TUNED"; do
  printf '  %-26s %s\n' "$s" "$(grep -a -c -F -- "$s" "$B/strata-0.1.54n2" 2>/dev/null)"
done

echo "=== 部署为 n3（cp -> .new -> mv，n2 保留） ==="
cp "$S/build-028r/strata" "$B/strata-0.1.54n3.new" && chmod +x "$B/strata-0.1.54n3.new" && mv "$B/strata-0.1.54n3.new" "$B/strata-0.1.54n3"
md5sum "$B/strata-0.1.54n3" "$S/build-028r/strata" | sed 's#/home/albus/strata166/##'
ls -la $B | grep -E 'n2|n3' | cut -c1-90
