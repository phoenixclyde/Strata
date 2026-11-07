#!/bin/bash
# W836: fetch v0.2.8 tag, then measure OUR delta and UPSTREAM's delta on each patched file
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. fetch the v0.2.8 tag (the base src028 was built from) ==="
timeout 300 git fetch ghup tag v0.2.8 --no-tags 2>&1 | tail -3
echo "v0.2.8 = $(git rev-parse v0.2.8 2>&1)"
git log -1 --format='%h %ad %s' --date=short v0.2.8 2>&1
echo
echo "=== B. per file: our delta (v0.2.8 -> src028) vs upstream delta (v0.2.8 -> main) ==="
printf "%-46s %10s %10s %s\n" FILE "our +-" "up +-" "conflict risk"
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
  # our delta vs the tag
  if git cat-file -e v0.2.8:$f 2>/dev/null; then
    base=$(mktemp); git show v0.2.8:$f > "$base"
    ours=$(diff -u "$base" "/home/albus/strata166/src028/$f" 2>/dev/null | grep -cE '^[+-][^+-]' )
    rm -f "$base"
  else ours=NA; fi
  # upstream delta vs the tag
  up=$(git diff --numstat v0.2.8 ghup/main -- "$f" 2>/dev/null | awk '{print $1"+"$2"-"}')
  [ -z "$up" ] && up="0"
  printf "%-46s %10s %10s\n" "$f" "$ours" "$up"
done
echo
echo "=== C. who else on upstream touched these files since v0.2.8 ==="
for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
  n=$(git log --oneline v0.2.8..ghup/main -- "$f" 2>/dev/null | wc -l)
  echo "  $f : $n commit(s)"
  git log --oneline v0.2.8..ghup/main -- "$f" 2>/dev/null | head -3 | sed 's/^/      /'
done
