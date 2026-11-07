#!/bin/bash
D=/home/albus/strata166/data/bin
B=/home/albus/strata166/gfx029-build
echo "=== md5: built tree vs deployed vs experiment ==="
md5sum "$B/strata" "$D/strata-0.1.55g" "$D/strata-0.1.55-mmvq" 2>/dev/null
echo "=== does the DEPLOYED binary carry the wave-rows patch? ==="
for f in "$D/strata-0.1.55g" "$D/strata-0.1.55-mmvq" "$B/strata"; do
  s1=$(nm -C "$f" 2>/dev/null | grep -c "wave_rows_for\|kWaveRows")
  s2=$(strings -a "$f" 2>/dev/null | grep -c "STRATA_MMVQ_WAVE_ROWS")
  echo "$(basename "$f"): wave_rows symbols=$s1  env-string=$s2"
done
echo "=== a control symbol that must exist (native_mmvq) ==="
nm -C "$D/strata-0.1.55g" 2>/dev/null | grep -c "native_mmvq"
