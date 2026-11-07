#!/bin/bash
# W1039: apply patch A, build the hipk candidate, stage it, then put the tree back on af797b90 and rebuild
# so /out matches the committed tree again (kvg reproducible).
set -u
cd /home/albus/strata166/pr/k10 || exit 1
S=/home/albus/strata166/tmp/w1039
IMG=strata-gfx906:0.2.11-101

echo "=== apply patch A ==="
python3 "$S/patchA_hip_knobs.py" || exit 1
git status --porcelain

echo "=== build hipk ==="
docker run --rm -v /home/albus/strata166/pr/k10:/src -v /home/albus/strata166/build-masterp:/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo "BLD=$?"; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' | tail -8

if [ -f /home/albus/strata166/build-masterp/strata ]; then
  cp -f /home/albus/strata166/build-masterp/strata /home/albus/strata166/data/bin/strata-0.1.57-hipk.new
  chmod 755 /home/albus/strata166/data/bin/strata-0.1.57-hipk.new
  mv -f /home/albus/strata166/data/bin/strata-0.1.57-hipk.new /home/albus/strata166/data/bin/strata-0.1.57-hipk
  echo "staged: $(md5sum /home/albus/strata166/data/bin/strata-0.1.57-hipk)"
fi

echo "=== revert tree, rebuild so /out == kvg again ==="
git checkout -- src/core/mtp.cpp src/core/verify.cpp src/program/generate.cpp
git status --porcelain | wc -l
docker run --rm -v /home/albus/strata166/pr/k10:/src -v /home/albus/strata166/build-masterp:/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b2.log 2>&1; echo "BLD=$?"; md5sum /out/strata' | tail -3
