echo "--- build ---"
tail -2 /home/albus/strata166/src028/build-028.log
grep -oE '^\[[0-9]+/[0-9]+\]' /home/albus/strata166/src028/build-028.log | tail -1
docker ps --format '{{.Names}}' | grep buildrun || echo "container gone"
echo "--- our AMD patch carried over? ---"
md5sum /home/albus/strata166/src0271/src/kernels/cuda/qsa_decode_attn.cu /home/albus/strata166/src028/src/kernels/cuda/qsa_decode_attn.cu
grep -c 'W794' /home/albus/strata166/src028/src/kernels/cuda/qsa_decode_attn.cu
echo "--- define check ---"
grep -o 'STRATA_VERIFY_MAX_T=[0-9]*' /home/albus/strata166/src028/build-028/build.ninja | sort -u
echo "--- mem/load ---"
free -g | head -2; cat /proc/loadavg
