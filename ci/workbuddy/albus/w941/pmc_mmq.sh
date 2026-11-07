#!/bin/bash
# W941 / R61: PMC on a production-shaped MMQ launch (16 experts x 1024 tokens = 16384 rows, Q4_K gate/up).
# rocprofv3 execs the driver directly, so the process exits on its own and the tool can finalize + write.
set -u
H=/home/albus/strata166
OUT=$H/data/w941pmc2
rm -rf "$OUT"; mkdir -p "$OUT"

echo "== stop prod =="
docker stop strata166-407 >/dev/null

echo "== run pmc =="
docker run --rm --device=/dev/kfd --device=/dev/dri \
  -v "$H/build-r28":/out -v "$H/data":/data -e STRATA_MMQ_KQ=1 -w /out \
  strata-gfx906:0.2.10-101 \
  bash -lc "rocprofv3 --pmc VALUBusy --output-format csv -d /data/w941pmc2 -- ./kq_bench 16 1024 3 > /tmp/b.log 2>&1; echo BENCH_RC=\$?; tail -12 /tmp/b.log" 2>&1 | tail -16

echo "== files =="
find "$OUT" -type f | head

echo "== restore prod =="
docker start strata166-407 >/dev/null
for i in $(seq 1 120); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
