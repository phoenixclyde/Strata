#!/bin/bash
# rebuild the 0.9.0 trial tree (src-v090) into build-v090 and report the first errors
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/w1031/src-v090
LL=/home/albus/strata166/ref/llama_b12110
OUT=/home/albus/strata166/build-v090
LOG=${1:-/out/_ninja3.log}
docker rm -f v090b >/dev/null 2>&1
docker run --rm --name v090b --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc "
set -u
cd /out
ninja -j12 strata > $LOG 2>&1
rc=\$?
echo NINJA_RC=\$rc
grep -m8 'error:' $LOG
ls -l /out/strata 2>/dev/null
md5sum /out/strata 2>/dev/null
exit \$rc"
