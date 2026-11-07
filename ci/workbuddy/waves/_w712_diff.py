# 解包 0.1.40.4 / 0.1.40.3，并做补丁面文件级 diff（对照 0.1.40.2）
import zipfile, os, difflib, hashlib, io

TMP = r"D:/workbuddy_space/strata_ws/deploy/tmp"
TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"

for tag, dd in [("0.1.40.4", "src404"), ("0.1.40.3", "src403")]:
    zp = os.path.join(TR, "strata-src-%s.zip" % tag)
    dst = os.path.join(TMP, dd)
    if not os.path.isdir(os.path.join(dst, "Strata-%s" % tag)):
        with zipfile.ZipFile(zp) as z:
            z.extractall(dst)
        print("extracted", tag, "->", dst)
    else:
        print("already extracted", tag)

def root(dd, tag):
    return os.path.join(TMP, dd, "Strata-%s" % tag)

A = root("src402", "0.1.40.2")
B = root("src404", "0.1.40.4")
print("A exists", os.path.isdir(A), "B exists", os.path.isdir(B))

FILES = [
    "CMakeLists.txt",
    "setup.py",
    "include/strata/platform/hip_compat/strata_hip.h",
    "include/strata/hip_compat/cuda_runtime.h",
    "src/kernels/cuda/fused_gr.cu",
    "src/core/mtp.cpp",
    "src/core/vmm.cpp",
    "src/prefill/prefill.cpp",
    "src/prefill/moe_mmq.cu",
    "src/core/expert_cache.cpp",
]

def rd(p):
    with open(p, "rb") as f:
        return f.read()

rep = io.StringIO()
for rel in FILES:
    pa, pb = os.path.join(A, rel.replace("/", os.sep)), os.path.join(B, rel.replace("/", os.sep))
    ea, eb = os.path.exists(pa), os.path.exists(pb)
    if not eb:
        rep.write("### %s : MISSING in 0.1.40.4 (was exists=%s)\n" % (rel, ea)); continue
    da, db = rd(pa) if ea else b"", rd(pb)
    ha = hashlib.md5(da).hexdigest()[:12] if ea else "-"
    hb = hashlib.md5(db).hexdigest()[:12]
    same = (da == db)
    rep.write("### %s : %s  md5 %s -> %s  bytes %d -> %d\n" % (rel, "SAME" if same else "**DIFF**", ha, hb, len(da), len(db)))
    if not same and ea:
        la = da.decode("utf-8", "replace").splitlines()
        lb = db.decode("utf-8", "replace").splitlines()
        d = list(difflib.unified_diff(la, lb, lineterm="", n=3,
                                      fromfile="0.1.40.2/" + rel, tofile="0.1.40.4/" + rel))
        if len(d) > 400:
            rep.write("\n".join(d[:400]) + "\n...[truncated %d more lines]\n" % (len(d) - 400))
        else:
            rep.write("\n".join(d) + "\n")
    rep.write("\n")

txt = rep.getvalue()
out = os.path.join(TMP, "_w712_diff_402_404.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write(txt)
print("wrote", out, len(txt), "chars")

# 关键常量
import re
for lbl, base in [("0.1.40.2", A), ("0.1.40.4", B)]:
    sp = os.path.join(base, "setup.py")
    t = open(sp, encoding="utf-8", errors="replace").read()
    m = re.search(r"LLAMA_CPP_COMMIT\s*=\s*[\"']([0-9a-f]+)", t)
    v = re.search(r"project\(strata VERSION ([0-9.]+)", open(os.path.join(base, "CMakeLists.txt"), encoding="utf-8", errors="replace").read())
    print(lbl, "LLAMA_CPP_COMMIT=", m.group(1) if m else "?", " CMake VERSION=", v.group(1) if v else "?")
