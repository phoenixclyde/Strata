#!/bin/bash
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== startup lines 81404-81460 (last start) ==="
sed -n '81404,81462p' "$L" | cut -c1-200
echo "=== any 'head' lines in whole log (uniq) ==="
grep -i "head" "$L" | sed 's/[0-9]\+/N/g' | sort -u | head -20
