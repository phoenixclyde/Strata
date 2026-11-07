set +e
C=strata166-407
echo "===== [A] 容器里 serve 0.2.8 是否真的没有 COALESCE/PAR_COUNTERS ====="
docker exec "$C" bash -lc "grep -c 'COALESCE_PREFILL' /src/serve/server.py; grep -c 'PAR_COUNTERS' /src/serve/server.py; grep -c 'STRATA_SELECT_SIMT' /src/serve/server.py"
echo "--- 对照：宿主 gfx029（=0.2.9 原文）"
grep -c "COALESCE_PREFILL" /home/albus/strata166/gfx029/serve/server.py
grep -c "PAR_COUNTERS" /home/albus/strata166/gfx029/serve/server.py
echo
echo "===== [B] 镜像有多大、几层 stage ====="
docker images strata-gfx906 --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}'
echo "--- Dockerfile stage 结构:"
grep -nE "^FROM|^RUN .*(cmake|ninja|make)|^COPY --from" /home/albus/strata166/src028/Dockerfile | head -20
echo
echo "===== [C] 现有镜像里 /src 与宿主 src028 的 serve 是否同源 ====="
docker exec "$C" bash -lc "ls /src/serve/*.py | wc -l; cat /src/VERSION 2>/dev/null | head -2; ls /src | grep -i -E 'version|VERSION' "
docker run --rm strata-gfx906:0.2.8p2 bash -lc "cat /opt/strata/VERSION 2>/dev/null; ls /opt/strata/components/engine/ 2>/dev/null | head -4" 2>&1 | head -6
echo
echo "===== [D] 0.2.8p2 镜像的构建历史（看花了多久/哪一步） ====="
docker history strata-gfx906:0.2.8p2 --format '{{.CreatedSince}}  {{.Size}}  {{.CreatedBy}}' 2>/dev/null | head -8
