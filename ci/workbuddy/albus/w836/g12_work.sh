#!/bin/bash
# W836: make 166 hold a version-controlled working copy of our branch
F=/home/albus/strata166/pr/strata-fork
W=/home/albus/strata166/gfx906
cd $F || exit 1

echo "=== A. refresh remote-tracking (the push refspec is main-only) ==="
git fetch origin gfx906/0.2.8-mi50:refs/remotes/origin/gfx906/0.2.8-mi50 2>&1 | tail -3
echo "origin/gfx906/0.2.8-mi50 = $(git rev-parse --short origin/gfx906/0.2.8-mi50 2>&1)"
echo
echo "=== B. is the published branch the same commit as local? ==="
echo "local  HEAD: $(git rev-parse HEAD)"
echo "origin HEAD: $(git rev-parse origin/gfx906/0.2.8-mi50 2>&1)"
echo
echo "=== C. working copy at $W ==="
if [ -d "$W/.git" ]; then
  echo "  exists; updating"
  git -C "$W" fetch origin 2>&1 | tail -2
  git -C "$W" checkout gfx906/0.2.8-mi50 2>&1 | tail -2
  git -C "$W" reset --hard origin/gfx906/0.2.8-mi50 2>&1 | tail -2
else
  echo "  cloning (depth 1, just this branch)"
  timeout 600 git clone --depth=1 -b gfx906/0.2.8-mi50 \
    https://gh-proxy.com/https://github.com/phoenixclyde/Strata.git "$W" 2>&1 | tail -5
fi
echo
echo "=== D. what is in the working copy ==="
if [ -d "$W/.git" ]; then
  git -C "$W" log -1 --format='%h %ad %s' --date=short
  echo "  files: $(git -C "$W" ls-files | wc -l)"
  for f in CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js; do
    printf "    %-46s %s B\n" "$f" "$(stat -c%s "$W/$f" 2>/dev/null || echo MISSING)"
  done
fi
