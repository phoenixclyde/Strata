#!/bin/bash
# W1046: build the B3 candidate; zero production downtime, no production config change.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1046
IMG=strata-gfx906:0.2.11-101
BR=gfx906/hc-dp4a
PROD=gfx906/lcpp-k10
LOG=$W/build_b3.log
mkdir -p "$W"
restore() {
  cd "$R" || return
  git checkout "$PROD" >/dev/null 2>&1 || true
  test -z "$(git status --porcelain)" || echo "WARN: tree not clean after restore"
}
trap restore EXIT INT TERM

cd "$R" || exit 1
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo "FAIL: not on $BR"; exit 1; }
SHA=$(git rev-parse --short HEAD)
echo "candidate source $BR@$SHA"

docker run --rm \
  -v "$R":/src \
  -v /home/albus/strata166/build-masterp:/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp \
  -v "$W":/w \
  -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_b3.log 2>&1; rc=$?; echo "BLD=$rc"; echo "FAILED=$(grep -c "^FAILED" /w/ninja_b3.log)"; grep -m10 "error:" /w/ninja_b3.log; exit $rc' \
  > "$LOG" 2>&1
RC=$?
tail -20 "$LOG"
[ "$RC" = 0 ] || exit "$RC"

CAND=/home/albus/strata166/data/bin/strata-0.1.57-hc4
cp /home/albus/strata166/build-masterp/strata "$CAND.new" || exit 1
chmod 755 "$CAND.new" || exit 1
mv -f "$CAND.new" "$CAND" || exit 1
md5sum "$CAND"
stat -c 'bytes=%s mtime=%y' "$CAND"
echo "BUILD_B3: PASS source=$BR@$SHA (not installed)"
