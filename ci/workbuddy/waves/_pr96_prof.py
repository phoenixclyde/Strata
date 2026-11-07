import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

rc, out, err = _sshutil.run_remote(r'''
echo "===== [1] 构建进度 ====="
pgrep -af 'docker build' >/dev/null && echo "BUILD_RUNNING" || echo "BUILD_DONE_OR_DEAD"
grep -oE '\[[0-9]+/[0-9]+\]' /home/albus/strata166/logs/build-402.log | tail -1
tail -3 /home/albus/strata166/logs/build-402.log

echo
echo "===== [2] expert-profile 在哪（容器可写层 or 挂载卷）====="
docker exec strata166-401 bash -lc 'ls -la /src/data/ 2>&1 | head -10; echo "---"; ls -la /src/data/expert-profile.bin 2>&1' 2>&1

echo
echo "===== [3] /data 里的配置与目录 ====="
docker exec strata166-401 bash -lc 'cat /data/strata-ud-iq4_xs.json' 2>&1
echo "--- /data/packs, /data/mtp ---"
docker exec strata166-401 bash -lc 'ls -la /data/packs/ 2>&1; echo ---; ls -la /data/mtp/ 2>&1 | head -8' 2>&1

echo
echo "===== [4] 宿主侧 weights / data ====="
ls -la /home/albus/strata166/weights/ 2>&1 | head -10
echo "--- data 目录大小 ---"
du -sh /home/albus/strata166/data /home/albus/strata166/weights 2>&1
echo "--- 镜像里有没有 /src/data/expert-profile.bin（新镜像会没有）---"
docker run --rm --entrypoint bash strata-gfx906:0.1.40.1 -c 'ls -la /src/data/ 2>&1 | head -6' 2>&1 | head -8

echo
echo "===== [5] 现有 0.1.40.1 镜像的 /src 里是否有运行期生成物 ====="
docker run --rm --entrypoint bash strata-gfx906:0.1.40.1 -c 'du -sh /src 2>/dev/null; ls /src | head -20' 2>&1 | head -25
''', timeout=300, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
