"""在容器内计算 src/include/CMake 每个文件的 git blob sha1，用于与上游 tree 逐文件比对。

输出: "<blobsha1> <path>" 每行。git blob sha1 = sha1("blob <len>\\0" + content)
"""
import hashlib
import os
import sys

ROOTS = ["/src/src", "/src/include", "/src/cmake"]
FILES = ["/src/CMakeLists.txt"]


def blob_sha1(path):
    h = hashlib.sha1()
    size = os.path.getsize(path)
    h.update(b"blob %d\0" % size)
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


out = sys.stdout
for f in FILES:
    if os.path.exists(f):
        out.write("%s %s\n" % (blob_sha1(f), f))
for r in ROOTS:
    for dp, dn, fn in os.walk(r):
        for name in fn:
            p = os.path.join(dp, name)
            try:
                out.write("%s %s\n" % (blob_sha1(p), p))
            except OSError:
                pass
