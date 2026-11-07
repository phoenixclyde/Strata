A=/home/albus/strata166/src028/src/kernels/cuda/qsa_decode_attn.cu
B=/home/albus/strata166/tmp/qsa_up.cu
echo "sizes: $(stat -c%s $A) $(stat -c%s $B)"
echo "crlf A: $(grep -c $'\r' $A || true)  B: $(grep -c $'\r' $B || true)"
echo "--- diff (first 60 lines) ---"
diff -u "$B" "$A" | head -60
echo "--- diff line count ---"
diff -u "$B" "$A" | wc -l
