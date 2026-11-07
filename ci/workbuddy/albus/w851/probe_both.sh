set +e
P=/home/albus/strata166/tmp/w851_probe
for IMG in strata-gfx906:0.2.9t2 strata-gfx906:0.2.9r1; do
  echo "===== $IMG ====="
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    --security-opt label=disable -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$P":/w:ro "$IMG" bash -lc '
set -e
cp /w/probe_hblt.cpp /tmp/p.cpp 2>/dev/null || { mkdir -p /tmp/p; cp /w/probe_hblt.cpp /tmp/p.cpp; }
cd /tmp
/opt/rocm/bin/hipcc -O2 -std=c++17 --offload-arch=gfx906 p.cpp -o probe -lhipblaslt 2>&1 | grep -vE "^$" | tail -3
./probe
' 2>&1 | tail -14
  echo
done
