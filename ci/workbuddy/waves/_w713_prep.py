# v0.1.41 本地取证：下载 + sha256 + 全树比对(对 0.1.40.4) + 补丁面 dry-run + LLAMA_CPP_COMMIT
import urllib.request, os, hashlib, zipfile, time, re, shutil, subprocess, sys, io

TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"
TMP = r"D:/workbuddy_space/strata_ws/deploy/tmp"
PY = r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe"

op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
op.addheaders = [("User-Agent", "curl/8.0")]

out = os.path.join(TR, "strata-src-0.1.41.zip")
if not (os.path.exists(out) and os.path.getsize(out) > 1_000_000):
    url = "https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/tags/v0.1.41.zip"
    t0 = time.time(); n = 0
    with op.open(url, timeout=300) as r, open(out, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b: break
            f.write(b); n += len(b)
    print("downloaded %d bytes in %.1fs (%.2f MB/s)" % (n, time.time()-t0, n/(time.time()-t0)/1e6))
else:
    print("exists", os.path.getsize(out))
sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
print("sha256 v0.1.41 =", sha)

# 解包
dst = os.path.join(TMP, "src411")
inner = os.path.join(dst, "Strata-0.1.41")
if not os.path.isdir(inner):
    os.makedirs(dst, exist_ok=True)
    with zipfile.ZipFile(out) as z:
        z.extractall(dst)
    print("extracted ->", inner)

# 与 0.1.40.4 全树比对（两边都用 zip 原件）
def idx(zp, tag):
    d = {}
    with zipfile.ZipFile(zp) as z:
        for nm in z.namelist():
            if nm.endswith("/"): continue
            rel = nm.split("/", 1)[1] if "/" in nm else nm
            with z.open(nm) as f:
                d[rel] = hashlib.md5(f.read()).hexdigest()
    return d

a = idx(os.path.join(TR, "strata-src-0.1.40.4.zip"), "0.1.40.4")
b = idx(out, "0.1.41")
only_a = sorted(set(a) - set(b)); only_b = sorted(set(b) - set(a))
chg = sorted(k for k in set(a) & set(b) if a[k] != b[k])
print("files %d -> %d ; only_old=%d only_new=%d changed=%d" % (len(a), len(b), len(only_a), len(only_b), len(chg)))
rep = ["== only in 0.1.40.4 =="] + ["  " + x for x in only_a] + \
      ["== only in 0.1.41 =="] + ["  " + x for x in only_b] + \
      ["== changed =="] + ["  " + x for x in chg]
io.open(os.path.join(TMP, "_w713_tree_diff.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(rep) + "\n")
print("\n".join(rep[:60]))

# 关键常量
for tag, base in [("0.1.40.4", os.path.join(TMP, "src404", "Strata-0.1.40.4")), ("0.1.41", inner)]:
    sp = os.path.join(base, "setup.py")
    t = io.open(sp, encoding="utf-8", errors="replace").read()
    m = re.search(r"LLAMA_CPP_COMMIT\s*=\s*[\"']([0-9a-f]+)", t)
    v = re.search(r"project\(strata VERSION ([0-9.]+)", io.open(os.path.join(base, "CMakeLists.txt"), encoding="utf-8", errors="replace").read())
    print("%-9s LLAMA_CPP_COMMIT=%s CMake VERSION=%s" % (tag, m.group(1) if m else "?", v.group(1) if v else "?"))

# 补丁面 dry-run（对 pristine 0.1.41 树的副本）
dry = os.path.join(TMP, "_w713_dry411")
if os.path.isdir(dry): shutil.rmtree(dry)
shutil.copytree(inner, dry)
r = subprocess.run([PY, "-u", r"D:/workbuddy_space/strata_ws/deploy/docker/patch_gfx906_402.py", "--root", dry],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("---- patcher dry-run on 0.1.41 (run1) rc=%d ----" % r.returncode)
print(r.stdout)
io.open(os.path.join(TMP, "_w713_dry411_run1.txt"), "w", encoding="utf-8", newline="\n").write(r.stdout or "")
r2 = subprocess.run([PY, "-u", r"D:/workbuddy_space/strata_ws/deploy/docker/patch_gfx906_402.py", "--root", dry],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
print("---- run2 (幂等) rc=%d ----" % r2.returncode)
print(r2.stdout[-500:])
