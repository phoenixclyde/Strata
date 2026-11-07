#!/bin/bash
# W863 接手：现况核对（只读）
echo "=== date ==="; date -u +%FT%TZ
echo "=== docker ps ==="
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null
echo "=== engine proc in container ==="
docker exec strata166-407 ps -eo pid,etime,cmd 2>/dev/null | grep -E "strata-0|--serve" | grep -v grep
echo "=== health ==="
curl -s --max-time 5 http://127.0.0.1:8090/health; echo
echo "=== git status pr/strata-fork ==="
cd /home/albus/strata166/pr/strata-fork && git status --porcelain && git log --oneline -1
echo "=== backup exists? ==="
ls -l /home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu* 2>/dev/null
echo "=== wave_rows patch present? ==="
grep -n "wave_rows_for\|STRATA_MMVQ_WAVE_ROWS" /home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu | head -20
echo "=== vram ==="
docker exec strata166-407 cat /sys/class/drm/card0/device/mem_info_vram_used 2>/dev/null || rocm-smi --showmeminfo vram 2>/dev/null | head -12
echo "=== pack manifest location ==="
ls -la /home/albus/strata166/data/*.json 2>/dev/null | head -20
ls -la /home/albus/strata166/data/ 2>/dev/null | head -30
