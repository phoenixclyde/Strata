set +e
C=strata166-407
echo "===== [A] 容器挂载 ====="
docker inspect "$C" --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} rw={{.RW}}{{println}}{{end}}'
echo "===== [B] 容器内 serve 代码在哪、是否来自挂载 ====="
docker inspect "$C" --format 'Entrypoint={{json .Config.Entrypoint}}{{"\n"}}Cmd={{json .Config.Cmd}}{{"\n"}}WorkDir={{.Config.WorkingDir}}'
echo "--- 容器内找 server.py（前 6 处）:"
docker exec "$C" bash -lc "find / -maxdepth 4 -name server.py -not -path '*/site-packages/*' 2>/dev/null | head -6"
echo "--- 容器内 serve 目录:"
docker exec "$C" bash -lc "ls -l /app 2>/dev/null | head -8; echo ---; ls -l /opt/strata 2>/dev/null | head -8"
echo "===== [C] 宿主 vs 容器 的 serve/server.py 是否同一份 ====="
echo -n "host src028/serve/server.py md5 = "; md5sum /home/albus/strata166/src028/serve/server.py | cut -c1-32
docker exec "$C" bash -lc "for p in /app/serve/server.py /opt/strata/serve/server.py /srv/serve/server.py; do [ -f \$p ] && echo \"in-container \$p md5=\$(md5sum \$p | cut -c1-32)\"; done"
echo "===== [D] 镜像里 serve 的版本痕迹 ====="
docker run --rm strata-gfx906:0.2.8p2 bash -lc "ls -d /app /opt/* 2>/dev/null | head -10; find / -maxdepth 3 -name 'serve' -type d 2>/dev/null | head -5" 2>&1 | head -20
echo "===== [E] 镜像构建脚本 ====="
ls -l /home/albus/strata166/*.sh /home/albus/strata166/tmp/build*.sh 2>/dev/null | head -20
find /home/albus/strata166 -maxdepth 2 -iname "Dockerfile*" 2>/dev/null | head -10
echo "===== [F] 门禁脚本里 PROVENANCE 的判定行 ====="
grep -n "PROVENANCE\|md5sum\|任一名为 strata" /home/albus/strata166/tmp/verify_patches.sh | head -12
