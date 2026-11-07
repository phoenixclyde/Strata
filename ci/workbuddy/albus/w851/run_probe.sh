set +e
IMG=strata-gfx906:0.2.9r1
echo "===== 在 10.1 镜像里编译并跑 hipBLASLt 探测（gfx906） ====="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  -v /home/albus/strata166/tmp/w851_probe:/w:ro \
  "$IMG" bash -lc '
set -e
mkdir -p /tmp/p && cp /w/probe_hblt.cpp /tmp/p/
cd /tmp/p
/opt/rocm/bin/hipcc -O2 -std=c++17 --offload-arch=gfx906 probe_hblt.cpp -o probe -lhipblaslt 2>&1 | tail -5
echo "--- build ok, run:"
./probe
' 2>&1 | tail -25
