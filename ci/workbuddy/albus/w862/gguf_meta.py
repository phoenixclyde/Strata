#!/usr/bin/env python3
"""Read GGUF metadata (header only) and print the keys that set the decode shape."""
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
    print("gguf v%d tensors=%d kvs=%d" % (ver, n_tensor, n_kv))

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
            if et in SCALAR and cnt > 64:
                fmt, sz = SCALAR[et]
                f.seek(sz * cnt, 1)
                return "<%d x type%d>" % (cnt, et)
            return [rval(et) for _ in range(cnt)]
        raise ValueError("type %d" % t)

    kv = {}
    for _ in range(n_kv):
        k = rstr()
        t, = struct.unpack("<I", f.read(4))
        kv[k] = rval(t)

    for k in sorted(kv):
        v = kv[k]
        if any(s in k for s in ("block_count", "embedding_length", "head_count", "expert",
                                "feed_forward", "context_length", "rope", "vocab_size",
                                "attention", "ssm", "state", "conv", "dense", "nextn", "mtp")):
            s = str(v)
            print("%-52s %s" % (k, s[:110]))


main()
