set +e
echo "=== sync ==="
bash /home/albus/strata166/tmp/sync_gfx906.sh 2>&1 | grep -E "DIFF|-> copied|qsa_select|drift" | tail -6
echo "--- 树里补丁标记:"; grep -c -F "W842 local" /home/albus/strata166/src028/src/kernels/cuda/qsa_select.cu
echo
echo "=== 容器内增量编译 ==="
docker run --rm --name strata-w842build -v /home/albus/strata166/src028:/src -w /src/build-028r \
  strata-gfx906:0.2.8p2 bash -lc "nice -n 15 ninja -j 10 strata 2>&1 | tail -15; echo RC=\$?"
echo "=== 产物 ==="
ls -l --time-style=+%H:%M /home/albus/strata166/src028/build-028r/strata
md5sum /home/albus/strata166/src028/build-028r/strata
echo "=== 二进制含 SIMT=2 横幅？ ==="
grep -a -c -F "STRATA_SELECT_SIMT=2), tiles 32/128" /home/albus/strata166/src028/build-028r/strata
