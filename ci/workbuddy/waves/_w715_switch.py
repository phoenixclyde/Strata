# W715：切换现役容器 -406(base) -> -407(huihui)；先 create 再 stop 旧再 start，轮询就绪
import base64, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
LOG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"


def run(sc, t=900):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(sc.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


CREATE = r'''set -u
if docker inspect strata166-407 >/dev/null 2>&1; then
  echo "(-407 已存在，先移除)"; docker rm -f strata166-407 || true
fi
docker create --name strata166-407 --restart unless-stopped \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --ipc=host --ulimit memlock=-1 \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  -p 8090:8090 \
  -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  strata-gfx906:0.1.41 \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090'
docker inspect strata166-407 --format 'created: image={{.Config.Image}} binds={{json .HostConfig.Binds}} ports={{json .HostConfig.PortBindings}}'
'''

print("===== 1) 建新容器 -407 =====")
rc, out, err = run(CREATE, 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])
if "created:" not in out:
    raise SystemExit("建容器失败，放弃切换")

print("===== 2) 停旧容器 -406（保留不删，供回滚）=====")
rc, out, err = run("docker stop -t 60 strata166-406; docker ps -a --filter name=strata166-40 --format '{{.Names}} {{.Status}}'", 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("===== 3) 启动 -407 =====")
rc, out, err = run("docker start strata166-407; sleep 2; docker ps --filter name=strata166 --format '{{.Names}} {{.Status}} {{.Ports}}'", 300)
print(out)

print("===== 4) 轮询就绪（<=600 s，看 'session is up'）=====")
t0 = time.time()
ready = False
while time.time() - t0 < 600:
    time.sleep(15)
    rc, out, err = run("grep -c 'session is up' %s 2>/dev/null || true" % LOG, 120)
    n = out.strip()
    rc2, out2, _ = run("tail -c 300 %s 2>/dev/null" % LOG, 120)
    print("[%4.0fs] 'session is up' x%s | tail: %s" % (time.time() - t0, n, out2.strip().replace("\n", " | ")[-200:]))
    if n.isdigit() and int(n) > 0:
        ready = True
        break
print("就绪 =", ready, " 用时 %.0fs" % (time.time() - t0))

print("===== 5) 状态与关键日志 =====")
rc, out, err = run("docker ps -a --filter name=strata166 --format '{{.Names}} | {{.Status}}'\n"
                   "echo '--- PLE / vision / MTP 相关 ---'\n"
                   "grep -nE 'PLE on|vision|draft layer loaded|engine started' %s | head -12" % LOG, 300)
print(out)
