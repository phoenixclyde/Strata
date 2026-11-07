#!/bin/bash
echo "=== existing benches ==="
ls -la /home/albus/w862_group/ 2>/dev/null
echo "=== kernels lib vs patched source timestamps ==="
ls -la /home/albus/strata166/gfx029-build/libstrata_kernels* 2>/dev/null
ls -la /home/albus/strata166/pr/strata-fork/src/kernels/cuda/native_mmvq.cu
echo "=== obj for native_mmvq in build dir ==="
find /home/albus/strata166/gfx029-build -name "native_mmvq*.o" -printf "%TY-%Tm-%Td %TH:%TM  %10s  %p\n" 2>/dev/null | head
echo "=== does the lib carry the wave_rows_for symbol? ==="
nm -C /home/albus/strata166/gfx029-build/libstrata_kernels.a 2>/dev/null | grep -c "wave_rows_for"
echo "=== window size stats in log ==="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -oE "drafts accepted [0-9]+ of [0-9]+" "$L" | tail -20
echo "=== any line mentioning verify window counts ==="
grep -nE "window[s]? " "$L" | grep -v "capturing\|captured\|up to 6" | tail -6 | cut -c1-220
