set +e
IMG=strata-gfx906:0.2.9r1
echo "===== [1] TensileLite 在镜像里的形态（源码 or 只有 rocisa） ====="
docker run --rm --entrypoint bash "$IMG" -lc '
  ls /opt/rocm/share/hipblaslt/tensilelite 2>/dev/null
  echo "--- Tensile 目录:"
  ls /opt/rocm/share/hipblaslt/tensilelite/Tensile 2>/dev/null | head -12
  echo "--- 有没有 TensileCreateLibrary 入口:"
  ls /opt/rocm/share/hipblaslt/tensilelite/Tensile/bin 2>/dev/null | head -6
  echo "--- logic 目录（gfx 分类）:"
  ls /opt/rocm/share/hipblaslt/tensilelite/Tensile/Logic 2>/dev/null | head -10
'
echo
echo "===== [2] 7.14 镜像里有没有 ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9t2 -lc '
  ls /opt/rocm/core-7.14/share/hipblaslt/tensilelite 2>/dev/null
  find /opt/rocm -maxdepth 5 -name "TensileCreateLibrary*" 2>/dev/null | head -4
  find /opt/rocm -maxdepth 6 -type d -name "Logic" 2>/dev/null | head -4
'
echo
echo "===== [3] rocBLAS 的 gfx906 内核数（对照：这条路是通的） ====="
docker run --rm --entrypoint bash "$IMG" -lc 'ls /opt/rocm/lib/rocblas/library/*gfx906* | wc -l; du -sh /opt/rocm/lib/rocblas/library | cut -f1'
