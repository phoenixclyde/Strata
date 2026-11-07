#!/bin/bash
echo "=== dirs under /home/albus newer than the patch ==="
ls -dt /home/albus/*/ 2>/dev/null | head -15
echo "=== any object/library containing wave_rows_for ==="
for f in $(find /home/albus -maxdepth 3 \( -name "*.o" -o -name "*.a" \) -newermt "2026-11-01 05:00" 2>/dev/null | head -40); do
  if nm -C "$f" 2>/dev/null | grep -q "wave_rows_for\|set_wave_rows"; then
    echo "HIT: $f  $(stat -c %y "$f")"
  fi
done
echo "=== other build trees ==="
ls -d /home/albus/strata166/*build* /home/albus/*build* 2>/dev/null
echo "=== w862 dir contents ==="
ls -la /home/albus/w862* 2>/dev/null | head -40
