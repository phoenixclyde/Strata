#!/bin/bash
# 从**真正的 base**重建派生镜像（深度恒定），并把 recreate 的 IMG 指过去
set -e
BASE=rk-netdata-base:6ac52ba4145c
cd /home/albus/netdata/ops/image
TAG="rk-netdata:$(date +%Y%m%d_%H%M%S)"
echo "== build FROM $BASE -> $TAG"
docker build --build-arg BASE="$BASE" -t "$TAG" . 2>&1 | tail -6
ID=$(docker image inspect "$TAG" -f '{{.Id}}')
echo "TAG=$TAG"
echo "ID=$ID"
sed -i "s|^IMG=.*|IMG=\"$ID\"|" /home/albus/netdata/ops/recreate_netdata.sh
grep -n '^IMG=' /home/albus/netdata/ops/recreate_netdata.sh
echo "== 层数"
docker image inspect "$TAG" -f '{{len .RootFS.Layers}}'
