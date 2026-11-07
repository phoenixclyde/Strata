#!/usr/bin/env python3
# R22: enumerate the REAL per-layer dense (native_mmvq) tensors from the GGUF tensor table.
# Filters mirror src/core/native_dense.cpp:140-152 (eligible) + :71-77 (hc_q8_name).
import os
import struct
import sys
from collections import defaultdict

D = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL"
SHARDS = [os.path.join(D, "Qwen3.8-Flash-Next-UD-Q4_K_XL-%05d-of-00004.gguf" % i) for i in (1, 2, 3, 4)]

SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4),
          5: ("<i", 4), 6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}

# ggml_type -> (block_elems, type_size_bytes)
TYPES = {
    0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24), 8: (32, 34), 9: (32, 40),
    10: (256, 84), 11: (256, 110), 12: (256, 144), 13: (256, 176), 14: (256, 210), 15: (256, 292),
    16: (256, 66), 17: (256, 74), 18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110),
    22: (256, 82), 23: (256, 136), 24: (1, 1), 25: (1, 2), 26: (1, 4), 27: (1, 8), 28: (1, 8),
    29: (256, 56), 30: (1, 2), 34: (256, 54), 35: (256, 66), 39: (32, 17),
}
NAME = {0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1", 8: "Q8_0", 9: "Q8_1",
        10: "Q2_K", 11: "Q3_K", 12: "Q4_K", 13: "Q5_K", 14: "Q6_K", 15: "Q8_K", 16: "IQ2_XXS",
        17: "IQ2_XS", 18: "IQ3_XXS", 19: "IQ1_S", 20: "IQ4_NL", 21: "IQ3_S", 22: "IQ2_S",
        23: "IQ4_XS", 24: "I8", 25: "I16", 26: "I32", 27: "I64", 28: "F64", 29: "IQ1_M",
        30: "BF16", 34: "TQ1_0", 35: "TQ2_0", 39: "MXFP4"}


def read_tensors(path):
    with open(path, "rb") as f:
        assert f.read(4) == b"GGUF", path
        ver, = struct.unpack("<I", f.read(4))
        n_tensor, = struct.unpack("<Q", f.read(8))
        n_kv, = struct.unpack("<Q", f.read(8))

        def rstr():
            n, = struct.unpack("<Q", f.read(8))
            return f.read(n).decode("utf-8", "replace")

        def rval(t):
            if t in SCALAR:
                fmt, sz = SCALAR[t]
                return struct.unpack(fmt, f.read(sz))[0]
            if t == 8:
                return rstr()
            if t == 9:
                et, = struct.unpack("<I", f.read(4))
                cnt, = struct.unpack("<Q", f.read(8))
                if et in SCALAR:
                    _, sz = SCALAR[et]
                    f.seek(sz * cnt, 1)
                    return "<%d vals>" % cnt
                for _ in range(cnt):
                    rval(et)
                return "<%d vals>" % cnt
            raise ValueError("kv type %d" % t)

        for _ in range(n_kv):
            rstr()
            t, = struct.unpack("<I", f.read(4))
            rval(t)

        out = []
        for _ in range(n_tensor):
            name = rstr()
            nd, = struct.unpack("<I", f.read(4))
            dims = struct.unpack("<%dQ" % nd, f.read(8 * nd))
            ty, = struct.unpack("<I", f.read(4))
            off, = struct.unpack("<Q", f.read(8))
            out.append((name, dims, ty, off))
        return out


ELIGIBLE = (".attn_qkv.weight", ".attn_gate.weight", ".ssm_out.weight",
            ".attn_q.weight", ".attn_k.weight", ".attn_v.weight", ".attn_output.weight",
            ".ffn_gate_shexp.weight", ".ffn_up_shexp.weight", ".ffn_down_shexp.weight")
HC = (".hc_attn_down.weight", ".hc_attn_up.weight", ".hc_attn_inject.weight",
      ".hc_ffn_down.weight", ".hc_ffn_up.weight", ".hc_ffn_inject.weight")
HC_OUT = ("output_hc_down.weight", "output_hc_up.weight", "output_hc_inject.weight")


def nbytes(dims, ty):
    if ty not in TYPES:
        raise SystemExit("unknown ggml type %d" % ty)
    blk, tsz = TYPES[ty]
    n = 1
    for d in dims:
        n *= d
    assert n % blk == 0, ("not block aligned", dims, ty)
    return n // blk * tsz


