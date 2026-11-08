#!/bin/bash
# K8/W1060: GDN_PP 3-case gate -- STRATA_GDN_PP=0/1/2 against gfx906_gdn_rec_head.
# Debt: GDN_PP was never unit-tested (audit P0-3); the 3 cases run in ~1 s after an
# incremental build (P565). Hooked into gpu-gate (self-hosted runner) per K8's exit plan.
# Runner user ghrunner may only sudo /usr/bin/docker -- so docker is invoked via sudo.
set -u
BUILD=${BUILD:-/home/albus/strata166/build-masterp}
IMG=${IMG:-strata-gfx906:0.2.11-101}
if [ "$(id -u)" = 0 ]; then DOCK=docker; elif docker info >/dev/null 2>&1; then DOCK=docker; else DOCK="sudo /usr/bin/docker"; fi
echo "GDNPP_GATE: build=$BUILD img=$IMG dock=$DOCK"
$DOCK run --rm --device /dev/kfd --device=/dev/dri --group-add video \
  -v "$BUILD":/out -v /home/albus/strata166/pr/k10:/src -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -w /out "$IMG" bash -lc '
    set -u
    ninja gfx906_gdn_rec_head >/tmp/b.log 2>&1 || { echo BUILD_FAIL; tail -20 /tmp/b.log; exit 2; }
    B=$(find /out -maxdepth 2 -name gfx906_gdn_rec_head -type f | head -1)
    test -x "$B" || { echo BINARY_MISSING; exit 2; }
    RC=0
    for pp in 0 1 2; do
      echo "== STRATA_GDN_PP=$pp =="
      STRATA_GDN_PP=$pp "$B" >/tmp/pp$pp.log 2>&1 || RC=3
      grep -E "^FAIL|FAILURES" /tmp/pp$pp.log | head -6
      if grep -qE "^FAIL(:|$)|FAILURES: [1-9]" /tmp/pp$pp.log; then RC=3; fi
      tail -1 /tmp/pp$pp.log
    done
    echo GDNPP_RC=$RC
    exit $RC
  '
RC=$?
if [ "$RC" != 0 ]; then echo "GDNPP_GATE: FAIL rc=$RC"; exit "$RC"; fi
echo "GDNPP_GATE: PASS"
