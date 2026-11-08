#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Poison-probe: mark the UNSIGNED strata_dp4a overload with a unique ISA constant,
rebuild scratch, and count per-TU whether any call site actually resolves to it.
Zero production impact: builds into build-masterp (scratch dir), header restored after."""
import sys
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''set -u
R=/home/albus/strata166/pr/k10
W=/home/albus/strata166/tmp/w1055
IMG=strata-gfx906:0.2.11-101
OUT=/home/albus/strata166/build-masterp
LOG=$W/probe.log
: > "$LOG"
H=$R/include/strata/platform/hip_compat/strata_hip.h
cp -f "$H" "$W/strata_hip.h.orig"
cd "$R" || exit 1
git status --porcelain include/strata/platform/hip_compat/strata_hip.h | head -2 >>"$LOG"
python3 - "$H" <<'PY'
import io,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
old="""static __device__ __forceinline__ unsigned int strata_dp4a(unsigned int a, unsigned int b, unsigned int c) {
    const uint8_t* va = reinterpret_cast<const uint8_t*>(&a);
    const uint8_t* vb = reinterpret_cast<const uint8_t*>(&b);
    return c + va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2] + va[3] * vb[3];
}"""
new="""static __device__ __forceinline__ unsigned int strata_dp4a(unsigned int a, unsigned int b, unsigned int c) {
    unsigned int probe; asm volatile("v_mov_b32_e32 %0, 0xdeadbeef" : "=v"(probe));
    if (probe == 0x12345678u) { const uint8_t* va = reinterpret_cast<const uint8_t*>(&a); return c + va[0]; }
    const uint8_t* va = reinterpret_cast<const uint8_t*>(&a);
    const uint8_t* vb = reinterpret_cast<const uint8_t*>(&b);
    return c + va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2] + va[3] * vb[3];
}"""
assert s.count(old)==1, s.count(old)
io.open(p,"w",encoding="utf-8",newline="\n").write(s.replace(old,new))
print("poisoned")
PY
cat "$LOG"
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" \
  bash -lc 'ninja -j 12 > /w/ninja_probe.log 2>&1; rc=$?; echo BLD=$rc; echo FAILED=$(grep -c "^FAILED" /w/ninja_probe.log); exit $rc' >>"$LOG" 2>&1
RC=$?
tail -3 "$LOG"
cp -f "$W/strata_hip.h.orig" "$H"
git -C "$R" checkout -f include/strata/platform/hip_compat/strata_hip.h 2>/dev/null
echo "header restored: $(md5sum $H | cut -c1-8) vs orig $(md5sum $W/strata_hip.h.orig | cut -c1-8)"
exit $RC
'''
rc, out, err = _sshutil.run_remote(S, timeout=1500)
print(out[-1500:])
if err.strip():
    print("ERR", err[-300:])