def main():
    total_all = 0
    seen = set()
    native = []      # (layer, suffix, dims, ty, bytes)
    hc = []
    for p in SHARDS:
        if not os.path.exists(p):
            raise SystemExit("missing " + p)
        for name, dims, ty, off in read_tensors(p):
            total_all += nbytes(dims, ty)
            if name in seen:
                print("DUP NAME %s" % name)
            seen.add(name)
            base = name[len("blk."):] if name.startswith("blk.") else ""
            layer = None
            if base:
                layer = int(base.split(".", 1)[0])
                tail = "." + base.split(".", 1)[1]
            else:
                tail = None
            if tail is not None and any(tail.endswith(s) for s in ELIGIBLE):
                native.append((layer, tail[1:], dims, ty, nbytes(dims, ty)))
            elif tail is not None and any(tail.endswith(s) for s in HC):
                hc.append((layer, tail[1:], dims, ty, nbytes(dims, ty)))
            elif name in HC_OUT:
                hc.append((-1, name, dims, ty, nbytes(dims, ty)))

    print("=== GGUF total: %.2f GiB over %d tensors ===" % (total_all / 2**30, len(seen)))

    # layer class: GDN has ssm_out, QSA has attn_q
    cls = {}
    for layer in range(48):
        names = {x[1] for x in native if x[0] == layer} | {x[1] for x in hc if x[0] == layer}
        if "ssm_out.weight" in names:
            cls[layer] = "GDN"
        elif "attn_q.weight" in names:
            cls[layer] = "QSA"
        else:
            cls[layer] = "?"
    n_gdn = sum(1 for v in cls.values() if v == "GDN")
    n_qsa = sum(1 for v in cls.values() if v == "QSA")
    print("=== layer classes: GDN %d / QSA %d / other %d ===" % (n_gdn, n_qsa, 48 - n_gdn - n_qsa))

    by_suffix = defaultdict(lambda: [0, 0, None])   # count, bytes, (dims, type)
    per_layer = defaultdict(int)
    for layer, suffix, dims, ty, b in native:
        e = by_suffix[suffix]
        e[0] += 1
        e[1] += b
        e[2] = (dims, NAME[ty])
        per_layer[layer] += b

    print("\n=== native dense, by tensor kind (all 48 layers) ===")
    print("%-24s %5s %14s %14s  %s" % ("suffix", "n", "MiB total", "MiB/layer", "shape x type"))
    tot = 0
    for suffix, (cnt, b, meta) in sorted(by_suffix.items(), key=lambda kv: -kv[1][1]):
        tot += b
        dims, tn = meta
        print("%-24s %5d %14.2f %14.2f  %s x %s" % (
            suffix, cnt, b / 2**20, b / 2**20 / max(1, cnt), tuple(reversed(dims)), tn))
    print("native dense total: %.2f MiB (%.2f MiB/layer avg over 48)" % (tot / 2**20, tot / 2**20 / 48))

    q8 = sum(b for _, _, _, ty, b in native if ty == 8)
    nonq8 = tot - q8
    print("  of which Q8_0: %.2f MiB ; non-Q8_0: %.2f MiB" % (q8 / 2**20, nonq8 / 2**20))

    print("\n=== per-layer native bytes (48 rows) ===")
    gd = [per_layer[l] for l in range(48) if cls[l] == "GDN"]
    qs = [per_layer[l] for l in range(48) if cls[l] == "QSA"]
    print("GDN layer: %.2f MiB each (n=%d) => %.2f MiB" % (sum(gd) / max(1, len(gd)) / 2**20, len(gd), sum(gd) / 2**20))
    print("QSA layer: %.2f MiB each (n=%d) => %.2f MiB" % (sum(qs) / max(1, len(qs)) / 2**20, len(qs), sum(qs) / 2**20))
    print("layers present: %s" % sorted(per_layer))

    print("\n=== HC (STRATA_HC_Q8) ===")
    hcs = defaultdict(lambda: [0, 0, None])
    for layer, suffix, dims, ty, b in hc:
        e = hcs[suffix]
        e[0] += 1
        e[1] += b
        e[2] = (dims, NAME[ty])
    tot_hc = 0
    for suffix, (cnt, b, meta) in sorted(hcs.items(), key=lambda kv: -kv[1][1]):
        tot_hc += b
        dims, tn = meta
        print("%-24s %5d %14.2f MiB  %s x %s" % (suffix, cnt, b / 2**20, tuple(reversed(dims)), tn))
    q8hc = sum(b for _, _, _, ty, b in hc if ty == 8)
    print("HC total: %.2f MiB ; Q8_0 part: %.2f MiB (%.3f GiB)" % (tot_hc / 2**20, q8hc / 2**20, q8hc / 2**30))

    print("\n=== summary for R22 ===")
    print("decode-step dense bytes = native(Q8_0 only, mmvq reads) %.2f MiB + HC Q8_0 %.2f MiB = %.2f MiB"
          % (q8 / 2**20, q8hc / 2**20, (q8 + q8hc) / 2**20))
    print("native non-Q8_0 (other types, still read) %.2f MiB" % (nonq8 / 2**20))


main()
