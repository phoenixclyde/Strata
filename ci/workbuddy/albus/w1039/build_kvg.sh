#!/bin/bash
# W1039 / R104: build the gfx906 VMM candidate from the PRODUCTION source tree (pr/k10 @ fa8e6761 + the vmm patch)
# with the exact b12180 recipe (build-masterp, /llama.cpp = tmp/w1037/llama-master).
set -u
IMG=strata-gfx906:0.2.11-101
LOG=/home/albus/strata166/tmp/w1039/build_kvg.log

docker run --rm \
  -v /home/albus/strata166/pr/k10:/src \
  -v /home/albus/strata166/build-masterp:/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp \
  -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo "BLD=$?"; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' > "$LOG" 2>&1

tail -12 "$LOG"
