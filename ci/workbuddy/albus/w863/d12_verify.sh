#!/bin/bash
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101
echo "=== md5 of the new build vs production ==="
md5sum "$B/strata" /home/albus/strata166/data/bin/strata-0.1.55g
echo
echo "=== FLAGS/INCLUDES used must equal the ones now in build.ninja ==="
grep -m1 "native_mmvq.cu.o -x hip -c" "$B/_w863_all.txt" | sed 's/ -MD.*//' > /tmp/used.txt
grep -m1 "native_mmvq.cu.o -x hip -c" "$B/build.ninja" 2>/dev/null | sed 's/ -MD.*//' > /tmp/now.txt
if [ -s /tmp/now.txt ]; then
  if diff -q /tmp/used.txt /tmp/now.txt >/dev/null; then echo "compile line: IDENTICAL"; else echo "compile line: DIFFERS"; diff /tmp/used.txt /tmp/now.txt | head -5; fi
else
  echo "compile line not found in build.ninja directly (expected: it is in the rule + vars)"
fi
echo "--- exact compile line used ---"
cat /tmp/used.txt | cut -c1-260
echo
echo "=== link line used ==="
tail -1 "$B/_w863_all.txt" | cut -c1-300
echo
echo "=== symbols: does the new binary carry the table? ==="
for f in "$B/strata" "/home/albus/strata166/data/bin/strata-0.1.55g"; do
  echo "$(basename $f): syms=$(nm -C "$f" 2>/dev/null | grep -c 'wave_rows_for\|kWaveRows') env=$(strings -a "$f" | grep -c 'STRATA_MMVQ_WAVE_ROWS') bytes=$(stat -c %s "$f")"
done
echo
echo "=== version banner (no GPU needed) ==="
"$B/strata" --version 2>&1 | head -3
"/home/albus/strata166/data/bin/strata-0.1.55g" --version 2>&1 | head -3
echo
echo "=== build.ninja md5 now ==="
md5sum "$B/build.ninja"
