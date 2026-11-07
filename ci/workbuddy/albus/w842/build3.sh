set +e
echo "=== 容器内增量编译（build-028r） ==="
docker run --rm --name strata-w842build -v /home/albus/strata166/src028:/src -w /src/build-028r \
  strata-gfx906:0.2.8p2 bash -lc "nice -n 15 ninja -j 10 strata 2>&1 | tail -25; echo RC=\$?"
echo "=== 产物 ==="
ls -l --time-style=+%H:%M /home/albus/strata166/src028/build-028r/strata
md5sum /home/albus/strata166/src028/build-028r/strata
echo "=== 新二进制里有没有 SIMT=2 的横幅 ==="
grep -a -c -F "STRATA_SELECT_SIMT=2), tiles 32/128" /home/albus/strata166/src028/build-028r/strata
