#!/usr/bin/env python3
import glob
import sys

sys.path.insert(0, "/llama.cpp/gguf-py")
import gguf  # noqa: E402

files = sorted(glob.glob("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/*.gguf"))
print("shards", len(files))
pat = {}
for p in files:
    r = gguf.GGUFReader(p)
    for t in r.tensors:
        if "ssm" not in t.name and "gdn" not in t.name:
            continue
        key = t.name
        for i in range(64):
            key = key.replace(".%d." % i, ".N.")
        if key not in pat:
            pat[key] = (0, str(t.tensor_type), tuple(int(x) for x in t.shape))
        n, ty, sh = pat[key]
        pat[key] = (n + 1, ty, sh)
print("=== ssm/gdn tensor families (count, ggml_type, shape) ===")
for k, (n, ty, sh) in sorted(pat.items()):
    print("%-46s %3d %-10s %s" % (k, n, ty, sh))
