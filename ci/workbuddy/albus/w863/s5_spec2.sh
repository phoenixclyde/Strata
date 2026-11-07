#!/bin/bash
S=/home/albus/strata166/pr/strata-fork/src/program/generate.cpp
echo "=== spec_min_p usage ==="
grep -n "spec_min_p" "$S" | head -12
echo
echo "=== around the draft-length loop ==="
n=$(grep -n "req_spec_min_p" "$S" | tail -1 | cut -d: -f1)
sed -n "$((n-18)),$((n+8))p" "$S"
echo
echo "=== S / S_mtp definitions near 12380 ==="
sed -n '12370,12400p' "$S"
