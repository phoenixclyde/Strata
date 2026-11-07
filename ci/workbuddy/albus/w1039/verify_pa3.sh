#!/bin/bash
S=/home/albus/strata166
B=$S/build-pa3
echo "=== A. 版本串 ==="
for f in $B/strata $S/data/bin/strata-0.1.57-b12180 $S/data/bin/strata-0.1.57-pa2; do
  [ -f "$f" ] || continue
  printf "%-46s b12180=%s b11062=%s\n" "$(basename $f)" \
    "$(strings $f | grep -c 'b12180')" "$(strings $f | grep -c 'b11062')"
done
echo
echo "=== B. overlay 里的 mmq.cuh 是不是 master 的 ==="
md5sum $B/ggml-tq-overlay/mmq.cuh 2>/dev/null | cut -c1-12
md5sum $S/tmp/w1037/llama-master/ggml/src/ggml-cuda/mmq.cuh | cut -c1-12
grep -c "prec_src1" $B/ggml-tq-overlay/mmq.cuh 2>/dev/null
echo
echo "=== C. ninja 是否还有待编 ==="
docker run --rm -v $S/pr/port-all:/src -v "$B":/out -v $S/tmp/w1037/llama-master:/llama.cpp -w /out strata-gfx906:0.2.11-101 \
  sh -c 'ninja -n 2>&1 | tail -3'
echo
echo "=== D. 引擎自述（run --help 头部） ==="
docker run --rm -v "$B":/b -v $S/data:/data strata-gfx906:0.2.11-101 sh -c '/b/strata --version 2>&1 | head -5' 2>&1 | head -8
echo
echo "=== E. 二进制身份 ==="
md5sum $B/strata; stat -c%s $B/strata
