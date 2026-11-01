#!/usr/bin/env python3
"""[W863 R26] Read the GGUF header keys that decide how many expert bytes a token reads.

Only the header is touched; the 4 shards are never read in full. What we need:
  * the MoE shape: expert count E and experts used per token k
  * the layer count
  * the per-expert tensor sizes, so "bytes per token" is E-independent arithmetic
"""
import struct
import sys

P = ("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/"
     "unsloth-UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf")

SCALAR = {0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2), 4: ("<I", 4),
          5: ("<i", 4), 6: ("<f", 4), 7: ("<?", 1), 10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8)}


def main():
    f = open(P, "rb")
    assert f.read(4) == b"GGUF", "not gguf"
    ver, = struct.unpack("<I", f.read(4))
    n_tensor, = struct.unpack("<Q", f.read(8))
    n_kv, = struct.unpack("<Q", f.read(8))
    print("gguf v%d  tensors=%d  kvs=%d" % (ver, n_tensor, n_kv))

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
            if et in SCALAR and cnt > 32:
                fmt, sz = SCALAR[et]
                f.seek(sz * cnt, 1)
                return "<%d values>" % cnt
            return [rval(et) for _ in range(cnt)]
        raise ValueError("type %d" % t)

    kv = {}
    for _ in range(n_kv):
        k = rstr()
        t, = struct.unpack("<I", f.read(4))
        kv[k] = rval(t)

    print()
    print("=== MoE shape ===")
    for k in sorted(kv):
        if any(s in k.lower() for s in ("expert", "moe", "block_count", "feed_forward", "n_ff", "layer")):
            print("  %-52s %s" % (k, kv[k]))

    print()
    print("=== tensors (name, dims, type, bytes) ===")
    GGML = {0: ("F32", 4), 1: ("F16", 2), 2: ("Q4_0", 0.5625), 8: ("Q8_0", 1.0625),
            12: ("Q4_K", 0.5625), 14: ("Q6_K", 0.8125), 15: ("Q8_K", 1.0625), 39: ("MXFP4", 0.53125)}
    rows = []
    for _ in range(n_tensor):
        name = rstr()
        nd, = struct.unpack("<I", f.read(4))
        dims = struct.unpack("<%dQ" % nd, f.read(8 * nd))
        tt, = struct.unpack("<I", f.read(4))
        off, = struct.unpack("<Q", f.read(8))
        n = 1
        for d in dims:
            n *= d
        nm, bpp = GGML.get(tt, ("type%d" % tt, 1.0))
        rows.append((name, dims, nm, int(n * bpp)))

    exp = [r for r in rows if "expert" in r[0].lower() or "ffn_" in r[0].lower()]
    print("total tensors=%d, expert-ish=%d" % (len(rows), len(exp)))
    agg = {}
    for name, dims, nm, b in exp:
        # group by the suffix after the layer number
        base = name.split(".", 2)
        key = base[-1] if len(base) > 2 else name
        a = agg.setdefault(key, [0, 0, nm, dims])
        a[0] += 1
        a[1] += b
    print()
    print("%-38s %6s %14s  %s" % ("tensor suffix", "count", "bytes each", "dims"))
    for key, (cnt, tot, nm, dims) in sorted(agg.items())[:12]:
        print("%-38s %6d %14d  %s %s" % (key[:38], cnt, tot // max(1, cnt), nm, dims))


if __name__ == "__main__":
    sys.exit(main())
