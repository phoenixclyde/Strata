#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r77

echo "=== A. 归档干净版 prefill ==="
docker run --rm -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
cp libstrata_prefill.a libstrata_prefill.a.bak_9d9cbe17 2>/dev/null
ar r libstrata_prefill.a CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o
echo "  ar rc=$?"
ls -l libstrata_prefill.a | awk "{print \"   size=\", \$5}"
' 2>&1 | tail -4

echo
echo "=== B. 重链 ==="
docker run --rm -v $B:/out -v /tmp/link_strata.sh:/tmp/link_strata.sh -w /out strata-gfx906:0.2.9-101 \
  bash /tmp/link_strata.sh 2>&1 | tail -6
echo "  link rc=$?"

echo
echo "=== C. 产物与符号核查 ==="
ls -l $B/strata | awk '{print "  size=", $5, $6, $7, $8}'
md5sum $B/strata
echo "--- 应有的（PLE 补丁）---"
for s in "this program may lock only" "raised to .* for the PLE table"; do
  printf "  %-40s %s\n" "$s" "$(strings $B/strata | grep -c "$s")"
done
echo "--- 应消失的（R66 三补丁 + R68）---"
for s in STRATA_PF_GROUP_SCRATCH STRATA_PREFILL_ROUTED_STREAM STRATA_PF_HC_REGION STRATA_SERVE_STOP_BOUND; do
  printf "  %-32s %s\n" "$s" "$(strings $B/strata | grep -c "$s")"
done
