import os, sys, shutil, zipfile, hashlib, subprocess

ZIP = r"D:/strata166/transfer/strata-src-0.1.40.2.zip"
TMP = r"D:/strata166/tmp/src402b"
PATCHER = r"D:/strata166/docker/patch_gfx906_402.py"

if os.path.isdir(TMP):
    shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(TMP)
inner = [d for d in os.listdir(TMP) if os.path.isdir(os.path.join(TMP, d))]
SRC = os.path.join(TMP, inner[0])
print("干净树 =", SRC)

KEYS = ["include/strata/platform/hip_compat/strata_hip.h",
        "src/kernels/cuda/fused_gr.cu", "src/core/mtp.cpp", "src/core/vmm.cpp",
        "CMakeLists.txt", "src/prefill/prefill.cpp"]

for run in (1, 2):
    print()
    print("################ 第 %d 遍 ################" % run)
    r = subprocess.run([sys.executable, PATCHER, "--root", SRC],
                       capture_output=True, timeout=300)
    print("rc =", r.returncode)
    print(r.stdout.decode("utf-8", "replace"))
    if r.stderr.strip():
        print("STDERR:", r.stderr.decode("utf-8", "replace")[:600])
    print("--- 关键文件 md5 ---")
    for k in KEYS:
        p = os.path.join(SRC, k)
        if os.path.isfile(p):
            print("   %-56s %s" % (k, hashlib.md5(open(p, "rb").read()).hexdigest()[:16]))

print()
print("=== 打完后核对两处目标形态 ===")
h = open(os.path.join(SRC, "include/strata/platform/hip_compat/strata_hip.h"),
         encoding="utf-8").read()
cm = open(os.path.join(SRC, "CMakeLists.txt"), encoding="utf-8").read()
print("  H6  cudaEventBlockingSync 映射存在 =", "#define cudaEventBlockingSync hipEventBlockingSync" in h)
print("  H5  q6_k 门含 OR STRATA_HIP_GFX906 =", "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906" in cm)
print("  H1  cudaFuncSetAttribute 模板函数存在 =", "inline hipError_t cudaFuncSetAttribute" in h)
