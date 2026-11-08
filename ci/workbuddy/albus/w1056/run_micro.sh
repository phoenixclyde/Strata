#!/bin/bash
# W1056: build + run the R116 PV microbench in the scratch container. Zero production impact.
W=/home/albus/strata166/tmp/w1056
IMG=strata-gfx906:0.2.11-101
mkdir -p $W
docker run --rm --device=/dev/kfd --device=/dev/dri -v $W:/w $IMG bash -lc '
hipcc -x hip -O3 --offload-arch=gfx906 /w/pv_micro_r116.cu -o /w/pv_micro_r116 2>/w/build.err
rc=$?
echo BUILD_RC=$rc
if [ $rc != 0 ]; then grep -E "error:" /w/build.err | head -40; exit 1; fi
for i in 1 2 3; do
  echo "=== RUN $i nchunk=256 reps=200 trials=5 ==="
  timeout 300 /w/pv_micro_r116 256 200 5
done
'
