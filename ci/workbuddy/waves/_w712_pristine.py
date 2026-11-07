# 直接读 zip 原件（pristine，不经任何本地解包/patch）比对 H5 锚点
import zipfile, os, io, re, difflib

TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"
TMP = r"D:/workbuddy_space/strata_ws/deploy/tmp"

def from_zip(zp, inner):
    with zipfile.ZipFile(os.path.join(TR, zp)) as z:
        return z.read(inner).decode("utf-8", "replace"), z.namelist()

def cmk(tag, zp):
    t, names = from_zip(zp, "Strata-%s/CMakeLists.txt" % tag)
    return t

def region(t, pat="STRATA_MMQ_KQUANTS"):
    ls = t.splitlines()
    for i, l in enumerate(ls):
        if "q6_k" in l and "list(APPEND _strata_mmq_cuda_types q6_k)" in l:
            return "\n".join(ls[max(0, i-4):i+3])
    return "(q6_k append not found)"

for tag, zp in [("0.1.40.2", "strata-src-0.1.40.2.zip"),
                ("0.1.40.3", "strata-src-0.1.40.3.zip"),
                ("0.1.40.4", "strata-src-0.1.40.4.zip")]:
    t = cmk(tag, zp)
    print("=" * 90)
    print(tag, "pristine CMakeLists q6_k region:")
    print(region(t))

# 同时看两版 hip 头是否 pristine 一致（zip 内）
for tag, zp in [("0.1.40.2", "strata-src-0.1.40.2.zip"), ("0.1.40.4", "strata-src-0.1.40.4.zip")]:
    t, names = from_zip(zp, "Strata-%s/include/strata/platform/hip_compat/strata_hip.h" % tag)
    has_blocking = "cudaEventBlockingSync" in t
    has_inline_func = "inline hipError_t cudaFuncSetAttribute" in t
    print("=" * 90)
    print(tag, "strata_hip.h: cudaEventBlockingSync=", has_blocking, " template-inline cudaFuncSetAttribute=", has_inline_func, " len=", len(t))
