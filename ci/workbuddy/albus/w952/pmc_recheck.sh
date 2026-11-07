#!/bin/bash
# AUDIT24 / R61 re-measure: reproduce the 67.1% VALUBusy on the production-shaped Q4_K MMQ launch.
# Same shape as W942: 16 experts x 1024 tokens = 16384 rows, type 12 (Q4_K), gate/up [1280,2560].
set -u
H=/home/albus/strata166
OUT=$H/data/w952pmc
rm -rf "$OUT"; mkdir -p "$OUT"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

echo "== run pmc (3 counters, one pass) =="
docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$H/build-r28":/out -v "$H/data":/data -e STRATA_MMQ_KQ=1 -w /out \
  strata-gfx906:0.2.10-101 \
  bash -lc "rocprofv3 --pmc VALUBusy --pmc MemUnitStalled --pmc FetchSize --output-format csv -d /data/w952pmc -- ./kq_bench 16 1024 3 12 1280 2560 > /tmp/b952.log 2>&1; echo BENCH_RC=\$?; tail -14 /tmp/b952.log" 2>&1 | tail -18

echo "== files =="
find "$OUT" -type f | head

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 130); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
