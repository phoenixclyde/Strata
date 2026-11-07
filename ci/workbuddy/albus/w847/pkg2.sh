set +e
T=/home/albus/strata166/gfx029
P=/home/albus/strata166/pkgs
IMG=strata-gfx906:0.2.8p2
rm -rf "$P"; mkdir -p "$P"
echo "===== 按上游 build_hip_linux.sh 的流程打包（BUILD.json → collect → stage_tuning → package --tree） ====="
docker run --rm -v "$T":/tree:ro -v /home/albus/strata166/data/bin:/in:ro -v "$P":/out "$IMG" bash -lc '
set -e
cd /tree
mkdir -p /out/stage
cp /in/strata-0.1.55g /out/stage/strata; chmod +x /out/stage/strata
cat > /out/stage/BUILD.json <<EOJ
{"version": "0.1.55", "source": "W844 build from v0.2.9 tree", "variant": "gfx906", "archs": ["gfx906"], "portable": true, "dsv41": false}
EOJ
echo "-- collect_libs（按上游参数）"
python3 packaging/collect_libs.py --binary /out/stage/strata \
  --search /opt/rocm/lib --search /opt/rocm/core-7.14/lib --search /opt/rocm/core-7.14/lib/llvm/lib \
  --search /opt/rocm/lib/rocm_sysdeps/lib \
  --also "libamd_comgr.so*" --also "libhiprtc*.so*" --out /out/stage \
  --data /opt/rocm/lib/rocblas/library=rocblas/library --data /opt/rocm/lib/hipblaslt/library=hipblaslt/library \
  --data-arch gfx906 2>&1 | tail -4
echo "-- 大小:"; du -sh /out/stage
echo "-- stage_tuning（写 hipblaslt_version + 表）"
python3 packaging/stage_tuning.py --stage /out/stage --archs "gfx906" --rocm /opt/rocm 2>&1 | tail -5
echo "-- package_engine --tree"
python3 packaging/package_engine.py --src /out/stage --backend hip --version 0.1.55 \
  --arch gfx906 --platform linux-x86_64 --variant gfx906 --tree \
  --build-id "aef9d25+rocm7.14" --out /out/components/engine \
  --notes "MI50/gfx906, engine 0.1.55 built from v0.2.9 tree (W844)" 2>&1 | tail -10
echo "-- verify"
for d in /out/components/engine/*/; do python3 packaging/package_engine.py --verify "$d" && echo "VERIFY OK: $d"; done
' 2>&1 | tail -26
echo
echo "===== 产物 ====="
ls -l "$P/components/engine" 2>/dev/null
du -sh "$P/components/engine"/* 2>/dev/null
