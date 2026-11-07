set +e
C=strata166-407
echo "started=$(docker inspect "$C" --format '{{.State.StartedAt}}')"
echo "restarts=$(docker inspect "$C" --format '{{.RestartCount}}')"
echo "container_id=$(docker inspect "$C" --format '{{.Id}}' | cut -c1-12)"
echo "image_ref=$(docker inspect "$C" --format '{{.Config.Image}}')"
echo "image_id=$(docker inspect "$C" --format '{{.Image}}')"
echo "image_size=$(docker images --format '{{.Size}}' strata-gfx906:0.2.9s1)"
echo "serve_md5=$(docker exec "$C" md5sum /src/serve/server.py | cut -d' ' -f1)"
echo "telemetry_md5=$(docker exec "$C" md5sum /src/serve/telemetry.py | cut -d' ' -f1)"
echo "cfg_md5=$(md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | cut -d' ' -f1)"
echo "exe_md5=$(md5sum /home/albus/strata166/data/bin/strata-0.1.55g | cut -d' ' -f1)"
echo "--- 旧容器:"
docker inspect strata166-407.pre-w846 --format 'old_image={{.Config.Image}} old_id={{slice .Id 0 12}} status={{.State.Status}}'
