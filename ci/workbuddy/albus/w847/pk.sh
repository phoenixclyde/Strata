set +e
D=/home/albus/strata166/gfx029
echo "===== [1] docker/build.sh 后半（步骤 3-5） ====="
sed -n '80,170p' "$D/docker/build.sh"
echo
echo "===== [2] package_engine.py 用法 ====="
sed -n '1,40p' "$D/packaging/package_engine.py"
echo
echo "===== [3] 本机有没有现成的 engine 包（engine-component.json） ====="
find /home/albus -maxdepth 4 -name "engine-component.json" 2>/dev/null | head -6
ls -lt --time-style=+%m-%d /home/albus/strata166/pkgs 2>/dev/null | head -8
ls -d /home/albus/pkgs 2>/dev/null && ls -lt /home/albus/pkgs | head -8
echo
echo "===== [4] base 镜像里 /opt/strata/components/engine 是什么 ====="
docker run --rm --entrypoint bash strata-gfx906:0.2.8p2 -lc 'ls /opt/strata/components/engine/ 2>/dev/null | head -4; cat /opt/strata/components/engine/*/engine-component.json 2>/dev/null | head -20'
