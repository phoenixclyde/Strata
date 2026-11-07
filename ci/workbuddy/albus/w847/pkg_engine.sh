set +e
T=/home/albus/strata166/gfx029
P=/home/albus/strata166/pkgs
IMG=strata-gfx906:0.2.8p2
mkdir -p "$P"
echo "===== [1] 在镜像里打包 hip/gfx906 引擎组件（不重编译，只打包已验证的 0.1.55g） ====="
docker run --rm -v "$T":/tree:ro -v /home/albus/strata166/data/bin:/in:ro -v "$P":/out "$IMG" bash -lc '
set -e
mkdir -p /stage
cp /in/strata-0.1.55g /stage/strata
chmod +x /stage/strata
echo "-- collect_libs"
python3 /tree/packaging/collect_libs.py --binary /stage/strata \
  --search /opt/rocm/lib --search /usr/lib/x86_64-linux-gnu \
  --out /stage --also "librocblas.so*" --also "libhipblas.so*" --also "libhipblaslt.so*" \
  --data /opt/rocm/lib/rocblas/library=rocblas/library --data-arch gfx906 2>&1 | tail -8
echo "-- 收集结果:"; ls /stage | head -12; du -sh /stage
echo "-- package_engine"
python3 /tree/packaging/package_engine.py --src /stage --backend hip --version 0.1.55 \
  --arch gfx906 --platform linux-x86_64 --out /out/engine --notes "gfx906 MI50, built from v0.2.9 tree (W844)" 2>&1 | tail -12
echo "-- verify"
for d in /out/engine/*/; do python3 /tree/packaging/package_engine.py --verify "$d" && echo "VERIFY OK $d"; done
' 2>&1 | tail -30
echo
echo "===== [2] 产物 ====="
ls -l "$P/engine" 2>/dev/null | head
du -sh "$P/engine"/* 2>/dev/null
