#!/bin/bash
# W1042: port the attention OPT work (B1/B2) onto the production tree.
#
# The key fact that makes this a copy and not a merge: k10@af797b90's qsa_decode_attn.cu is BYTE-IDENTICAL
# to port-all@e181bda5's (the common ancestor) -- k10 never touched that file.  So port-all@62d10e25's version
# is exactly "k10's file + the OPT work", and replacing it loses nothing.
set -u
S=/home/albus/strata166
R=$S/pr/k10
W=$S/tmp/w1042
IMG=strata-gfx906:0.2.11-101
LOG=$W/build.log
mkdir -p "$W"
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

cd $R || fail "no tree"
[ "$(git rev-parse --short HEAD)" = "af797b90" ] || fail "tree is not at af797b90"
[ "$(git status --porcelain | wc -l)" = "0" ] || fail "tree dirty before we start"

log "=== branch + copy ==="
git checkout -b gfx906/attn-opt af797b90 >> "$LOG" 2>&1 || fail "checkout -b"
(cd $S/pr/port-all && git show 62d10e25:src/kernels/cuda/qsa_decode_attn.cu) > src/kernels/cuda/qsa_decode_attn.cu || fail "extract file"
git add src/kernels/cuda/qsa_decode_attn.cu
git -c user.name=albus -c user.email=albus@166 commit -q -m "gfx906: the attention OPT ports on the production tree (B1/B2 dp4a score + DPP, W1042)" >> "$LOG" 2>&1 || fail "commit"
NEWC=$(git rev-parse --short HEAD)
log "port commit $NEWC  ($(git show --stat --format='' HEAD | tail -2 | head -1))"

log "=== build (build-masterp, incremental) ==="
T0=$(date +%s)
docker run --rm \
  -v $R:/src \
  -v $S/build-masterp:/out \
  -v $S/tmp/w1037/llama-master:/llama.cpp \
  -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo "BLD=$?"; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' >> "$LOG" 2>&1
T1=$(date +%s)
tail -6 "$LOG"
grep -q "BLD=0" "$LOG" || fail "build failed (see $LOG)"
grep -q "FAILED=0" "$LOG" || fail "build had FAILED lines"

MD5=$(md5sum $S/build-masterp/strata | cut -d' ' -f1)
SZ=$(stat -c%s $S/build-masterp/strata)
log "built $MD5 / $SZ B in $(( T1 - T0 )) s"
[ "$MD5" = "a85743d7f554159e8ac1e2d432d2e5ea" ] && fail "binary identical to kvg: the port changed nothing"

log "=== static proof the OPT code is in ==="
log "ATTN_DP4A strings: $(strings $S/build-masterp/strata | grep -c 'STRATA_GFX906_ATTN_DP4A')"
log "dp4a/sdot4 in the fatbin: $(strings $S/build-masterp/strata | grep -c 'v_dot4_i32_i8')"

log "=== install the candidate next to the others (not production) ==="
sudo -n cp $S/build-masterp/strata $S/data/bin/strata-0.1.57-attn || cp $S/build-masterp/strata $S/data/bin/strata-0.1.57-attn || fail "copy candidate"
chmod +x $S/data/bin/strata-0.1.57-attn
md5sum $S/data/bin/strata-0.1.57-attn | tee -a "$LOG"

log "=== restore the tree to the production state ==="
git checkout -q gfx906/lcpp-k10 >> "$LOG" 2>&1 || fail "checkout back"
[ "$(git rev-parse --short HEAD)" = "af797b90" ] || fail "tree not back at af797b90"
[ "$(git status --porcelain | wc -l)" = "0" ] || fail "tree dirty after restore"
log "tree back: $(git describe --tags --always) @ $(git rev-parse --short HEAD), clean"

log "DONE commit=$NEWC md5=$MD5 size=$SZ"
