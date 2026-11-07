S=/home/albus/strata166/src028
docker rm -f b028r >/dev/null 2>&1
docker run -d --name b028r --security-opt label=disable \
  -v "$S":/src -w /src strata-gfx906:0.2.8 \
  bash -lc 'ninja -C /src/build-028r -j10 > /src/build-028r.log 2>&1; echo "EXIT=$?" >> /src/build-028r.log' >/dev/null
sleep 25
docker ps --format '{{.Names}} {{.Status}}' | grep b028r || echo "not running"
tail -3 /home/albus/strata166/src028/build-028r.log 2>/dev/null | cut -c1-150
