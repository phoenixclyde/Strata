#!/bin/bash
# W836: confirm ghup/main is the real upstream head and its tree is complete
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. head identity ==="
echo "ghup/main   = $(git rev-parse ghup/main 2>&1)"
echo "expected    = 870aedd9 (2026-10-29 SYCL prompt attention batch)"
git log -1 --format='%h %ad %s' --date=short ghup/main 2>&1
echo
echo "=== B. tree complete? object count + the files we patch ==="
echo "commits reachable: $(git rev-list --count ghup/main 2>&1)"
echo "shallow file lines: $(wc -l < .git/shallow 2>/dev/null || echo 0)"
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js src/core/arch_defaults.cpp; do
  s=$(git cat-file -s ghup/main:$f 2>/dev/null || echo MISSING)
  printf "  %-46s %s\n" "$f" "$s"
done
echo
echo "=== C. total blobs in tree (sanity) ==="
echo "files in tree: $(git ls-tree -r ghup/main 2>/dev/null | wc -l)"
echo
echo "=== D. does upstream main differ from our v0.2.8-era files in the 5 we patch? ==="
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
  a=$(git rev-parse ghup/main:$f 2>/dev/null)
  b=$(git hash-object "/home/albus/strata166/src028/$f" 2>/dev/null)
  [ "$a" = "$b" ] && st=SAME || st=DIFF
  printf "  %-46s upstream=%s  src028=%s  -> %s\n" "$f" "${a:0:8}" "${b:0:8}" "$st"
done
