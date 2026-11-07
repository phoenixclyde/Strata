set +e
C=strata166-407
echo "===== [A] 引擎二进制是否自包含（ldd） ====="
docker exec "$C" bash -lc "ldd /data/bin/strata-0.1.55g 2>&1 | head -14; echo '--- 非系统库:'; ldd /data/bin/strata-0.1.55g 2>/dev/null | grep -vE 'libc|libm|libpthread|libdl|librt|ld-linux|libstdc|libgcc|linux-vdso' | head -10"
echo "===== [B] /src 里有什么（是否被运行时使用） ====="
docker exec "$C" bash -lc "ls /src | head -20; echo '--- serve:'; ls /src/serve | head -12; echo '--- 有没有编译产物 .so:'; find /src -maxdepth 2 -name '*.so*' 2>/dev/null | head -8"
echo "===== [C] 容器内 serve 与宿主 gfx029/serve 的差异（我们只改了 3 个） ====="
echo -n "host gfx029/serve/server.py   md5 = "; md5sum /home/albus/strata166/gfx029/serve/server.py | cut -c1-32
docker exec "$C" bash -lc "md5sum /src/serve/server.py"
echo -n "host gfx029/serve/telemetry.py md5 = "; md5sum /home/albus/strata166/gfx029/serve/telemetry.py | cut -c1-32
docker exec "$C" bash -lc "md5sum /src/serve/telemetry.py"
echo "===== [D] 宿主 gfx029 相对 v0.2.9 的 serve 改动行数 ====="
git -C /home/albus/strata166/gfx029 diff --stat -- serve/ include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp CMakeLists.txt src/program/generate.cpp 2>/dev/null | tail -14
echo "===== [E] 镜像构建上下文哪个最新、serve 怎么进镜像 ====="
ls -lt --time-style=+%m-%d_%H:%M /home/albus/strata166/build-ctx*/Dockerfile* 2>/dev/null | head -5
grep -n "COPY\|ADD" /home/albus/strata166/build-ctx/Dockerfile 2>/dev/null | head -10
echo "===== [F] 门禁 PROVENANCE 现场：树里有哪些叫 strata 的文件 ====="
find /home/albus/strata166/gfx029 -maxdepth 2 -name strata -type f -exec md5sum {} \; 2>/dev/null
echo "--- 构建目录产物:"; md5sum /home/albus/strata166/gfx029-build/strata /home/albus/strata166/gfx029-build/strata-0.1.55g 2>/dev/null
echo "--- 生产部署:"; md5sum /home/albus/strata166/data/bin/strata-0.1.55g
