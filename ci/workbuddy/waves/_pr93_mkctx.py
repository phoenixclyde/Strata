import sys, hashlib
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

print("=== [0] 本机 zip 的 sha256（与 166 下载的对比）===")
b = open(r"D:/strata166/transfer/strata-src-0.1.40.2.zip", "rb").read()
print("  local  size=%d  sha256=%s" % (len(b), hashlib.sha256(b).hexdigest()))
print("  remote size=18570716  sha256=7d595d4ae04b1e163ddd642c5e307d1931b17c36c26a267be0c201f90173383b")

print()
print("=== [1] build-ctx-401 结构 ===")
rc, out, err = _sshutil.run_remote(
    'find /home/albus/strata166/build-ctx-401 -maxdepth 3 | head -30; '
    'echo "--- strata166 根 ---"; ls -la /home/albus/strata166 | head -20',
    timeout=120, host=HOST)
print(out)

print()
print("=== [2] 建 build-ctx-402 ===")
rc, out, err = _sshutil.run_remote(r'''
set -e
CTX=/home/albus/strata166/build-ctx-402
rm -rf "$CTX"
mkdir -p "$CTX/docker" "$CTX/transfer"
# 166 已下好的源码 zip
mv /tmp/strata-src-0.1.40.2.zip "$CTX/transfer/"
# 复用同一份 llama.cpp（LLAMA_CPP_COMMIT 相同）
cp /home/albus/strata166/build-ctx-401/transfer/llama.cpp-3cf0325.tar.gz "$CTX/transfer/"
echo "--- ctx 内容 ---"
ls -la "$CTX" "$CTX/transfer"
echo -n "zip sha256 = "; sha256sum "$CTX/transfer/strata-src-0.1.40.2.zip" | cut -d' ' -f1
''', timeout=300, host=HOST)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:800])

print()
print("=== [3] 传 patch_gfx906_402.py 与 Dockerfile-0.1.40.2 ===")
for lp, rp in [(r"D:/strata166/docker/patch_gfx906_402.py",
                "/home/albus/strata166/build-ctx-402/patch_gfx906_402.py"),
               (r"D:/strata166/docker/Dockerfile-0.1.40.2",
                "/home/albus/strata166/build-ctx-402/Dockerfile-0.1.40.2")]:
    ok, size, md5, det = _sshutil.push_b64(lp, rp)
    print("  %-34s ok=%s size=%s md5=%s" % (lp.split("/")[-1], ok, size, md5))
    print("     " + det.strip().replace("\n", " | ")[:220])

print()
print("=== [4] 复核 ctx 就位 ===")
rc, out, err = _sshutil.run_remote(r'''
CTX=/home/albus/strata166/build-ctx-402
ls -la "$CTX" "$CTX/transfer" "$CTX/docker"
echo "--- patch 语法自检（本机跑一遍 dry-run 需要源码树，这里只做 py_compile）---"
python3 -m py_compile "$CTX/patch_gfx906_402.py" && echo "PY_COMPILE_OK"
''', timeout=180, host=HOST)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:800])
