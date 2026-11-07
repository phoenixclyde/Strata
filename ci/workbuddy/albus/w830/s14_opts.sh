echo "=== STRATA_* options in the 0.1.54 configure ==="
grep -E "^STRATA_[A-Z0-9_]+:" /home/albus/strata166/src028/build-028w/CMakeCache.txt | grep -v INTERNAL | sed 's/^/  /'
echo
echo "=== llama/ggml source dir used ==="
grep -E "^(STRATA_LLAMA|STRATA_GGML|GGML_SOURCE|STRATA_ROOT)" /home/albus/strata166/src028/build-028w/CMakeCache.txt | head -8
echo
echo "=== how the build was launched (log head) ==="
head -6 /home/albus/strata166/src028/build-028.log 2>/dev/null | cut -c1-200
ls -la /home/albus/strata166/tmp/r02_cfg.sh /home/albus/strata166/tmp/r04_build.sh 2>/dev/null
