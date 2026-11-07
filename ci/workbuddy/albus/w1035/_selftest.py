"""Self-test for cmp_extra.py: synthetic dumps, no engine, no GPU.

  python3 /w1035/_selftest.py
expects:  b -> identical YES / max|dlogit| 0 ;  c -> identical no / max|dlogit| ~1e-3
"""
import os

import numpy as np

base = "/w1035/_t"
rng = np.random.default_rng(0)
for d in ("a", "b", "c"):
    os.makedirs(os.path.join(base, d), exist_ok=True)
for i in range(3):
    x = rng.normal(size=4096).astype("float32") * 4.0
    x.tofile(os.path.join(base, "a", "first.%d" % i))
    x.tofile(os.path.join(base, "b", "first.%d" % i))
    (x + rng.normal(0.0, 1e-3, size=x.shape).astype("float32")).tofile(os.path.join(base, "c", "first.%d" % i))
print("wrote 3x3 synthetic dumps")
