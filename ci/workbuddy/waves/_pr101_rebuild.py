import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

print("=== [1] 传更新后的两个文件 ===")
for lp, rp in [(r"D:/strata166/docker/patch_gfx906_402.py",
                "/home/albus/strata166/build-ctx-402/patch_gfx906_402.py"),
               (r"D:/strata166/docker/Dockerfile-0.1.40.2",
                "/home/albus/strata166/build-ctx-402/Dockerfile-0.1.40.2")]:
    ok, size, md5, det = _sshutil.push_b64(lp, rp)
    print("  %-32s ok=%s size=%s md5=%s" % (lp.split("/")[-1], ok, size, md5))
    print("     " + det.strip().replace("\n", " | ")[:200])

print()
print("=== [2] 重建镜像（后台）+ 观察 ===")
rc, out, err = _sshutil.run_remote(r'''
CTX=/home/albus/strata166/build-ctx-402
LOG=/home/albus/strata166/logs/build-402b.log
rm -f "$LOG"
cd "$CTX"
setsid nohup docker build -f Dockerfile-0.1.40.2 -t strata-gfx906:0.1.40.2 . > "$LOG" 2>&1 < /dev/null &
sleep 120
echo "--- 进程 ---"
pgrep -af 'docker build' >/dev/null && echo BUILD_RUNNING || echo BUILD_FINISHED
echo "--- 补丁步骤输出 ---"
sed -n '/gfx906 构建补丁 v3/,/PATCH_V3_OK/p' "$LOG" | head -30
echo "--- 复核 grep 段 ---"
sed -n '/复核改动处/,/STRATA_Q6K_EXPERTS OR/p' "$LOG" | head -20
echo "--- 编译进度 ---"
grep -oE '\[[0-9]+/[0-9]+\]' "$LOG" | tail -1
echo "--- 尾部 8 行 ---"
tail -8 "$LOG"
''', timeout=560, host=HOST)
print("rc =", rc)
print(out)
if err.strip():
    print("--- STDERR ---")
    print(err[:1200])
