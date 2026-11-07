#!/bin/bash
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1047
IMG=strata-gfx906:0.2.11-101
BR=gfx906/hc-dp4a
PROD=gfx906/lcpp-k10
LOG=$W/build_hc4b.log
restore() { cd "$R" || return; git checkout "$PROD" >/dev/null 2>&1 || true; }
trap restore EXIT INT TERM
cd "$R" || exit 1
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo "not on $BR"; exit 1; }
SHA=$(git rev-parse --short HEAD)
echo "candidate source $BR@$SHA"
docker run --rm -v "$R":/src -v /home/albus/strata166/build-masterp:/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_hc4b.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_hc4b.log); grep -m8 "error:" /w/ninja_hc4b.log; exit $rc' > "$LOG" 2>&1
RC=$?
tail -16 "$LOG"
[ "$RC" = 0 ] || exit "$RC"
CAND=/home/albus/strata166/data/bin/strata-0.1.57-hc4b
cp /home/albus/strata166/build-masterp/strata "$CAND.new"
chmod 755 "$CAND.new"
mv -f "$CAND.new" "$CAND"
md5sum "$CAND"
stat -c 'bytes=%s' "$CAND"
echo "BUILD_HC4B: PASS source=$BR@$SHA"
