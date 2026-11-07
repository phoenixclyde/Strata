#!/bin/bash
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== log size ==="; ls -l "$L"; wc -l "$L"
echo "=== startup memory accounting (MiB/GiB lines) ==="
grep -nE "MiB|GiB" "$L" | head -60
