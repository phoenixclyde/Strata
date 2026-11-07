set +e
D=/home/albus/strata166/gfx029
echo "===== [1] package_engine.py 参数 ====="
grep -nE "add_argument|backend|choices" "$D/packaging/package_engine.py" | head -30
echo
echo "===== [2] collect_libs.py 对 hip 的支持 ====="
grep -nE "hip|rocm|amd|add_argument" "$D/packaging/collect_libs.py" | head -20
echo
echo "===== [3] 磁盘 ====="
df -h /home/albus /var/lib/docker 2>/dev/null | tail -3
echo
echo "===== [4] 本地 gfx906 ROCm 基础镜像 ====="
docker images | grep -E "mixa3607|rocm-gfx906|gfx906" | head -8
echo
echo "===== [5] 我们的二进制 + 依赖库位置 ====="
ls -l /home/albus/strata166/data/bin/strata-0.1.55g
docker exec strata166-407 bash -lc "ls /opt/rocm/lib/librocblas* /opt/rocm/lib/libamdhip64* 2>/dev/null | head -4; du -sh /opt/rocm 2>/dev/null"
echo
echo "===== [6] gfx029 树大小（去掉 build/git） ====="
du -sh --exclude=.git --exclude=build-029g "$D" 2>/dev/null
du -sh "$D/.git" 2>/dev/null
