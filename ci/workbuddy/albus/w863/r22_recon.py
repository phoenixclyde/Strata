#!/usr/bin/env python3
# Reconcile: the log says 499 matrices / 3619.14 MiB; my enumeration says 300 native + 194 HC = 494.
import os
import struct
import sys

sys.path.insert(0, "/home/albus/strata166/w863")
import importlib.util
spec = importlib.util.spec_from_file_location("e", "/home/albus/strata166/w863/r22_enum.py")

D = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL"
SHARDS = [os.path.join(D, "Qwen3.8-Flash-Next-UD-Q4_K_XL-%05d-of-00004.gguf" % i) for i in (1, 2, 3, 4)]
SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4),
          5: ("<i", 4), 6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}
TYPES = {0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 6: (32, 22), 7: (32, 24), 8: (32, 34), 9: (32, 40),
         10: (256, 84), 11: (256, 110), 12: (256, 144), 13: (256, 176), 14: (256, 210), 15: (256, 292),
         16: (256, 66), 17: (256, 74), 18: (256, 98), 19: (256, 50), 20: (32, 18), 21: (256, 110),
         22: (256, 82), 23: (256, 136), 24: (1, 1), 25: (1, 2), 26: (1, 4), 27: (1, 8), 28: (1, 8),
         29: (256, 56), 30: (1, 2), 34: (256, 54), 35: (256, 66), 39: (32, 17)}
NAME = {0: "F32", 1: "F16", 2: "Q4_0", 8: "Q8_0", 12: "Q4_K", 14: "Q6_K", 23: "IQ4_XS", 30: "BF16"}


def read_tensors(path):
    with open(path, "rb") as f:
        assert f.read(4) == b"GGUF", path
        struct.unpack("<I", f.read(4))
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
                    return "<n>"
                for _ in range(cnt):
                    rval(et)
                return "<n>"
            raise ValueError(t)

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
            out.append((name, dims, ty))
        return out


def nb(dims, ty):
    blk, tsz = TYPES[ty]
    n = 1
    for d in dims:
        n *= d
    return n // blk * tsz


allt = []
for p in SHARDS:
    allt += read_tensors(p)

print("total tensors:", len(allt))
print("\n=== every tensor with 'ple' in the name ===")
for name, dims, ty in allt:
    if "ple" in name and "simple" not in name:
        print("  %-40s %-6s %s  %d B" % (name, NAME.get(ty, ty), dims, nb(dims, ty)))

HCSUF = (".hc_attn_down.weight", ".hc_attn_up.weight", ".hc_attn_inject.weight",
         ".hc_ffn_down.weight", ".hc_ffn_up.weight", ".hc_ffn_inject.weight")
hc8 = [t for t in allt if t[2] == 8 and (t[0] in ("output_hc_down.weight", "output_hc_up.weight")
                                          or any(t[0].endswith(s) for s in HCSUF))]
print("\nHC Q8_0 matrices: %d, %.2f MiB" % (len(hc8), sum(nb(d, y) for _, d, y in hc8) / 2**20))
hcf32 = [t for t in allt if t[2] == 0 and (t[0] in ("output_hc_down.weight", "output_hc_up.weight")
                                           or any(t[0].endswith(s) for s in HCSUF))]
print("HC F32 matrices: %d, %.2f MiB" % (len(hcf32), sum(nb(d, y) for _, d, y in hcf32) / 2**20))

ELIGIBLE = (".attn_qkv.weight", ".attn_gate.weight", ".ssm_out.weight",
            ".attn_q.weight", ".attn_k.weight", ".attn_v.weight", ".attn_output.weight",
            ".ffn_gate_shexp.weight", ".ffn_up_shexp.weight", ".ffn_down_shexp.weight")
nat = [t for t in allt if any(t[0].endswith(s) for s in ELIGIBLE)]
print("native eligible: %d, %.2f MiB" % (len(nat), sum(nb(d, y) for _, d, y in nat) / 2**20))

print("\n=== Q8_0 tensors under blk.* that are 2-D and NOT in either set (possible missed natives) ===")
tot = 0
for name, dims, ty in allt:
    if ty != 8 or not name.startswith("blk.") or len(dims) != 2:
        continue
    if any(name.endswith(s) for s in ELIGIBLE) or any(name.endswith(s) for s in HCSUF):
        continue
    print("  %-42s %s  %.2f MiB" % (name, dims, nb(dims, ty) / 2**20))
    tot += nb(dims, ty)
print("  subtotal %.2f MiB" % (tot / 2**20))

print("\n=== gap check ===")
g = 3619.14 * 2**20
mine = sum(nb(d, y) for _, d, y in nat) + sum(nb(d, y) for _, d, y in hc8)
print("engine log 3619.14 MiB - mine %.2f MiB = %.2f MiB (%.0f B)" % (mine / 2**20, (g - mine) / 2**20, g - mine))
print("matrix count: mine %d, log 499, gap %d" % (len(nat) + len(hc8), 499 - len(nat) - len(hc8)))
