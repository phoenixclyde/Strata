import sys
sys.path.insert(0, "D:/workbuddy/_z_rk80")
import _sshutil

HOST = "192.168.50.166"

print("=== [0] 传 unit 到 /tmp ===")
ok, size, md5, det = _sshutil.push_b64(
    r"D:/strata166/systemd/strata166.service", "/tmp/strata166.service")
print("  ok=%s size=%s md5=%s" % (ok, size, md5))
print("  " + det.strip().replace("\n", " | ")[:220])

print()
print("=== [1] pillow 对照（0.1.40.1 vs 0.1.40.2）===")
rc, out, err = _sshutil.run_remote(r'''
for IMG in strata-gfx906:0.1.40.1 strata-gfx906:0.1.40.2; do
  echo -n "  $IMG : "
  docker run --rm --entrypoint bash "$IMG" -c 'python3 -c "import PIL, pillow; print(pillow.__version__)" 2>&1 | tail -1' 2>&1 | tail -1
done
echo
echo "--- 0.1.40.2 已装的顶层包（前 30）---"
docker run --rm --entrypoint bash strata-gfx906:0.1.40.2 -c 'python3 -m pip list --format=freeze 2>/dev/null | head -30' 2>&1
echo
echo "--- serve/server.py 是否 import PIL / pillow ---"
docker run --rm --entrypoint bash strata-gfx906:0.1.40.2 -c 'grep -nE "^ *(import|from) +(PIL|pillow)" /src/serve/*.py /src/tools/*.py 2>/dev/null | head -10; echo "(空即未 import)"' 2>&1
''', timeout=300, host=HOST)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:800])

print()
print("=== [2] 备份旧容器配置 ===")
rc, out, err = _sshutil.run_remote(r'''
mkdir -p /home/albus/strata166/logs
docker inspect strata166-401 > /home/albus/strata166/logs/inspect-401-backup.json 2>&1
ls -l /home/albus/strata166/logs/inspect-401-backup.json
# 同时落一份可读的启动方式备忘
docker inspect strata166-401 --format '{{.Config.Image}}' > /home/albus/strata166/logs/old-container-image.txt
echo "backup ok"
''', timeout=180, host=HOST)
print(out)
if err.strip():
    print("--- STDERR ---"); print(err[:800])
