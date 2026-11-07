#!/bin/bash
set -u
S=/home/albus/strata166
B=$S/build-pa3
IMG=strata-gfx906:0.2.11-101
docker run --rm -v "$S/pr/port-all":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -t targets all 2>/dev/null | grep -m3 qsa_decode_attn; echo ====; t=$(ninja -t targets all 2>/dev/null | grep -m1 -o "[^:]*qsa_decode_attn.cu.o"); echo "T=$t"; ninja -t commands "$t" 2>/dev/null | tail -1 > /tmp/cmd.txt; wc -c /tmp/cmd.txt; head -c 300 /tmp/cmd.txt'
