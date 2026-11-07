set +e
IMG=routek-base:gfx906-rocm101-hip716-torch215-tv030-df1
echo "===== [1] routek-base 的来历（history 头部） ====="
docker history "$IMG" --format '{{.CreatedSince}}  {{.Size}}  {{.CreatedBy}}' 2>/dev/null | head -10
echo
echo "===== [2] 它的 ROCm 到底是不是 10.1 / HIP 7.16，且 rocBLAS 有没有 gfx906 内核 ====="
docker run --rm --entrypoint bash "$IMG" -lc '
  cat /opt/rocm/.info/version 2>/dev/null; hipcc --version | grep -iE "HIP version|clang version" | head -2
  echo "-- rocblas library 里的架构:"; ls /opt/rocm/lib/rocblas/library 2>/dev/null | sed "s/^/   /" | head -8
  echo -n "-- gfx906 内核数: "; ls /opt/rocm/lib/rocblas/library 2>/dev/null | grep -c gfx906
  echo "-- rocblas 版本串:"; ls /opt/rocm/lib/librocblas.so.5.* 2>/dev/null | head -2
  echo "-- 关键 soname:"; ls /opt/rocm/lib/libamdhip64.so.* /opt/rocm/lib/libhipblaslt.so.* 2>/dev/null | head -6
  echo "-- hipblaslt 有没有 gfx906: "; ls /opt/rocm/lib/hipblaslt/library 2>/dev/null | grep -c gfx906
'
echo
echo "===== [3] 与本机生产的 soname 对比 ====="
docker exec strata166-407 bash -lc 'ls /opt/rocm/lib/libamdhip64.so.* /opt/rocm/lib/libhipblaslt.so.* 2>/dev/null | head -6; ls /opt/rocm/lib/rocblas/library | head -3; ls /opt/rocm/lib/rocblas/library | grep -c gfx906'
