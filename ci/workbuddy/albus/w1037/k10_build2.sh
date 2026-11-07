#!/bin/bash
# W1037: build the K10 candidate = current mainline (/src) + reconstructed llama-k10 (/llama.cpp).
set -u
R=/home/albus/strata166/tmp/w1037
B=/home/albus/strata166/build-k10p
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/pr/k10
LL=$R/llama-k10

grep -c "/llama.cpp/" /home/albus/strata166/build-port2/build.ninja

if [ ! -d "$B" ]; then
  cp -a /home/albus/strata166/build-port2 "$B" || { echo "FAIL copy build dir"; exit 1; }
  python3 - "$B/build.ninja" <<'PY'
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
n = 0
for tgt in ("RERUN_CMAKE", "VERIFY_GLOBS"):
    import re
    s, k = re.subn(r"build [^\n]*: %s [^\n]*\n((?:  [^\n]*\n)*)" % tgt,
                   lambda m: "build %s: phony\n" % m.group(0).split()[1], s)
    n += k
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("phony-ised", n, "rules")
PY
fi

docker run --rm \
  -v "$SRC":/src -v "$B":/build -v "$B":/out -v "$LL":/llama.cpp \
  -w /build "$IMG" ninja -j 12 > "$R/build_k10b.log" 2>&1
rc=$?
echo "RC=$rc  FAILED=$(grep -c '^FAILED' "$R/build_k10b.log")  warned=$(grep -c 'warning' "$R/build_k10b.log")"
grep -m8 'error:' "$R/build_k10b.log"
if [ -f "$B/strata" ]; then md5sum "$B/strata"; ls -l "$B/strata"; fi
