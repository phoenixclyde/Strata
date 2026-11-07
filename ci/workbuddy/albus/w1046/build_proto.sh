#!/bin/bash
W=/home/albus/strata166/tmp/w1046
IMG=strata-gfx906:0.2.11-101
docker run --rm --device=/dev/kfd --device=/dev/dri -v $W:/w $IMG bash -lc '
hipcc -x hip -O3 --offload-arch=gfx906 /w/k8v4_pv_dot8_proto.cu -o /w/k8v4_pv_dot8_proto 2>/w/proto.err
rc=$?
echo BUILD_RC=$rc
grep -A4 -B2 "error:" /w/proto.err | head -100
if [ $rc = 0 ]; then timeout 180 /w/k8v4_pv_dot8_proto; fi
'
