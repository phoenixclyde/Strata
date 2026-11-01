#!/bin/bash
# strata-ci build -- rebuild one translation unit of the engine in the production image,
# re-archive, re-link.  Nothing else; no CMake, no image rebuild, no service restart.
#
# Why not `ninja`: build.ninja contains add_subdirectory("/llama.cpp/ggml") and one
# VerifyGlobs mismatch, so ninja always tries to regenerate CMake first and dies.
# We therefore take ninja's OWN command lines (no hand-copied flags: losing -DNDEBUG
# costs 47%, the wrong hip_compat path costs 45%) and run exactly three of them.
#
# Usage: build.sh [--file src/kernels/cuda/native_mmvq.cu] [--archive libstrata_kernels.a]
#                 [--name strata-ci-build] [--foreground]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/config.sh"

FILE=src/kernels/cuda/native_mmvq.cu
LIB=libstrata_kernels.a
CNAME=strata-ci-build
FOREGROUND=0
while [ $# -gt 0 ]; do
  case "$1" in
    --file) FILE=$2; shift 2 ;;
    --archive) LIB=$2; shift 2 ;;
    --name) CNAME=$2; shift 2 ;;
    --foreground) FOREGROUND=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

OBJ=$(basename "$FILE").o
echo "=== build: $FILE -> $OBJ  (archive $LIB) ==="
echo "repo=$REPO"
echo "build=$BUILD"
echo "image=$IMG"
echo "before: $(md5sum "$BUILD/strata" 2>/dev/null | cut -d' ' -f1)  $(stat -c%s "$BUILD/strata" 2>/dev/null) bytes"

docker rm -f "$CNAME" >/dev/null 2>&1
docker run -d --name "$CNAME" --security-opt label=disable \
  -v "$REPO":$SRC_MOUNT -v "$BUILD":/out "$IMG" bash -lc "
set -u
cd /out || exit 1
cmd=/out/_ci_all.txt
ninja -t commands strata > \$cmd 2>/dev/null || { echo 'NINJA -t commands FAILED'; exit 1; }
total=\$(wc -l < \$cmd)
L1=\$(grep -n '$OBJ' \$cmd | grep -- '-x hip -c' | head -1 | cut -d: -f1)
L2=\$(grep -n 'llvm-ar qc $LIB' \$cmd | head -1 | cut -d: -f1)
L3=\$total
echo \"total commands: \$total  compile line: \${L1:-none}  archive line: \${L2:-none}  link line: \$L3\"
[ -z \"\$L1\" ] && { echo 'COMPILE LINE NOT FOUND for $OBJ'; exit 11; }
[ -z \"\$L2\" ] && { echo 'ARCHIVE LINE NOT FOUND for $LIB'; exit 12; }
sed -n \"\${L1}p;\${L2}p;\${L3}p\" \$cmd > /out/_ci_step.sh
echo '--- the three commands (flags taken verbatim from ninja) ---'
cut -c1-160 /out/_ci_step.sh
echo '--- compiling ---'
time bash -e /out/_ci_step.sh
echo STEP_RC=\$?
ls -l strata $LIB
" 2>&1 | tail -2

if [ "$FOREGROUND" = "1" ]; then
  docker wait "$CNAME" >/dev/null 2>&1
fi

sleep 3
echo "=== container status: $(docker inspect "$CNAME" --format '{{.State.Status}} exit={{.State.ExitCode}}' 2>/dev/null) ==="
docker logs "$CNAME" 2>&1 | tail -6
echo "after:  $(md5sum "$BUILD/strata" 2>/dev/null | cut -d' ' -f1)  $(stat -c%s "$BUILD/strata" 2>/dev/null) bytes"
echo
echo "poll:  docker inspect $CNAME --format '{{.State.Status}}'; docker logs $CNAME | tail"
