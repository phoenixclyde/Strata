#!/bin/bash
# W835: DFlash2 x INT8 upsteam record (our draft path)
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. HANDOVER-dflash2.md head ==="
git show FETCH_HEAD:docs/gfx906/HANDOVER-dflash2.md 2>/dev/null | head -45
echo
echo "=== B. DEVLOG-dflash2.md verdict/perf lines ==="
git show FETCH_HEAD:docs/gfx906/DEVLOG-dflash2.md 2>/dev/null | grep -nE "VERDICT|SHIPPED|DEAD|2\.83|3\.14|t/s|accept|tok/step|%" | head -35
