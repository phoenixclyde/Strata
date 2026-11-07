#!/bin/bash
# W836: stop the redundant configure containers (keep production untouched), then summarise
echo "=== A. containers before ==="
docker ps --format '{{.Names}}' | grep -vE 'strata166-407|searxng|netdata|open-webui|comfyui|portainer' | head -8
echo
echo "=== B. remove ONLY the throwaway configure containers ==="
for c in jolly_chatterjee wonderful_mendel vibrant_villani; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    docker rm -f "$c" >/dev/null 2>&1 && echo "  removed $c"
  fi
done
pkill -f "cmake -S . -B /build" 2>/dev/null; sleep 2
echo
echo "=== C. production untouched? ==="
docker ps --format '{{.Names}} | {{.Status}}' | grep strata166-407
docker inspect strata166-407 --format '  img={{.Config.Image}}'
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 100; echo
echo
echo "=== D. what the configure run had already proven ==="
echo "  (from build 1's cfg.log, which reached the rocBLAS probe)"
grep -nE "rocblas" /home/albus/strata166/gfx906-build/cfg.log 2>/dev/null | head -4
echo
echo "=== E. leftover dirs (safe to delete later, root-owned) ==="
du -sh /home/albus/strata166/gfx906-build /home/albus/strata166/gfx906-b2 2>/dev/null
