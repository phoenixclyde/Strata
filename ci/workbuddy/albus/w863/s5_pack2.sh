#!/bin/bash
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== packs dir ==="
ls -la /home/albus/strata166/data/packs/
echo "=== last 3 'native pack' lines with line numbers ==="
grep -n "native pack" "$L" | tail -3
echo "=== last startup: find last 'engine started' ==="
grep -n "engine started" "$L" | tail -3
echo "=== tail block: last 60 non-serve-request lines of startup ==="
grep -n "HC_Q8\|native projection\|token embedding\|window up to\|VRAM free with everything" "$L" | tail -12
