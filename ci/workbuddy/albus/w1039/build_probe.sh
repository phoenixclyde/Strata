#!/bin/bash
# W1039: build (and optionally run) the probe.  A file, not an inline command -- inline `$VAR` gets eaten
# by the python -> ssh -> docker chain (bitten twice already).
set -u
C=/opt/rocm/lib/llvm/bin/clang++
echo "=== build ==="
$C -x hip --offload-arch=gfx906 -O3 -w -o /w/t_probe /w/t_probe.cu > /w/probe_build.log 2>&1
echo "BUILD_RC=$?"
grep -m4 error: /w/probe_build.log
ls -l /w/t_probe 2>&1 | tail -1

if [ "${1:-}" = "run" ]; then
  echo "=== run ==="
  /w/t_probe 2>&1 | head -40
  echo "RUN_RC=$?"
fi
