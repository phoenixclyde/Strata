set +e
python3 - <<'PY'
import io
p = "/home/albus/strata166/tmp/sync_gfx906.sh"
s = io.open(p, encoding="utf-8").read()
if "qsa_select.cu" in s.split("\n")[20]:
    print("already in FILES")
else:
    old = 'src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp"'
    new = 'src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp src/kernels/cuda/qsa_select.cu"'
    assert s.count(old) == 1, "anchor count=%d" % s.count(old)
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("FILES + src/kernels/cuda/qsa_select.cu")
PY
echo "--- 回读第 21 行 ---"
sed -n '21p' /home/albus/strata166/tmp/sync_gfx906.sh
echo
echo "=== 重新同步 ==="
bash /home/albus/strata166/tmp/sync_gfx906.sh 2>&1 | grep -E "DIFF|copy|same   src/kernels/cuda/qsa_select|drift" | tail -8
echo
echo "=== 容器内增量编译 ==="
docker run --rm --name strata-w842build -v /home/albus/strata166/src028:/src -w /src/build-028r \
  strata-gfx906:0.2.8p2 bash -lc "nice -n 15 ninja -j 10 strata 2>&1 | tail -12; echo RC=\$?"
ls -l --time-style=+%H:%M /home/albus/strata166/src028/build-028r/strata
md5sum /home/albus/strata166/src028/build-028r/strata
echo "=== 新二进制是否含 SIMT=2 横幅 ==="
grep -a -c -F "STRATA_SELECT_SIMT=2), tiles 32/128" /home/albus/strata166/src028/build-028r/strata
