#!/bin/bash
R=/home/albus/strata166/pr/strata-fork
D=/home/albus/strata166/data/bin
echo "=== the simt2 banner string exists only in the published hunk ==="
for f in "$D/strata-0.1.55h" "$D/strata-0.1.55g" "$D/strata-0.1.55-mmvq"; do
  echo "$(basename $f): simt2_banner=$(strings -a "$f" | grep -c 'SIMT=2)')  w839_trace=$(strings -a "$f" | grep -c 'W839')"
done
echo
echo "=== commit dates ==="
cd "$R" || exit 1
git log -1 --format='%h %ci %s' HEAD
git log -1 --format='%h %ci %s' origin/gfx906/0.2.9-mi50
git log -1 --format='%h %ci %s' origin/gfx906/0.2.8-mi50
echo
echo "=== reflog around the build (Oct 31 19:06) ==="
git reflog --date=iso -20 | head -20
echo
echo "=== is -DSTRATA_USE_HIP global or per-file? ==="
grep -n -- "-DSTRATA_USE_HIP" /home/albus/strata166/gfx029-build/build.ninja | cut -c1-200
