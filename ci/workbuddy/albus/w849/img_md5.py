import hashlib
import os
import sys

count = 0
missing = 0
with open("/data/w849_files.txt", encoding="utf-8") as fh:
    for line in fh:
        rel = line.rstrip("\n")
        if not rel:
            continue
        p = os.path.join("/src", rel)
        if not os.path.isfile(p):
            missing += 1
            continue
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        print("%s  %s" % (h.hexdigest(), rel))
        count += 1

print("count=%d missing=%d" % (count, missing), file=sys.stderr)
