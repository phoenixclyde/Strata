set +e
echo "===== [1] hipBLASLt codegen 路径（HipBLASLtCodegen.cmake） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc 'sed -n "1,60p" /opt/rocm/lib/cmake/hipblaslt/HipBLASLtCodegen.cmake'
echo
echo "===== [2] rocisa / Tensile 支持哪些 arch（Python 里的枚举） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc '
  ls /opt/rocm/share/hipblaslt/tensilelite
  echo "--- rocisa 里的 arch 枚举:"
  grep -rohE "gfx[0-9]{3,4}" /opt/rocm/share/hipblaslt/tensilelite 2>/dev/null | sort -u | tr "\n" " "; echo
  echo "--- Tensile 里的 gfx906 出现次数:"
  grep -rl "gfx906" /opt/rocm/share/hipblaslt/tensilelite 2>/dev/null | head -5
'
echo
echo "===== [3] hipblaslt 版本与它自报的支持架构（.so 里的架构表上下文） ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.9r1 -lc '
  cat /opt/rocm/include/hipblaslt/hipblaslt-version.h 2>/dev/null | grep -E "VERSION_(MAJOR|MINOR|PATCH|Tweak)" | head -5
  echo "--- gfx906 在 .so 里的上下文:"
  strings /opt/rocm/lib/libhipblaslt.so.1 | grep -n "gfx906" | head -5
'
