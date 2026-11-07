#!/bin/bash
# R22 第一步：pack 目录结构 + manifest
P=/home/albus/strata166/data/packs/ud-q4_k_xl
echo "=== ls pack ==="
ls -la "$P" 2>/dev/null | head -40
echo "=== du ==="
du -sh "$P" 2>/dev/null
echo "=== find json/manifest ==="
find "$P" -maxdepth 2 -type f \( -name "*.json" -o -name "*.tsv" -o -name "*manifest*" -o -name "*.idx" \) 2>/dev/null | head -20
echo "=== find all top files with size ==="
find "$P" -maxdepth 2 -type f -printf "%10s  %p\n" 2>/dev/null | sort -rn | head -30
echo "=== config json ==="
cat /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
