import io, os, shutil, sys

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/kv_q8.cu"
OLD = "#if defined(STRATA_EXPERIMENTAL_SM60)\n    if (pre75_q8_gather()) {"
NEW = "#if defined(STRATA_EXPERIMENTAL_SM60) || defined(STRATA_HIP_GFX906)\n    if (pre75_q8_gather()) {"

if not os.path.isfile(P):
    print("FAIL: missing", P)
    sys.exit(2)

s = io.open(P, encoding="utf-8").read()
if NEW in s:
    print("SKIP: already patched")
    sys.exit(0)
if s.count(OLD) != 1:
    print("FAIL: anchor count =", s.count(OLD))
    sys.exit(3)

shutil.copy2(P, P + ".bak_w1037")
t = s.replace(OLD, NEW, 1)
assert NEW in t and t != s
with io.open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(t)
print("OK patched; backup =", P + ".bak_w1037")
