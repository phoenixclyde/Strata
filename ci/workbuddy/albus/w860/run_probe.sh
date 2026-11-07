#!/bin/bash
set -u
export LD_LIBRARY_PATH=/out/build/library:/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /in
hipcc -O2 --offload-arch=gfx906 -o /tmp/ps probe_shape.cpp -lhipblaslt 2>&1 | grep -E 'error' | head -4
echo "=== baseline: no libpath ==="
/tmp/ps - 64 5056 256 f16 2>&1 | grep -vE 'LLVM option|Did you mean' | tail -4
echo "=== our gfx906 lib ==="
/tmp/ps /v20/lib906 64 5056 256 f16 2>&1 | grep -vE 'LLVM option|Did you mean' | tail -6
