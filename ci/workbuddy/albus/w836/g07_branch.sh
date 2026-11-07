#!/bin/bash
# W836: create our branch off upstream head, and land the patches by re-running the idempotent patchers
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. do we still have the idempotent patchers? ==="
for f in /home/albus/strata166/tmp/restore_cmake.py /home/albus/strata166/tmp/tel_merged.py \
         /home/albus/strata166/tmp/w831_patch_appjs.py /home/albus/strata166/tmp/verify_patches.sh; do
  [ -f "$f" ] && echo "  OK  $f ($(stat -c%s "$f") B)" || echo "  --  $f MISSING"
done
echo
echo "=== B. base commit we branch from ==="
git log -1 --format='%h %ad %s' --date=short ghup/main
echo
echo "=== C. create the branch (idempotent) ==="
git branch -D gfx906/0.2.8-mi50 2>/dev/null && echo "  dropped old branch"
git checkout -B gfx906/0.2.8-mi50 ghup/main 2>&1 | tail -3
echo "HEAD now: $(git rev-parse --short HEAD)  branch: $(git rev-parse --abbrev-ref HEAD)"
echo
echo "=== D. working tree clean? ==="
git status --porcelain | head -8
echo "  (empty = clean)"
