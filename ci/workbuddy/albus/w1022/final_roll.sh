#!/bin/bash
set -euo pipefail
R=/home/albus/strata166/pr/strata-fork
CTX=/home/albus/strata166/build-ctx-211

cd "$R"
git add ci/release_check.py ci/selftest_pin.py
git -c user.name=albus -c user.email=a@b commit -q -m "release_check: two pin declarations, compared instead of picked

third_party/ggml/VERSION.txt is the declaration CMakeLists.txt:2078 obeys when
STRATA_GGML_DIR is empty; the workflow pin is a second copy of the same fact.  The
first version of this check read only the workflow, i.e. it trusted the copy and
ignored the source.  Now both are read and a disagreement fails:

  VERSION.txt  3cf03257f219afbe7334045ff7c6a06ac68c627d Sun Sep 20 16:08:11 2026 +0800
  workflow     LLAMA_CPP_COMMIT: 3cf03257f219afbe7334045ff7c6a06ac68c627d

Self-test now also covers the disagreement case (4/4)."
git tag -a mi50-0.2.11-r33-8 -m "plus the two-declaration pin check" HEAD
git push -q origin gfx906/mi50 mi50-0.2.11-r33-8

N=$(git rev-list --count upstream/main..HEAD)
T=$(git describe --tags)
echo "commits_on_top=$N tag=$T"

git archive --format=tar.gz -o "$CTX/strata-src-0.2.11.tar.gz" HEAD
cd "$CTX"
docker build -q -t strata-gfx906:0.2.11-101 \
  --build-arg COMMITS_ON_TOP="$N" --build-arg STRATA_TAG="$T" \
  -f "$R/ci/docker/Dockerfile-gfx906-0.2.11" . >/dev/null
echo "image=$(docker images --no-trunc --format '{{.ID}}' strata-gfx906:0.2.11-101 | cut -c8-19)"

docker stop strata166-407 >/dev/null && docker rm -f strata166-407 >/dev/null
docker run -d --name strata166-407 --device /dev/kfd --device /dev/dri --group-add video \
  --restart unless-stopped -p 8090:8090 -v /home/albus/strata166/data:/data -v /models:/models:ro \
  --shm-size 64m --ipc host --security-opt label=disable strata-gfx906:0.2.11-101 \
  bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >/dev/null
for i in $(seq 1 18); do h=$(curl -s -m 3 localhost:8090/health); case "$h" in *"\"ok\""*) echo "healthy after ${i}0s"; break;; esac; sleep 10; done
docker inspect -f 'container={{.Id}} img={{.Config.Image}} restarts={{.RestartCount}} started={{.State.StartedAt}}' strata166-407 | cut -c1-120
cd "$R" && python3 ci/release_check.py 2>&1 | tail -4
