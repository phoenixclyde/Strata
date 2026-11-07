#!/bin/bash
# Isolate ONE variable: apply only #31047 (69ee2ecc, +230/-231, 6 files) on top of b12129.
# The full b12169 tree is 39 MB at 10-30 KB/s from here; this patch is ~50 KB and is the
# only commit in b12129..b12169 that touches MMQ/MoE kernels.
set -uo pipefail
REF=/home/albus/strata166/ref
SRC=$REF/llama_b12129
DST=$REF/llama_b12129_p31047
P=$REF/p31047.patch
SHA=69ee2ecc0150ba7d1204a7f7393dfd651569db8c

rm -f "$P"
for U in "https://gh-proxy.com/https://github.com/ggml-org/llama.cpp/commit/$SHA.patch" \
         "https://github.com/ggml-org/llama.cpp/commit/$SHA.patch"; do
  echo "try: $U"
  curl -fL --retry 2 --max-time 60 -o "$P" "$U" 2>/dev/null && break
done
ls -l "$P" || { echo PATCH_DOWNLOAD_FAIL; exit 3; }
head -3 "$P"

rm -rf "$DST"
cp -a "$SRC" "$DST" || { echo COPY_FAIL; exit 4; }
cd "$DST" || exit 4
patch -p1 --dry-run < "$P" > /tmp/p_dry.log 2>&1
echo "dry-run rc=$?"; tail -8 /tmp/p_dry.log
patch -p1 < "$P" > /tmp/p_apply.log 2>&1
echo "apply rc=$?"; tail -6 /tmp/p_apply.log

echo "=== the commit's own claim, in the tree:"
grep -c "id_map\|tile" "$DST/ggml/src/ggml-cuda/mmid.cu" 2>/dev/null || true
md5sum "$DST/ggml/src/ggml-cuda/mmq.cuh" "$DST/ggml/src/ggml-cuda/mmid.cu"
