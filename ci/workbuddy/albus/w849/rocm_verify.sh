set +e
TAG=strata-gfx906:0.2.9r1
echo "===== 用挂载真实二进制来静态验证（上一版忘挂 /data，ldd 空跑） ====="
docker run --rm -v /home/albus/strata166/data/bin:/in:ro --entrypoint bash "$TAG" -lc '
  echo -n "  ldd 缺失项: "; ldd /in/strata-0.1.55g 2>&1 | grep -c "not found"
  echo "  解析结果（关键库）:"
  ldd /in/strata-0.1.55g 2>/dev/null | grep -E "rocblas|amdhip|hipblaslt" | sed "s/^/    /"
  echo -n "  --version: "; /in/strata-0.1.55g --version 2>&1 | head -2
  echo -n "  rocblas 完整版本串: "; ls /opt/rocm/lib/librocblas.so.5.* | head -1 | sed "s#.*/librocblas.so.##"
'
echo
echo "===== 对照：当前生产镜像（7.14）同样方式 ====="
docker run --rm -v /home/albus/strata166/data/bin:/in:ro --entrypoint bash strata-gfx906:0.2.9t2 -lc '
  echo -n "  ldd 缺失项: "; ldd /in/strata-0.1.55g 2>&1 | grep -c "not found"
  echo -n "  --version: "; /in/strata-0.1.55g --version 2>&1 | head -1
  echo -n "  rocblas 版本串: "; ls /opt/rocm/lib/librocblas.so.5.* | head -1 | sed "s#.*/librocblas.so.##"
' 2>&1 | grep -v "cannot reach"
