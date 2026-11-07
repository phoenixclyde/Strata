import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
echo "===== [1] 新镜像 ====="
docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}' | grep -i 'strata-gfx906'
echo
echo "===== [2] 镜像内自证（不占 GPU）====="
docker run --rm --entrypoint bash strata-gfx906:0.1.40.2 -c '
echo "--- 引擎二进制 ---"
ls -l /src/build-906/strata
echo "--- 版本（CMakeLists project VERSION）---"
grep -m1 "project(strata VERSION" /src/CMakeLists.txt
echo "--- 补丁落点复核（H1/H5/H6）---"
grep -n "inline hipError_t cudaFuncSetAttribute" /src/include/strata/platform/hip_compat/strata_hip.h
grep -n "define cudaEventBlockingSync hipEventBlockingSync" /src/include/strata/platform/hip_compat/strata_hip.h
grep -n "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906" /src/CMakeLists.txt
echo "--- 源码自带 /src/data ---"
ls -l /src/data/expert-profile.bin /src/data/draft_vocab.bin 2>&1
echo "--- python 依赖 ---"
python3 -c "import numpy,jinja2,psutil,regex,yaml,tqdm,requests,pillow; print(\"py deps ok\")"
echo "--- serve 入口 ---"
ls -l /src/serve/server.py
' 2>&1

echo
echo "===== [3] 引擎 --help（看是否可执行）====="
docker run --rm --entrypoint bash strata-gfx906:0.1.40.2 -c '/src/build-906/strata --help 2>&1 | head -6' 2>&1

echo
echo "===== [4] 磁盘 ====="
docker system df 2>&1 | head -6
df -h / | tail -1
''', timeout=420, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
