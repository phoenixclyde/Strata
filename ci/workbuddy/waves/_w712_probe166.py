# 166 现场：build-ctx-402 内容 / -402 容器完整 run 配置 / 磁盘与镜像
import subprocess, base64, time

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_probe166.out.txt"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

remote = r"""
set -u
echo "== build-ctx-402 =="
ls -l /home/albus/strata166/build-ctx-402/ 2>&1 | head -20
echo "== images =="
docker images --format '{{.Repository}}:{{.Tag}} | {{.ID}} | {{.Size}} | {{.CreatedAt}}' | grep -i strata
echo "== container -402 run config =="
docker inspect strata166-402 --format '{{json .HostConfig.Binds}}'
docker inspect strata166-402 --format '{{json .HostConfig.Devices}}'
docker inspect strata166-402 --format '{{json .HostConfig.PortBindings}}'
docker inspect strata166-402 --format '{{json .Config.Env}}'
docker inspect strata166-402 --format '{{json .Config.Cmd}}'
docker inspect strata166-402 --format 'Image={{.Config.Image}} Net={{.HostConfig.NetworkMode}} IPC={{.HostConfig.IpcMode}} Ulimits={{json .HostConfig.Ulimits}} GroupAdd={{json .HostConfig.GroupAdd}} RAS={{json .HostConfig.RestartPolicy}}'
echo "== disk / docker root =="
df -h / /var/lib/docker 2>/dev/null | tail -n 3
echo "== 166 free RAM =="
free -g | head -2
echo DONE
"""
assert "\r" not in remote
b64 = base64.b64encode(remote.encode("utf-8")).decode("ascii")
p = subprocess.run(
    ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
     "albus@192.168.50.166", "base64 -d | bash"],
    input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=120)
log("ssh rc=%d" % p.returncode)
out = p.stdout.decode("utf-8", "replace")
out = "".join(ch if ch == "\n" or 32 <= ord(ch) < 127 else "." for ch in out)
f.write(out + "\n")
if p.stderr:
    f.write("STDERR:\n" + p.stderr.decode("utf-8", "replace") + "\n")
f.close()
assert p.returncode == 0
