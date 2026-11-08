#!/bin/bash
# ci/lcpp_picks/recipe_k10.sh -- rebuild the b12180 llama.cpp tree from upstream only.
#
# WHY THIS EXISTS (W1061):
#   The engine is built against a *composite* pin, not a tag:
#       b12180 = bcb01528  +  mmq* @ 4c1004c
#   Verified by git-blob on the production build tree:
#       vecdotq.cuh d5ff93b9 / quantize.cu 727764cd / fattn-common.cuh 26a432d8  -> bcb01528
#       mmq.cuh e008a34c / mmq-load-tiles.cuh b37d88c1 / mmq.cu 46efdfe0        -> 4c1004c
#   apply.sh cannot reproduce it: 4c1004c is status=INERT in PICKS.tsv (the Stream-K
#   block cap does nothing on gfx906 because every stream_k row is false), so the
#   default ADOPTED-only pass skips it.  INERT is a *performance* verdict, not a
#   "not used" verdict -- and it was used, for the J_best/越界读 refactor that K10
#   carries.  This script is the missing reproduction path.
#
#   Run it on a pristine bcb01528 tree; it overwrites exactly those three files
#   from 4c1004c and leaves everything else alone.
#
#   recipe_k10.sh <llama.cpp tree at bcb01528> <path to a 4c1004c checkout>
set -u

TREE=${1:?usage: recipe_k10.sh <bcb01528 tree> <4c1004c tree>}
SRC=${2:?usage: recipe_k10.sh <bcb01528 tree> <4c1004c tree>}
G=ggml/src/ggml-cuda

[ -d "$TREE/$G" ] || { echo "not a llama.cpp tree: $TREE" >&2; exit 2; }
[ -d "$SRC/$G" ]  || { echo "not a llama.cpp tree: $SRC" >&2; exit 2; }

# The three files 4c1004c touches relative to bcb01528 (blob-verified).
FILES="mmq.cuh mmq-load-tiles.cuh mmq.cu"

echo "== before"
for f in $FILES; do printf "  %-24s %s\n" "$f" "$(git -C "$TREE" hash-object "$TREE/$G/$f" 2>/dev/null || md5sum "$TREE/$G/$f" | cut -d' ' -f1)"; done

for f in $FILES; do
  cp -f "$SRC/$G/$f" "$TREE/$G/$f" || { echo "copy failed: $f" >&2; exit 3; }
done

echo "== after"
for f in $FILES; do printf "  %-24s %s\n" "$f" "$(git -C "$TREE" hash-object "$TREE/$G/$f" 2>/dev/null || md5sum "$TREE/$G/$f" | cut -d' ' -f1)"; done

# The expected values are the production build tree's; a mismatch means the input
# trees are not the two the composite pin names.
cat <<'EOF'
== expected (production build tree)
  mmq.cuh              e008a34c08a01b3c06f821021121217cedc728c0
  mmq-load-tiles.cuh   b37d88c16b512c98e0a21039110d940e0a82f6a8
  mmq.cu               46efdfe0f73e54a8426fd9f8d26ebe8b04be5416
EOF
