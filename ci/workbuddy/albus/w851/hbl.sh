set +e
echo "===== [1] 两个镜像里 hipblaslt 支持的架构（文件名里的 gfx） ====="
for img in strata-gfx906:0.2.9t2 strata-gfx906:0.2.9r1; do
  echo "--- $img"
  docker run --rm --entrypoint bash "$img" -lc '
    d=$(ls -d /opt/rocm/lib/hipblaslt/library 2>/dev/null)
    if [ -z "$d" ]; then echo "   (无 hipblaslt/library 目录)"; else
      ls "$d" | sed -E "s/.*_(gfx[0-9a-z]+)\.(dat|co)_.*/\1/" | sed -E "s/^TensileLibrary_.*/\1/" | grep -oE "gfx[0-9a-z]+" | sort -u | tr "\n" " "; echo
      echo -n "   文件总数: "; ls "$d" | wc -l
    fi
    echo -n "   hipblaslt.so: "; ls /opt/rocm/lib/libhipblaslt.so.* 2>/dev/null | head -1'
done
echo
echo "===== [2] rocblas library 的架构（对照：有 gfx906） ====="
for img in strata-gfx906:0.2.9t2 strata-gfx906:0.2.9r1; do
  echo -n "  $img : "
  docker run --rm --entrypoint bash "$img" -lc 'ls /opt/rocm/lib/rocblas/library 2>/dev/null | grep -oE "gfx[0-9a-z]+" | sort -u | tr "\n" " "'
  echo
done
echo
echo "===== [3] hipblaslt 库里能不能为 gfx906 拿到 algo（直接跑 API 试） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc 'ls /opt/rocm/lib/hipblaslt/library | head -5; echo "--- 文件名样式:"; ls /opt/rocm/lib/hipblaslt/library | grep -E "gfx1100" | head -3'
