#!/bin/bash
R=/home/albus/strata166/pr/strata-fork
D=/home/albus/strata166/data/bin
echo "=== in the WORKING TREE: where does 'SIMT=2' come from? ==="
grep -rn "SIMT=2" "$R/src/" | head -5
echo
echo "=== in the WORKING TREE: 'tiles 32/128' (the =2 dispatch banner) ==="
grep -rn "32/128" "$R/src/kernels/cuda/qsa_select.cu" | head -5
echo
echo "=== in the binaries ==="
for f in "$D/strata-0.1.55h" "$D/strata-0.1.55g"; do
  echo "$(basename $f): simt2=$(strings -a "$f" | grep -c 'SIMT=2), tiles 32/128')  tiles128=$(strings -a "$f" | grep -c '32/128')"
done
echo
echo "=== git: was cc8a0711 / aef9d256 ever checked out in this worktree? ==="
git -C "$R" reflog --date=iso --all 2>/dev/null | grep -E "aef9d256|cc8a0711" | head -5
echo
echo "=== does the current tree contain the simt_level dispatch? ==="
grep -n "simt_level" "$R/src/kernels/cuda/qsa_select.cu" | head -5
