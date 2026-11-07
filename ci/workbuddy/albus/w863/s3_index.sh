#!/bin/bash
P=/home/albus/strata166/data/packs/ud-q4_k_xl
echo "=== index.txt head 40 ==="
head -40 "$P/index.txt"
echo "=== line count / field count ==="
wc -l "$P/index.txt"
awk -F'\t' '{print NF}' "$P/index.txt" | sort | uniq -c | head
echo "=== distinct type field (col?) sample ==="
head -3 "$P/index.txt" | cat -A | cut -c1-300
echo "=== grep Q8_0 count ==="
grep -c "Q8_0" "$P/index.txt"
echo "=== grep Q8_0 sample 12 ==="
grep "Q8_0" "$P/index.txt" | head -12
echo "=== conversions.json head ==="
head -c 1200 "$P/conversions.json"; echo
echo "=== native_experts.txt head ==="
head -8 "$P/native_experts.txt"
