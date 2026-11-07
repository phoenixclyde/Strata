# 细看 0.1.40.2 -> 0.1.40.4 里与 HIP/gfx906 可能相关的内核改动
import zipfile, os, difflib, io

TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_kernel_diff.txt"

FILES = [
    "src/kernels/cuda/native_bf16.cu",
    "src/kernels/cuda/native_mmvq.cu",
    "src/kernels/native_multi_parity.cpp",
    "include/strata/kernels/pdl.hpp",
    "src/program/generate.cpp",
    "src/core/mtp.cpp",
    "docker-entrypoint.sh",
]

def rd(zp, tag, rel):
    with zipfile.ZipFile(os.path.join(TR, zp)) as z:
        return z.read("Strata-%s/%s" % (tag, rel)).decode("utf-8", "replace")

rep = io.StringIO()
for rel in FILES:
    a = rd("strata-src-0.1.40.2.zip", "0.1.40.2", rel)
    b = rd("strata-src-0.1.40.4.zip", "0.1.40.4", rel)
    la, lb = a.splitlines(), b.splitlines()
    d = list(difflib.unified_diff(la, lb, lineterm="", n=6,
                                  fromfile="0.1.40.2/" + rel, tofile="0.1.40.4/" + rel))
    rep.write("=" * 100 + "\n# %s  (+%d/-%d lines)\n" % (rel, sum(1 for x in d if x.startswith("+") and not x.startswith("+++")), sum(1 for x in d if x.startswith("-") and not x.startswith("---"))))
    rep.write("\n".join(d) + "\n\n")

txt = rep.getvalue()
open(OUT, "w", encoding="utf-8").write(txt)
print("wrote", OUT, len(txt))
