set -e
cd /home/albus/strata166
docker rm -f buildt1 >/dev/null 2>&1 || true
docker run --rm --name buildt1 -v /home/albus/strata166/src028:/src -w /src strata-gfx906:0.2.4p4 \
  bash -lc 'cd /src/build-028 && ninja CMakeFiles/strata_engine.dir/src/core/dflash2.cpp.o 2>&1 | tail -12'
