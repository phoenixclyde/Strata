set +e
P=/home/albus/strata166/tmp/w851_probe
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable -v "$P":/w:ro strata-gfx906:0.2.9r1 bash -lc '
cp /w/probe_hblt.cpp /tmp/p.cpp; cd /tmp
/opt/rocm/bin/hipcc -O2 -std=c++17 --offload-arch=gfx906 p.cpp -o probe -lhipblaslt 2>&1 | grep -E "error:" | head -10
' 2>&1 | head -14
