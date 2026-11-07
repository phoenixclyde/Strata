set +e
for img in strata-gfx906:0.2.9r1 stratisfake; do :; done
echo "===== [1] hipBLASLt 的内核到底装在哪 ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc '
  echo "-- libhipblaslt 相关文件:"
  ls -lh /opt/rocm/lib/libhipblaslt* 2>/dev/null
  echo "-- /opt/rocm 下所有 Tensile / hipblaslt 路径:"
  find /opt/rocm -maxdepth 4 -iname "*tensile*" -o -maxdepth 4 -iname "*hipblaslt*" 2>/dev/null | head -20
  echo "-- 有没有 hipsolutions/libsolutions:"
  ls -d /opt/rocm/lib/hipblaslt /opt/rocm/lib/hipsolutions /opt/rocm/share/hipblaslt 2>/dev/null
  echo "-- .so 里的 arch 字符串（grep gfx 目标）:"
  strings /opt/rocm/lib/libhipblaslt.so.1 2>/dev/null | grep -oE "^gfx[0-9]{3,4}$" | sort -u | tr "\n" " "; echo
  echo "-- .so 里 Tensile 库名:"
  strings /opt/rocm/lib/libhipblaslt.so.1 2>/dev/null | grep -E "TensileLibrary" | head -5
'
echo
echo "===== [2] 对照 7.14 镜像 ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9t2 -lc '
  ls -lh /opt/rocm/lib/libhipblaslt* 2>/dev/null
  find /opt/rocm -maxdepth 4 -iname "*tensile*" 2>/dev/null | head -6
  echo -n "-- .so 里 arch: "; strings /opt/rocm/lib/libhipblaslt.so.1 2>/dev/null | grep -oE "^gfx[0-9]{3,4}$" | sort -u | tr "\n" " "; echo
'
