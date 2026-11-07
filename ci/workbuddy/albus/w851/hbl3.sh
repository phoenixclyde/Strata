set +e
echo "===== [1] hipBLASLt 真内核目录 share/hipblaslt/tensilelite ====="
for img in strata-gfx906:0.2.9t2 strata-gfx906:0.2.9r1; do
  echo "--- $img"
  docker run --rm --entrypoint bash "$img" -lc '
    for d in /opt/rocm/share/hipblaslt/tensilelite /opt/rocm/core-7.14/share/hipblaslt/tensilelite /opt/rocm/share/hipblaslt; do
      [ -d "$d" ] || continue
      echo "   dir=$d"; ls "$d" | head -6
      echo -n "   里面的 gfx 架构: "; ls "$d" | grep -oE "gfx[0-9a-z]+" | sort -u | tr "\n" " "; echo
      echo -n "   .dat 个数: "; ls "$d"/*.dat 2>/dev/null | wc -l
    done'
done
echo
echo "===== [2] rocBLAS 真内核目录（对照，gfx906 在这里） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc 'ls /opt/rocm/lib/rocblas/library | grep -c .; ls /opt/rocm/lib/rocblas/library | grep -oE "gfx[0-9]+" | sort -u | tr "\n" " "; echo; ls -lh /opt/rocm/lib/rocblas/library/*gfx906* 2>/dev/null | head -3'
