#!/bin/bash
set -u
cd /home/albus/strata166/ci || exit 1

echo "=== 1) config.sh 指向新构建目录与新镜像 ==="
cp -f config.sh config.sh.bak_w938
sed -i 's#^BUILD=/home/albus/strata166/gfx029-build.*#BUILD=/home/albus/strata166/build-r28          # cmake build dir (container sees it as /out)#' config.sh
sed -i 's#^IMG=strata-gfx906:0\.2\.9-101#IMG=strata-gfx906:0.2.10-101#' config.sh
grep -E "^(BUILD|IMG|CFG|CONTAINER)=" config.sh

echo
echo "=== 2) gate ==="
bash strata-ci check 2>&1 | tail -8

echo
echo "=== 3) status ==="
bash strata-ci status 2>&1 | tail -18
