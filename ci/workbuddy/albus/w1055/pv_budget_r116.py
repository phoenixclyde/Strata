#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1055/R116: offline P(int8) x V(int8-exact) error budget from the real PV dump.
# Spec (PROGRESS R116): P quantized to int8 (127 levels, per 8-cell group, scale=max|u|/127);
# V is Q4_0 nibble -> int8 (-8..7) EXACT (no error); hardware path = v_dot4_i32_i8 (4 MAC/inst).
# Baseline comparison: the same groups under the R110 P(int4) scheme (rel_rms 4.60%).
import io
import math
import struct
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else r"D:/workbuddy_space/strata_ws/albus/w1052/pv.dump"
G, CELLS, BLOCKS, QK = 12, 64, 8, 32
OFF_SROW, OFF_SP, OFF_VRAW, RECSZ = 24, 536, 3608, 12824


def half_to_float(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def load(path):
    raw = io.open(path, "rb").read()
    (cnt,) = struct.unpack_from("<i", raw, 0)
    recs = []
    for r in range(cnt):
        base = 4 + r * RECSZ
        n_here, slot, chunk, kvh, qz = struct.unpack_from("<5i", raw, base)
        srow = struct.unpack_from("<64q", raw, base + OFF_SROW)
        sp = struct.unpack_from("<768f", raw, base + OFF_SP)
        vraw = raw[base + OFF_VRAW: base + OFF_VRAW + CELLS * BLOCKS * 18]
        recs.append(dict(n_here=n_here, slot=slot, chunk=chunk, kvh=kvh, qz=qz,
                         srow=srow, sp=sp, vraw=vraw))
    return recs


def v_val(vraw, c, d):
    b = d // QK
    off = (c * BLOCKS + b) * 18
    d16, = struct.unpack_from("<H", vraw, off)
    dd = half_to_float(d16)
    rem = d % QK
    byte = vraw[off + 2 + (rem if rem < 16 else rem - 16)]
    nib = ((byte & 0x0F) if rem < 16 else (byte >> 4)) - 8
    return nib, dd


def run(recs, pbits):
    """P quantized to +/- (2**(pbits-1)-1) per 8-cell group; V nibble exact."""
    lvl = (1 << (pbits - 1)) - 1          # 7 for int4, 127 for int8
    max_abs = 0.0
    se = se_ref = 0.0
    n_out = 0
    for ri, r in enumerate(recs):
        nh = r["n_here"]
        rows = [c for c in range(nh) if r["srow"][c] >= 0]
        if len(rows) < 8:
            continue
        for h in range(G):
            for d in range(256):
                ref = 0.0
                q_acc = 0.0
                for g0 in range(0, len(rows) - len(rows) % 8, 8):
                    grp = rows[g0:g0 + 8]
                    u, v4 = [], []
                    for c in grp:
                        nib, dd = v_val(r["vraw"], c, d)
                        u.append(r["sp"][h * CELLS + c] * dd)
                        v4.append(nib)
                    amax = max(abs(x) for x in u) if u else 0.0
                    if amax <= 0.0:
                        continue
                    ps = amax / float(lvl)
                    pq = [max(-lvl, min(lvl, int(round(x / ps)))) for x in u]
                    dot = 0
                    for a, b2 in zip(pq, v4):
                        dot += a * b2
                    q_acc += ps * float(dot)
                    for uc, vc in zip(u, v4):
                        ref += uc * vc
                e = q_acc - ref
                max_abs = max(max_abs, abs(e))
                se += e * e
                se_ref += ref * ref
                n_out += 1
    rel = math.sqrt(se / se_ref) if se_ref > 0 else 0.0
    return rel, max_abs, n_out


def main():
    recs = load(PATH)
    print("records", len(recs))
    if not recs:
        return 2
    rel4, m4, n4 = run(recs, 4)
    print("P(int4)  rel_rms %.4f%%  max_abs %.3e  outputs %d   (R112 baseline: 4.5951%%)" % (rel4 * 100, m4, n4))
    rel8, m8, n8 = run(recs, 8)
    print("P(int8)  rel_rms %.4f%%  max_abs %.3e  outputs %d   <- R116 budget" % (rel8 * 100, m8, n8))
    if rel4 > 0:
        print("int8/int4 improvement: %.1fx   (spec predicted ~16x)" % (rel4 / rel8))
    # adoption arithmetic (P557 kill-line logic): the R110 reject was 4.60% >> budget;
    # the noise floor for an attention-path numeric change is KL 0.0411 (P461/P470).
    print("verdict-line inputs: int8 rel_rms=%.4f%% vs int4 4.5951%%; V traffic cost = 2x (int8 vs 4-bit)" % (rel8 * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
