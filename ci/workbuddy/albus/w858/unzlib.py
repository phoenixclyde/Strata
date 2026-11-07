# -*- coding: utf-8 -*-
"""把 Tensile 库目录里的 *.zlib 解成不带 .zlib 的文件，并打印头部，供 hipBLASLt 直读。"""
import glob
import os
import sys
import zlib

d = sys.argv[1] if len(sys.argv) > 1 else "."
for f in sorted(glob.glob(os.path.join(d, "*.zlib"))):
    raw = open(f, "rb").read()
    print("%-70s magic=%s size=%d" % (os.path.basename(f), raw[:2].hex(), len(raw)))
    try:
        out = zlib.decompress(raw)
    except Exception as e:
        print("   !! not zlib: %s" % e)
        continue
    tgt = f[:-5]
    with open(tgt, "wb") as fh:
        fh.write(out)
    print("   -> %-64s %d bytes  head=%s" % (os.path.basename(tgt), len(out), out[:4].hex()))
