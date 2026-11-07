#!/usr/bin/env python3
"""W910: read a GGUF v2/v3 header and report the ACTUAL quantization type of every tensor.

Answers "is this model IQ4 or Q4_K" from the file itself, not from the file name.
Usage: gguf_types.py <shard1.gguf> [shard2.gguf ...]
"""
import struct, sys, collections

# ggml_type -> (name, block elements, bytes per block)
TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144), 13: ("Q5_K", 256, 176),
    14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292), 16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74),
    18: ("IQ3_XXS", 256, 98), 19: ("IQ1_S", 256, 50), 20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110),
    22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136), 24: ("I8", 1, 1), 25: ("I16", 1, 2),
    26: ("I32", 1, 4), 27: ("I64", 1, 8), 28: ("F64", 1, 8), 29: ("IQ1_M", 256, 56), 30: ("BF16", 1, 2),
    34: ("TQ1_0", 256, 54), 35: ("TQ2_0", 256, 66), 36: ("IQ4_NL_4_4", 32, 18),
}

SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4), 5: ("<i", 4),
          6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}


class R:
    def __init__(self, f):
        self.f = f

    def read(self, n):
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError("short read")
        return b

    def u32(self):
        return struct.unpack("<I", self.read(4))[0]

    def u64(self):
        return struct.unpack("<Q", self.read(8))[0]

    def s(self):
        n = self.u64()
        return self.read(n).decode("utf-8", "replace")

    def value(self, t):
        if t == 8:
            return self.s()
        if t == 9:                      # array
            et = self.u32()
            n = self.u64()
            if et == 8:
                for _ in range(n):
                    self.s()
            elif et == 9:
                raise ValueError("nested array")
            else:
                fmt, sz = SCALAR[et]
                self.read(sz * n)
            return "<array>"
        fmt, sz = SCALAR[t]
        return struct.unpack(fmt, self.read(sz))[0]


def scan(path):
    with open(path, "rb") as f:
        r = R(f)
        magic = r.read(4)
        if magic != b"GGUF":
            raise ValueError("%s: not a GGUF (%r)" % (path, magic))
        ver = r.u32()
        n_tensor = r.u64()
        n_kv = r.u64()
        meta = {}
        for _ in range(n_kv):
            k = r.s()
            t = r.u32()
            v = r.value(t)
            if k in ("general.architecture", "general.name", "general.file_type",
                     "general.quantization_version", "split.count"):
                meta[k] = v
        rows = []
        for _ in range(n_tensor):
            name = r.s()
            nd = r.u32()
            dims = [r.u64() for _ in range(nd)]
            tt = r.u32()
            r.u64()                          # offset
            ne = 1
            for d in dims:
                ne *= d
            rows.append((name, tt, ne))
    return ver, meta, rows


def main(paths):
    aggr = collections.defaultdict(lambda: [0, 0, 0])     # type -> [count, elements, bytes]
    exp = collections.defaultdict(lambda: [0, 0])          # experts only
    dense = collections.defaultdict(lambda: [0, 0])
    meta_all = {}
    total_t = 0
    for p in paths:
        ver, meta, rows = scan(p)
        meta_all.update(meta)
        total_t += len(rows)
        for name, tt, ne in rows:
            tn, blk, bpb = TYPES.get(tt, ("type%d" % tt, 1, 1))
            nbytes = ne // blk * bpb
            a = aggr[tn]
            a[0] += 1
            a[1] += ne
            a[2] += nbytes
            is_exp = "expert" in name.lower()
            (exp if is_exp else dense)[tn][0] += 1
            (exp if is_exp else dense)[tn][1] += nbytes
        print("%-60s v%d  %5d tensors" % (p.split("/")[-1], ver, len(rows)))

    print("\nmetadata:", {k: meta_all[k] for k in sorted(meta_all)})
    print("\n== 全部 %d 个张量，按类型 ==" % total_t)
    print("%-10s %7s %16s %10s" % ("type", "count", "GiB", "share"))
    tot = sum(v[2] for v in aggr.values()) or 1
    for tn, (c, ne, nb) in sorted(aggr.items(), key=lambda kv: -kv[1][2]):
        print("%-10s %7d %16.2f %9.1f%%" % (tn, c, nb / 2**30, 100.0 * nb / tot))

    for label, d in (("专家张量", exp), ("非专家张量", dense)):
        s = sum(v[1] for v in d.values()) or 1
        parts = ", ".join("%s %.1f%%" % (k, 100.0 * v[1] / s)
                          for k, v in sorted(d.items(), key=lambda kv: -kv[1][1])[:6])
        print("\n%s：%s" % (label, parts))


if __name__ == "__main__":
    main(sys.argv[1:])
