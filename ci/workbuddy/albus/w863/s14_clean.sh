#!/bin/bash
# 把误推造成的杂项目录挪到 /tmp（不删除，可回退）
if [ -d "/home/albus/D:" ]; then
  T=/tmp/stray_w863_$(date +%s)
  mkdir -p "$T"
  mv "/home/albus/D:" "$T"/ 
  echo "moved /home/albus/D: -> $T"
  find "$T" -type f | head
else
  echo "no stray dir"
fi
echo "=== production still untouched ==="
docker ps --format '{{.Names}} {{.Status}}' | grep strata
rocm-smi --showmeminfo vram 2>/dev/null | grep Used
