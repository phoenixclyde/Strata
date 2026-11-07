#!/bin/bash
# W945: split the Q5_1 down kernel's stall structure (VALU busy vs memory stalled) — decides whether
# the repack's "alignment + planes" is the mechanism worth porting (R86).
set -u
H=/home/albus/strata166
rm -rf "$H/data/w945q51" "$H/data/w945q4k"; mkdir -p "$H/data/w945q51" "$H/data/w945q4k"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

echo "== Q5_1 down [2560,640] =="
docker run --rm --device=/dev/kfd --device=/dev/dri -v "$H/build-r28":/out -v "$H/data":/data \
  -e STRATA_MMQ_KQ=1 -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'rocprofv3 --pmc VALUBusy MemUnitStalled FetchSize --output-format csv -d /data/w945q51 -- ./kq_bench 16 320 3 7 2560 640 > /tmp/q51.log 2>&1; echo RC=$?; tail -7 /tmp/q51.log' 2>&1 | tail -10

echo "== Q4_K gate/up [1280,2560] =="
docker run --rm --device=/dev/kfd --device=/dev/dri -v "$H/build-r28":/out -v "$H/data":/data \
  -e STRATA_MMQ_KQ=1 -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'rocprofv3 --pmc VALUBusy MemUnitStalled FetchSize --output-format csv -d /data/w945q4k -- ./kq_bench 16 320 3 12 1280 2560 > /tmp/q4k.log 2>&1; echo RC=$?; tail -7 /tmp/q4k.log' 2>&1 | tail -10

echo "== files =="
find "$H/data/w945q51" "$H/data/w945q4k" -name "*counter_collection*"

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 120); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
