set +e
TAG=strata-gfx906:0.2.9
PKG=0.1.55-linux-x86_64-hip-gfx906
echo "===== [1] 镜像信息 ====="
docker images "$TAG" --format '  {{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}'
docker image inspect "$TAG" --format '  id={{.Id}}'
echo
echo "===== [2] /src 是否 0.2.9 全树 ====="
docker run --rm --entrypoint bash "$TAG" -lc '
  echo -n "  gdn_probe.hpp (0.2.9 独有): "; ls /src/include/strata/prefill/gdn_probe.hpp 2>/dev/null || echo MISSING
  echo -n "  gdn_wmma12.inc (0.2.9 独有): "; ls /src/src/prefill/gdn_wmma12.inc 2>/dev/null || echo MISSING
  echo -n "  replica_profile.py (0.2.9 独有): "; ls /src/strata_control/replica_profile.py 2>/dev/null || echo MISSING
  echo -n "  par_counters.hpp (0.2.9 独有): "; ls /src/include/strata/program/par_counters.hpp 2>/dev/null || echo MISSING
  echo -n "  /src 文件数: "; find /src -type f | wc -l
  echo -n "  目录: "; ls /src | tr "\n" " " | head -c 300; echo
  echo -n "  serve/server.py    md5: "; md5sum /src/serve/server.py | cut -d" " -f1
  echo -n "  telemetry.py       md5: "; md5sum /src/serve/telemetry.py | cut -d" " -f1
  echo -n "  web/app.js         md5: "; md5sum /src/serve/web/app.js | cut -d" " -f1
  echo -n "  arch_defaults.cpp  md5: "; md5sum /src/src/core/arch_defaults.cpp | cut -d" " -f1
  echo -n "  CMakeLists.txt     W793/W776: "; grep -c "W793" /src/CMakeLists.txt; grep -c "W776 local" /src/CMakeLists.txt
  echo -n "  generate.cpp       W839 local: "; grep -c "W839 local" /src/src/program/generate.cpp
'
echo
echo "===== [3] 组件包在镜像里并能 verify ====="
docker run --rm --entrypoint bash "$TAG" -lc "ls /opt/strata/components/engine/; python3 /src/packaging/package_engine.py --verify /opt/strata/components/engine/$PKG 2>&1 | tail -2"
echo
echo "===== [4] 与源码树逐文件对比（抽样 8 个） ====="
for f in serve/server.py serve/telemetry.py serve/web/app.js src/core/arch_defaults.cpp src/program/generate.cpp CMakeLists.txt src/kernels/cuda/qsa_select.cu include/strata/prefill/gdn_probe.hpp; do
  a=$(docker run --rm --entrypoint bash "$TAG" -lc "md5sum /src/$f 2>/dev/null | cut -d' ' -f1")
  b=$(md5sum "/home/albus/strata166/gfx029/$f" 2>/dev/null | cut -d' ' -f1)
  [ "$a" = "$b" ] && r=same || r=DIFF
  printf '  %-46s img=%s tree=%s %s\n' "$f" "$a" "$b" "$r"
done
