#!/bin/bash
set -uo pipefail
docker run --rm --security-opt label=disable \
  -v /home/albus/strata166/build-lcpp:/out -v /home/albus/strata166/ref/llama_b12129:/llama.cpp \
  strata-gfx906:0.2.11-101 bash -lc '
cd /out
./strata --version
echo "=== size/md5"
stat -c %s strata; md5sum strata
echo "=== ggml paths baked in"
strings -a strata | grep -c "/llama.cpp/ggml"
echo "=== iqp (should be absent in b12129)"
strings -a strata | grep -c "ggml-cpu/iqp"
'
