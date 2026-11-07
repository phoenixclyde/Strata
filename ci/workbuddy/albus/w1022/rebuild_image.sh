#!/bin/bash
set -euo pipefail
R=/home/albus/strata166/pr/strata-fork
CTX=/home/albus/strata166/build-ctx-211

cd "$R"
git add ci/docker/Dockerfile-gfx906-0.2.11
git -c user.name=albus -c user.email=a@b commit -q -m "docker: build args, so commits_on_top cannot go stale in the image metadata

The literal 66 in BUILD-IMAGE.json was already wrong by two commits a few minutes
after it was written.  A number nobody re-derives is the exact failure this project
keeps repeating, so the Dockerfile now takes COMMITS_ON_TOP and STRATA_TAG from the
build command (documented in the header) and the tag becomes visible in the image."
git tag -a mi50-0.2.11-r33-7 -m "plus build-arg metadata (commits_on_top, tag) in the image" HEAD
git push -q origin gfx906/mi50 mi50-0.2.11-r33-7

N=$(git rev-list --count upstream/main..HEAD)
T=$(git describe --tags)
echo "commits_on_top=$N tag=$T"

git archive --format=tar.gz -o "$CTX/strata-src-0.2.11.tar.gz" HEAD
cd "$CTX"
docker build -t strata-gfx906:0.2.11-101 \
  --build-arg COMMITS_ON_TOP="$N" --build-arg STRATA_TAG="$T" \
  -f "$R/ci/docker/Dockerfile-gfx906-0.2.11" . 2>&1 | tail -3

docker run --rm --entrypoint sh strata-gfx906:0.2.11-101 -c 'cat /src/BUILD-IMAGE.json'
