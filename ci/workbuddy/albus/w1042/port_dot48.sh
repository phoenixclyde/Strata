#!/bin/bash
# W1042 (机主 15:26 指令): port BOTH gfx906 integer dot cores onto the production tree.
#
#   dot4  = ALREADY LIVE in include/strata/platform/hip_compat/strata_hip.h
#           (strata_dp4a -> __builtin_amdgcn_sdot4).  ISA: 384 v_dot4_i32_i8
#           in qsa_decode_attn.cu.o.  We align the legacy dead header with it
#           and label the trap so nobody edits the wrong file again.
#   dot8  = NEW in the live compat layer (strata_dp8a/__dp8a) + a standalone
#           include/strata/kernels/gfx906_dot.hpp with bit-exact fallback +
#           tools/gfx906_dot48_selfcheck.cu that really runs v_dot8_i32_i4.
#           NO production kernel consumes dot8 yet (k8v4 V is 4-bit but the
#           attention probabilities are float -> needs p->int4 + numeric gate,
#           PORT_PLAN C2 / R108).  Deliberately NOT faked as "wired in".
#
# Base = gfx906/attn-opt@deb41e12 (the W1042 OPT port).  Nothing is installed.
set -u
S=/home/albus/strata166
R=$S/pr/k10
W=$S/tmp/w1042
IMG=strata-gfx906:0.2.11-101
LOG=$W/port_dot48.log
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() {
  log "FAIL: $*"
  cd $R && git checkout -q gfx906/lcpp-k10 2>/dev/null
  log "restored branch=$(git rev-parse --abbrev-ref HEAD) head=$(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l)"
  exit 1
}

cd $R || fail "no tree"
[ "$(git status --porcelain | wc -l)" = "0" ] || fail "dirty tree before start"
[ "$(git rev-parse --abbrev-ref HEAD)" = "gfx906/lcpp-k10" ] || fail "not on production branch"

log "=== branch from the W1042 OPT port ==="
git checkout -B gfx906/dot48 gfx906/attn-opt >> "$LOG" 2>&1 || fail "checkout -B"
[ "$(git rev-parse --short HEAD)" = "deb41e12" ] || fail "base is not the OPT port"

log "=== dot4: align the legacy (dead) header, label the trap ==="
python3 $W/patch_intrinsics.py >> "$LOG" 2>&1 || fail "intrinsics patch"
log "=== dot8: add the core to the LIVE compat layer ==="
python3 $W/patch_strata_hip.py >> "$LOG" 2>&1 || fail "strata_hip patch"
log "=== install standalone core header + self-check + wrapper doc ==="
cp $W/gfx906_dot.hpp include/strata/kernels/gfx906_dot.hpp || fail "header copy"
mkdir -p tools
cp $W/dot48_selfcheck.cu tools/gfx906_dot48_selfcheck.cu || fail "selfcheck copy"
python3 $W/patch_dp4a.py >> "$LOG" 2>&1 || fail "dp4a patch"

git add include/strata/platform/hip_compat/strata_hip.h \
        include/strata/hip_compat/intrinsics.hpp \
        include/strata/kernels/gfx906_dot.hpp include/strata/kernels/dp4a.hpp \
        tools/gfx906_dot48_selfcheck.cu
git -c user.name=albus -c user.email=albus@166 commit -q -m \
  "gfx906: port the dot8 core into the live compat layer; align/label the dot4 cores (W1042)" \
  >> "$LOG" 2>&1 || fail "commit"
COMMIT=$(git rev-parse --short HEAD)
log "commit $COMMIT  files=$(git show --stat --format='' HEAD | tail -1)"

log "=== build (strata_hip.h invalidates every HIP TU) ==="
T0=$(date +%s)
docker run --rm -v $R:/src -v $S/build-masterp:/out \
  -v $S/tmp/w1037/llama-master:/llama.cpp -w /out "$IMG" \
  sh -c 'ninja -j 12 > /tmp/b.log 2>&1; echo "BLD=$?"; echo "FAILED=$(grep -c "^FAILED" /tmp/b.log)"; grep -m8 "error:" /tmp/b.log; md5sum /out/strata; stat -c%s /out/strata' >> "$LOG" 2>&1
T1=$(date +%s)
grep -q "BLD=0" "$LOG" || fail "build failed"
grep -q "FAILED=0" "$LOG" || fail "build had FAILED lines"
MD5=$(md5sum $S/build-masterp/strata | cut -d' ' -f1)
SZ=$(stat -c%s $S/build-masterp/strata)
log "built $MD5 / $SZ B in $(( T1 - T0 )) s"
if [ "$MD5" = "3b758f88ddad25cdad236be267810a9e" ]; then
  log "NOTE: binary is byte-identical to the W1042 attn candidate - EXPECTED:"
  log "      dot8 has no production call site yet, so the linker drops the new helper."
  log "      The proof that the core works is the self-check + its ISA, not the binary md5."
fi

cp $S/build-masterp/strata $S/data/bin/strata-0.1.57-dot48 || fail "copy candidate"
chmod +x $S/data/bin/strata-0.1.57-dot48
log "candidate installed as /data/bin/strata-0.1.57-dot48 (NOT production)"

log "=== compile + run the runtime self-check (zero downtime) ==="
docker run --rm --device=/dev/kfd --device=/dev/dri -v $R:/src -v $W:/w "$IMG" \
  bash -lc 'hipcc -x hip -O3 --offload-arch=gfx906 -I/src/include \
    /src/tools/gfx906_dot48_selfcheck.cu -o /w/dot48_selfcheck 2>/w/selfcheck.err && /w/dot48_selfcheck' \
  >> "$LOG" 2>&1
log "selfcheck rc=$?"
grep -q "dot4_bad=0 dot8_bad=0" "$LOG" || fail "selfcheck mismatch"
grep -q "HW_device=1" "$LOG" || fail "selfcheck did not take the hardware path"

log "=== ISA proof (fatbin unbundle, not host objdump) ==="
docker run --rm -v $S/build-masterp:/out -v $W:/w "$IMG" bash /w/isa_final.sh >> "$LOG" 2>&1
log "isa rc=$?"
grep -q "selfcheck.*v_dot8_i32_i4=[1-9]" "$LOG" || fail "v_dot8_i32_i4 missing from self-check ISA"
grep -q "attn_tu.*v_dot4_i32_i8=[1-9]" "$LOG" || fail "v_dot4_i32_i8 missing from the production attn TU"

log "=== restore the production branch ==="
git checkout -q gfx906/lcpp-k10 >> "$LOG" 2>&1 || fail "checkout back"
[ "$(git rev-parse --short HEAD)" = "af797b90" ] || fail "tree not back at af797b90"
[ "$(git status --porcelain | wc -l)" = "0" ] || fail "tree dirty after restore"
log "tree back: $(git describe --tags --always) @ $(git rev-parse --short HEAD), clean"
log "DONE commit=$COMMIT md5=$MD5 size=$SZ"
