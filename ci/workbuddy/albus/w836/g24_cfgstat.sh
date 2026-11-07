#!/bin/bash
# W836: is the background configure still alive, and how far did it get?
echo "=== A. containers ==="
docker ps --format '{{.Names}} | {{.Status}} | {{.Command}}' | head -6
echo
echo "=== B. build dir progress ==="
B=/home/albus/strata166/gfx906-b2
ls -la $B 2>/dev/null | head -10
echo "  size: $(du -sh $B 2>/dev/null | cut -f1)"
echo "  build.ninja: $([ -f $B/build.ninja ] && echo YES || echo no)"
echo "  _deps entries: $(ls $B/_deps 2>/dev/null | wc -l)"
echo
echo "=== C. cfg2 log ==="
L=/home/albus/strata166/data/w836_cfg2.out
wc -l "$L" 2>/dev/null
tail -6 "$L" 2>/dev/null
echo
echo "=== D. container-side cfg.log tail (if reachable) ==="
tail -6 $B/cfg.log 2>/dev/null || echo "  (cfg.log not readable by albus; root-owned)"
echo
echo "=== E. any cmake process still running? ==="
pgrep -af "cmake|ninja" 2>/dev/null | head -5 || echo "  none"
