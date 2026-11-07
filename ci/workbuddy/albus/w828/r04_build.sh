set -e
cd /home/albus/strata166
TAG=${1:-028}
J=${2:-8}
docker rm -f buildrun$TAG >/dev/null 2>&1 || true
docker run -d --name buildrun$TAG \
  -v /home/albus/strata166/src028:/src \
  -w /src \
  strata-gfx906:0.2.4p4 \
  bash -lc "ninja -C /src/build-$TAG -j $J strata > /src/build-$TAG.log 2>&1; echo EXIT=\$? >> /src/build-$TAG.log"
sleep 8
docker ps --format '{{.Names}} {{.Status}}' | grep buildrun$TAG || echo "NOT RUNNING (check log)"
tail -5 /home/albus/strata166/src028/build-$TAG.log 2>/dev/null || true
free -g | head -2
