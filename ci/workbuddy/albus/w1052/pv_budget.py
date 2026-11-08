#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1052/R112: offline P(int4)xV(int4) error budget from a real PV dump.
# Reference:  acc[h][d] = sum_c P[h][c] * v4(c,d) * Vs(c,d)        (kernel's fmaf loop)
# Dot8:       per 8-cell group g and 32-dim block b: u_c = P[h][c]*Vs(c,b),
#             p4 = round(u/ps) to int4 (ps = max|u|/7), v4 = nibble-8;
#             acc += ps * (int32 dot8(p4, v4))                      (R110 spec)
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


def main():
    recs = load(PATH)
    print("records", len(recs))
    if not recs:
        print("empty dump")
        return 2
    # --- P distribution (kernel-local chunk probabilities) ---
    allp = []
    for r in recs:
        nh = r["n_here"]
        for h in range(G):
            for c in range(nh):
                if r["srow"][c] >= 0:
                    allp.append(r["sp"][h * CELLS + c])
    allp.sort()
    n = len(allp)
    print("P values", n, "min %.3e max %.3e mean %.3e" % (allp[0], allp[-1], sum(allp) / n))
    for q in (0.5, 0.9, 0.99, 0.999):
        print("  P quantile %.3f = %.3e" % (q, allp[int(q * (n - 1))]))
    tiny = sum(1 for x in allp if x < 1e-6 * allp[-1])
    print("  frac P < 1e-6*max: %.2f%%" % (100.0 * tiny / n))

    # --- error budget over every (record, head, dim) ---
    max_abs = 0.0
    se = 0.0
    se_ref = 0.0
    n_out = 0
    worst = None
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
                    b = d // QK
                    u = []
                    vs = []
                    v4 = []
                    for c in grp:
                        nib, dd = v_val(r["vraw"], c, d)
                        u.append(r["sp"][h * CELLS + c] * dd)
                        vs.append(dd)
                        v4.append(nib)
                    amax = max(abs(x) for x in u) if u else 0.0
                    if amax <= 0.0:
                        continue
                    ps = amax / 7.0
                    p4 = [max(-8, min(7, int(round(x / ps)))) for x in u]
                    dot = 0
                    for a, b2 in zip(p4, v4):
                        dot += a * b2
                    q_acc += ps * float(dot)
                    for uc, vc in zip(u, v4):
                        ref += uc * vc
                e = abs(q_acc - ref)
                if e > max_abs:
                    max_abs = e
                    worst = (ri, h, d, ref, q_acc)
                se += (q_acc - ref) ** 2
                se_ref += ref * ref
                n_out += 1
    rel = math.sqrt(se / se_ref) if se_ref > 0 else 0.0
    print("outputs", n_out)
    print("max_abs_err %.4e  worst(rec,h,d,ref,q)=%s" % (max_abs, worst))
    print("rel_rms %.4f%%  (W1046 synthetic upper: 6.23%%)" % (rel * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
