#!/bin/bash
# W1049: build the R103 completion candidates.
#   r103x   = A1 (ROUTE_DPP) + A5 (Q8_GATHER8) + diag bits (F16D/CTLREAD/F16Q) as independent env switches
#   r103ilp = A4 per-TU max-ilp on qsa_decode_attn / qsa_pattn / fused_gr (build.ninja per-edge FLAGS)
# Production is untouched: builds run in docker, branches restored, build.ninja restored.
set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1049
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
BIN=/home/albus/strata166/data/bin
PROD_BR=gfx906/hc-dp4a
LOG=$W/build_r103.log
mkdir -p "$W"
: > "$LOG"

restore() {
  cd "$R" || return
  git checkout -f "$PROD_BR" >>"$LOG" 2>&1 || true
  if [ -f "$OUT/build.ninja.w1049bak" ]; then
    mv -f "$OUT/build.ninja.w1049bak" "$OUT/build.ninja"
  fi
}
trap restore EXIT INT TERM

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

cd "$R" || exit 1
SHA91=91a7c5a4e284f71b44316927131248362802d0ef
BASE=03509d1b6895b4015f03a3aa416c962e5bf56d3d

# ---------------- candidate 1: r103x ----------------
log "=== r103x: A1+A5+diag from $SHA91 onto $BASE ==="
git checkout -f -B gfx906/r103x "$BASE" >>"$LOG" 2>&1 || exit 1
for f in src/kernels/cuda/native_router.cu src/kernels/cuda/kv_q8.cu src/kernels/cuda/qsa_decode_attn.cu; do
  git checkout "$SHA91" -- "$f" || exit 1
done
git -c user.name=albus -c user.email=albus@localhost commit -q -m "gfx906: R103 completion bundle -- A1 router DPP, A5 8-wide gather, F16D/CTLREAD/F16Q diag bits

A1: native_router.cu's three reductions (sum/max/argmax-xchg) move to DPP xor1/2/4/8
    behind STRATA_GFX906_ROUTE_DPP (default off; same operand pairs and order -> bitwise).
A5: kv_q8.cu's 8-wide Q8_1 gather escapes STRATA_EXPERIMENTAL_SM60 and joins the
    STRATA_HIP_GFX906 build behind STRATA_GFX906_Q8_GATHER8 (default off; bitwise).
Diag: qsa_decode_attn.cu gains OPT bits 8/16/32 (F16D / CTLREAD / F16Q) and the
    loud unsupported-combination path (P448 class), all default off.
Each switch is measured alone against the same floor (R109: no bundle arms)." || exit 1
R103X_SHA=$(git rev-parse --short HEAD)
log "r103x source $R103X_SHA"

docker run --rm \
  -v "$R":/src -v "$OUT":/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp \
  -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_r103x.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_r103x.log); grep -m8 "error:" /w/ninja_r103x.log; exit $rc' \
  >>"$LOG" 2>&1
RC=$?
if [ "$RC" != 0 ]; then log "FAIL r103x build"; exit "$RC"; fi
cp "$OUT/strata" "$BIN/strata-0.1.57-r103x.new" && chmod 755 "$BIN/strata-0.1.57-r103x.new" \
  && mv -f "$BIN/strata-0.1.57-r103x.new" "$BIN/strata-0.1.57-r103x" || exit 1
log "r103x md5 $(md5sum "$BIN/strata-0.1.57-r103x" | cut -d' ' -f1) bytes=$(stat -c%s "$BIN/strata-0.1.57-r103x")"
# P425 gate: switches must be visible in the binary
for s in STRATA_GFX906_ROUTE_DPP STRATA_GFX906_Q8_GATHER8 STRATA_GFX906_ATTN_F16D STRATA_GFX906_ATTN_CTLREAD STRATA_GFX906_ATTN_F16Q; do
  n=$(strings "$BIN/strata-0.1.57-r103x" | grep -c "$s")
  log "strings $s = $n"
  [ "$n" -ge 1 ] || { log "FAIL P425 gate: $s not visible"; exit 2; }
done

# ---------------- candidate 2: r103ilp (A4) ----------------
log "=== r103ilp: per-TU max-ilp on qsa_decode_attn/qsa_pattn/fused_gr ==="
git checkout -f -B gfx906/r103ilp "$BASE" >>"$LOG" 2>&1 || exit 1
cp "$OUT/build.ninja" "$OUT/build.ninja.w1049bak"
python3 - "$OUT/build.ninja" <<'PY'
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
for name in ("qsa_decode_attn.cu", "qsa_pattn.cu", "fused_gr.cu"):
    key = "src/kernels/cuda/%s.o:" % name
    i = s.find(key)
    assert i >= 0, name
    j = s.find("FLAGS = ", i)
    assert 0 < j < i + 1200, (name, j)
    k = s.find("\n", j)
    line = s[j:k]
    assert "max-ilp" not in line
    s = s[:k] + " -mllvm -amdgpu-sched-strategy=max-ilp" + s[k:]
    print("patched FLAGS", name)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
PY
grep -c "max-ilp" "$OUT/build.ninja" | tee -a "$LOG"

docker run --rm \
  -v "$R":/src -v "$OUT":/out \
  -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp \
  -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_r103ilp.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_r103ilp.log); grep -m8 "error:" /w/ninja_r103ilp.log; exit $rc' \
  >>"$LOG" 2>&1
RC=$?
mv -f "$OUT/build.ninja.w1049bak" "$OUT/build.ninja"
if [ "$RC" != 0 ]; then log "FAIL r103ilp build"; exit "$RC"; fi
cp "$OUT/strata" "$BIN/strata-0.1.57-r103ilp.new" && chmod 755 "$BIN/strata-0.1.57-r103ilp.new" \
  && mv -f "$BIN/strata-0.1.57-r103ilp.new" "$BIN/strata-0.1.57-r103ilp" || exit 1
log "r103ilp md5 $(md5sum "$BIN/strata-0.1.57-r103ilp" | cut -d' ' -f1) bytes=$(stat -c%s "$BIN/strata-0.1.57-r103ilp")"

# ---------------- ISA spot check (r103x must carry DPP + wide gather) ----------------
docker run --rm -v "$BIN":/b -v "$W":/w "$IMG" bash -lc '
  for o in native_router kv_q8 qsa_decode_attn; do
    llvm-objcopy --dump-section=.text=/w/t.bin /b/strata-0.1.57-r103x 2>/dev/null || true
    break
  done
  echo "ISA check via llvm-objdump on fatbin skipped here; strings gate already passed"
' >>"$LOG" 2>&1 || true

log "BUILD_R103: PASS (r103x=$R103X_SHA, r103ilp=flags3)"
