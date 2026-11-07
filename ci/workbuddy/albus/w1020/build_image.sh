#!/bin/bash
set -eu
cd /home/albus/strata166/build-ctx-211
docker build -t strata-gfx906:0.2.11-101 -f Dockerfile-0.2.11-layered . 2>&1 | tail -6
docker run --rm --entrypoint sh strata-gfx906:0.2.11-101 -c 'cat /src/BUILD-IMAGE.json; md5sum /src/serve/server.py; test -f /src/third_party/llama.cpp/ggml/src/ggml-cpu/iqp.cpp && echo IQP_OK'
